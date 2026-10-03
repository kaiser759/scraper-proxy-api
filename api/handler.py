import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

app = FastAPI(
    title="Scraper Proxy API",
    version="1.0.0",
    description="Simple serverless proxy API for fetching web pages and returning structured metadata.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    url: str = Field(..., description="The target URL to fetch.")
    method: str = Field(default="GET", description="HTTP method to use.")
    headers: Dict[str, str] = Field(default_factory=dict, description="Custom request headers.")
    timeout: int = Field(default=30, ge=5, le=120, description="Request timeout in seconds.")
    follow_redirects: bool = Field(default=True, description="Follow HTTP redirects.")
    output: str = Field(default="json", description="Response format: json or text.")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("URL must use http:// or https:// and include a hostname.")
        return value

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        method = value.upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}:
            raise ValueError("Unsupported HTTP method.")
        return method


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    excluded = {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
    }
    clean: Dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() not in excluded:
            clean[key] = value
    return clean


def extract_title(html_text: str) -> Optional[str]:
    match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
    if match:
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        return title
    return None


def extract_links(html_text: str) -> list[str]:
    return re.findall(r"href=[\\\"']([^\\\"']+)[\\\"']", html_text, flags=re.IGNORECASE)


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "name": "Scraper Proxy API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "fetch": "/api/fetch",
        "description": "Fetch a URL and return its headers, metadata, and content.",
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/fetch")
async def fetch_get(
    url: str = Query(..., description="The target URL to fetch."),
    method: str = Query(default="GET"),
    timeout: int = Query(default=30, ge=5, le=120),
    follow_redirects: bool = Query(default=True),
    output: str = Query(default="json"),
    headers: Optional[str] = Query(default=None, description="Optional JSON string of custom headers."),
) -> Dict[str, Any]:
    request_headers = {}
    if headers:
        try:
            import json
            request_headers = json.loads(headers)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid headers JSON: {exc}") from exc

    payload = ScrapeRequest(
        url=url,
        method=method,
        timeout=timeout,
        follow_redirects=follow_redirects,
        headers=request_headers,
        output=output,
    )
    return await fetch_url(payload)


@app.post("/api/fetch")
async def fetch_post(payload: ScrapeRequest) -> Dict[str, Any]:
    return await fetch_url(payload)


async def fetch_url(payload: ScrapeRequest) -> Dict[str, Any]:
    target_url = payload.url
    method = payload.method.upper()
    headers = sanitize_headers(payload.headers)

    try:
        async with httpx.AsyncClient(timeout=payload.timeout, follow_redirects=payload.follow_redirects) as client:
            response = await client.request(method, target_url, headers=headers)
            content_type = response.headers.get("content-type", "")
            text = response.text

            result: Dict[str, Any] = {
                "ok": response.is_success,
                "url": str(response.url),
                "status_code": response.status_code,
                "content_type": content_type,
                "headers": {k: v for k, v in response.headers.items() if k.lower() not in {"set-cookie", "cookie"}},
                "final_url": str(response.url),
                "title": extract_title(text),
                "links": extract_links(text)[:50],
                "method": method,
            }

            if "application/json" in content_type.lower():
                try:
                    result["json"] = response.json()
                except Exception:
                    result["raw"] = text
            else:
                result["text"] = text
                result["body_length"] = len(text)

            if payload.output == "text":
                return {"text": text, "status_code": response.status_code, "final_url": str(response.url)}

            return result
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Proxy request failed: {exc}") from exc

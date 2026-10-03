# Scraper Proxy API

A lightweight Python API for Vercel that proxies HTTP requests to arbitrary web pages and returns the response content plus metadata.

## Features

- Fetch any public `http://` or `https://` page
- Supports GET, POST, PUT, PATCH, DELETE, and HEAD
- Returns status code, final URL, headers, title, and extracted links
- Works as a serverless function on Vercel

## Deploy to Vercel

1. Push this project to GitHub
2. Import the repo in Vercel
3. Use the default Python settings
4. Deploy

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.handler:app --reload --port 8000
```

## API examples

### Health check

```bash
curl https://your-project.vercel.app/health
```

### Fetch a page

```bash
curl "https://your-project.vercel.app/api/fetch?url=https://example.com"
```

### Fetch with custom headers

```bash
curl -X POST https://your-project.vercel.app/api/fetch \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "method": "GET",
    "headers": {"User-Agent": "Mozilla/5.0"},
    "timeout": 30
  }'
```

## Response shape

```json
{
  "ok": true,
  "url": "https://example.com",
  "status_code": 200,
  "content_type": "text/html; charset=UTF-8",
  "headers": {},
  "final_url": "https://example.com",
  "title": "Example Domain",
  "links": ["https://www.iana.org/domains/example"],
  "method": "GET",
  "text": "<html>...</html>"
}
```

## API Routes

- `GET /` - Root info endpoint
- `GET /health` - Health check
- `GET /api/fetch?url=<url>` - Fetch URL via GET
- `POST /api/fetch` - Fetch URL via POST with JSON body

## Notes

- Some websites block automated traffic or require JavaScript rendering.
- For a production-grade scraper, consider adding browser automation, rate limiting, and caching.

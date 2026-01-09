# 1_extract.md — Unqork Docs: Sitemap-first Discovery (EXTRACT ONLY)

## Goal
Stop false “gated/blocked” findings caused by URL guessing. Build a deterministic discovery set using **sitemaps**, then fetch and extract content only from real discovered doc URLs on `docs.unqork.io`.

## Non-negotiables
- **NO URL guessing** (no wildcards like `/docs/*`, no slug generation, no directory probing).
- **Never label “gated/blocked” based on 404 or “valid HTML.”**
- Record **HTTP status**, **final URL after redirects**, and **content-type** for every fetch.
- Primary target domain: `docs.unqork.io` (ignore marketing pages unless explicitly allowed).

## Inputs
- Existing crawler/extractor codebase (wherever current rules/processes live).
- Current output JSON shape (the report that currently includes `gated_content`).

## Step 1 — Discover sitemap locations
Fetch in this order:
1) `https://docs.unqork.io/robots.txt`  
   - Parse `Sitemap:` lines (one or many).
2) If none found, probe common sitemap endpoints (GET or HEAD+GET on 200):
   - `https://docs.unqork.io/sitemap.xml`
   - `https://docs.unqork.io/sitemap-index.xml`
   - `https://docs.unqork.io/sitemap_index.xml`
   - `https://docs.unqork.io/sitemaps.xml`
   - `https://docs.unqork.io/sitemap/`

A response counts as a sitemap only if:
- status is **200**, and
- content-type contains **xml** OR body contains `<urlset` or `<sitemapindex`.

If response is HTML, treat it as NOT_A_SITEMAP (often soft-404).

## Step 2 — Parse sitemap(s) into discovered URL set
Handle both forms:
- `<urlset>`: collect each `<url><loc>...</loc></url>`
- `<sitemapindex>`: collect each `<sitemap><loc>...</loc></sitemap>` and recursively fetch/parse.

Normalize and filter URLs:
- Keep only:
  - `https://docs.unqork.io/` (optional)
  - `https://docs.unqork.io/docs/<slug>` where `<slug>` matches `[a-z0-9-]+`
- Drop:
  - `/search`, `/tag`, `/tags` and similar
  - external domains
  - duplicates after normalization (strip trailing slash; decode consistently)

Persist:
- `discovery.discovered_urls[]`
- `discovery.sitemaps_used[]`
- `discovery.discovered_count`

## Step 3 — Fetch each discovered page (HTML-only is fine)
For each discovered URL:
- Fetch with sane headers (User-Agent), follow redirects, retry on transient errors.
- Record:
  - `status_code`
  - `final_url`
  - `content_type`
  - `fetched_at`

Do NOT attempt screenshots as proof of UI unless you actually render and analyze images.

## Step 4 — Extract content
Extract at minimum:
- `<title>`
- main H1 (first `<h1>`)
- body text (cleaned)
- all internal links matching docs allow-regex (for optional incremental discovery)
- optional: metadata like “Updated on / Published on” if present

Store per-page extraction in:
- `pages[]: { url, final_url, status_code, content_type, title, h1, text, outbound_links[] }`

## Step 5 — Fallback if sitemaps are missing or tiny
If sitemap discovery fails OR discovered_count < 50:
- Seed crawl from:
  - `https://docs.unqork.io/`
  - `https://docs.unqork.io/docs/unqork-user-manual`
  - `https://docs.unqork.io/docs/how-to-guides`
  - `https://docs.unqork.io/docs/getting-started`
- Follow only links matching:
  - `^https://docs\.unqork\.io/docs/[a-z0-9\-]+/?$`
- Still: NO URL guessing.

## Output expectations
Update the run report to include:
- `discovery`: sitemaps used, discovered_count, discovered_urls sample
- `fetch_stats`: counts by status code
- `pages`: per-page extraction items
- Remove/stop writing the old “docs/* is gated” conclusion.

## Acceptance criteria
- The system no longer labels `docs.unqork.io/docs/*` as gated due to 404.
- Discovered URL set is sourced from sitemap(s) or link-follow fallback only.
- Every fetched page has recorded `status_code` and `final_url`.

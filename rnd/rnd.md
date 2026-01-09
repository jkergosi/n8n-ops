# rnd.md — Notes / Edge Cases / Debug Playbook (Unqork Docs Crawling)

## Why “valid HTML” misleads
A 404 page and many WAF/bot-challenge pages return perfectly valid HTML.
Therefore: HTML validity is not a signal. Status + page cues are.

## Practical debug checklist (use when results look wrong)
1) Pick 5 example URLs from each classification bucket.
2) For each URL, log:
   - requested URL
   - status_code
   - final_url
   - content-type
   - first 2KB of title/H1
   - first 5KB of body text
3) Verify:
   - NOT_FOUND: shows not-found cues OR status 404
   - AUTH_REQUIRED: 401/403 plus login cues
   - BLOCKED: 403 plus bot/WAF cues (captcha, cloudflare, “verify you are human”, etc.)
   - RATE_LIMITED: 429

## Incremental crawling
If sitemap(s) exist, store:
- sitemap URL(s)
- last successful fetch time
- (optional) per-URL `<lastmod>` when available
Then do incremental refreshes by re-reading sitemap and fetching only changed URLs.

## Link-follow fallback quality controls
When sitemap is absent:
- allow-regex strictly for docs slugs:
  - `^https://docs\.unqork\.io/docs/[a-z0-9\-]+/?$`
- deny `/search`, `/tags`, `/tag` pages
- forbid querystring crawling (unless explicitly needed)

## Anti-bot hygiene
- Concurrency low (1–3)
- Respect 429 backoff with exponential delays
- Stable User-Agent
- Avoid fetching the same URL rapidly

## Output contract recommendation
In the final JSON report, include:
- `discovery: { method, sitemaps_used[], discovered_count }`
- `fetch_stats: { by_status_code, by_classification }`
- `access_issues[]` with evidence fields
- `pages[]` with extracted content fields

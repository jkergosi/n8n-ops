# 2_reconcile.md — Unqork Docs: Correct “Gated/Blocked” Classification (RECONCILE)

## Goal
Fix reporting so “gated/blocked” is only used when there is hard evidence. Separate:
- NOT_FOUND (404/soft-404)
- AUTH_REQUIRED (login wall / 401 / 403 with auth cues)
- BLOCKED (bot challenge / WAF / repeated 403 without auth cues)
- RATE_LIMITED (429)
- OK (200 content)

## Replace the current gated_content logic
### Never infer gated from:
- 404 responses
- “Valid HTML” pages
- missing screenshots
Then: delete any rule that marks `docs.unqork.io/docs/*` as gated simply because guessed URLs 404.

## Page classification algorithm (deterministic)

### 1) Hard status-based classification
If `status_code` in:
- 401 → AUTH_REQUIRED
- 429 → RATE_LIMITED
- 5xx → SERVER_ERROR
- 404 → NOT_FOUND
- 403 → go to step 2 (needs disambiguation)

### 2) 403 disambiguation (AUTH_REQUIRED vs BLOCKED)
Inspect body (first ~200KB) for **auth-wall cues**:
- text contains (case-insensitive): `sign in`, `log in`, `password`, `username`, `SSO`, `SAML`, `Okta`, `Azure AD`,
  `you must be logged in`, `unauthorized`
- presence of HTML form inputs with `type="password"` or name/id suggesting login

If auth cues present:
- AUTH_REQUIRED
Else:
- BLOCKED

### 3) Soft-404 detection for 200 pages
If `status_code == 200`, still detect SOFT_404:
- title or first H1 matches: `\b(404|not\s+found|page\s+not\s+found)\b`
- body contains common not-found boilerplate

If soft-404 cues present:
- classify as NOT_FOUND (soft)

### 4) OK content determination
If none of the above:
- OK

## Reporting changes

### Replace `gated_content[]` with `access_issues[]`
Write entries like:
- `{ url, status_code, final_url, classification, evidence: { matched_terms: [], redirect_chain: [] } }`

Classifications:
- NOT_FOUND
- AUTH_REQUIRED
- BLOCKED
- RATE_LIMITED
- SERVER_ERROR

### Add a “why” section
Summarize counts and top evidence:
- `counts_by_classification`
- `top_blocked_signals` (e.g., “cloudflare”, “captcha”, etc.)
- `top_auth_signals` (e.g., “sign in”, “password”)

## Guarantees
- A URL is never marked AUTH_REQUIRED or BLOCKED unless:
  - status is 401/403/429, OR
  - body contains strong auth/bot signals.

## Acceptance criteria
- “Gated” is never emitted for 404 pages.
- “Blocked” is only emitted for repeated 403 without auth cues, or explicit bot-challenge markers.
- The run report clearly explains why each problematic URL is classified as it is.

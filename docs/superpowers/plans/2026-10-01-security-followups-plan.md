# Security Follow-ups (backend) - Plan

Start from `main` after `security-hardening-2026-09-28` is merged. New branch: `security-followups`.
Context: items deferred or only partly done in the 2026-09-28 hardening; see that plan and the final review.

## Phase 1 - small code fixes

- [ ] **1. CSRF Origin check** (`main.py`): middleware that returns 403 for POST/PUT/PATCH/DELETE when an `Origin` header is present and not in the CORS allowlist. No `Origin` header (curl, server-to-server) passes. Reuse the allowlist from `CORSMiddleware` (extract to a constant).
- [ ] **2. MP3 magic bytes** (`app/services/upload.py::_sniff_content_type`): accept `\xff\xfb`, `\xff\xfa`, `\xff\xf3`, `\xff\xf2` (MPEG audio frame syncs) in addition to `ID3`.

## Phase 2 - automated auth tests (pytest)

No test suite exists. Add `tests/` with a throwaway Mongo (`mongomock-motor`, or a temporary Mongo container) and FastAPI `TestClient`:
- [ ] login sets `access_token` + `refresh_token` as HttpOnly cookies
- [ ] a request authenticates with the Authorization header alone, the cookie alone, and header wins when both are sent
- [ ] `/logout` blacklists access AND refresh token; both then fail; cookies are cleared
- [ ] `/logout-all` rejects every token issued before it, but a login in the same second afterwards still works
- [ ] `/refresh` after logout-all returns 401; a suspended user cannot refresh
- [ ] admin: plain admin cannot change role/email/status (403); super admin can; invalid role -> 422
- [ ] Google callback: unverified email rejected; existing verified account gets `google_id` linked
- [ ] upload: spoofed Content-Type rejected; oversized rejected
- [ ] regex search with `(a+)+$` is escaped (property + admin + blog)

## Phase 3 - needs your decision

- [ ] **Cookie domain**: set `COOKIE_DOMAIN=.houzdey.com` in production only if the site and API are sibling subdomains and you want the frontend to read the cookie server-side. Required for a server-side admin gate (frontend plan item 2).

## Your side (not code)

- [ ] Rotate the old scraper key (still in git history). The scraper route/settings are already removed.
- [ ] Confirm the API host shares the site's registrable domain (e.g. `api.houzdey.com`), otherwise cookie login breaks.
- [ ] Run login / logout / logout-all against staging before the first deploy.

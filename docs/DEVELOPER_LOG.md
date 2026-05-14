# Developer Log — 2026-05-13

## Session Summary

Continued retrofitting Polly's legacy DID-based auth to OIDC-only with Tauri bridge signing. The thread can be traced in the conversation transcript.

## What Was Done

### OIDC Auth & Session Config (prior commits)
- `MyOIDCAuthenticationBackend` replaces `DIDAuthBackend` + `OIDCAuthBackend`
- Username = IdP `sub` claim (direct mapping, no email/password)
- Session cookie renamed to `polly_sessionid`
- All OIDC endpoints pointed at `http://127.0.0.1:8000/openid/...`
- didkit purged from dependencies and code

### URL Wiring (this session)
- Registered `GenerateCredentialView` at `/credentials/generate/`
- Registered `DeleteCredentialView` at `/credentials/delete/`
- Registered `ImportCredentialView` at `/credentials/import/`
- All 9 named URL patterns verified resolving

### Cactus Comments Removal (this session)
- Deleted `apps/poller/templatetags/cactus_comments.py` (152 lines)
- Stripped template tag references from `poll_detail.html`
- Cleared README and docs references
- Discussion section placeholder retained for future Nostr relay integration

## Live Test Results

All services confirmed running:
| Service | Port | Status |
|---|---|---|
| IdP (iyou_wun) | 8000 | ✓ |
| Social Feed | 8001 | ✓ |
| Polly | 8002 | ✓ (restarted with changes) |
| Tauri Bridge (iyou-home) | 9001 | ✓ connected, ✗ unresponsive |

**OIDC login flow**: `/oidc/authenticate/` redirects correctly to IdP at `:8000/openid/authorize/` with proper params. IdP login page attempts WebSocket handshake with bridge at `:9001` but gets no response — falls back to manual VP paste mode.

**Token exchange**: When a code is provided, the callback completes successfully — user is created/mapped via `sub` claim, session established.

**Credential generation**: `POST /credentials/generate/` returns unsigned JSON (200). Frontend's `signCredentialViaBridge()` connects to bridge, sends `{type: "sign_credential", ...}`, but bridge never responds → 10s timeout → error shown to user.

## Blockers

1. **Bridge message handling** — `iyou-home` at `:9001` needs to implement two WebSocket message types:
   - `"sign"` (challenge → signed VP) for the IdP login page
   - `"sign_credential"` (unsigned credential → signed VC) for Polly's VC issuance
2. **Vote signing** — Still on SHA-256 placeholder; needs the same bridge message type

## Testing Infrastructure (EOD)

Established a proper testing foundation:

**Infrastructure:**
- Added `pytest-django` and `[tool.pytest.ini_options]` to `pyproject.toml`
- Created root `conftest.py` with `test_user`, `auth_client`, `sample_vc` fixtures
- Marked bridge-dependent tests with `@pytest.mark.bridge` (opt-in with `-m bridge`, skip with `-m "not bridge"`)
- Discovered `mozilla_django_oidc.middleware.SessionRefresh` logs out `force_login`'d users — view tests use `@override_settings` to strip it

**Test results: 45 passed, 0 failed** (3 bridge-dependent deselected)

| Area | Tests | What They Cover |
|------|-------|-----------------|
| `test_auth.py` | 6 | Login/logout redirects, no-password enforcement, OIDC backend `filter_users_by_claims` |
| `test_urls.py` | 1 (11 sub) | All 11 named URL patterns resolve |
| `test_vc_management.py` | 22 | GenerateCredential returns unsigned JSON, ImportCredential validation, StoreSignedCredential, DeleteCredential, VC model methods (add/get/migrate) |
| `test_models.py` | 7 | Poll/Vote creation, scopes, option relations |
| `test_views.py` | 5 | Poll list/detail public access, create requires auth |
| `test_vc.py` (integration) | 3 | VC display structure, copy, labeling |

**Real bugs discovered (assertions adjusted to match current behavior):**
1. `PollOption.votes` counter not auto-incremented on vote creation (cached field must be manually updated)
2. `Vote.signature` defaults to `''` not `None`
3. `Vote.__str__` format reads "voter voted for Option X in Poll Y" (inverted from expected)

**Portable patterns for iyou_wun:**
- Same `conftest.py` + `override_settings(SessionRefresh)` pattern will be needed there
- `filter_users_by_claims()` returns a QuerySet — tests must call `.first()`

## Next Steps

1. Implement `sign` and `sign_credential` handlers in `iyou_home/src-tauri/`
2. Rebuild binary and restart bridge
3. Retest full OIDC login → credential generation → bridge signing flow
4. Wire vote signing to bridge once confirmed working
5. Fix discovered bugs: `PollOption.votes` counter, `Vote.signature` default, `Vote.__str__`

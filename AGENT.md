# AGENT.md — iyou_poly Onboarding

## CRITICAL: OpenID Connect & Ingress Invariants

All authentication and user provisioning logic in this repository MUST conform strictly to the canonical ecosystem specifications located at:

- `docs/ecosystem_shared/OMNI_SOCIAL_AUTH_STANDARDIZATION.md`
- `docs/ecosystem_shared/AUTH_FLOW_SPECIFICATION.md`

Reference Implementation to follow: `docs/ecosystem_shared/auth_pkce.py`

Do NOT implement cleartext client secrets, do NOT use email addresses as database lookup anchors, and ensure all post-auth logic implements the `evaluate_sovereign_admin_posture` routine.

### Non-Negotiable Rules

1. **Secretless PKCE only** — No `OIDC_RP_CLIENT_SECRET` in code, manifests, or env defaults. The auth backend is a public client.
2. **DID-as-username** — `User.username = claims["sub"]` (the full DID string). Never email, never a derived hash.
3. **No `OIDCAuthenticationBackend` inheritance** — The active backend `PKCEAuthenticationBackend` extends `ModelBackend`, not `OIDCAuthenticationBackend`.
4. **Callback view inherits `OIDCAuthenticationCallbackView`** — `PKCEOIDCAuthenticationCallbackView` must NOT override `get()`. It only overrides `get_backend_kwargs()` to inject the PKCE code_verifier.
5. **Admin elevation** — `is_staff`/`is_superuser` granted only when `user.username == env.str("ADMIN_DID")`. Uses dirty-flag `save(update_fields=[...])` pattern.

---

## Project Summary

**iyou_poly** is a Django 6.0 decentralized polling platform. It uses OIDC (PKCE flow) for authentication, Ed25519 cryptographic vote signatures, Nostr relay broadcast for mesh federation, and a scope/credential system for access control.

### Quick Facts

| Item | Value |
|------|-------|
| Framework | Django 6.0 + DRF |
| Auth | OIDC PKCE via `mozilla-django-oidc` |
| Active Backend | `PKCEAuthenticationBackend` (`apps/accounts/utils/auth_pkce.py`) |
| Callback View | `PKCEOIDCAuthenticationCallbackView` (inherits `OIDCAuthenticationCallbackView`) |
| User Model | `apps.accounts.models.User` (extends `AbstractUser`) |
| Username Field | DID string from `sub` claim |
| Session Cookie | `poly_sessionid`, `SameSite=Lax`, `HttpOnly=True`, `Secure=True` |
| Session Engine | `django.contrib.sessions.backends.db` |
| Default Port | `8002` |
| IDP | `iyou_idp` at `https://iyou.me` (public) / `http://iyou-idp.identity.svc.cluster.local:8000` (internal) |
| Test Command | `.venv/bin/python manage.py test apps.accounts.tests.test_auth` |

### Key Files

| Path | Purpose |
|------|---------|
| `apps/accounts/utils/auth_pkce.py` | PKCE auth views + backend (canonical auth reference) |
| `apps/accounts/backends.py` | `MyOIDCAuthenticationBackend` (legacy, NOT the active backend) |
| `apps/accounts/models.py` | User model, FederatedIdentity, VC storage |
| `apps/poller/models.py` | Poll, PollOption, Vote models |
| `apps/poller/views.py` | API + template views, `CastVoteAPIView` |
| `apps/poller/nostr.py` | Outbound Nostr event broadcast |
| `apps/poller/nostr_ingest.py` | Inbound Nostr ingestion (NIP-01 Schnorr verification) |
| `apps/core/verification.py` | Pure-Python Ed25519 vote signature verification |
| `apps/core/models.py` | DID, Scope, Credential, Trust models |
| `config/settings.py` | All Django + OIDC + Nostr configuration |

### Auth Flow Summary

```
Browser → GET /oidc/authenticate/
  → PKCEOIDCAuthenticationRequestView generates code_verifier + code_challenge
  → Stores verifier in session["pkce_code_verifier"] + session["oidc_states"][state]
  → Redirects to iyou_idp /openid/authorize/

IDP authenticates user → redirects to /oidc/callback/?code=...&state=...

Browser → GET /oidc/callback/
  → OIDCAuthenticationCallbackView.get() (parent — NOT overridden)
  → Extracts code_verifier from oidc_states session dict
  → Posts token exchange to IDP /openid/token/ with code_verifier
  → Decodes id_token, verifies nonce
  → Calls auth.authenticate(request, nonce, code_verifier)
    → PKCEAuthenticationBackend.authenticate()
      → Picks up code_verifier from kwargs
      → _exchange_code_for_claims() performs token POST + JWT decode
      → filter_users_by_claims() → get_or_create(username=sub)
      → _evaluate_admin_elevation() → ADMIN_DID check
  → login_success() → auth.login(request, user)
  → Redirects to LOGIN_REDIRECT_URL
```

### Active OIDC Settings (`config/settings.py`)

```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")   # line 92 — PRESENT
OIDC_RP_CLIENT_ID = env.str("OIDC_RP_CLIENT_ID", default="")    # line 220
OIDC_RP_CLIENT_SECRET = env.str("OIDC_RP_CLIENT_SECRET", default="")  # line 221 — SHOULD BE EMPTY
OIDC_RP_SIGN_ALGO = "RS256"                                      # line 222
OIDC_RP_CALLBACK_URL = env.str("OIDC_RP_CALLBACK_URL", default="/oidc/callback/")  # line 224
OIDC_OP_AUTHORIZATION_ENDPOINT = f"{IDP_BASE_PUBLIC_URL}/openid/authorize/"  # line 226
OIDC_OP_TOKEN_ENDPOINT = f"{IDP_BASE_INTERNAL_URL}/openid/token/"           # line 227
OIDC_OP_USER_ENDPOINT = f"{IDP_BASE_INTERNAL_URL}/openid/userinfo/"         # line 228
OIDC_OP_JWKS_ENDPOINT = f"{IDP_BASE_INTERNAL_URL}/openid/jwks/"            # line 229
OIDC_USERNAME_ALGO = lambda claims: claims.get("sub")           # line 232
OIDC_RP_REQUIRED_CLAIMS = []                                    # line 235
OIDC_VERIFY_SSL = False                                         # line 236
OIDC_STORE_ID_TOKEN = True                                      # line 237
```

> **Note:** `OIDC_RP_SCOPES` is NOT defined in settings.py. The default `"openid email"` is used via `getattr(settings, "OIDC_RP_SCOPES", "openid email")` in `PKCEOIDCAuthenticationRequestView.get()` at `auth_pkce.py:78`.

### Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `OIDC_RP_CLIENT_ID` | Public client ID registered with iyou_idp | Yes |
| `OIDC_RP_CLIENT_SECRET` | Should be empty for public PKCE flow | No |
| `ADMIN_DID` | DID string to grant staff/superuser elevation | No |
| `NOSTR_PRIVATE_KEY` | Hex-encoded secp256k1 private key for Nostr relay publish | No (disables Nostr) |
| `NOSTR_RELAYS` | Comma-separated list of Nostr relay URLs | No |
| `IDP_BASE_INTERNAL_URL` | Internal IDP URL (K8s service) | Yes |
| `IDP_BASE_PUBLIC_URL` | Public IDP URL | Yes |
| `APP_NAME_PREFIX` | Prefix for session/CSRF cookies (default: `poly`) | No |
| `POLY_ALLOWED_HOSTS` | Comma-separated allowed hostnames | Yes |

### Testing

```bash
# Auth tests (fast, focused)
.venv/bin/python manage.py test apps.accounts.tests.test_auth apps.accounts.tests.test_urls

# Poller tests
.venv/bin/python manage.py test apps.poller.tests.test_views apps.poller.tests.test_models

# Lint
.venv/bin/python -m ruff check apps/
```

### Docs Structure

```
docs/
├── DEVELOPER_GUIDE.md                ← full setup, env vars, architecture, troubleshooting
├── ecosystem_shared/
│   ├── OMNI_SOCIAL_AUTH_STANDARDIZATION.md  ← platform auth rules (READ THIS FIRST)
│   ├── AUTH_FLOW_SPECIFICATION.md            ← flow diagrams
│   ├── auth_pkce.py                          ← reference implementation
│   └── satellite-coordination.md             ← multi-satellite sync
└── archive/                          ← historical docs (do not edit)
    ├── POLY_PROTOCOL.md
    ├── DECENTRALIZED_POLLING_SPEC.md
    ├── CREDENTIAL_ISSUANCE_ARCHITECTURE.md
    └── ...
```

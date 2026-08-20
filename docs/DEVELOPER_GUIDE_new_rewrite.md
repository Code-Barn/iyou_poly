# iyou_poly Developer Guide

## 1. Overview & Core Mission

**iyou_poly** is the primary consensus discovery and governance engine of the **omni_social** ecosystem. It is a Django 6.0 decentralized polling platform that uses OIDC (PKCE flow) for authentication, Ed25519 cryptographic vote signatures, Nostr relay broadcast for mesh federation, and a scope/credential system for access control.

Because this application handles high-stakes group decision-making, **information security, cryptographically verifiable voting, input validation, and robustness** are top concerns.

| Item | Value |
|------|-------|
| Framework | Django 6.0 + DRF |
| Auth | OIDC PKCE via `mozilla-django-oidc` |
| Active Backend | `PKCEAuthenticationBackend` (`apps/accounts/utils/auth_pkce.py`) |
| Callback View | `PKCEOIDCAuthenticationCallbackView` (inherits `OIDCAuthenticationCallbackView`) |
| User Model | `apps.accounts.models.User` (extends `AbstractUser`) |
| Username Field | DID string from `sub` claim (`User.username = claims["sub"]`) |
| Session Cookie | `poly_sessionid`, `SameSite=Lax`, `HttpOnly=True`, `Secure=True` |
| CSRF Cookie | `poly_csrftoken`, `Secure=True` |
| Session Engine | `django.contrib.sessions.backends.db` |
| Default Port | `8002` |
| IDP | `iyou_idp` at `https://iyou.me` (public) / `http://iyou-idp.identity.svc.cluster.local:8000` (internal) |
| Test Command | `.venv/bin/python manage.py test apps.accounts.tests.test_auth` |
| Lint | `.venv/bin/python -m ruff check apps/` |

### Key Files

| Path | Purpose |
|------|---------|
| `apps/accounts/utils/auth_pkce.py` | PKCE auth views + backend (canonical auth reference) |
| `apps/accounts/backends.py` | `MyOIDCAuthenticationBackend` (legacy, NOT the active backend) |
| `apps/accounts/models.py` | User model, FederatedIdentity, VC storage |
| `apps/poller/models.py` | Poll, PollOption, Vote, RevocationAttestation, TrustedIssuer models |
| `apps/poller/views.py` | API + template views, `CastVoteAPIView`, `NostrIngestWebhook` |
| `apps/poller/nostr.py` | Outbound Nostr event broadcast (secp256k1 Schnorr) |
| `apps/poller/nostr_ingest.py` | Inbound Nostr ingestion (NIP-01 Schnorr verification) |
| `apps/core/verification.py` | Pure-Python Ed25519 vote signature verification |
| `apps/core/models.py` | DID, Scope, Credential, Trust, FederatedNode models |
| `config/settings.py` | All Django + OIDC + Nostr configuration |
| `config/urls.py` | Root URL routing |

---

## 2. Architecture & Data Schema

### apps/poller/models.py — Polling Domain

**Poll** — Central entity for all voting.

| Field | Type | Notes |
|-------|------|-------|
| `poll_type` | CharField | `public`, `family_scoped`, `family_unit`, `organization` |
| `temporal_type` | CharField | `timed`, `scheduled`, `ongoing` |
| `is_mutable` | BooleanField | Allows DID re-vote (flip `is_current` checkpoint) |
| `parent_poll` | FK(self) | Hierarchical family/organization polls |
| `embedding_app` | CharField | External app filter (e.g. `byers-brands-llc`) |
| `title` / `description` | CharField/TextField | |
| `created_by` | FK(User) | `on_delete=PROTECT` |
| `required_scope_type` | FK(ScopeType) | Nullable — scope-type gate |
| `required_scope` | FK(Scope) | Nullable — specific scope gate |
| `required_credential_type` | CharField | String gate, e.g. `"municipal_voter"` |
| `min_fidelity_required` | PositiveSmallIntegerField | 1=Social, 2=Institutional, 3=Hardware |
| `min_issuer_trust_score` | FloatField | 0.0–1.0 |
| `require_multiple_issuers` | BooleanField | |
| `vote_power_rule` | CharField | Default `"1:1"` |
| `vote_power_ratio` | FloatField | Default 1.0 |
| `starts_at` / `ends_at` | DateTimeField | Nullable — temporal bounds |
| `is_proposal` / `funding_goal` / `funding_current` / `funding_deadline` | | Proposal/funding workflow |
| `ipfs_cid` / `blockchain_anchor` / `votes_merkle_root` / `vote_count_anchor` | CharField | Decentralized anchoring (fields exist, no integration) |
| `nostr_event_id` | CharField(unique, nullable) | SHA-256 event ID for idempotent Nostr ingestion |
| `nostr_pubkey` | CharField | Nostr event creator pubkey |
| `is_active` | BooleanField | |
| `allow_write_ins` | BooleanField | Write-in ballot governance |
| `write_in_display_limit` | PositiveIntegerField | Default 5 |

Computed properties: `is_ongoing`, `is_expired`, `is_active_now`, `total_votes` (via `Max(id)` aggregation), `funding_progress`, `starts_at_unix`, `ends_at_unix`.

Model-level validation (`clean()`): TIMED/SCHEDULED polls require `ends_at`; SCHEDULED polls require `starts_at`.

**PollOption** — Each option within a poll.

| Field | Type | Notes |
|-------|------|-------|
| `poll` | FK(Poll) | `on_delete=CASCADE` |
| `text` | CharField | |
| `votes` | PositiveIntegerField | **DEPRECATED** — use `dynamic_vote_count` |
| `is_write_in` | BooleanField | Crowd-sourced write-in option |
| `nominated_by` | CharField | DID of voter who first proposed it |

`dynamic_vote_count` property: timestamp-derived aggregation via `Max(Vote.id)` per `(poll, voter_did)` — immune to out-of-order federation arrivals.

**Vote** — Immutable record of a cast vote.

| Field | Type | Notes |
|-------|------|-------|
| `poll` | FK(Poll) | `on_delete=CASCADE` |
| `option` | FK(PollOption) | `on_delete=CASCADE` |
| `user` | FK(User) | Nullable — `on_delete=PROTECT` |
| `voter_did` | CharField | DID of the voter (can vote without local account) |
| `signature` | TextField | Ed25519 hex signature (128 chars) — nullable |
| `merkle_root` | CharField | Vote batch Merkle root |
| `credential_cid` | CharField | IPFS CID of voting credential |
| `credential_proof` | JSONField | ZK proof of credential possession |
| `credential_data` | JSONField | Un-blinded verification credential proof package |
| `weight` | PositiveIntegerField | Always 1 |
| `is_verified` | BooleanField | |
| `verification_details` | JSONField | |
| `is_current` | BooleanField | Active checkpoint flag for mutable polls |
| `nostr_event_id` | CharField(unique, nullable) | Idempotent Nostr ingestion |

No DB-level uniqueness constraint on `(poll, voter_did)` — view-layer deduplication only. DB-level unique constraint on `nostr_event_id`.

**RevocationAttestation** — Cryptographic attestation that revokes a previously-issued credential.

| Field | Type | Notes |
|-------|------|-------|
| `issuer_did` | CharField | DID of issuer who originally issued the credential |
| `subject_did` | CharField | DID of credential subject (voter) |
| `original_credential_id` | CharField | Optional identifier of specific credential |
| `signature` | TextField | Base58btc-encoded Ed25519 signature |
| `timestamp` | DateTimeField | When revocation was issued |

Indexed on `(issuer_did, subject_did)`.

**TrustedIssuer** — Whitelisted issuer for a poll's credential gate.

| Field | Type | Notes |
|-------|------|-------|
| `poll` | FK(Poll) | `on_delete=CASCADE` |
| `issuer_did` | CharField | Authorized issuer DID |
| `is_mandatory` | BooleanField | Constitutional registrar — bypasses per-poll whitelist |

`unique_together = ("poll", "issuer_did")`.

**FederatedPoll** — Proxy model of `FederatedData` for cross-node sync.

### apps/accounts/models.py — Identity Domain

**User** (extends `AbstractUser`).

| Field | Type | Notes |
|-------|------|-------|
| `username` | CharField | **Holds the DID** from OIDC `sub` claim — the primary identity anchor |
| `did` | CharField | **DEPRECATED** — backward compat only |
| `did_method` | CharField | **DEPRECATED** |
| `did_key` | TextField | **DEPRECATED** — signing now via Tauri bridge |
| `vcs` | JSONField | List of VCs with metadata; both old and new format supported |

Key methods: `add_vc()`, `get_vcs_by_type()`, `get_other_vcs()`, `get_authentication_vc()`, `ensure_vcs_migrated()`.

**FederatedIdentity** — Maps external OIDC provider identities to users. `unique_together = ("provider", "external_id")`.

### apps/core/models.py — Infrastructure Domain

**DID System:** `DIDMethod`, `DID`, `DIDDocument` — full DID lifecycle with `did_uri` computed on save.

**Scope System:** `ScopeType` (hierarchical, self-authorizing types) and `Scope` (instances within a type, parent-child hierarchy).

**Credential System:** `CredentialType`, `VerifiableCredential`, `CredentialIssuance`, `IssuerAuthorization`, `IssuerMetrics`, `IssuerEndorsement`.

**Federation:** `FederatedNode`, `FederatedData`, `SyncMessage` (gossip protocol), `DataSyncLog`.

### apps/poller/serializers.py

- `PollSerializer` — Full poll with computed fields (`is_ongoing`, `starts_at_unix`, `ends_at_unix`, `dynamic_vote_count`, `funding_progress`)
- `PollCreateSerializer` — Accepts UNIX epoch integers for `starts_at`/`ends_at` via `to_internal_value`
- `PollResultsSerializer` — Segmented results: `core_options` + `write_in_leaderboard`, timestamp-derived aggregation
- `VoteSerializer` — Full vote with `credential_data`
- `VoteCreateSerializer` — Accepts `voter_did`, `signature`, `credential`, `credential_presentation`, `write_in_text`
- `NostrEventSerializer` — Validates NIP-01 event structure (`id`, `pubkey`, `created_at`, `kind`, `tags`, `content`, `sig`)

### apps/core/serializers.py

`ScopeTypeSerializer`, `ScopeSerializer`, `CredentialTypeSerializer`, `CredentialIssuanceSerializer`, `IssuerAuthorizationSerializer`, `FederatedNodeSerializer`, `FederatedDataSerializer`, `SyncMessageSerializer`, `DataSyncLogSerializer`, `IssuerMetricsSerializer`, `IssuerEndorsementSerializer`, plus request/response serializers for credential issuance, verification, trust scoring.

---

## 3. Security & Cryptographic Invariants

### 3.1 Authentication & Authorization — OIDC/PKCE Compliance

**Active backend:** `PKCEAuthenticationBackend` (`apps/accounts/utils/auth_pkce.py:206`) — inherits `BaseBackend` (not `OIDCAuthenticationBackend`).

**Legacy backend:** `MyOIDCAuthenticationBackend` (`apps/accounts/backends.py:19`) — retained for test compatibility only; NOT registered in `AUTHENTICATION_BACKENDS`.

**5 Federation Rules compliance:**

| Rule | Status | Implementation |
|------|--------|----------------|
| Rule 1: Proxy Header | ✅ | `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` + `USE_X_FORWARDED_HOST = True` in `settings.py:92-93` |
| Rule 2: Public Client | ✅ | Backend inherits `BaseBackend`, not `OIDCAuthenticationBackend`. `OIDC_RP_CLIENT_SECRET` defaults to empty string. |
| Rule 3: Instance State Relay | ✅ | `PKCEOIDCAuthenticationCallbackView.get_backend_kwargs()` injects `code_verifier` into kwargs; parent `get()` is NOT overridden. |
| Rule 4: Sovereign Profile Anchoring | ✅ | `get_username()` returns `claims["sub"]` (the full DID). `_evaluate_sovereign_admin_posture()` uses `settings.ADMIN_DID` with dirty-flag pattern and `set_unusable_password()`. |
| Rule 5: Logout View | ✅ | `path("oidc/logout/", OIDCLogoutView.as_view())` in `apps/accounts/urls.py:36`. `LOGOUT_REDIRECT_URL = "/"` in `settings.py:201`. |

**Auth flow summary:**

```
Browser → GET /oidc/authenticate/
  → PKCEOIDCAuthenticationRequestView generates code_verifier + code_challenge
  → Stores verifier in session["pkce_code_verifier"]
  → Redirects to iyou_idp /openid/authorize/

IDP authenticates → redirects to /oidc/callback/?code=...&state=...

Browser → GET /oidc/callback/
  → OIDCAuthenticationCallbackView.get() (parent — NOT overridden)
  → get_backend_kwargs() extracts code_verifier from session
  → Posts token exchange to IDP with code_verifier
  → Gets userinfo, calls auth.authenticate()
    → PKCEAuthenticationBackend.authenticate()
      → _exchange_code_for_claims() (token POST + JWT decode)
      → _get_or_create_user(username=sub)
      → _evaluate_sovereign_admin_posture()
  → login_success() → auth.login(request, user)
```

**Non-negotiable invariants:**
1. No `OIDC_RP_CLIENT_SECRET` in code, manifests, or env defaults
2. `User.username = claims["sub"]` (the full DID string) — never email, never a derived hash
3. Backend inherits `BaseBackend`, not `OIDCAuthenticationBackend`
4. Callback view overrides `get_backend_kwargs()`, NOT `get()`
5. Admin elevation uses dirty-flag `save(update_fields=[...])` pattern — idempotent, elevation-only
6. All back-channel HTTP calls wrapped in `try/except requests.RequestException`

### 3.2 Vote Verification & Sybil Resistance

**Ed25519 Signature Verification:**
- `apps/core/verification.py` — pure-Python, zero network dependencies
- Public key extracted from `did:key:z6M...` via base58btc decode → strip `\xed` multicodec → load 32-byte `Ed25519PublicKey`
- Canonical payload: `json.dumps(vote_envelope, sort_keys=True, separators=(',', ':'))` → SHA-256 → Ed25519 verify
- `CastVoteAPIView._verify_signature()` delegates to `verify_vote_signature()` — 401 on failure

**Double-voting prevention:**
- View-layer deduplication: `Vote.objects.filter(poll=poll, voter_did=voter_did, is_current=True).first()`
- Immutable polls: reject duplicate `(poll, voter_did)` — returns 400 or 201 duplicate-success if signature matches
- Mutable polls: flip previous `is_current` to `False`, ingest fresh record
- No DB-level uniqueness constraint on `(poll, voter_did)` — view-layer only

**Sybil resistance:**
- DID-as-username: one OIDC session = one DID = one identity
- Credential gating: polls can require `required_credential_type` + scope verification
- Trust fidelity levels: `min_fidelity_required` (1=Social, 2=Institutional, 3=Hardware)
- Issuer whitelist: `TrustedIssuer` per poll; `MANDATORY_ISSUER_DIDS` bypass per-poll lists
- Revocation: `RevocationAttestation` model blocks revoked credentials at vote time

**VP (Verifiable Presentation) handshake:**
- `IssueCredentialChallengeView` issues a cryptographic nonce via cache (5-min TTL)
- `CastVoteAPIView` consumes the challenge on vote, verifying `proof.challenge` matches
- Dual-layer verification: VP envelope Ed25519 (holder) + inner VC attestation (issuer)

### 3.3 Privacy vs. Auditability

- **Voter privacy:** `voter_did` stored on Vote but not linked to personal info beyond DID
- **Auditability:** `GET /api/polls/{id}/history/` returns all votes with signatures, voter DIDs, timestamps
- **Merkle root:** `Poll.votes_merkle_root` field exists; `anchor_ledger` management command computes on-demand but does not auto-store
- **Credential data:** `Vote.credential_data` stores un-blinded verification proof package
- **Timestamp-derived aggregation:** `Max(Vote.id)` per `(poll, voter_did)` — deterministic, audit-friendly

### 3.4 Input & State Hardening

**CSRF Protection:**
- Django `CsrfViewMiddleware` enabled in middleware stack
- `CastVoteAPIView` and `NostrIngestWebhook` are `@csrf_exempt` — **by design** (headless/nostr endpoints accept external requests)
- `IssueCredentialChallengeView` has empty `authentication_classes` and `permission_classes` — **no CSRF or auth required** (challenge issuance is public)
- Template-based voting (`vote_api`) uses session auth + CSRF

**Input Validation:**
- DRF serializers (`VoteCreateSerializer`, `PollCreateSerializer`, `NostrEventSerializer`) validate all inbound data
- Write-in text: NFKC normalization + whitespace collapse + `__iexact` coalescence
- Duplicate option detection in poll creation
- `Poll.clean()` enforces temporal field requirements

**Rate Limiting:**
- **NOT IMPLEMENTED** — no `django-ratelimit` or similar middleware. All endpoints are unthrottled.

**State Machine Transitions:**
- `Poll.is_active_now` — computed from `temporal_type`, `starts_at`, `ends_at`, `is_active`
- `Poll.is_expired` — returns `False` for ONGOING polls
- `Vote.is_current` — checkpoint flag flipped on re-vote for mutable polls
- No formal state machine enforcement at model level — transitions are view-layer only

**Session Security:**
- `SESSION_COOKIE_SAMESITE = "Lax"`, `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `SESSION_TRUSTED_ORIGINS = [f"https://{APP_NAME_PREFIX}.iyou.me"]`
- Cookie names prefixed by `APP_NAME_PREFIX` for session isolation across ecosystem

---

## 4. Polling & Voting Capabilities (Current State)

### Poll Types
- `public` — Open to all authenticated users
- `family_scoped` — Scoped to family hierarchy with credential verification
- `family_unit` — Single family unit (creator-only visibility)
- `organization` — Organization-scoped polls

### Temporal Types
- `timed` — Immediate start, defined end time
- `scheduled` — Defined start and end times
- `ongoing` — No temporal bounds; supports mutable re-vote

### Voting Mechanisms
- **Standard voting** — Select one option per poll
- **Write-in ballots** — Optional (`allow_write_ins`); NFKC normalization, view-layer coalescence, race-guarded creation
- **Mutable re-vote** — For `is_mutable=True` polls (typically ONGOING); previous `is_current` flipped
- **Credential-gated voting** — `required_credential_type` string gate; VP handshake or legacy bare-VC mode
- **Proposal/funding** — `is_proposal`, `funding_goal`, `funding_current`, `funding_deadline`

### Timing Mechanisms
- `starts_at` / `ends_at` DateTimeFields with UNIX epoch computed properties
- `is_active_now` / `is_expired` computed properties
- Temporal validation at vote time: reject before `starts_at` or after `ends_at` for TIMED/SCHEDULED
- Clock-skew grace: 900 seconds (15 min) for Nostr ingestion

### Tallying
- `Poll.total_votes` — timestamp-derived via `Max(Vote.id)` per `(poll, voter_did)`
- `PollOption.dynamic_vote_count` — same aggregation, filtered by option
- `PollResultsSerializer` — segmented into `core_options` + `write_in_leaderboard`
- `PollOption.votes` — **DEPRECATED** denormalized counter (unreliable under federation)

### Federation
- Outbound: Nostr kind:30023 (polls) and kind:1111 (votes) via `nostr.publish_*()`
- Inbound: `NostrIngestWebhook` at `POST /api/nostr/ingest/` — NIP-01 Schnorr verification
- Gossip worker: async Nostr subscription loop (`gossip_worker.py`)
- Idempotent: `nostr_event_id` unique constraint on Poll and Vote

---

## 5. API & Route Inventory

### Authentication Routes (`apps/accounts/urls.py`)

| Method | URL | View | Name |
|--------|-----|------|------|
| GET | `/oidc/authenticate/` | `PKCEOIDCAuthenticationRequestView` | `oidc_authentication_init` |
| GET | `/oidc/callback/` | `PKCEOIDCAuthenticationCallbackView` | `oidc_authentication_callback` |
| GET | `/oidc/logout/` | `OIDCLogoutView` | `oidc_logout` |
| GET/POST | `/login/` | Redirect to `oidc_authentication_init` | `login` |
| GET/POST | `/logout/` | Redirect to `oidc_logout` | `logout` |

### Poller API Routes (`apps/poller/urls.py`)

**DRF Router (auto-generated):**

| Method | URL | ViewSet | Name |
|--------|-----|---------|------|
| GET/POST | `/api/polls/` | `PollViewSet` | `poll-list` |
| GET/PUT/PATCH/DELETE | `/api/polls/{id}/` | `PollViewSet` | `poll-detail` |
| GET | `/api/polls/{id}/results/` | `PollViewSet.results` | `poll-results` |
| POST | `/api/polls/{id}/fund/` | `PollViewSet.fund` | `poll-fund` |
| GET | `/api/votes/` | `VoteViewSet` | `vote-list` |
| GET | `/api/votes/{id}/` | `VoteViewSet` | `vote-detail` |

**Function-based APIs:**

| Method | URL | View | Name |
|--------|-----|------|------|
| GET/POST | `/api/polls/` | `poll_api` | `poll_api` |
| GET | `/api/polls/{id}/` | `poll_detail_api` | `poll_detail_api` |
| POST | `/api/polls/{id}/vote/` | `vote_api` (HTMX + JSON) | `vote_api` |
| GET | `/api/polls/{id}/history/` | `get_votes` | `poll_history_api` |

**DRF APIViews:**

| Method | URL | View | Name |
|--------|-----|------|------|
| POST | `/api/polls/{id}/cast/` | `CastVoteAPIView` | `cast_vote_api` |
| GET | `/api/polls/{id}/eligibility/` | `CheckVotingEligibilityAPIView` | `check_eligibility_api` |
| POST | `/api/polls/{id}/credential-request/` | `IssueCredentialChallengeView` | `credential_request_api` |
| POST | `/api/nostr/ingest/` | `NostrIngestWebhook` | `nostr_ingest` |

**Embed Routes:**

| Method | URL | View | Name |
|--------|-----|------|------|
| GET | `/api/embed/polls/` | `EmbeddablePollWidget` | `embed_polls` |
| GET | `/api/embed/polls/{id}/` | `EmbeddablePollWidget` | `embed_poll_detail` |

**Template Views:**

| Method | URL | View | Name |
|--------|-----|------|------|
| GET | `/` | `poll_list` | `poll_list` |
| GET | `/{id}/` | `poll_detail` | `poll_detail` |
| GET/POST | `/create/` | `CreatePollView` | `poll_create` |

### Core API Routes (`apps/core/urls.py`)

**DRF Router:**

| Prefix | ViewSet |
|--------|---------|
| `/api/scope-types/` | `ScopeTypeViewSet` |
| `/api/scopes/` | `ScopeViewSet` |
| `/api/credential-types/` | `CredentialTypeViewSet` |
| `/api/credential-issuances/` | `CredentialIssuanceViewSet` |
| `/api/issuer-authorizations/` | `IssuerAuthorizationViewSet` |
| `/api/federation/nodes/` | `FederatedNodeViewSet` |
| `/api/federation/messages/` | `SyncMessagesViewSet` |
| `/api/federation/logs/` | `DataSyncLogViewSet` |
| `/api/issuer-metrics/` | `IssuerMetricsViewSet` |
| `/api/issuer-endorsements/` | `IssuerEndorsementViewSet` |

**Core APIViews:**

| Method | URL | View |
|--------|-----|------|
| GET/POST | `/api/federated-data/` | `federated_data_api` |
| GET/PUT/DELETE | `/api/federated-data/{node}/{type}/{id}/` | `federated_data_detail_api` |
| GET | `/api/dids/` | `did_api` |
| GET | `/api/dids/{did_uri}/` | `did_api` |
| POST | `/api/credentials/issue/` | `IssueCredentialAPIView` |
| POST | `/api/credentials/verify/` | `VerifyCredentialAPIView` |
| GET | `/api/credentials/` | `GetCredentialsAPIView` |
| GET/POST | `/api/federation/sync/` | `DataSyncView` |
| GET | `/api/trust/score/` | `GetTrustScoreAPIView` |
| POST | `/api/trust/check/` | `CheckIssuerTrustAPIView` |

### Credential Management Routes (`config/urls.py`)

| Method | URL | View | Name |
|--------|-----|------|------|
| GET/POST | `/credentials/` | `VCManagementView` | `vc_management` |
| POST | `/credentials/store-signed/` | `StoreSignedCredentialView` | `store_signed_credential` |
| GET/POST | `/credentials/generate/` | `GenerateCredentialView` | `generate_credential` |
| POST | `/credentials/delete/` | `DeleteCredentialView` | `delete_credential` |
| GET/POST | `/credentials/import/` | `ImportCredentialView` | `import_credential` |

---

## 6. Known Gaps & Roadmap

### Missing Capabilities (Identified in Audit)

1. **Binary (Yes/No) Polls** — No dedicated binary poll type. All polls require 2+ manually-created options. A `binary` poll type with automatic Yes/No options is absent.

2. **Fluid/Ongoing Re-voting** — Partially implemented: `is_mutable` flag + `is_current` checkpoint exists, but no UI or API guidance for voters on re-voting behavior. ONGOING polls lack explicit lifecycle management (no auto-deactivation).

3. **Hard-cutoff Elections** — No `hard_cutoff` field or mechanism. Once `ends_at` passes, votes are rejected — but there is no explicit "election mode" with ballot freezing, mandatory credential verification, or enhanced audit trails.

4. **Credential Gating Gaps** — `required_credential_type` is a simple string, not a FK. No runtime credential schema validation. No ZK-proof verification for privacy-preserving credential checks. The `verify_attestation()` function uses open-trust fallback when no `IssuerAuthorization` records exist.

5. **Rate Limiting** — **NOT IMPLEMENTED**. All API endpoints (including `CastVoteAPIView`, `NostrIngestWebhook`, `IssueCredentialChallengeView`) are unthrottled. No `django-ratelimit` or equivalent middleware.

6. **State Machine Enforcement** — Poll lifecycle transitions (`draft → active → closed`) are not enforced at the model level. `is_active` is a simple boolean; no transition guards or audit log of state changes.

7. **Merkle Root Auto-computation** — `Poll.votes_merkle_root` field exists but is never auto-populated. The `anchor_ledger` management command computes on demand but does not store the result.

8. **IPFS/Blockchain Anchoring** — Model fields (`ipfs_cid`, `blockchain_anchor`, `blockchain_tx`) exist on Poll and Vote but no integration code implements actual storage or verification.

9. **Real-time Updates** — No WebSocket/SSE implementation. Poll results require page refresh or HTMX polling.

10. **Advanced Voting Methods** — No ranked-choice, Condorcet, or approval voting. All polls are single-choice.

11. **Delegated/Liquid Democracy** — No delegation mechanism or vote-proxy features.

12. **Discussion Threads** — No comment or deliberation system on polls/proposals.

### Priority Roadmap

**P0 — Security Hardening:**
- Add rate limiting to all API endpoints (especially `CastVoteAPIView`, `NostrIngestWebhook`, `IssueCredentialChallengeView`)
- Migrate template-based voting (`vote_api`) to cryptographic verification
- Add DB-level uniqueness constraint or advisory lock for `(poll, voter_did)` to prevent race-condition double-inserts
- Enforce `Poll.clean()` on all creation/update paths (currently only called by admin/forms)

**P1 — Feature Gaps:**
- Binary poll type with automatic Yes/No options
- Hard-cutoff election mode with ballot freezing and enhanced audit
- Merkle root auto-computation on vote batch close
- Explicit poll state machine (`draft → active → closed`) with transition guards

**P2 — Federation & Scalability:**
- IPFS integration for poll/vote anchoring
- Redis caching for poll results
- Database indexing for common query patterns
- Materialized views for vote counts

**P3 — UX & Advanced Governance:**
- Real-time updates (WebSocket/SSE)
- Advanced voting methods (ranked-choice, Condorcet, approval)
- Delegated voting / liquid democracy
- Discussion threads on polls/proposals
- PWA / mobile-optimized UI

---

## Appendix A: Architecture Decision Records

### ADR #1: OIDC PKCE as Sole Auth Method
OIDC via `mozilla-django-oidc` is the sole authentication method. Username = IdP `sub` claim (the full DID). No password-based auth. Trade-off: relies on external `iyou_idp`; no local auth fallback.

### ADR #2: Pure-Python Ed25519 Verification
Vote signatures verified via `cryptography.hazmat.primitives.asymmetric.ed25519` — no bridge dependency for verification. Public key extracted from `did:key:z6M...` identifier. Trade-off: no hardware-backed verification; fully stateless.

### ADR #3: View-layer Vote Deduplication
No DB-level uniqueness constraint on `(poll, voter_did)`. Deduplication is view-layer only. Trade-off: double-insert possible under concurrent race; second insert's `is_current` flag is the canonical checkpoint.

### ADR #4: Timestamp-derived Vote Aggregation
`Max(Vote.id)` per `(poll, voter_did)` used instead of `is_current` flag for tallying. Monotonically increasing ID is a proxy for latest timestamp. Trade-off: O(n) scan per poll; acceptable at current scale.

### ADR #5: Write-in Ballot Coalescence
No DB unique constraint on `PollOption.text` per poll. Coalescence handled at view layer: NFKC normalization + `__iexact` lookup with race-guarded try/except. Trade-off: homoglyph attacks mitigated by NFKC; concurrent double-insert accepted.

### ADR #6: String-based Credential Gate
`required_credential_type` migrated from `ForeignKey(CredentialType)` to `CharField`. Inline validation stub replaces HTTP callback. Trade-off: no runtime credential schema validation.

### ADR #7: Nostr Inbound Ingestion
Two crypto domains: secp256k1/Schnorr for Nostr transport (NIP-01); Ed25519 for application-layer identity (vote signatures). Strict BIP-340 verification via `coincurve.PublicKeyXOnly`. Trade-off: Rust signer must use `sign_raw()` to avoid double SHA-256.

### ADR #8: Cross-curve User Attribution
`_resolve_user_by_nostr_pubkey()` matches secp256k1 x-only pubkey to local User Ed25519 DID via byte comparison. Filter prefix: `"did:key:z"` (NOT `"did:key:z6M"`). Trade-off: O(n) linear scan per ingested event.

### ADR #9: Clock-skew Grace for Federation
`CLOCK_SKEW_GRACE_SECONDS = 900` (15 min) tolerance for Nostr event timestamps. Future-drift guard + poll-closing guard. Trade-off: extended window may accept stale votes in high-latency scenarios.

### ADR #10: CORS Whitelist
Restrictive whitelist for `django-cors-headers`. No wildcard origins. Trade-off: must be updated per-environment.

---

## Appendix B: Testing

```bash
# Auth tests
.venv/bin/python manage.py test apps.accounts.tests.test_auth apps.accounts.tests.test_urls

# Poller tests
.venv/bin/python manage.py test apps.poller.tests.test_views apps.poller.tests.test_models

# Nostr ingestion tests
.venv/bin/python manage.py test apps.poller.tests.test_nostr_ingest

# VP credential gate tests
.venv/bin/python manage.py test apps.poller.tests.test_vp_credential_gate

# Revocation tests
.venv/bin/python manage.py test apps.poller.tests.test_revocation

# Lint
.venv/bin/python -m ruff check apps/
```

**Current test count:** 70+ passing tests across views, nostr ingestion, VP credential gate, and revocation suites.

---

## Appendix C: Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `OIDC_RP_CLIENT_ID` | Public client ID registered with iyou_idp | Yes |
| `OIDC_RP_CLIENT_SECRET` | Must be empty for public PKCE flow | No |
| `ADMIN_DID` | DID string to grant staff/superuser elevation | No |
| `NOSTR_PRIVATE_KEY` | Hex-encoded secp256k1 private key for Nostr relay publish | No (disables Nostr) |
| `NOSTR_RELAYS` | Comma-separated list of Nostr relay URLs | No |
| `IDP_BASE_INTERNAL_URL` | Internal IDP URL (K8s service) | Yes |
| `IDP_BASE_PUBLIC_URL` | Public IDP URL | Yes |
| `APP_NAME_PREFIX` | Prefix for session/CSRF cookies (default: `poly`) | No |
| `POLY_ALLOWED_HOSTS` | Comma-separated allowed hostnames | Yes |
| `POLY_SECRET_KEY` | Django secret key (insecure default for dev only) | Yes (prod) |
| `DATABASE_URL` | Database URL (defaults to sqlite) | No |
| `IDP_HOME_URL` | Home satellite URL | No |
| `IDP_HOME_WS_URL` | Home satellite WebSocket URL | No |

---

## Appendix D: Docs Structure

```
docs/
├── DEVELOPER_GUIDE.md                ← this file
├── ecosystem_shared/
│   ├── OMNI_SOCIAL_AUTH_STANDARDIZATION.md  ← platform auth rules (READ THIS FIRST)
│   ├── AUTH_FLOW_SPECIFICATION.md            ← flow diagrams
│   ├── auth_pkce.py                          ← reference implementation
│   └── satellite-coordination.md             ← multi-satellite sync
└── archive/                          ← historical docs (do not edit)
    ├── CODE_OF_CONDUCT.md
    ├── CONTRIBUTING.md
    ├── POLY_PROTOCOLv2.md
    └── VOTING_FUNCTIONALITY.md
```

# iyou_poly Developer Guide

## Project State Assessment

This document provides a comprehensive technical overview of the iyou_poly decentralized polling platform to guide future development decisions.

### Architecture Overview

iyou_poly is a Django-based decentralized polling platform using OIDC for authentication, with a credential-based authorization system and federated data synchronization.

#### **Signature-Strict Voting**

- **Requirement**: All votes must include cryptographic signatures
- **Implementation**:
  - `Vote.signature` field stores Ed25519 hex signatures (128 chars)
  - Inbound votes at `POST /api/polls/{id}/cast/` are verified via `apps/core/verification.py:verify_vote_signature()` — pure-Python Ed25519 validation with **zero network dependencies**
  - The public key is extracted directly from the `did:key:z6M...` voter DID: base58btc decode → strip `\xed` multicodec → load 32-byte key
  - Canonical payload: `json.dumps(vote_envelope, sort_keys=True, separators=(',', ':'))`
  - Bridge (`iyou_home` port 9001) is used for *signing only*; verification is local
- **Verification**: Headless endpoint validates cryptographically. Template-based votes (HTMX) still use `is_verified=True` pending full migration

#### **Cryptographic Voting Flow**

1. **User Authentication**: OIDC-based authentication via `iyou_idp`; username mapped from `sub` claim (the full DID string, e.g. `did:key:z6Mk...`)
2. **Vote Casting** (Headless mode):
   - Client sends `voter_did`, `signature`, and `vote_envelope` JSON to `POST /api/polls/{id}/cast/`
   - Server canonicalises the envelope via `json.dumps(sort_keys=True, separators=(',', ':'))`
   - Server extracts the voter's Ed25519 public key from the DID string
   - Server verifies the Ed25519 signature using `cryptography.hazmat.primitives.asymmetric.ed25519`
   - On success, vote stored with signature in database; duplicate `(poll, voter_did)` with matching signature returns 201 duplicate-success
3. **Ledger Anchoring**:
   - On-demand Merkle root calculation from last 100 vote signatures via `anchor_ledger` command
   - Merkle root is printed to stdout; not automatically stored in `Poll.votes_merkle_root`
4. **Nostr Broadcast**:
   - On every vote/poll save, `apps/poller/signals.py` calls `nostr.publish_poll()` or `nostr.publish_vote()` to broadcast kind:30023 / kind:1112 events to all configured relays
5. **Audit**:
   - `GET /api/polls/{id}/history/` returns vote history with signatures
   - Merkle root can be recalculated from signature list

#### **Signature Bridge Protocol (Port 9001)**

iyou_poly delegates cryptographic **signing** (operations requiring private keys) to the **Tauri Desktop Bridge** (`iyou_home` at `ws://127.0.0.1:9001`). The server never holds private keys. Cryptographic **verification** is handled locally by pure-Python Ed25519 in `apps/core/verification.py` — no bridge call needed.

**WebSocket Message Types:**

| Type | Payload | Response | Purpose |
|------|---------|----------|---------|
| `sign` | `{ challenge: "<uuid>" }` | `{ type: "signed", challenge, signature }` | IdP login proof — builds a Verifiable Presentation from the challenge |
| `sign_event` | `{ kind, content, tags, ... }` | `{ type: "signed_event", event }` | Nostr event signing for mesh distribution |
| `sign_credential` | `{ credential: { ...unsigned VC... } }` | `{ type: "signed_credential", vc: { ...signed VC with proof... } }` | VC issuance — bridge stamps `proof` block on the unsigned credential |

**Mesh Probe:** The nav badge (`_nav.html`) probes `http://127.0.0.1:9001/` via `fetch` with a 300ms timeout. If the bridge responds, "Sovereign Mesh Active" badge appears.

## Current Implementation Status

### Core Architecture

**Complete and Functional:**
- ✅ Django 6.0 backend with REST Framework
- ✅ OIDC-only authentication via `mozilla-django-oidc`
- ✅ Scope-based authorization with credential types
- ✅ Poll CRUD with family/organization scoping
- ✅ Proposal/funding workflows
- ✅ Embeddable widget API
- ✅ Federation data model with Nostr relay broadcast
- ✅ Ed25519 vote signature verification (`apps/core/verification.py`)
- ✅ Nostr event publishing (kind:30023 polls, kind:1112 votes)
- ✅ Temporal poll scheduling (TIMED/SCHEDULED/ONGOING) with mutable re-vote — Phase 1
- ✅ Timestamp-derived vote aggregation via `Max(id)` per `(poll, voter_did)` — Phase 1
- ✅ Write-in ballot options with NFKC normalization and view-layer coalescence — Phase 2
- ✅ Segmented leaderboards (`core_options` / `write_in_leaderboard`) — Phase 2
- ✅ Unified string-based credential gate with inline validation — Phase 3

**Partially Implemented:**
- 🟡 DID-based identity (did:key, did:ethr, did:web, did:ion) — DIDs are used in the credential/voting flow (scope checking, eligibility), but auth remains OIDC-only
- ✅ Verifiable Credential (VC) issuance — Full flow operational: Generate → Sign (via Tauri bridge) → Store → Import → Delete → Manage. See `apps/accounts/views.py` (GenerateCredentialView, StoreSignedCredentialView, VCManagementView). The bridge `sign_credential` WebSocket is still marked `xfail` in tests pending bridge-side implementation.
- ❌ IPFS/blockchain anchoring — fields exist on models but no integration code
- ❌ Real-time updates — no WebSocket/SSE implementation

### Poller App - Detailed Technical Analysis

#### Models (`apps/poller/models.py`)

**Poll Model:**
- **Poll Types**: `public`, `family_scoped`, `family_unit`, `organization`
- **Temporal Types**: `timed`, `scheduled`, `ongoing` — see TemporalPollType (Phase 1)
- **Hierarchy**: `parent_poll` FK for family/organization hierarchy
- **Embedding**: `embedding_app` field for external app filtering (e.g., `byers-brands-llc`)
- **Scope Requirements**: `required_scope_type`, `required_scope`
- **Credential Gate**: `required_credential_type` (CharField, was FK to `CredentialType` in Phase 3) — a simple string match parameter e.g. `"municipal_voter"`. Templated views compare against `CredentialIssuance.credential_type.name`; the headless API validates inline from the inbound `credential` payload.
- **Write-In Governance**: `allow_write_ins` (BooleanField), `write_in_display_limit` (PositiveIntegerField, default 5) — Phase 2
- **Mutability**: `is_mutable` (BooleanField, default False) — ONGOING polls can allow DID re-votes (Phase 1)
- **Trust System**: `min_issuer_trust_score`, `require_multiple_issuers`
- **Vote Power**: `vote_power_rule` (default `1:1`), `vote_power_ratio` (default 1.0)
- **Proposal Mode**: `is_proposal`, `funding_goal`, `funding_current`, `funding_deadline`
- **Timing**: `starts_at`, `ends_at` with `is_active_now` / `is_expired` properties
- **Decentralized Storage**: `ipfs_cid`, `blockchain_anchor`, `votes_merkle_root`, `vote_count_anchor` (fields exist, no integration)

**PollOption Model:**
- **Fields**: `poll` (FK), `text`, `votes` (DEPRECATED counter — use `dynamic_vote_count` property instead), timestamps
- **Write-In Fields**: `is_write_in` (BooleanField), `nominated_by` (CharField, voter DID who first proposed it) — Phase 2
- **Constraint Removed**: `unique_together = ("poll", "text")` was removed in Phase 2. Text-matching coalescence is handled entirely at the view layer via NFKC normalization + `__iexact` lookup, with a race-guarded try/except for concurrent creation.
- **Tallying**: `dynamic_vote_count` property uses timestamp-derived aggregation (`Max(Vote.id)` per `(poll, voter_did)`) — immune to out-of-order federation arrivals.

**Vote Model:**
- **Fields**: `poll` (FK), `option` (FK), `user` (FK, nullable), `voter_did`, `signature`, `merkle_root`, `credential_cid`, `credential_proof`, `credential_data` (JSONField, nullable — stores the un-blinded verification cred proof from Phase 3), `weight` (always 1), `ipfs_cid`, `blockchain_tx`, `is_verified`, `verification_details`, `is_current` (checkpoint flag for mutable polls)
- **Constraint**: No DB-level uniqueness on `(poll, voter_did)` — idempotency enforced at view layer
- **Mutable Checkpoint**: When a DID re-votes on an `is_mutable` poll, the previous record's `is_current` is flipped to `False` and a fresh record is ingested (Phase 1)
- **Deduplication**: View-layer idempotency — if `(poll, voter_did)` exists and signature matches, returns 201 duplicate-success; if signature differs, rejects with 400
- **Signature**: Ed25519 hex signature (128 chars) verified via `apps/core/verification.py` on the headless endpoint

**FederatedPoll:**
- Proxy model extending `FederatedData` for cross-node synchronization
- `data_type` auto-set to `"poll"` on save

#### Views (`apps/poller/views.py`)

**DRF ViewSets (via router):**
- `PollViewSet` at `api/polls/` — list/create/update/delete polls
  - `@action(detail=True, methods=["get"]) results` at `api/polls/{id}/results/` — poll results with percentages
  - `@action(detail=True, methods=["post"]) fund` at `api/polls/{id}/fund/` — add funding to proposals
- `VoteViewSet` at `api/votes/` — list votes (filterable by `poll_id`, `voter_did`)

**Function-based APIs:**
- `GET/POST /api/polls/` — `poll_api` (simple JSON poll management)
- `GET /api/polls/{id}/` — `poll_detail_api` (single poll JSON)
- `POST /api/polls/{id}/vote/` — `vote_api` (HTMX + JSON voting; delegates to `cast_vote`)
- `POST /api/polls/{id}/cast/` — **`CastVoteAPIView`** (headless DRF endpoint with Ed25519 signature verification, idempotent ingestion, v2 response envelope)
- `GET /api/polls/{id}/eligibility/` — **`CheckVotingEligibilityAPIView`** (check if voter DID can vote; v2 response envelope)
- `GET /api/polls/{id}/history/` — `get_votes` (return vote list with signatures for verification)

**Key Headless Features (`CastVoteAPIView`):**
- `@csrf_exempt`, `authentication_classes=[]`, `permission_classes=[]` — no session/auth required
- `_verify_signature()` delegates to `apps.core.verification.verify_vote_signature()` — pure Ed25519, zero network calls
- **Write-in Resolution** (Phase 2): If `write_in_text` is present in the payload, applies NFKC normalization → whitespace collapse → `__iexact` lookup on `PollOption`. Coalesces to existing authored/write-in options or creates new `PollOption` with `is_write_in=True` in a race-guarded try/except block. Rejects with 400 if `poll.allow_write_ins` is `False`.
- **Credential Gate** (Phase 3): If `poll.required_credential_type` is populated, validates the inbound `credential` payload's `type` field against the gate string. Extracts issuer/subject metadata into `Vote.credential_data` on success. Rejects with 400 + v2 error envelope `{"valid": false, "error": "Missing or invalid identity credential required for this poll type"}` on failure. Replaces the old HTTP callback to `/api/credentials/verify/`.
- **Temporal Gate** (Phase 1): Rejects votes before `starts_at` / after `ends_at` for `TIMED` and `SCHEDULED` polls; `ONGOING` polls have no temporal bounds.
- **Mutable Re-vote** (Phase 1): When `poll.is_mutable=True`, flips the prior `is_current` flag to `False` before ingesting the new vote record.
- Idempotent: existing `(poll, voter_did)` with matching signature → `{"valid": true, "details": {"duplicate": true}}` (201)
- Signature failure → `{"valid": false, "error": "Cryptographic signature validation failure."}` (401)

**Template Views:**
- `poll_list` at `/` — poll list with credential-based filtering
- `poll_detail` at `/{id}/` — poll detail with voting interface
- `CreatePollView` at `/create/` — poll creation with scope/credential requirements (text input for credential gate, not dropdown)
- HTMX-powered dynamic voting via `vote_api` (no page reload)

**Key Features:**
- **Scope-Aware Filtering**: `PollViewSet._filter_by_user_credentials()` method
- **Credential Verification**: Checks `CredentialIssuance` table + `User.vcs` JSONField; compares against `required_credential_type` string
- **Funding Workflow**: Proposal funding tracking via `fund` action
- **HTMX Integration**: Dynamic form updates without full page reloads
- **V2 Response Envelope**: All headless endpoints return `{"valid": bool, "error": str, "details": dict}` via the `ok()`/`err()` helpers

#### Serializers (`apps/poller/serializers.py`)

**Poll Serializers:**
- `PollSerializer`: Full poll representation with computed fields (exposes `required_credential_type` as a direct string, not a FK ID)
- `PollCreateSerializer`: Poll creation with option validation (accepts `required_credential_type` as a plain string)
- `PollResultsSerializer`: Results with percentage calculations — splits options into `core_options` (authored) and `write_in_leaderboard` (crowd-sourced, truncated to `write_in_display_limit`) — Phase 2

**Vote Serializers:**
- `VoteSerializer`: Full vote representation (exposes `credential_data` JSONField — Phase 3)
- `VoteCreateSerializer`: Vote casting with optional `credential` (JSONField), `credential_cid`, and `write_in_text` (Phase 2) fields

#### Embed System (`apps/poller/embed.py`)

**EmbeddablePollWidget** at `/api/embed/polls/` and `/api/embed/polls/{id}/`:
- **Parameters**: `embedding_app`, `user_did`, `scope`, `theme`
- **Visibility Logic**: `_can_user_view_poll()` — checks embedding_app match, poll type, user scopes
- **Scope Filtering**: `_filter_by_scopes()` — filters polls by user's credential scopes
- **Limits**: Returns max 10 polls (newest first)

**EmbedPollView (unused in URLs):**
- Returns JSON with HTML snippet for iframe embedding
- JavaScript fetches poll data dynamically

#### Signals (`apps/poller/signals.py`)

**Poll Federation:**
- `sync_poll_on_save` (post_save, sender=Poll): Converts Poll → FederatedData entry; increments version on updates; calls `nostr.publish_poll(poll)`
- `sync_poll_on_delete` (post_delete, sender=Poll): Marks FederatedData as inactive
- `sync_poll_option_on_save` (post_save, sender=PollOption): Re-syncs poll on option changes (skips creation)
- `sync_vote_on_save` (post_save, sender=Vote): On creation, increments `PollOption.votes` counter via `F()` expression, then updates the poll's FederatedData entry version and calls `nostr.publish_vote(vote, poll.id)`

**Nostr Integration (new):**
- `apps/poller/nostr.py` — Schnorr-secp256k1 event construction, relay publish/subscribe via `websockets`
- Kind:30023 for poll definitions, kind:1111/1112 for vote envelopes
- Instance keypair loaded from `NOSTR_PRIVATE_KEY` env var or generated ephemerally
- Gossip worker (`gossip_worker.py`) is now an async Nostr subscription loop

### Authentication System

**Identity Model:**
- **Passwords are DEPRECATED.** The project uses OIDC exclusively. No password-based backends are registered; no standard Django login views are used.
- **Primary entry point:** `http://127.0.0.1:8002/oidc/authenticate/` redirects to `iyou_idp` at `http://127.0.0.1:8000/openid/authorize/`. The IdP returns the `sub` claim, which becomes the user's `username` (the DID).
- **Session:** `poly_sessionid` cookie, `SameSite=Lax`, `HttpOnly=True`. Prevents collisions with WUN/IdP cookies.

**Current Implementation:**
- ✅ OIDC-only authentication via `mozilla-django-oidc` + `MyOIDCAuthenticationBackend` (in `apps/accounts/backends.py`)
- ✅ Username = IdP `sub` claim (no separate DID field for new users)
- ✅ Credential-based authorization via `User.vcs` JSONField and `CredentialIssuance` table
- ❌ Traditional password auth removed
- ❌ DID-based backends (`DIDAuthBackend`, `OIDCAuthBackend`) fully removed — no trace remains even in dead code

**Models (in `apps/accounts/models.py`):**
- `User` (extends `AbstractUser`): `username` holds the IdP `sub`; deprecated `did`/`did_key`/`did_method` fields for legacy data; `vcs` JSONField active for VC storage with metadata format
- `FederatedIdentity`: Maps external OIDC provider identities to users

**Key User Model Methods:**
- `add_vc(vc, name)`: Add VC with dedup and auth-VC protection
- `get_vcs_by_type(vc_type)`: Filter VCs by credential type
- `get_other_vcs()`: Get non-authentication VCs
- `get_authentication_vc()`: Get the auth VC
- `ensure_vcs_migrated()`: Migrate old-format VCs to new metadata format

### Federation Protocol

**Data Model Location:** `apps/core/models.py`

**Core Models:**
- `FederatedNode`: Registered peer nodes (name, endpoint, public_key, is_active)
- `FederatedData`: Synchronized data entries (node, data_type, data_id, data JSON, version, is_active)
- `SyncMessage`: Gossip protocol messages (message_id, message_type, sender, signature, payload, previous_hash, proof_of_work, is_processed)
- `DataSyncLog`: Sync event audit trail (source/target node, data_type, data_id, status)

**Signal-Based Sync:** `apps/core/signals.py`
- `log_federated_data_on_save`: Audit-logs local FederatedData changes (network dispatch removed in v2 — replaced by Nostr)
- `log_federated_data_on_delete`: Audit-logs deletion events
- **Note**: HTTP dispatch stubs removed in v2. Mesh propagation happens via `apps/poller/signals.py` → `nostr.publish_*()`

**Conflict Resolution:** `apps/core/utils.py`
- `ConflictResolution.resolve(data_a, data_b)`: Last-write-wins by version, then timestamp
- `ConflictResolution.resolve_multiple(versions)`: Iterative pairwise resolution

**Message Validation:**
- `ProofOfWork.compute(data, difficulty)`: SHA-256 hash with leading-zero requirement
- `ProofOfWork.verify(data, hash, nonce, difficulty)`: Validates PoW

**Message Types:**
- `announce`, `request`, `response`, `vote`, `credential`, `poll`, `merkle_update`, `ping`, `pong`

**Gossip Worker:** `apps/poller/management/commands/gossip_worker.py`
- Async Nostr subscription loop listening for kind:30023 and kind:1111 events from all configured relays
- Reconnects on failure with 30s backoff
- Disabled when `NOSTR_PRIVATE_KEY` is not set (`NOSTR_ENABLED = False`)

### Core Data Models (`apps/core/models.py`)

**DID System:**
- `DIDMethod`: Registry of DID methods (key, web, ion, ethr)
- `DID`: User-associated DIDs (method, identifier, did_uri, is_primary)
- `DIDDocument`: JSON document per DID (public keys, service endpoints)

**Scope System:**
- `ScopeType`: Registry of scope types with hierarchy (geographic, organization, company, family); supports parent-child authorization chains
- `Scope`: Specific scope instances within a type; supports parent-child hierarchy

**Credential System:**
- `CredentialType`: Defines credential types (name, display_name, scope_type, parent_credential_type, max_issuers, requires_approval, min_approvals)
- `VerifiableCredential`: Stored VCs linked to users (user FK, credential JSON, issuer DID, is_active)
- `CredentialIssuance`: Full audit trail of credential issuance (holder_did, issuer_did, credential_type, scope, ipfs_cid, blockchain_tx, status)
- `IssuerAuthorization`: Which issuers are authorized for which credential types and scopes
- `IssuerMetrics`: Trust metrics per issuer per scope (total issued, unique holders, verifications, scope violations)
- `IssuerEndorsement`: Peer endorsements between issuers within a scope

### Trust System

**Implementation:** `apps/core/utils.py` — `TrustScorer` class

**Current Implementation:**
- ✅ Trust scoring (0.0-1.0) via `TrustScorer.calculate_score(metrics)`
- ✅ Issuer metrics tracking via `IssuerMetrics` model
- ✅ Peer endorsements via `IssuerEndorsement` model
- ✅ Scope violation detection
- ✅ Dynamic threshold compliance via `get_trust_level(score)`

**Scoring Factors:**
- Verification success rate (30%)
- Peer endorsements (20%)
- Time since first issuance (15%)
- Unique holders (15%)
- Scope violations (-20% penalty, 0.05 per violation cap 0.5)

**Trust Levels:** `low` (≥0.0), `medium` (≥0.4), `high` (≥0.7), `very_high` (≥0.9)

## Technical Debt & Areas for Improvement

### Critical Issues

1. **Federation Consistency:**
   - Version vectors may not handle concurrent updates correctly
   - No transactional consistency across nodes

2. **Performance:**
   - Poll list queries with complex credential filtering
   - Vote counting requires full option table scans
   - No caching layer for frequently accessed polls

3. **Security:**
   - Credential verification happens synchronously in vote flow
   - No rate limiting on vote endpoints
   - Template-based (HTMX) votes still use `is_verified=True` without cryptographic verification

### Major Refactoring Opportunities

1. **Federation Overhaul:**
   - Implement proper CRDTs for conflict-free data types
   - Add transactional outbox pattern for reliable messaging
   - Implement Merkle tree verification for vote integrity
   - **Completed**: HTTP dispatch stubs removed; Nostr relay broadcast operational

2. **Performance Optimization:**
   - Add Redis caching for poll results
   - Implement materialized views for vote counts
   - Add database indexing for common query patterns

3. **Security Enhancements:**
   - Asynchronous credential verification
   - Rate limiting and DDoS protection
   - Full IPFS/blockchain integration
   - **Completed**: Pure-Python Ed25519 signature verification in headless endpoint

4. **API Design:**
   - Standardize error responses → **in progress**: `CastVoteAPIView` and `CheckVotingEligibilityAPIView` use v2 `{"valid": bool, ...}` envelope
   - Add pagination to all list endpoints
   - Implement proper ETag/Last-Modified headers

### Missing Features

1. **Real-time Updates:**
   - WebSocket implementation for live results
   - Server-Sent Events for poll updates
   - Push notifications for vote events

2. **Advanced Polling:**
   - Ranked choice voting
   - Condorcet method support
   - Approval voting

3. **Governance:**
   - Delegated voting
   - Liquid democracy features
   - Proposal discussion threads

4. **Mesh Inbound:**
   - **Completed**: Outbound Nostr broadcast for polls/votes
   - **🚧 Inbound**: Gossip worker logs inbound events but does not yet upsert polls or ingest votes from the mesh
   - **🚧**: Vote ingestion from Nostr kind:1112 events into the local database

5. **Mobile:**
   - PWA manifest and service worker
   - Offline-first capabilities
   - Mobile-optimized UI components

## Development Recommendations

### Short-term (Next 3 Months)

1. **Nostr Inbound Ingestion:**
   - Upsert polls from inbound kind:30023 events
   - Idempotent vote ingestion from inbound kind:1112 events
   - Verify Schnorr transport signatures on inbound Nostr events

2. **Performance:**
   - Add Redis caching layer
   - Optimize credential filtering queries
   - Implement database indexing

3. **Security:**
   - Add rate limiting to headless endpoints
   - Migrate HTMX voting to cryptographic verification
   - Add proper CORS configuration

### Medium-term (3-6 Months)

1. **Real-time Features:**
   - WebSocket implementation
   - Live result updates
   - Notification system

2. **Advanced Voting Methods:**
   - Ranked choice voting
   - Condorcet method
   - Approval voting

3. **Enhanced Federation:**
   - Merkle tree verification
   - Blockchain anchoring
   - IPFS integration

### Long-term (6-12 Months)

1. **Mobile Strategy:**
   - PWA implementation
   - Offline capabilities
   - Mobile SDK

2. **Governance Features:**
   - Delegated voting
   - Liquid democracy
   - Discussion threads

3. **Scalability:**
   - Horizontal scaling
   - Sharding strategy
   - Multi-region deployment

## Migration Strategy

### Backward Compatibility

**Breaking Changes to Expect:**
- Federation protocol changes will require node coordination
- Database schema changes for performance optimization
- API endpoint restructuring

**Migration Path:**
1. Implement new features behind feature flags
2. Maintain dual API versions during transition
3. Provide migration scripts for database changes
4. Document breaking changes clearly

### Testing Strategy

**Current Coverage:**
- Unit tests for core models
- Integration tests for API endpoints
- E2E tests for voting workflows

**Recommended Additions:**
- Federation consistency tests
- Load testing for performance
- Security penetration testing
- Cross-browser compatibility tests

## Architecture Decision Records

### Key Decisions Made

1. **Django Framework:**
   - Chosen for rapid development and admin interface
   - Trade-off: Less flexible than FastAPI for async operations

2. **OIDC-based Authentication:**
   - OIDC via `mozilla-django-oidc` as sole auth method; username = IdP `sub` claim
   - Trade-off: Relies on external IdP (`iyou_idp`); local auth not available

3. **Scope-based Authorization:**
   - Flexible scope system for geographic/organizational polling
   - Trade-off: Complex credential filtering logic

4. **Federation Protocol:**
   - Gossip protocol replaced by Nostr relay broadcast for v2
   - Trade-off: Eventual consistency across relays vs strong consistency

5. **Signature Verification:**
   - Pure-Python Ed25519 via `cryptography` library (no bridge dependency)
   - DID public key extracted locally from `did:key:z6M...` identifier
   - Trade-off: No hardware-backed verification; fully stateless

6. **Idempotency:**
   - No DB-level uniqueness constraint on `(poll, voter_did)` — View-layer only
   - `CastVoteAPIView` handles deduplication with signature-match check
   - Trade-off: Double-insert possible under concurrent race; second insert's `is_current` flag is the canonical checkpoint

7. **Write-In Ballot Options (Phase 2):**
   - **No DB unique constraint** on `PollOption.text` per poll — `unique_together` removed
   - Coalescence handled at view layer: NFKC normalization + `__iexact` lookup with race-guarded try/except
   - `is_write_in` flag + `nominated_by` DID for audit trail
   - Leaderboard split into `core_options` / `write_in_leaderboard` via `PollResultsSerializer`
   - Trade-off: Homoglyph attacks mitigated by NFKC; concurrent double-insert of identical write-in accepted (view-layer coalescence on subsequent votes)

8. **Credential Gate (Phase 3):**
   - `required_credential_type` migrated from `ForeignKey(CredentialType)` to simple `CharField`
   - Inline validation stub replaces HTTP callback to `/api/credentials/verify/`
   - Credential metadata stored in `Vote.credential_data` JSONField
   - Trade-off: No runtime credential schema validation; relies on client to provide well-formed `credential` payload

### Future Architecture Decisions

1. **Real-time Protocol:**
   - WebSockets vs Server-Sent Events vs polling
   - Recommendation: WebSockets for bidirectional communication

2. **Database:**
   - SQLite (dev) vs PostgreSQL (prod)
   - Recommendation: PostgreSQL for production scalability

3. **Frontend Framework:**
   - Current: Django templates + HTMX
   - Future: React/Vue for complex interactions

## Getting Started for Developers

### Development Setup

```bash
# Clone repository
git clone https://github.com/Code-Barn/iyou_poly.git
cd iyou_poly

# Install dependencies
uv sync

# Run migrations
uv run python manage.py migrate

# Start server
uv run python manage.py runserver 127.0.0.1:8002
```

### Key Development Areas

1. **Nostr & Mesh Federation:**
   - `apps/poller/nostr.py` — Event construction, Schnorr signing, relay publish/subscribe
   - `apps/poller/signals.py` — Signal handlers calling `nostr.publish_*()`
   - `apps/poller/management/commands/gossip_worker.py` — Async Nostr subscription loop
   - `apps/core/signals.py` — Audit logging (HTTP dispatch removed in v2)

2. **Cryptographic Verification:**
   - `apps/core/verification.py` — `verify_vote_signature()` pure Ed25519 validation
   - `apps/poller/views.py` — `CastVoteAPIView._verify_signature()` integration

3. **Polling:**
   - `apps/poller/models.py` — Data models
   - `apps/poller/views.py` — API and template views

4. **Authentication:**
   - `apps/accounts/models.py` — User model with VC storage
   - `apps/accounts/backends.py` — `MyOIDCAuthenticationBackend` (OIDC identity bridge)

### Testing

```bash
# Run all tests (Django test runner)
uv run python manage.py test

# Run with pytest (faster, better output)
uv run pytest apps/poller/tests/ -v

# Run with coverage
uv run pytest --cov=apps

# Run a specific test class
uv run pytest apps/poller/tests/test_views.py::CredentialGateTests -v

# Run excluding pre-existing DataSyncLog failures
uv run pytest apps/poller/tests/test_views.py -v -k "not test_poll_vote_count"
```

**Current Test Coverage (as of Phase 3):**
- **22 passing tests** across 7 test classes in `apps/poller/tests/test_views.py`:
  - `PollListViewTests` (2) — list accessibility, content
  - `PollDetailViewTests` (1) — detail accessibility
  - `PollCreateViewTests` (2) — auth gate, authenticated access
  - `VoteAPITests` (7) — authenticate, counter, unauthenticated reject, duplicate, validation, public poll, HTMX
  - `TemporalPollingTests` (11) — scheduled/timed/ongoing/mutable, dynamic tally, aggregation ordering
  - `WriteInBallotTests` (7) — disabled reject, normalization coalescence, option creation, authored coalescence, mutable re-vote, serializer split, leaderboard truncation
  - `CredentialGateTests` (3) — blank gate accepts, missing credential rejects, valid credential stored
- 10 pre-existing failures in template-based endpoints caused by `DataSyncLog` F() expression bug (`apps/core/signals.py:63`) — unrelated to polling features
- 4 passing tests in `apps/poller/tests/test_models.py` (3 fail from same `DataSyncLog` bug)

## Conclusion

iyou_poly provides a solid foundation for decentralized polling with:
- OIDC-based authentication via `iyou_idp`
- Flexible scope-based authorization with credential types
- Federation via Nostr relay broadcast (polls + votes)
- Embeddable widget API
- Proposal/funding workflows
- Extensible scope/credential system (ScopeType, CredentialType, CredentialIssuance)
- Pure-Python Ed25519 signature verification (no bridge dependency)
- Headless idempotent ingestion endpoint (`CastVoteAPIView`) with v2 response envelope
- Temporal poll scheduling (`TIMED`/`SCHEDULED`/`ONGOING`) with mutable re-vote support
- Timestamp-derived vote aggregation using `Max(id)` per `(poll, voter_did)` — resilient to out-of-order federation
- Write-in ballot options with NFKC normalization and view-layer text coalescence
- Segmented leaderboards (`core_options` / `write_in_leaderboard`) with configurable display limits
- Unified string-based credential gate with inline validation

**Key Focus Areas for Next Phase:**
1. Fix `DataSyncLog` F() expression bug in `apps/core/signals.py:63` (affects all template-based vote tests)
2. Migrate template-based voting to full cryptographic verification
3. Inbound Nostr event ingestion (upsert polls, ingest votes from mesh)
4. Implement real-time updates
5. Add advanced voting methods (ranked choice, Condorcet, approval)
6. Enhance mobile support

**Recently Completed (Phases 1–3):**
- **Phase 1** — Temporal polling states (TIMED/SCHEDULED/ONGOING), `is_mutable` re-vote, timestamp-derived `Max(id)` aggregation, `is_current` checkpoint flag
- **Phase 2** — Write-in ballot options with NFKC normalization, view-layer coalescence, segmented leaderboards (`core_options` / `write_in_leaderboard`), 7 write-in tests
- **Phase 3** — Unified string-based credential gate (`required_credential_type` CharField), inline validation stub in `CastVoteAPIView`, `Vote.credential_data` storage, 3 credential gate tests, full FK→string refactor across 47 references

The architecture supports the planned features but requires refinement in federation consistency and performance optimization before production deployment.

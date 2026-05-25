# 🗳️ iyou_poly Protocol Specification v2

## 1. Objective & Architectural Intent

The `iyou_poly` protocol establishes the foundational rules, cryptographic guarantees, data schemas, and synchronization behaviors for a verifiable, decentralized, and multi-tenant polling/governance engine.

### 1.1 The Sovereign Mesh Mandate

Within the Omni-Social infrastructure, the protocol functions across a dual-phase architectural roadmap:

1. **Server Deployment Mode (Active Baseline):** Operates as a stateless backend calculation service that handles multi-tenant, credential-scoped polling requests proxied via headless endpoints.
2. **Embedded Daemon Mode (Long-Term Evolution):** Compiles down into an un-deplatformable local background listener/relay service running natively within the user's local `iyou_home` desktop suite. In this mode, it acts as a resilient peer-to-peer ledger mirror to handle regional network splits, political forks, or internet brownouts.

### 1.2 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    SOVEREIGN MESH                        │
├────────────┬────────────────┬───────────────────────────┤
│  iyou_idp  │   iyou_poly    │       iyou_home           │
│  :8000     │   :8002        │       :9001               │
│  (IdP)     │   (Governance) │       (Tauri Bridge)      │
├────────────┼────────────────┼───────────────────────────┤
│ OIDC auth  │ Poll CRUD      │ did_rust crypto           │
│ DID mgmt   │ Vote casting   │ Key generation            │
│ Challenge  │ VC management  │ VC signing                │
│  signing    │ Scope system   │ Nostr event signing       │
│            │ Federation DM  │ Local verification         │
│            │ Embed widget   │                           │
└────────────┴────────────────┴───────────────────────────┘
```

---

## 2. Component Responsibility Matrix

### Integration Status Key

| Tag | Meaning |
|-----|---------|
| ✅ | Implemented in this repository (`iyou_poly`) |
| 🔧 | Delegated to an external mesh component (`iyou_home`, `iyou_idp`, `iyou_wun`) |
| 🚧 | Defined in the spec but not yet implemented |

### Responsibility Matrix

| Capability | Core Component | Transport Protocol / Interface | Strategy & Isolation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Sovereign Key Custody** | `iyou_home` | Hardware/Enclave (`did_rust`) | Private keys remain strictly sealed inside the client vault. | 🔧 Delegated |
| **Payload Signing** | `iyou_home` | Local WebSocket (`ws://127.0.0.1:9001`) | Generates cryptographically signed envelopes upon explicit user approval. | 🔧 Delegated |
| **Social Discovery / UI** | `iyou_wun` | Web presentation / Browser | Renders feeds, manages interactive voting states, handles fallback Auditor Mode. | 🔧 Delegated |
| **Stateless Calculation** | `iyou_poly` | Headless REST API (`X-Iyou-Wun-Proxy`) | Tallies records, verifies signature math, tracks aggregate data inputs. | ✅ Implemented |
| **Federation Transport** | Nostr Network | Relays (NIP-01 WebSockets) | Propagates definitions and verified votes globally across the peer-to-peer mesh. | ✅ Implemented |
| **OIDC authentication** | `iyou_idp` | OIDC Protocol | Federated identity provider at `127.0.0.1:8000`. | 🔧 Delegated |
| **User session & auth backend** | `iyou_poly` | Django `mozilla-django-oidc` | Session management, claims mapping. | ✅ Implemented |
| **Poll CRUD & voting** | `iyou_poly` | Django ORM + DRF | Full lifecycle: create, vote, tally, audit. | ✅ Implemented |
| **Credential issuance & management** | `iyou_poly` | Django ORM + DRF | Scope-credential issuance, verification, trust scoring. | ✅ Implemented |
| **Scope-based authorization** | `iyou_poly` | DRF ViewSet filters | Per-poll scope/credential eligibility checking. | ✅ Implemented |
| **Merkle root calculation** | `iyou_poly` | `apps/poller/utils/merkle.py` | SHA-256 Merkle root of vote signatures. | ✅ Implemented |
| **Federation data model** | `iyou_poly` | `apps/core/models.py` | `FederatedNode`, `FederatedData`, `SyncMessage`, `DataSyncLog`. | ✅ Implemented |
| **Embeddable widget** | `iyou_poly` | Template-based | `GET /api/embed/polls/` with scope/theme parameters. | ✅ Implemented |
| **Cryptographic signing (`did_rust`)** | `iyou_home` | WebSocket bridge | All signing delegated; `iyou_poly` never holds private keys. | 🔧 Delegated |
| **Key generation & storage** | `iyou_home` | Hardware/Enclave | Keys never leave the client. | 🔧 Delegated |
| **Verifiable Credential signing** | `iyou_home` | WebSocket `sign_credential` | Bridge stamps `proof` block. Pending bridge endpoint — marked `xfail` in tests. | 🔧 Delegated |
| **Vote DID-signature verification** | `iyou_poly` | Pure-Python Ed25519 (`apps/core/verification.py`) | True mathematical verification via `did:key:z6M...` public key extraction. | ✅ Implemented |
| **Blossom/IPFS ledger anchoring** | — | — | Finalized ledger/Merkle root publication. Not implemented. | 🚧 Planned |
| **Nostr event broadcast** | `iyou_poly` | NIP-01 WebSockets | Poll definitions (kind:30023) and vote envelopes (kind:1112) published to relays. | ✅ Implemented |
| **Real-time updates (WebSocket/SSE)** | — | — | No real-time subscription layer yet. | 🚧 Planned |

---

## 3. Cryptographic Invariants & Identity Format

### 3.1 Voter Identity Suffix

Voter identities must be formatted as standardized W3C Decentralized Identifiers utilizing the `did:key` Ed25519 multicodec standard:

```
did:key:z6M[Base58-encoded multicodec public key payload]
```

### 3.2 Pure Mathematical Signature Verification

To preserve complete stateless separation and ensure seamless execution whether running as a cloud server or an embedded desktop daemon, the verification of an inbound vote payload requires **zero network dependencies**. Nodes must parse the public key out of the `voter_did` string locally via application-layer base58btc decoding and evaluate the hex signature array natively using standard Ed25519 primitives.

The implementation lives in `apps/core/verification.py:verify_vote_signature()`. The function:

1. Strips the `did:key:` prefix and `z` multibase marker from the DID.
2. Base58btc-decodes the remaining payload.
3. Validates the `\xed` multicodec prefix (Ed25519 public key).
4. Extracts the 32-byte public key and loads it as an `Ed25519PublicKey`.
5. Verifies the hex signature against the canonical JSON serialisation of the vote envelope.
6. Returns `True` or `False` with no network calls.

### 3.3 Sybil Resistance Constraint

The database-layer unique boundary must remain strictly tied to a single voter instance per poll definition:

```python
unique_together = ("poll", "voter_did")
```

Deduplication is enforced at the application view layer. If an incoming vote matches an existing voter/poll record and the signature aligns perfectly, it resolves as a graceful transaction duplicate-success (201 Created). If choice or signature properties conflict, the transaction is rejected instantly (400/401 Bad Request).

### 3.4 OIDC Authentication & Session Model

- **OIDC-Only Authentication:** All users authenticate through `iyou_idp` at `127.0.0.1:8000` via OpenID Connect. The `mozilla-django-oidc` library handles the protocol. No password-based backends are registered.
- **Primary Identifier:** The OIDC `sub` claim contains the user's full DID string (e.g., `did:key:z6Mk...`). This becomes `User.username` and is used throughout the codebase as `voter_did`.
- **Legacy Password Auth:** Strictly disabled. The `login/` and `logout/` routes redirect to OIDC endpoints. Only `MyOIDCAuthenticationBackend` is registered.
- **Session Cookie:** `poly_sessionid`, `SameSite=Lax`, `HttpOnly=True`. Prevents collision with IdP cookies on `127.0.0.1`.
- **DID Usage in Voting Flow:** DIDs are queried for credential lookup and scope checking during vote eligibility. See `apps/poller/views.py` — `user.dids.filter(is_primary=True)`.
- **WebAuthn:** Future consideration for hardware key support. Not implemented.

### 3.5 Sovereign Spectrum

Supports two modes of key management:

- **Managed Mode (Level 1):** Cloud-based key management via `iyou_idp`.
- **Sovereign Mode (Level 2):** Local key signing via the `iyou_home` WebSocket bridge at `ws://127.0.0.1:9001`.

---

## 4. Nostr Global Framing & Schema Standards

To ensure external Nostr relays pass, index, and cache data cleanly without causing namespace parsing logjams in the social feed, governance structures are bifurcated into two specific event kinds.

### 4.1 Nostr Kind 30023: Parameterized Replaceable Poll Definition

Used to define and broadcast a poll's rules, configuration boundaries, and geographic scope requirements.

```json
{
  "id": "canonical_poll_event_id_hex",
  "pubkey": "creator_nostr_public_key",
  "kind": 30023,
  "created_at": 1716500000,
  "tags": [
    ["d", "poll:unique_poll_id_uuid"],
    ["title", "The Regional Governance Split Survey"],
    ["option", "opt_01", "Option A: Maintain Shared Infrastructure"],
    ["option", "opt_02", "Option B: Establish Independent Node Sync"],
    ["geohash", "dp3w"],
    ["org", "county-clerk-office"],
    ["expires", "1719100000"]
  ],
  "content": "Detailed markdown explanation of the ballot question and systemic choices goes here.",
  "sig": "schnorr_signature_hex"
}
```

### 4.2 Nostr Kind 1112: The Governance Vote Envelope

Used to broadcast and distribute verified vote transactions. This is kept entirely separated from standard kind:1111 nested text comment schemas.

- **The Outer Frame:** Structured as a native Nostr envelope utilizing network-layer secp256k1 keys for valid relay routing and indexing.
- **The Inner Frame (`content`):** Holds the raw, idempotent, stringified Omni-Social JSON Vote Envelope, carrying the voter's true Ed25519 `did_rust` signature identity.

```json
{
  "id": "transport_event_id_hex",
  "pubkey": "carrier_or_user_nostr_pubkey",
  "kind": 1112,
  "created_at": 1716501500,
  "tags": [
    ["a", "30023:creator_nostr_public_key:poll:unique_poll_id_uuid"],
    ["p", "voter_identity_did_string"]
  ],
  "content": "{\n  \"voter_did\": \"did:key:z6M...\",\n  \"signature\": \"ed25519_hex_signature_of_envelope_bytes\",\n  \"vote_envelope\": {\n    \"poll_id\": \"unique_poll_id_uuid\",\n    \"option_id\": \"opt_01\",\n    \"timestamp\": 1716501480\n  }\n}",
  "sig": "schnorr_transport_signature_hex"
}
```

### 4.3 Event Broadcast Implementation

Both event kinds are signed with the instance's secp256k1 keypair (via `coincurve`) and published to all configured Nostr relays using NIP-01 WebSocket messaging. The module at `apps/poller/nostr.py` provides:

- `get_instance_keypair()` — Loads or generates the instance Nostr keypair.
- `make_event(kind, content, tags)` — Constructs and Schnorr-signs a Nostr event.
- `make_poll_event(poll)` — Builds kind:30023 from a `Poll` model instance.
- `make_vote_event(vote, poll_id)` — Builds kind:1112 with the Ed25519 voter signature in `content`.
- `publish_event(event)` — Broadcasts to all relays; returns list of accepting relays.
- `subscribe_loop(relay, kinds, on_event)` — Long-lived subscription for the gossip worker.

---

## 5. API Interface: Headless Proxy Operations

To facilitate automated ingestion from decoupled discovery portals (`iyou_wun`), calculation engines must expose public endpoints unburdened by browser session logic or CSRF constraints.

### 5.1 Request Ingestion Blueprint

- **Endpoint:** `POST /api/v2/polls/{poll_id}/cast/`
- **Mandatory Header:** `X-Iyou-Wun-Proxy: true`
- **Payload Format:** Strict Omni-Social JSON Structure

```json
{
  "voter_did": "did:key:z6M...",
  "signature": "hex_string",
  "vote_envelope": {
    "poll_id": "string",
    "option_id": "string",
    "timestamp": 1234567890
  }
}
```

### 5.2 Deterministic Canonical Serialization Rule

Before calculating or checking signatures against the inner `vote_envelope` bytes, the runtime context must force strict canonical serialization. This guarantees uniform sorting regardless of which language (Python in Django, Rust in Tauri, or JavaScript in the Browser) compiles or reads the parameters:

```python
json.dumps(vote_envelope, sort_keys=True, separators=(',', ':')).encode('utf-8')
```

### 5.3 Unified API Response Envelope

All views must catch mutations and return the unified platform signature envelope:

```json
{"valid": true, "error": "", "details": { "vote_id": 412, "duplicate": false }}

{"valid": false, "error": "Cryptographic signature validation failure.", "details": {}}
```

### 5.4 Current DRF Endpoint (Pre-v2 Transition)

The current `CastVoteAPIView` at `POST /api/polls/{id}/cast/` uses the v2 response envelope and headless auth bypass (`@csrf_exempt`, `authentication_classes=[]`, `permission_classes=[]`). The endpoint name will migrate to `/api/v2/polls/{id}/cast/` in a future release.

---

## 6. Voting Power & Transparency

- **Default Rule:** **1:1** (one user, one vote). `vote_power_ratio` defaults to 1.0 on the `Poll` model.
- **Weighted Voting:** Custom ratios are declared in poll metadata via `vote_power_rule` (CharField, e.g., `"investor_share"`, `"daily"`) and `vote_power_ratio` (FloatField, default 1.0). Both fields are exposed in the API serializers.
- **Visual Mandate:** Any poll with a non-1:1 ratio displays the gear icon ⚙️ with a tooltip explaining the voting power calculation:
  ```html
  <span class="cursor-help"
        title="Custom voting power: {{ poll.vote_power_rule }}
               ({{ poll.vote_power_ratio }}x multiplier)">⚙️</span>
  ```
  - `apps/poller/templates/poller/poll_list.html:111` — ⚙️ in poll cards.
  - `apps/poller/templates/poller/poll_detail.html:14` — ⚙️ in poll detail.
- **Scope Filtering UI:** Poll list includes dropdown filters for scope type and scope value. Per-poll requirement badges show scope type, scope value, and required credential type. See `apps/poller/templates/poller/poll_list.html:7-86`.
- **🚧 `/api/polls/{id}/rules` Endpoint:** Defined in the spec but not implemented. Vote power rules are currently exposed inline in the poll serializers, not via a dedicated endpoint.

---

## 7. Federation & The Omni-Social Mesh

### 7.1 Data Model

The federation data layer exists in `apps/core/models.py`:

| Model | Purpose | Status |
|-------|---------|--------|
| `FederatedNode` | Registered peer nodes (name, endpoint, public_key, is_active) | ✅ Implemented |
| `FederatedData` | Synchronized data entries (node, data_type, data_id, data JSON, version, is_active) | ✅ Implemented |
| `SyncMessage` | Gossip protocol messages (message_id, message_type, sender, signature, payload, previous_hash, proof_of_work, is_processed) | ✅ Implemented |
| `DataSyncLog` | Sync event audit trail (source/target node, data_type, data_id, status) | ✅ Implemented |

### 7.2 Signal-Based Sync

- `apps/core/signals.py` — `log_federated_data_on_save` and `log_federated_data_on_delete` audit-log local `FederatedData` changes. Network dispatch is removed in favour of the Nostr protocol layer.
- `apps/poller/signals.py` — `sync_poll_on_save`, `sync_poll_on_delete`, `sync_poll_option_on_save`, `sync_vote_on_save` convert local model changes into `FederatedData` entries and call `nostr.publish_poll()` / `nostr.publish_vote()` for mesh propagation.

### 7.3 Gossip Worker

`apps/poller/management/commands/gossip_worker.py` runs an async Nostr subscription loop that listens for kind:30023 (poll) and kind:1111/1112 (vote) events from all configured relays. Inbound events are logged; future iterations will upsert polls and ingest votes directly from the mesh.

### 7.4 Conflict Resolution

`apps/core/utils.py` — `ConflictResolution.resolve(data_a, data_b)` implements last-write-wins by version, then timestamp. `ConflictResolution.resolve_multiple(versions)` provides iterative pairwise resolution.

### 7.5 Planned but Not Implemented (🚧)

- **Blossom/IPFS Publishing:** Shared audit ledgers via Blossom/IPFS. Not implemented.
- **`iyou_wun` Global Aggregation:** Global-scoped polls aggregated by the satellite app. Not implemented.

---

## 8. API Reference

### 8.1 Response Format Convention

All v2 APIs use the unified response envelope:

```json
{"valid": true, "error": "", "details": { ... }}
{"valid": false, "error": "Description of error", "details": { ... }}
```

> **v1 legacy:** Function-based views historically returned `{"status": "success", "data": ...}` / `{"status": "error", "message": "..."}`. These will migrate to the v2 envelope in a transitional release.

### 8.2 Poll & Vote Endpoints

| Method | Endpoint | Description | View | Response Envelope |
|--------|----------|-------------|------|-------------------|
| GET, POST | `/api/polls/` | List / create polls | `PollViewSet` | DRF default / v2 (transitioning) |
| GET, PUT, PATCH, DELETE | `/api/polls/{id}/` | Poll detail / update / delete | `PollViewSet` | DRF default |
| GET | `/api/polls/{id}/results/` | Poll results with percentages | `PollViewSet.results` | DRF default |
| POST | `/api/polls/{id}/fund/` | Add funding to proposal | `PollViewSet.fund` | DRF default |
| GET, POST | `/api/votes/` | List / create votes | `VoteViewSet` | DRF default |
| GET, PUT, PATCH, DELETE | `/api/votes/{id}/` | Vote detail / update / delete | `VoteViewSet` | DRF default |
| POST | `/api/polls/{id}/vote/` | HTMX + JSON vote casting | `vote_api` | Legacy `{"status": ...}` |
| POST | `/api/polls/{id}/cast/` | DRF vote casting (headless, idempotent) | `CastVoteAPIView` | ✅ v2 `{"valid": ...}` |
| GET | `/api/polls/{id}/history/` | Vote history with signatures for audit | `get_votes` | Legacy `{"status": ...}` |
| GET | `/api/polls/{id}/eligibility/` | Check if `voter_did` can vote | `CheckVotingEligibilityAPIView` | ✅ v2 `{"valid": ...}` |

### 8.3 Embed Widget Endpoints

| Method | Endpoint | Description | View | Status |
|--------|----------|-------------|------|--------|
| GET | `/api/embed/polls/` | Embeddable poll list (params: `embedding_app`, `user_did`, `theme`, `scope`) | `EmbeddablePollWidget` | ✅ |
| GET | `/api/embed/polls/{id}/` | Embeddable single poll | `EmbeddablePollWidget` | ✅ |

### 8.4 Scope & Credential Endpoints

| Method | Endpoint | Description | View | Status |
|--------|----------|-------------|------|--------|
| GET, POST | `/api/scope-types/` | List / create scope types | `ScopeTypeViewSet` | ✅ |
| GET, POST | `/api/scopes/` | List / create scopes | `ScopeViewSet` | ✅ |
| GET, POST | `/api/credential-types/` | List / create credential types | `CredentialTypeViewSet` | ✅ |
| GET, POST | `/api/credential-issuances/` | List / create credential issuances | `CredentialIssuanceViewSet` | ✅ |
| GET, POST | `/api/issuer-authorizations/` | List / create issuer authorizations | `IssuerAuthorizationViewSet` | ✅ |
| POST | `/api/credentials/issue/` | Issue a credential | `IssueCredentialAPIView` | ✅ |
| POST | `/api/credentials/verify/` | Verify a credential | `VerifyCredentialAPIView` | ✅ |
| GET | `/api/credentials/` | Get user credentials | `GetCredentialsAPIView` | ✅ |
| GET, POST | `/api/issuer-metrics/` | Issuer trust metrics | `IssuerMetricsViewSet` | ✅ |
| GET, POST | `/api/issuer-endorsements/` | Issuer peer endorsements | `IssuerEndorsementViewSet` | ✅ |

### 8.5 DID Endpoints

| Method | Endpoint | Description | View | Status |
|--------|----------|-------------|------|--------|
| GET, POST | `/api/dids/` | List / create DIDs | `did_api` | ✅ |
| GET, PUT, DELETE | `/api/dids/{did_uri}/` | DID detail / update / delete | `did_api` | ✅ |

### 8.6 Federation Endpoints

| Method | Endpoint | Description | View | Status |
|--------|----------|-------------|------|--------|
| GET, POST | `/api/federation/nodes/` | List / create federated nodes | `FederatedNodeViewSet` | ✅ |
| GET, POST | `/api/federation/messages/` | List / create sync messages | `SyncMessagesViewSet` | ✅ |
| GET, POST | `/api/federation/logs/` | Sync event audit trail | `DataSyncLogViewSet` | ✅ |
| GET | `/api/federated-data/` | List federated data entries | `federated_data_api` | ✅ |
| GET | `/api/federated-data/{node_name}/` | List entries by node | `federated_data_api` | ✅ |
| GET | `/api/federated-data/{node_name}/{data_type}/{data_id}/` | Get specific federated entry | `federated_data_detail_api` | ✅ |
| POST | `/api/federation/sync/` | Trigger data sync | `DataSyncView` | ✅ |

### 8.7 Trust Endpoints

| Method | Endpoint | Description | View | Status |
|--------|----------|-------------|------|--------|
| GET | `/api/trust/score/` | Get trust score for an issuer | `GetTrustScoreAPIView` | ✅ |
| GET | `/api/trust/check/` | Check if issuer meets trust threshold | `CheckIssuerTrustAPIView` | ✅ |

### 8.8 Credential Management (Template Views)

| Method | Path | Description | View | Status |
|--------|------|-------------|------|--------|
| GET | `/credentials/` | VC management dashboard | `VCManagementView` | ✅ |
| POST | `/credentials/generate/` | Generate unsigned VC JSON | `GenerateCredentialView` | ✅ |
| POST | `/credentials/store-signed/` | Store bridge-signed VC in `user.vcs` | `StoreSignedCredentialView` | ✅ |
| POST | `/credentials/delete/` | Delete a VC | `DeleteCredentialView` | ✅ |
| GET, POST | `/credentials/import/` | Import a VC | `ImportCredentialView` | ✅ |

### 8.9 Template Views

| Method | Path | Description | View | Status |
|--------|------|-------------|------|--------|
| GET | `/` | Poll list | `poll_list` | ✅ |
| GET | `/{id}/` | Poll detail | `poll_detail` | ✅ |
| GET, POST | `/create/` | Create poll | `CreatePollView` | ✅ |

### 8.10 Non-Existent Endpoints

The following endpoints from earlier drafts do not exist in the codebase:

| Claimed Endpoint | Reality |
|-----------------|---------|
| `GET /api/polls/{id}/verify/` | ❌ Not implemented |
| `GET /api/polls/{id}/rules/` | ❌ Not implemented |
| CLI `polly-audit verify --poll-id` | ❌ Not implemented |

> `GET /api/polls/{id}/vote/` (standalone) does exist for HTMX voting — this is a template view, not a pure API.

---

## 9. Bridge Protocol — WebSocket (Port 9001)

`iyou_poly` delegates all cryptographic signing to `iyou_home` at `ws://127.0.0.1:9001`. The server never holds private keys. Signature **verification** is handled locally via pure-Python Ed25519 (see §3.2); the bridge is used exclusively for signing operations that require the private key.

### 9.1 Message Types

| Type | Payload | Response | Purpose | Status |
|------|---------|----------|---------|--------|
| `sign` | `{ "challenge": "<uuid>" }` | `{ "type": "signed", challenge, signature }` | IdP login proof — builds a Verifiable Presentation | 🔧 Delegated |
| `sign_event` | `{ kind, content, tags, ... }` | `{ "type": "signed_event", event }` | Nostr event signing for mesh distribution | 🔧 Delegated |
| `sign_credential` | `{ "credential": { ...unsigned VC... } }` | `{ "type": "signed_credential", vc: { ...signed VC with proof... } }` | VC issuance — bridge stamps `proof` block | 🔧 Delegated (pending bridge impl — marked `xfail` in tests) |

### 9.2 Mesh Probe

The nav badge (`apps/core/templates/partials/_nav.html`) probes `http://127.0.0.1:9001/` via `fetch` with a 300ms timeout. If the bridge responds, "Sovereign Mesh Active" badge appears. ✅ Implemented.

---

## 10. Security & Audit — Current State

### 10.1 What Works Now (✅)

- **Vote History Audit:** `GET /api/polls/{id}/history/` returns a JSON array of all votes with their `voter_did`, `signature`, `option_text`, and `created_at`. This enables manual verification:

  ```json
  {
    "status": "success",
    "poll_title": "Sample Poll",
    "merkle_root": "",
    "votes": [
      {
        "voter_did": "did:key:z6Mk...",
        "option_text": "Option A",
        "signature": "ed25519sig...",
        "created_at": "2026-05-24T12:00:00"
      }
    ]
  }
  ```

- **Merkle Root Recalculation:** Anyone can collect the signatures from the history endpoint and recalculate the Merkle root via `calculate_merkle_root()` in `apps/poller/utils/merkle.py`.

- **Credential Verification:** `POST /api/credentials/verify/` checks issuer authorization, scope matching, expiration, and trust score.

- **Ed25519 Signature Verification:** `POST /api/polls/{id}/cast/` validates the incoming signature using `apps/core/verification.py:verify_vote_signature()` — pure-Python, zero network calls.

### 10.2 What Is Placeholder (🚧)

- **Automatic `is_verified`:** All votes are currently created with `is_verified=True` and `verification_details={"credential_verified": True}`. The cryptographic verification in the headless endpoint is the first step toward per-vote verification.
- **Anti-Tampering Alerts:** No automated alert system exists for Merkle root mismatches.
- **"Verify on Desktop":** The template includes a button that fetches vote history, but the bridge handoff for local verification is not implemented.
- **Ledger Auto-Storage:** The Merkle root is **not** automatically stored in `Poll.votes_merkle_root`. The field exists on the model but is never populated by any code.
- **Scheduled Anchoring:** No scheduling logic exists for "every 100 votes or upon poll closure." Anchoring is a manual operation via `uv run python manage.py anchor_ledger`.

---

## 11. Omni-Social Design Intent (Archived)

> **Note**: This section is retained from v1 as architectural design intent. None of these features beyond what is documented in preceding sections are implemented.

### 11.1 Role in the Omni-Stack (Design)

| Layer | Protocol / Tool | iyou_poly's Intended Role |
|-------|-----------------|--------------------------|
| **Identity** | DID (`did_rust`) | Use DID for voter authentication and signature verification |
| **Messaging** | Nostr | Broadcast poll events and results as Nostr events |
| **Real-time** | XMPP (Prosody) | Not directly used by iyou_poly |
| **Storage** | Blossom (BUD-01) | Publish Merkle roots and ledgers to Blossom/IPFS |
| **Governance** | iyou_poly | Provide verifiable polling and auditing capabilities |

### 11.2 Sovereign Spectrum Compliance (Design)

- **Managed Mode (Level 1):** Cloud-based key management via `iyou_idp`.
- **Sovereign Mode (Level 2):** Integration with `iyou_home` via Local WebSocket Bridge for local key signing.

### 11.3 Data Standardization (Design)

- **JSON Envelopes:** The v1 draft specified `{"valid": bool, "error": "...", "details": {}}`. This format is now the v2 standard (see §5.3).
- **Sync to Home:** Push vote history to local `iyou_home` instances. Not implemented.

### 11.4 Strategic Alignment (Design)

- **Protocolized Opining:** Every Omni-Social ecosystem project to support iyou_poly Protocol for governance.
- **Verifiable Proofs:** Cryptographic signatures integrating with the broader Omni-Social verification framework.
- **Scoped Transparency:** Polls filtered by geographical or social scope as defined in user's verified identity.

---

## Appendix: Version Evolution Matrix

| Paradigm Vector | Protocol v1 (Deprecated) | Protocol v2 (Sovereign Mesh Standard) |
| :--- | :--- | :--- |
| Project Nomenclature | Polly Django | `iyou_poly` |
| Implementation status | All claims presented as requirements | Each claim tagged ✅ / 🔧 / 🚧 |
| Architecture | Implicit | Explicit component matrix |
| Authentication Flow | Implicit Cookie Sessions / Forms | Headless Session-Free Proxy Handshakes |
| API endpoints | 4 listed | 30+ actual endpoints documented |
| Response format | No standard | `{"valid": bool, ...}` v2 envelope |
| Vote Ingestion Kind | Reused kind:1111 (Comment Chaos) | Explicit kind:1112 (Isolated Vote Ledgers) |
| Cryptographic Status | Mock Validation (`is_verified=True`) | True Mathematical Ed25519 Checking |
| Deduplication Boundary | Database Alteration Failure | View-Layer Layered Graceful Idempotency |
| `/api/polls/{id}/verify/` | Listed as requirement | Removed — not implemented |
| `/api/polls/{id}/rules/` | Listed as requirement | Removed — not implemented |
| `did_rust` location | Implied in-repo | Explicitly delegated to `iyou_home` |
| Target Infrastructure | Standalone Monolithic Cloud Server | Cloud Engine evolving into an Embedded Client Daemon |
| Design intent | Interleaved with requirements | Archived in dedicated section |

---

## License

Copyright (C) 2026 David Byers dba Byers Brands

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

See [LICENSE](/LICENSE) for the full GPLv3 text.

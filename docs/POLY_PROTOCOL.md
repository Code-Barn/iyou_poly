# 🗳️ iyou_poly Protocol Spec v2

**Objective**: Define the rules, cryptographic guarantees, and transparency mechanisms for the iyou_poly verifiable polling system.

**Role in the Omni-Social Mesh**: iyou_poly serves as the **Governance Layer** — a Django backend providing OIDC-authenticated, credential-scoped polling with verifiable audit trails. Cryptographic signing is delegated to the local Tauri Desktop Bridge (`iyou_home`) — this server never holds private keys.

**Version Note**: v2 freezes the implemented state as of May 2026. Claims below are tagged with their implementation status:

| Tag | Meaning |
|-----|---------|
| ✅ | Implemented in this repository (`iyou_poly`) |
| 🔧 | Delegated to an external mesh component (`iyou_home`, `iyou_idp`, `iyou_wun`) |
| 🚧 | Defined in the spec but not yet implemented |

---

## 1. Architecture Overview

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

### Component Responsibility Matrix

| Capability | Component | Status |
|------------|-----------|--------|
| OIDC authentication | `iyou_idp` (external) | 🔧 Delegated |
| User session & auth backend | `iyou_poly` | ✅ Implemented |
| Poll CRUD & voting | `iyou_poly` | ✅ Implemented |
| Credential issuance & management | `iyou_poly` | ✅ Implemented |
| Scope-based authorization | `iyou_poly` | ✅ Implemented |
| Merkle root calculation | `iyou_poly` | ✅ Implemented |
| Federation data model | `iyou_poly` | ✅ Implemented |
| Embeddable widget | `iyou_poly` | ✅ Implemented |
| Cryptographic signing (`did_rust`) | `iyou_home` (external) | 🔧 Delegated |
| Key generation & storage | `iyou_home` (external) | 🔧 Delegated |
| Verifiable Credential signing | `iyou_home` (external) | 🔧 Delegated (bridge protocol defined; `sign_credential` not yet wired through) |
| Vote DID-signature verification | — | 🚧 Not implemented (SHA-256 placeholder) |
| Blossom/IPFS ledger anchoring | — | 🚧 Not implemented |
| Nostr event broadcast | — | 🚧 Not implemented |
| Real-time updates (WebSocket/SSE) | — | 🚧 Not implemented |

---

## 2. Authentication & Identity

- **✅ OIDC-Only Authentication**: All users authenticate through `iyou_idp` at `127.0.0.1:8000` via OpenID Connect. The `mozilla-django-oidc` library handles the protocol. No password-based backends are registered.

- **✅ Primary Identifier**: The OIDC `sub` claim contains the user's full DID string (e.g., `did:key:z6Mk...`). This becomes `User.username` and is used throughout the codebase as `voter_did`.

- **✅ Legacy Password Auth**: Strictly disabled. The `login/` and `logout/` routes redirect to OIDC endpoints. Only `MyOIDCAuthenticationBackend` is registered.

- **✅ Session Cookie**: `poly_sessionid`, `SameSite=Lax`, `HttpOnly=True`. Prevents collision with IdP cookies on `127.0.0.1`.

- **✅ DID Usage in Voting Flow**: DIDs are queried for credential lookup and scope checking during vote eligibility. See `apps/poller/views.py` lines 362, 1165, 1265 — `user.dids.filter(is_primary=True)`.

- **🔧 `did_rust` Crypto**: All cryptographic operations are delegated to `iyou_home` at `ws://127.0.0.1:9001`. The `iyou_poly` server never holds private keys. The bridge protocol defines three message types (`sign`, `sign_event`, `sign_credential`).

- **🔧 Sovereign Spectrum**: Supports both **Managed (Level 1)** — cloud-based key management via `iyou_idp`, and **Sovereign (Level 2)** — local key signing via the `iyou_home` WebSocket bridge.

- **🚧 WebAuthn**: Future consideration for hardware key support. Not implemented.

---

## 3. Voting & The Cryptographic Ledger

### Vote Integrity

- **✅ Immutable Vote Records**: Votes are append-only by convention. The `Vote` model stores `poll` (FK), `option` (FK), `voter_did`, `signature`, `credential_cid`, `credential_proof`, `weight`, `is_verified`, and timestamps. The DRF `VoteViewSet` does expose `DELETE /api/votes/{id}/` via the router, but no application-level vote deletion UI or workflow exists.

- **🚧 Signature-Strict Voting**: The spec mandates that votes must carry a valid DID-generated cryptographic signature. In practice, the server generates a SHA-256 hash of `(poll_id, option_id, voter_did, timestamp)` as a placeholder:

  ```python
  # apps/poller/views.py:979-987
  signature = hashlib.sha256(json.dumps(sign_data, sort_keys=True).encode()).hexdigest()
  ```

  All votes are created with `is_verified=True` — no actual cryptographic verification occurs. Bridge signing (`sign_credential` WebSocket) is defined but not wired into the voting flow.

### Ledger Anchoring

- **✅ Merkle Root Calculation**: The system calculates a SHA-256 Merkle root of vote signatures via `apps/poller/utils/merkle.py:calculate_merkle_root()`.

- **✅ `anchor_ledger` Command**: Management command at `apps/poller/management/commands/anchor_ledger.py` — aggregates the last 100 votes, computes the Merkle root, and prints it to stdout:

  ```
  $ uv run python manage.py anchor_ledger
  --- Ledger Anchor Point ---
  Votes aggregated: 100
  Merkle Root: a1b2c3d4...
  ----------------------------
  ```

- **🚧 Auto-Storage**: The root is **not** automatically stored in `Poll.votes_merkle_root`. The field exists on the model but is never populated by any code.

- **🚧 Scheduled Anchoring**: No scheduling logic exists for "every 100 votes or upon poll closure." Anchoring is a manual operation.

### Storage

- **✅ Local**: Metadata is stored in Django (SQLite in development, PostgreSQL in production) via the ORM. Fields include `ipfs_cid`, `blockchain_anchor`, `votes_merkle_root`, `vote_count_anchor` — all defined but unused for external storage.

- **🚧 Global (Blossom/IPFS)**: Finalized ledgers and Merkle roots are defined for publication to **Blossom (BUD-01)** with IPFS redundancy. **No integration code exists** — zero imports of `web3`, `ipfshttpclient`, or any IPFS/blossom library in `apps/`.

- **🚧 Omni-Social Storage Compliance**: The architecture calls for Postgres-as-index-only with primary data content-addressed via Blossom/IPFS. Not yet implemented.

---

## 4. Voting Power & Transparency

- **✅ Default Rule**: **1:1** (one user, one vote). `vote_power_ratio` defaults to 1.0 on the `Poll` model.

- **✅ Weighted Voting**: Custom ratios are declared in poll metadata via `vote_power_rule` (CharField, e.g., `"investor_share"`, `"daily"`) and `vote_power_ratio` (FloatField, default 1.0). Both fields are exposed in the API serializers.

- **✅ Visual Mandate**: Any poll with a non-1:1 ratio displays the gear icon ⚙️ with a tooltip explaining the voting power calculation:

  ```html
  <span class="cursor-help"
        title="Custom voting power: {{ poll.vote_power_rule }}
               ({{ poll.vote_power_ratio }}x multiplier)">⚙️</span>
  ```

  - `apps/poller/templates/poller/poll_list.html:111` — ⚙️ in poll cards
  - `apps/poller/templates/poller/poll_detail.html:14` — ⚙️ in poll detail

- **✅ Scope Filtering UI**: Poll list includes dropdown filters for scope type and scope value. Per-poll requirement badges show scope type, scope value, and required credential type. See `apps/poller/templates/poller/poll_list.html:7-86`.

- **🚧 `/api/polls/{id}/rules` Endpoint**: Defined in the spec but not implemented. Vote power rules are currently exposed inline in the poll serializers, not via a dedicated endpoint.

---

## 5. Federation & The Omni-Social Mesh

### Data Model (✅ Implemented)

The federation data layer exists in `apps/core/models.py`:

| Model | Purpose | Status |
|-------|---------|--------|
| `FederatedNode` | Registered peer nodes (name, endpoint, public_key, is_active) | ✅ Implemented |
| `FederatedData` | Synchronized data entries (node, data_type, data_id, data JSON, version, is_active) | ✅ Implemented |
| `SyncMessage` | Gossip protocol messages (message_id, message_type, sender, signature, payload, previous_hash, proof_of_work, is_processed) | ✅ Implemented |
| `DataSyncLog` | Sync event audit trail (source/target node, data_type, data_id, status) | ✅ Implemented |

### Signal-Based Sync (✅ Implemented, 🚧 Local Only)

- `apps/core/signals.py` — `sync_federated_data_on_save` and `sync_federated_data_on_delete` propagate changes but **do not make network calls**. Actual dispatch is a placeholder:
  ```python
  # apps/core/signals.py:124-132
  def sync_data_to_node(...):
      log_sync_event(...)  # Logs only — no HTTP dispatch
  ```

- `apps/poller/signals.py` — `sync_poll_on_save`, `sync_poll_on_delete`, `sync_poll_option_on_save`, `sync_vote_on_save` convert local model changes into `FederatedData` entries. These save locally only.

### Gossip Worker (✅ Implemented, 🚧 No Message Dispatch)

- `apps/poller/management/commands/gossip_worker.py` — a 28-line heartbeat loop (60s interval) that prints a heartbeat message:
  ```
  [gossip_worker] heartbeat — mesh active
  ```
  No gossip protocol message dispatch exists. This is a K3s sidecar placeholder.

### Conflict Resolution (✅ Implemented)

- `apps/core/utils.py` — `ConflictResolution.resolve(data_a, data_b)` implements last-write-wins by version, then timestamp. `ConflictResolution.resolve_multiple(versions)` provides iterative pairwise resolution.

- `apps/core/utils.py` — `ProofOfWork.compute(data, difficulty)` and `ProofOfWork.verify(data, hash, nonce, difficulty)` provide SHA-256 proof-of-work for message validation.

### Planned but Not Implemented (🚧)

- **Nostr Integration**: Cross-instance poll federation via Nostr relays. No Nostr code exists in the codebase.
- **Blossom/IPFS Publishing**: Shared audit ledgers via Blossom/IPFS. Not implemented.
- **`iyou_wun` Global Aggregation**: Global-scoped polls aggregated by the satellite app. Not implemented.
- **ActivityPub**: Replaced by Nostr per Omni-Social strategic directive. Neither is implemented.

---

## 6. API Reference

### Response Format Convention

All API responses follow one of two conventions:

**Function-based views (dominant pattern)**:
```json
{"status": "success", "data": {...}}
{"status": "error", "message": "Description of error"}
```

**DRF ViewSets**:
```json
{"status": "success", ...fields...}
{"error": "Validation error", "details": {...}}
```

The `{"valid": bool, "error": "...", "details": {}}` envelope from earlier drafts is not used.

### Poll & Vote Endpoints

| Method | Endpoint | Description | View | Status |
|--------|----------|-------------|------|--------|
| GET, POST | `/api/polls/` | List / create polls | `poll_api` + `PollViewSet` | ✅ |
| GET, PUT, PATCH, DELETE | `/api/polls/{id}/` | Poll detail / update / delete | `PollViewSet` | ✅ |
| GET | `/api/polls/{id}/results/` | Poll results with percentages | `PollViewSet.results` | ✅ |
| POST | `/api/polls/{id}/fund/` | Add funding to proposal | `PollViewSet.fund` | ✅ |
| GET, POST | `/api/votes/` | List / create votes | `VoteViewSet` | ✅ |
| GET, PUT, PATCH, DELETE | `/api/votes/{id}/` | Vote detail / update / delete | `VoteViewSet` | ✅ |
| POST | `/api/polls/{id}/vote/` | HTMX + JSON vote casting | `vote_api` | ✅ |
| POST | `/api/polls/{id}/cast/` | DRF vote casting (requires `signature`) | `CastVoteAPIView` | ✅ |
| GET | `/api/polls/{id}/history/` | Vote history with signatures for verification | `get_votes` | ✅ |
| GET | `/api/polls/{id}/eligibility/` | Check if `voter_did` can vote on poll | `CheckVotingEligibilityAPIView` | ✅ |

### Embed Widget Endpoints

| Method | Endpoint | Description | View | Status |
|--------|----------|-------------|------|--------|
| GET | `/api/embed/polls/` | Embeddable poll list (params: `embedding_app`, `user_did`, `theme`, `scope`) | `EmbeddablePollWidget` | ✅ |
| GET | `/api/embed/polls/{id}/` | Embeddable single poll | `EmbeddablePollWidget` | ✅ |

### Scope & Credential Endpoints

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

### DID Endpoints

| Method | Endpoint | Description | View | Status |
|--------|----------|-------------|------|--------|
| GET, POST | `/api/dids/` | List / create DIDs | `did_api` | ✅ |
| GET, PUT, DELETE | `/api/dids/{did_uri}/` | DID detail / update / delete | `did_api` | ✅ |

### Federation Endpoints

| Method | Endpoint | Description | View | Status |
|--------|----------|-------------|------|--------|
| GET, POST | `/api/federation/nodes/` | List / create federated nodes | `FederatedNodeViewSet` | ✅ |
| GET, POST | `/api/federation/messages/` | List / create sync messages | `SyncMessagesViewSet` | ✅ |
| GET, POST | `/api/federation/logs/` | Sync event audit trail | `DataSyncLogViewSet` | ✅ |
| GET | `/api/federated-data/` | List federated data entries | `federated_data_api` | ✅ |
| GET | `/api/federated-data/{node_name}/` | List entries by node | `federated_data_api` | ✅ |
| GET | `/api/federated-data/{node_name}/{data_type}/{data_id}/` | Get specific federated entry | `federated_data_detail_api` | ✅ |
| POST | `/api/federation/sync/` | Trigger data sync | `DataSyncView` | ✅ |

### Trust Endpoints

| Method | Endpoint | Description | View | Status |
|--------|----------|-------------|------|--------|
| GET | `/api/trust/score/` | Get trust score for an issuer | `GetTrustScoreAPIView` | ✅ |
| GET | `/api/trust/check/` | Check if issuer meets trust threshold | `CheckIssuerTrustAPIView` | ✅ |

### Credential Management (Template Views)

| Method | Path | Description | View | Status |
|--------|------|-------------|------|--------|
| GET | `/credentials/` | VC management dashboard | `VCManagementView` | ✅ |
| POST | `/credentials/generate/` | Generate unsigned VC JSON | `GenerateCredentialView` | ✅ |
| POST | `/credentials/store-signed/` | Store bridge-signed VC in `user.vcs` | `StoreSignedCredentialView` | ✅ |
| POST | `/credentials/delete/` | Delete a VC | `DeleteCredentialView` | ✅ |
| GET, POST | `/credentials/import/` | Import a VC | `ImportCredentialView` | ✅ |

### Template Views

| Method | Path | Description | View | Status |
|--------|------|-------------|------|--------|
| GET | `/` | Poll list | `poll_list` | ✅ |
| GET | `/{id}/` | Poll detail | `poll_detail` | ✅ |
| GET, POST | `/create/` | Create poll | `CreatePollView` | ✅ |

### Non-Existent Endpoints

The following endpoints from earlier drafts do not exist in the codebase:

| Claimed Endpoint | Reality |
|-----------------|---------|
| `GET /api/polls/{id}/verify/` | ❌ Not implemented |
| `GET /api/polls/{id}/rules/` | ❌ Not implemented |
| `GET /api/polls/{id}/vote/` (standalone) | ✅ Does exist at this path (HTMX voting) |
| CLI `polly-audit verify --poll-id` | ❌ Not implemented |

---

## 7. Bridge Protocol — WebSocket (Port 9001)

iyou_poly delegates all cryptographic signing to `iyou_home` at `ws://127.0.0.1:9001`. The server never holds private keys.

### Message Types

| Type | Payload | Response | Purpose | Status |
|------|---------|----------|---------|--------|
| `sign` | `{ "challenge": "<uuid>" }` | `{ "type": "signed", challenge, signature }` | IdP login proof — builds a Verifiable Presentation | 🔧 Delegated |
| `sign_event` | `{ kind, content, tags, ... }` | `{ "type": "signed_event", event }` | Nostr event signing for mesh distribution | 🔧 Delegated |
| `sign_credential` | `{ "credential": { ...unsigned VC... } }` | `{ "type": "signed_credential", vc: { ...signed VC with proof... } }` | VC issuance — bridge stamps `proof` block | 🔧 Delegated (pending bridge impl — marked `xfail` in tests) |

### Mesh Probe

The nav badge (`apps/core/templates/partials/_nav.html`) probes `http://127.0.0.1:9001/` via `fetch` with a 300ms timeout. If the bridge responds, "Sovereign Mesh Active" badge appears. ✅ Implemented.

---

## 8. Security & Audit — Current State

### What Works Now (✅)

- **Vote History Audit**: `GET /api/polls/{id}/history/` returns a JSON array of all votes with their `voter_did`, `signature`, `option_text`, and `created_at`. This enables manual verification:

  ```json
  {
    "status": "success",
    "poll_title": "Sample Poll",
    "merkle_root": "",
    "votes": [
      {
        "voter_did": "did:key:z6Mk...",
        "option_text": "Option A",
        "signature": "sha256hash...",
        "created_at": "2026-05-24T12:00:00"
      }
    ]
  }
  ```

- **Merkle Root Recalculation**: Anyone can collect the signatures from the history endpoint and recalculate the Merkle root via `calculate_merkle_root()`.

- **Credential Verification**: `POST /api/credentials/verify/` checks issuer authorization, scope matching, expiration, and trust score.

### What Is Placeholder (🚧)

- **Vote Signatures**: SHA-256 hash of vote data, not a real DID signature. Bridge `sign`/`sign_credential` integration into the voting flow is pending.
- **Automatic `is_verified`**: All votes are created with `is_verified=True` and `verification_details={"credential_verified": True}`. No actual cryptographic verification runs.
- **Anti-Tampering Alerts**: No automated alert system exists for Merkle root mismatches.
- **"Verify on Desktop"**: The template includes a button that fetches vote history, but the bridge handoff for local verification is not implemented.

---

## 9. Omni-Social Design Intent (Archived)

> **Note**: This section is retained from v1 as architectural design intent. None of these features are implemented in the current codebase.

### Role in the Omni-Stack (Design)

| Layer | Protocol / Tool | iyou_poly's Intended Role |
|-------|-----------------|--------------------------|
| **Identity** | DID (`did_rust`) | Use DID for voter authentication and signature verification |
| **Messaging** | Nostr | Broadcast poll events and results as Nostr events |
| **Real-time** | XMPP (Prosody) | Not directly used by iyou_poly |
| **Storage** | Blossom (BUD-01) | Publish Merkle roots and ledgers to Blossom/IPFS |
| **Governance** | iyou_poly | Provide verifiable polling and auditing capabilities |

### Sovereign Spectrum Compliance (Design)

- **Managed Mode (Level 1)**: Cloud-based key management via `iyou_idp`.
- **Sovereign Mode (Level 2)**: Integration with `iyou_home` via Local WebSocket Bridge for local key signing.

### Data Standardization (Design)

- **JSON Envelopes**: The v1 draft specified `{"valid": bool, "error": "...", "details": {}}`. The actual format is `{"status": "success", "data": ...}` (see API Reference above).
- **Sync to Home**: Push vote history to local `iyou_home` instances. Not implemented.

### Strategic Alignment (Design)

- **Protocolized Opining**: Every Omni-Social ecosystem project to support iyou_poly Protocol for governance.
- **Verifiable Proofs**: Cryptographic signatures integrating with the broader Omni-Social verification framework.
- **Scoped Transparency**: Polls filtered by geographical or social scope as defined in user's verified identity.

---

## Appendix: v1 → v2 Changes

| Change | v1 | v2 |
|--------|----|----|
| Project name | Poly | iyou_poly |
| Implementation status | All claims presented as requirements | Each claim tagged ✅ / 🔧 / 🚧 |
| Architecture | Implicit | Explicit component matrix |
| API endpoints | 4 listed | 30+ actual endpoints documented |
| Response format | `{"valid": bool, ...}` | `{"status": "success", ...}` (actual) |
| `/api/polls/{id}/verify/` | Listed as requirement | Removed — not implemented |
| `/api/polls/{id}/rules/` | Listed as requirement | Removed — not implemented |
| `did_rust` location | Implied in-repo | Explicitly delegated to `iyou_home` |
| License reference | (none) | GPLv3 |
| Design intent | Interleaved with requirements | Archived in dedicated section |

---

## License

Copyright (C) 2026 David Byers dba Byers Brands

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

See [LICENSE](/LICENSE) for the full GPLv3 text.

# Poly - Decentralized Polling Application

## Overview

Poly transforms a basic Django polling app into a blockchain-based decentralized polling application with:
- Immutable ledger for poll data
- Distributed, decentralized records across nodes
- DID-based authentication (did:key, did:ethr, did:web, did:ion)
- Credential-based voting authorization with flexible scopes
- Equal-weighted votes (1:1) that are tamper-proof
- Federation across multiple nodes with gossip protocol

## Tech Stack

- **Backend**: Django 6.0 + Django REST Framework
- **Database**: SQLite (default), PostgreSQL-ready
- **DID/VC**: didkit, web3.py
- **Authentication**: DID-based (decentralized)

## Project Structure

```
poly/
├── apps/
│   ├── accounts/          # User accounts, DID management
│   ├── core/             # Core models, credentials, federation
│   └── poller/           # Polls, votes, voting logic
├── config/               # Django settings
├── docs/                 # Technical specifications
└── manage.py
```

## Key Models

### Core (apps/core/models.py)

| Model | Purpose |
|-------|---------|
| `DIDMethod` | Supported DID methods (did:key, did:ethr, etc.) |
| `DID` | User decentralized identifiers |
| `ScopeType` | Registry of scope types (geographic, organization, etc.) |
| `Scope` | Specific scope values (town, county, state, company) |
| `CredentialType` | Credential types (VotingAuthorization, Membership) |
| `CredentialIssuance` | Issued credentials |
| `IssuerAuthorization` | Who can issue what credentials |
| `FederatedNode` | Federation network nodes |
| `FederatedData` | Synced data across nodes |
| `SyncMessage` | Gossip protocol messages |
| `IssuerMetrics` | Trust metrics per issuer |
| `IssuerEndorsement` | Peer endorsements |

### Poller (apps/poller/models.py)

| Model | Purpose |
|-------|---------|
| `Poll` | Poll with scope requirements |
| `PollOption` | Poll choices |
| `Vote` | DID-based votes with credentials |

## API Endpoints

### Authentication
- `GET /login/did/` - DID login

### Credentials & Scopes
- `GET/POST /api/scope-types/` - Scope type registry
- `GET/POST /api/scopes/` - Scope values
- `GET/POST /api/credential-types/` - Credential types
- `POST /api/credentials/issue/` - Issue credential
- `POST /api/credentials/verify/` - Verify credential
- `GET /api/credentials/` - List credentials

### Polling
- `GET/POST /api/polls/` - List/create polls
- `GET /api/polls/{id}/results/` - Poll results
- `POST /api/polls/{id}/cast/` - Cast DID-based vote
- `GET /api/polls/{id}/eligibility/` - Check voting eligibility

### Federation
- `GET/POST /api/federation/nodes/` - Manage nodes
- `POST /api/federation/nodes/{name}/sync/` - Sync with node
- `POST /api/federation/nodes/{name}/announce/` - Announce data
- `GET /api/federation/sync/` - Get changes since version

### Trust Scoring
- `GET /api/issuer-metrics/` - List metrics
- `GET/POST /api/issuer-endorsements/` - List/create endorsements
- `GET /api/trust/score/?issuer_did=&scope_value=` - Get trust score
- `POST /api/trust/check/` - Check threshold compliance

## Getting Started

### 1. Install Dependencies
```bash
cd /home/user/CODE_BASE/poly
uv sync
```

### 2. Run Migrations
```bash
uv run python manage.py migrate
```

### 3. Create Initial Data
```bash
# Populate default scope types and DID methods
uv run python manage.py shell -c "
from apps.core.models import ScopeType, DIDMethod
# Run the data populating logic from migrations
"
```

### 4. Start Server
```bash
uv run python manage.py runserver
```

### 5. Access API
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/

## Trust Scoring

Trust scores (0.0-1.0) are calculated from:
- **verification_success_rate** (30%) - How often credentials verify
- **peer_endorsements** (20%) - Other issuer endorsements
- **time_since_first_issuance** (15%) - Longevity
- **unique_holders** (15%) - Breadth of issuance
- **scope_violations** (-20% penalty) - Out-of-scope issuances

Thresholds:
- `low`: 0.0
- `medium`: 0.4
- `high`: 0.7
- `very_high`: 0.9

## Federation Protocol

Nodes sync using a gossip protocol with:
- Message types: announce, request, response, vote, credential, poll, merkle_update, ping, pong
- Last-write-wins conflict resolution with version vectors
- Proof-of-work for message validation

## Testing

Run tests:
```bash
uv run python manage.py test
```

Run with coverage:
```bash
uv run pytest --cov=apps
```

## Key Files

| File | Purpose |
|------|---------|
| `apps/core/models.py` | Core data models |
| `apps/core/views.py` | API views |
| `apps/core/serializers.py` | DRF serializers |
| `apps/core/utils.py` | Trust scoring, conflict resolution |
| `apps/poller/views.py` | Poll/vote views |
| `docs/DECENTRALIZED_POLLING_SPEC.md` | Full technical spec |

## Environment Variables

- `DJANGO_SETTINGS_MODULE=config.settings`
- `SECRET_KEY` - Django secret key
- `DEBUG=True` - Development mode

## Future Improvements

1. IPFS integration for immutable storage
2. Blockchain anchoring for vote verification
3. Merkle tree for vote integrity
4. Real-time federation sync (WebSocket)
5. Mobile/frontend client

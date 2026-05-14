# Polly Project - Technical Overview for New Developers

## What is Polly?

Polly is a **decentralized/federated identity provider and polling platform** built with Django. It enables:

- Decentralized Identity (DID) management using W3C standards
- Verifiable Credentials (VCs) for authorization
- Federated authentication (Google, GitHub, etc.)
- Decentralized polling with credential-based voting eligibility
- Cross-node data synchronization via gossip protocol

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 6.0 + Django REST Framework |
| Database | SQLite (dev), PostgreSQL-ready |
| DID/VC | didkit (Rust), web3.py |
| Auth | DID-based + OAuth2 (OIDC) |
| Frontend | Django Templates + HTMX |

## Project Structure

```
polly/
├── apps/
│   ├── accounts/         # User auth, DIDs, credentials
│   ├── core/             # Core models, federation, trust
│   ├── poller/           # Polls, votes, voting logic
│   └── discuss/          # Discussion forum (extra)
├── config/               # Django settings
├── docs/                 # Technical documentation
├── manage.py
└── pyproject.toml
```

## Key Apps

### 1. `apps/accounts` - Identity & Authentication
- **DID management**: Create, validate, resolve DIDs
- **User models**: Link DIDs to user accounts
- **Backends**: DID-based + OIDC (Google, GitHub)
- **Rust wrapper**: `did_rust_wrapper/` for high-performance DID ops

Key files:
- `models.py` - User, LinkedDID, DIDDocument
- `backends.py` - Authentication backends
- `did_views.py` - DID login flow
- `utils/did_utils.py` - DID/VC utilities

### 2. `apps/core` - Core Infrastructure
- **DID methods**: did:key, did:ethr, did:web, did:ion
- **Verifiable Credentials**: Issuance, verification, storage
- **Scopes**: Geographic (local, state, national, global)
- **Federation**: Node sync, gossip protocol, conflict resolution
- **Trust scoring**: Issuer reputation metrics

Key models:
- `DIDMethod`, `DID`, `DIDDocument`
- `CredentialType`, `CredentialIssuance`
- `ScopeType`, `Scope`
- `FederatedNode`, `FederatedData`, `SyncMessage`
- `IssuerMetrics`, `IssuerEndorsement`

### 3. `apps/poller` - Polling System
- **Polls**: Create polls with scope requirements
- **Votes**: DID-based voting with credential authorization
- **Results**: Vote tallying with federation sync

Key models:
- `Poll`, `PollOption`, `Vote`

## Key Concepts

### DID (Decentralized Identifier)
```python
from apps.accounts.utils.did_utils import generate_did, validate_did

did = generate_did(method="key")
# -> "did:key:z6Mkj..."

is_valid = validate_did("did:key:z6M...")
```

### Verifiable Credentials
```python
from apps.accounts.utils.did_utils import issue_vc

vc = issue_vc(
    issuer_did="did:key:...",
    holder_did="did:key:...",
    credential_type="VotingAuthorization",
    context={"scope": "local", "jurisdiction": "NYC"}
)
```

### Trust Scoring (0.0-1.0)
- **verification_success_rate** (30%)
- **peer_endorsements** (20%)
- **time_since_first_issuance** (15%)
- **unique_holders** (15%)
- **scope_violations** (-20% penalty)

Thresholds: low (0.0), medium (0.4), high (0.7), very_high (0.9)

### Federation Protocol
- Gossip-based sync between nodes
- Message types: announce, request, response, vote, credential, poll
- Last-write-wins conflict resolution with version vectors

## API Endpoints

### Authentication
- `GET /login/did/` - DID login page
- `GET /login/` - OIDC login options
- `POST /auth/did/` - DID authentication

### Credentials
- `GET/POST /api/credential-types/`
- `GET/POST /api/credentials/`
- `POST /api/credentials/issue/` - Issue VC
- `POST /api/credentials/verify/` - Verify VC

### Scopes
- `GET/POST /api/scope-types/`
- `GET/POST /api/scopes/`

### Polling
- `GET/POST /api/polls/`
- `GET /api/polls/{id}/`
- `POST /api/polls/{id}/cast/` - Cast vote
- `GET /api/polls/{id}/eligibility/` - Check if user can vote

### Federation
- `GET/POST /api/federation/nodes/`
- `POST /api/federation/nodes/{name}/sync/`
- `GET/api/federation/sync/`

### Trust
- `GET /api/issuer-metrics/`
- `GET/POST /api/issuer-endorsements/`
- `GET /api/trust/score/?issuer_did=&scope_value=`

## Getting Started

```bash
# Install dependencies
uv sync

# Run migrations
uv run python manage.py migrate

# Create initial data
uv run python manage.py create_geographical_scopes

# Start server
uv run python manage.py runserver
```

Access:
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/

## Running Tests

```bash
# All tests
uv run python manage.py test

# With coverage
uv run pytest --cov=apps
```

## Environment Variables

- `DJANGO_SETTINGS_MODULE=config.settings`
- `SECRET_KEY` - Django secret
- `DEBUG=True` - Development mode
- `DID_BACKEND=rust` - Use Rust DID backend (recommended)

## Known Issues

1. **Federated Poll Versioning**: Version may increment multiple times during poll creation
2. **Vote Count Synchronization**: Vote counts may increment multiple times during sync

## Key Documentation Files

| File | Description |
|------|-------------|
| `docs/DECENTRALIZED_POLLING_SPEC.md` | Full technical specification |
| `docs/CREDENTIAL_ISSUANCE_ARCHITECTURE.md` | VC system architecture |
| `docs/FEDERATED_AUTHENTICATION.md` | Authentication flow |
| `docs/OIDC_INTEGRATION.md` | OIDC setup guide |
| `docs/RUST_DID_INTEGRATION.md` | Rust DID backend |
| `apps/accounts/utils/VcGenerationDocs.md` | VC generation details |

## Architecture Highlights

1. **Hybrid Python/Rust DID**: Uses didkit (Rust) for performance-critical operations
2. **Credential-based voting**: Votes require valid VCs matching poll scope
3. **Federated sync**: Nodes share data via gossip with conflict resolution
4. **Trust system**: Issuer reputation calculated from multiple factors
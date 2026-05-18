# Poly: Sovereign Decentralized Polling Platform

Poly is the **Governance Layer** of the Sovereign Mesh. It provides OIDC/DID-authenticated,
credential-scoped polling with verifiable audit trails. All cryptographic signing is
delegated to the local Tauri Desktop Bridge (`iyou_home` at `ws://127.0.0.1:9001`) —
the server never holds private keys.

## Architecture

```
┌─────────────┐     OIDC Auth     ┌──────────────┐
│  iyou_idp   │◄────────────────►│    Poly     │
│  :8000      │                   │  :8002       │
└─────────────┘                   └──────┬───────┘
                                         │
                                   WebSocket │ sign_credential
                                         ▼
                               ┌──────────────────┐
                               │  iyou_home        │
                               │  Tauri Bridge     │
                               │  :9001            │
                               └──────────────────┘
```

## Prerequisites

- Python 3.13+
- Django 6.0+
- SQLite (dev) / PostgreSQL (prod)
- `iyou_idp` running on `127.0.0.1:8000`
- `iyou_home` Tauri bridge on `127.0.0.1:9001` (for VC signing)

## Features

- **OIDC-Only Authentication**: All users authenticate through `iyou_idp` at `127.0.0.1:8000`. Username is the IdP `sub` claim (the DID). No passwords, no social logins.
- **Verifiable Credentials (VCs)**: Issue, store, and manage credentials. Signing done via the Tauri bridge WebSocket protocol (`ws://127.0.0.1:9001`).
- **Signature Bridge Protocol**: `sign`, `sign_event`, `sign_credential` message types — see [Developer Guide](POLY_DEVELOPER_GUIDE.md).
- **Scope-Based Voting**: Credential-aware polls with family, organization, and geographic scoping.
- **Family-Scoped Polling**: Family-unit, family-scoped, and organization poll types.
- **Proposal & Funding**: Polls with funding goals and progress tracking.
- **Embeddable Widget**: Integrate polls into external apps via iframe.
- **Federated Database**: Gossip-protocol sync across nodes with version vectors.
- **HTMX-Powered UI**: Dynamic voting without full page reloads.
- **RESTful API**: Full API for polls, votes, credentials, and federation.

## Getting Started

```bash
# Clone
git clone https://github.com/Code-Barn/poly-django.git
cd poly-django

# Install
uv sync

# Migrate
uv run python manage.py migrate

# Create initial scopes
uv run python manage.py create_geographical_scopes

# Start server
uv run python manage.py runserver 127.0.0.1:8002
```

Access: `http://127.0.0.1:8002/`

> **Note:** The server must bind to `127.0.0.1` (not `0.0.0.0` or `localhost`) to
> comply with the Omni-Mesh Private Network Access (PNA) rules. Safari requires
> the bridge at `:9001` to respond with `Access-Control-Allow-Private-Network: true`.

## OIDC Authentication Flow

1. User visits `http://127.0.0.1:8002/` and clicks **Login**
2. Redirected to `http://127.0.0.1:8000/openid/authorize/` (iyou_idp)
3. IdP authenticates (may request a signature challenge from `ws://127.0.0.1:9001`)
4. Callback at `http://127.0.0.1:8002/oidc/callback/` creates/authenticates user
5. `username` is set to the `sub` claim (the DID)
6. Session cookie: `poly_sessionid`

## Signature Bridge

The Tauri Desktop Bridge (`iyou_home` on `:9001`) handles all cryptographic operations:

| Message Type | Purpose |
|-------------|---------|
| `sign` | Sign a challenge for IdP login (returns Verifiable Presentation) |
| `sign_event` | Sign a Nostr event for mesh distribution |
| `sign_credential` | Stamp a `proof` block on an unsigned VC |

**Credential issuance flow:**
```
POST /credentials/generate/    → unsigned VC JSON
  → WebSocket ws://127.0.0.1:9001  → sign_credential
  → bridge returns signed VC (with proof)
POST /credentials/store-signed/ → stored in user.vcs
```

## Polling API Endpoints

### Poll API
- `GET /api/polls/` — List active polls
- `GET /api/polls/<id>/` — Poll detail
- `POST /api/polls/` — Create poll
- `PUT /api/polls/<id>/` — Update poll
- `DELETE /api/polls/<id>/` — Delete poll
- `POST /api/polls/<id>/fund/` — Add funding to proposal

### Vote API
- `POST /api/polls/<id>/vote/` — Cast vote (HTMX)
- `POST /api/polls/<id>/cast/` — Cast vote (DRF)
- `GET /api/polls/<id>/eligibility/` — Check voting eligibility

### Embed API
- `GET /api/embed/polls/` — Embeddable poll list
- `GET /api/embed/polls/<id>/` — Embeddable single poll

### Credential API
- `GET /credentials/` — VC management dashboard
- `POST /credentials/generate/` — Generate unsigned VC
- `POST /credentials/store-signed/` — Store bridge-signed VC
- `POST /credentials/delete/` — Delete a VC
- `GET /credentials/import/` — Import a VC

## Testing

```bash
# Run all tests (skips bridge-dependent)
uv run python -m pytest -v -m "not bridge"

# Run specific app tests
uv run python -m pytest apps/poller/tests/
uv run python -m pytest apps/accounts/tests/

# Run with coverage
uv run pytest --cov=apps -m "not bridge"
```

## Known Issues

1. **Federated Poll Versioning**: The `version` of `FederatedData` entries may be incremented multiple times during poll creation.
2. **Bridge-Dependent Tests**: 3 tests marked `@pytest.mark.xfail` require the Tauri bridge on `:9001` to respond to `sign_credential`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write code + tests
4. Ensure `pytest -m "not bridge"` passes
5. Submit a pull request

## License

MIT License. See [LICENSE](LICENSE) for details.

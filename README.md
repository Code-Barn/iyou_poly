# Polly: Decentralized/Federated Identity and Polling Platform

Polly is a decentralized/federated identity provider and polling platform. It provides DID-based authentication, Verifiable Credentials, scope-aware polling, and can be embedded in external applications.

## Prerequisites
- Python 3.13 or higher
- Django 6.0+
- SQLite (dev) or PostgreSQL (production)

## Features

- **Decentralized Identity (DID) Support**: Manage DIDs (did:key, did:ethr, did:web, did:ion), DID methods, and DID documents.
- **DID-Based Authentication**: Passwordless login using Verifiable Credentials (VCs).
- **OpenID Connect (OIDC) Support**: Integrate with Google, GitHub, and other OAuth2 providers.
- **Verifiable Credentials (VCs)**: Issue, store, verify, and manage credentials.
- **Hybrid Authentication**: Combine DID, traditional, and OIDC auth.
- **Scope-Based Voting**: Credential-aware polls with scope requirements.
- **Family-Scoped Polling**: Family-unit, family-scoped, and organization polls.
- **Proposal & Funding**: Polls with funding goals and progress tracking.
- **Embeddable Widget**: Integrate polls into external apps.
- **Federated Database**: Sync data across nodes with conflict resolution.
- **Cactus Comments**: Decentralized discussions via Matrix.
- **RESTful API**: Full API for identity, credentials, polls, and federation.

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/Code-Barn/polly-django.git
   cd polly-django
   ```

2. Install dependencies (using uv recommended):
   ```bash
   uv sync
   ```

3. Run migrations:
   ```bash
   uv run python manage.py migrate
   ```

4. Create initial scopes:
   ```bash
   uv run python manage.py create_geographical_scopes
   ```

5. Start the server:
   ```bash
   uv run python manage.py runserver
   ```

6. Access: Admin at `http://localhost:8000/admin/` | API at `http://localhost:8000/api/`

## Roadmap

### Phase 1: Core Identity & Credentials - ✅ COMPLETE
### Phase 2: Polling System - ✅ COMPLETE
### Phase 3: Embeddable & Federation - ✅ COMPLETE

### Phase 4: Next Steps
- [ ] IPFS integration for immutable storage
- [ ] Blockchain anchoring for votes
- [ ] WebSocket real-time federation
- [ ] Mobile/PWA frontend

## Front-End Development
Polly now includes a front-end built with Django Templates and HTMX for dynamic interactions. Here’s what’s available:

### Features
- **Poll List**: View all active polls at `http://localhost:8000/`.
- **Poll Detail**: View and vote on individual polls at `http://localhost:8000/<poll_id>/`.
- **Authentication**: Log in and out using the links in the header.
- **Voting**: Cast votes dynamically without a full page reload.

### Testing Front-End Functionality
The test suite includes tests for the front-end views and API endpoints. To run the tests:
```bash
python manage.py test
```

## Usage

### OIDC Authentication
Users can authenticate using external providers like Google or GitHub. The login page provides options for OIDC-based authentication:

```html
<!-- Example OIDC login buttons -->
<a href="{% url 'social:begin' 'google-oauth2' %}"
   class="block w-full text-center bg-red-600 text-white p-2 rounded">
    Login with Google
</a>
<a href="{% url 'social:begin' 'github' %}"
   class="block w-full text-center bg-gray-800 text-white p-2 rounded">
    Login with GitHub
</a>
```

### Front-End
- **Poll List**: Visit `http://localhost:8000/` to view all active polls.
- **Poll Detail**: Click on a poll to view its details and vote.
- **Authentication**: Use the login/logout links in the header to authenticate.

### Core API Endpoints

#### Federated Data API
- **GET `/api/federated-data/`**: Retrieve all federated data.
- **GET `/api/federated-data/<node_name>/`**: Retrieve federated data for a specific node.
- **GET `/api/federated-data/<node_name>/<data_type>/<data_id>/`**: Retrieve a specific federated data entry.
- **POST `/api/federated-data/<node_name>/`**: Create a new federated data entry.
- **PUT `/api/federated-data/<node_name>/<data_type>/<data_id>/`**: Update a specific federated data entry.
- **DELETE `/api/federated-data/<node_name>/<data_type>/<data_id>/`**: Delete a specific federated data entry.

#### DID API
- **GET `/api/dids/`**: Retrieve all DIDs.
- **GET `/api/dids/<did_uri>/`**: Retrieve a specific DID and its DID Document.

### Polling API Endpoints

#### Poll API
- **GET `/api/polls/`**: Retrieve all active polls.
- **GET `/api/polls/?embedding_app=<app>`**: Filter by embedding app.
- **GET `/api/polls/?poll_type=family_unit`**: Filter by poll type.
- **GET `/api/polls/?scope_type=organization&scope_value=Acme`**: Filter by scope.
- **GET `/api/polls/<poll_id>/`**: Retrieve a specific poll.
- **POST `/api/polls/`**: Create a new poll.
- **PUT `/api/polls/<poll_id>/`**: Update a poll.
- **DELETE `/api/polls/<poll_id>/`**: Delete a poll.
- **POST `/api/polls/<poll_id>/fund/`: Add funding to a proposal.

#### Vote API
- **POST `/api/polls/<poll_id>/vote/`**: Cast a vote.
- **POST `/api/polls/<poll_id>/cast/`**: Cast vote (DRF endpoint).
- **GET `/api/polls/<poll_id>/eligibility/`**: Check voting eligibility.

#### Embed API
- **GET `/api/embed/polls/`**: Get polls for embedding (filtered by user credentials).
- **GET `/api/embed/polls/<poll_id>/`**: Get single poll for embedding.

### DID Utilities
```python
from apps.accounts.utils.did_utils import generate_did, validate_did, create_did_document

# Generate a DID
did = generate_did(method="key")
print(did)  # Output: did:key:example123456789

# Validate a DID
is_valid = validate_did(did)
print(is_valid)  # Output: True

# Create a DID Document
did_document = create_did_document(did)
print(did_document)
```

### Custom Authentication
```python
from django.contrib.auth import authenticate

# Authenticate using a DID
user = authenticate(request, did="did:key:example123456789")
print(user)
```

## Embeddable Polly Widget

Polly can be embedded in external applications like Byers Brands LLC or Namechart.

### API Endpoints

```bash
# Get polls for embedding (filtered by app + user credentials)
GET /api/embed/polls/?embedding_app=byers-brands-llc&user_did=did:key:...

# Get single poll for embedding
GET /api/embed/polls/123/?embedding_app=byers-brands-llc&user_did=...
```

### Query Parameters

| Parameter | Description |
|-----------|-------------|
| `embedding_app` | External app identifier (e.g., 'byers-brands-llc') |
| `user_did` | User's DID for credential-based filtering |
| `scope` | Filter by scope value |
| `theme` | 'light' or 'dark' |

### Embed Template

Include the widget in your HTML:

```html
{% load cactus_comments %}
{% include "poller/partials/embed_widget.html" %}
```

## Family-Scoped Polling

Polls support different visibility and authorization types:

| Poll Type | Description |
|-----------|-------------|
| `public` | Visible to all users |
| `family_unit` | Private polls for family members only (creator + authorized) |
| `family_scoped` | Public within family scope, includes descendants |
| `organization` | Organization-specific polls |

### Creating Family Polls

```python
from apps.poller.models import Poll

# Family-unit poll (private)
poll = Poll.objects.create(
    title="Family Vacation Vote",
    poll_type=Poll.PollType.FAMILY_UNIT,
    created_by=user,
    ...
)

# Family-scoped poll
poll = Poll.objects.create(
    title="Family Reunion Location",
    poll_type=Poll.PollType.FAMILY_SCOPED,
    required_scope=family_scope,
    parent_poll=parent_poll,  # Optional hierarchy
    ...
)
```

## Proposal & Funding Workflows

Polls can be used as proposals with funding goals:

### Create Proposal

```python
poll = Poll.objects.create(
    title="Community Project",
    is_proposal=True,
    funding_goal=10000.00,
    funding_deadline=datetime(2026, 12, 31),
    ...
)
```

### Fund Proposal

```bash
POST /api/polls/{poll_id}/fund/
Content-Type: application/json

{"amount": 500.00}
```

### Funding Progress

The `funding_progress` property returns percentage (0-100).

## Cactus Comments Integration

Decentralized comments using Matrix network. Add to poll templates:

```html
{% load cactus_comments %}
{% cactus_comments poll.id %}
```

Configuration (optional, defaults to public Cactus server):

```python
# settings.py
CACTUS_HOMESERVER_URL = "https://matrix.cactus.chat:8448"
CACTUS_SERVER_NAME = "cactus.chat"
CACTUS_SITE_NAME = "your-site-name"
```

## Known Issues

1. **Federated Poll Versioning**: The `version` of `FederatedData` entries may be incremented multiple times during poll creation.
2. **Vote Count Synchronization**: The vote count in `FederatedData` entries may be incremented multiple times when a vote is cast.

We are actively working to resolve these issues in upcoming releases.

## Contributing

We welcome contributions! Please follow these guidelines to contribute to Polly:

1. **Fork the Repository**: Create a fork of the Polly repository on GitHub.
2. **Create a Branch**: Create a new branch for your feature or bugfix.
3. **Write Code**: Implement your changes, ensuring they follow the project's coding standards.
4. **Write Tests**: Add unit tests for your changes to ensure they work as expected.
5. **Submit a Pull Request**: Open a pull request to the `main` branch of the Polly repository.

For more details, see our [Contribution Guidelines](CONTRIBUTING.md). We welcome contributions to help resolve the known issues!

## License


This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

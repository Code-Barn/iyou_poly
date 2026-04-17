# Polly: Decentralized/Federated Identity and Polling Platform

Polly is a decentralized/federated identity provider and federated database front-end. It aims to provide a foundation for building applications that leverage decentralized identity (DID) and verifiable credentials (VCs) while ensuring compatibility with federated identity systems.

## Features

- **OpenID Connect (OIDC) Support**: Integrate with external identity providers like Google, GitHub, and more for seamless authentication.

- **Decentralized Identity (DID) Support**: Manage DIDs, DID methods, and DID documents.
- **Verifiable Credentials (VCs)**: Store, verify, manage, and share verifiable credentials with advanced features:
  - Custom naming for credentials
  - Tracking of when credentials were added
  - In-place renaming of credentials
  - Generation of new credentials with custom types
  - Import of existing credentials
  - Automatic migration of legacy credential formats
- **Federated Identity Support**: Link multiple external identities to a single user.
- **Custom Authentication**: Support for DID-based and federated authentication.
- **Federated Database**: Synchronize data across multiple federated nodes with conflict resolution.
- **Core API**: RESTful API endpoints for managing decentralized identity and federated data.
- **Data Synchronization**: Automatically sync data across federated nodes with versioning and logging.

## Roadmap

### Phase 1: Standardization and Core Functionality
- **Completed**:
  - Implemented core models for decentralized identity (DIDs, DID documents, verifiable credentials).
  - Implemented federated database models with synchronization and conflict resolution.
  - Added RESTful API endpoints for managing decentralized identity and federated data.
  - Implemented advanced verifiable credential management with:
    - Custom naming and metadata
    - Credential generation and import
    - In-place renaming functionality
    - Format migration for legacy credentials
- **Next Steps**:
  - Adopt W3C DID and VC standards.
  - Enhance DID resolution and utilities.
  - Implement federated identity providers (OAuth2, OpenID Connect, SAML).
  - Improve verifiable credentials support.

### Phase 2: Federated Database Support
- **Completed**:
  - Implemented federated database models with synchronization and conflict resolution.
  - Added RESTful API endpoints for managing federated data.
- **Next Steps**:
  - Adopt Solid Protocol for federated databases.
  - Enhance data synchronization and conflict resolution.
  - Expand API endpoints for advanced federated data operations.

### Phase 3: Extensibility and Compatibility
- Design a plugin architecture for extending functionality.
- Adopt semantic versioning and backward-compatible changes.
- Implement testing and CI/CD pipelines.

### Phase 3: Polling Functionality
- Research and design a decentralized polling system.
- Implement models and views for managing polls.
- Add support for geographical layers (local, state, national, global).
- Integrate polling functionality with the federated database.

## Rust DID Implementation

Polly uses a hybrid Python/Rust DID implementation for high-performance operations:

```bash
# Use Rust backend (recommended)
DID_BACKEND=rust python manage.py runserver
```

See [docs/RUST_DID_INTEGRATION.md](docs/RUST_DID_INTEGRATION.md) for details.

## Verifiable Credential Management

Polly provides a comprehensive interface for managing verifiable credentials:

### Key Features

1. **Custom Naming**: Assign meaningful names to credentials for easy identification
2. **Added Date Tracking**: See when each credential was added to your wallet
3. **In-Place Renaming**: Rename credentials at any time without re-importing
4. **Credential Generation**: Create new credentials with custom types and attributes
5. **Credential Import**: Import existing credentials from JSON files
6. **Format Migration**: Automatic conversion of legacy credential formats

### Using the VC Management Interface

1. **Access the VC Management Page**: Click "Credentials" in the navigation bar
2. **Generate a New Credential**: Click "Generate Credential" and provide a name and type
3. **Import a Credential**: Click "Import Credential" and paste the JSON data
4. **Rename a Credential**: Click the "Rename" button next to any credential
5. **Download a Credential**: Click "Download" to save a credential as a JSON file

### Technical Implementation

- Credentials are stored with metadata including name and added date
- The system automatically migrates legacy credentials to the new format
- All operations are performed through secure, authenticated endpoints
- Credentials can be filtered by type (e.g., authentication vs. other credentials)

### Phase 4: Front-End Development
- Design and implement a user-friendly front-end.
- Integrate with the RESTful API for decentralized identity, federated data, and polling.
- Develop interfaces for user management, data synchronization, and polling.

## Getting Started

### OIDC Configuration
To enable OIDC authentication, add the following configuration to your `settings.py`:

```python
# settings.py
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.github.GithubOAuth2',
    'apps.accounts.backends.HybridAuthBackend',
]

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = 'your-google-oauth2-key'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = 'your-google-oauth2-secret'

SOCIAL_AUTH_GITHUB_KEY = 'your-github-key'
SOCIAL_AUTH_GITHUB_SECRET = 'your-github-secret'
```

### Prerequisites
- Python 3.13 or higher
- Django 6.0 or higher
- SQLite (for development)

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/polly.git
   cd polly
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Create initial geographical scopes:
   ```bash
   python manage.py create_geographical_scopes
   ```

6. Start the development server:
   ```bash
   python manage.py runserver
   ```

7. Access the admin interface at `http://localhost:8000/admin/` and the API at `http://localhost:8000/api/`.

## Installation

1. Clone the repository:
   
   git clone https://github.com/your-username/polly.git
   cd polly
   
2. Set up a virtual environment:

  python -m venv .venv
  source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`

3. Install dependencies:
  
  pip install -e .

4. Run migrations: 

  python manage.py migrate

5. Start the development server:
  ```bash
  python manage.py runserver
  ```

## Running Tests
To run the test suite:
```bash
python manage.py test
```

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
- **GET `/api/polls/?geographical_scope=<scope>`**: Filter polls by geographical scope.
- **GET `/api/polls/<poll_id>/`**: Retrieve a specific poll.
- **POST `/api/polls/`**: Create a new poll (authenticated users only).
- **PUT `/api/polls/<poll_id>/`**: Update a poll (authenticated users only).
- **DELETE `/api/polls/<poll_id>/`**: Delete a poll (authenticated users only).

#### Vote API
- **POST `/api/polls/<poll_id>/votes/`**: Cast a vote in a poll (authenticated users only).
- **GET `/api/polls/<poll_id>/votes/detail/`**: Retrieve all votes for a poll.

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

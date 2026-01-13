# Federated Authentication

## Overview

Polly supports **federated authentication**, allowing users to authenticate using:
- **Decentralized Identity (DID)** for passwordless, self-sovereign authentication.
- **OpenID Connect (OIDC)** for integration with external identity providers like Google, GitHub, and more.
- **Traditional username/password** for backward compatibility.

This document provides an overview of the federated authentication system, including configuration and usage examples.

---

## Authentication Methods

### 1. Decentralized Identity (DID)
DID-based authentication allows users to log in using **Verifiable Credentials (VCs)** issued by trusted entities. This method is **passwordless** and **self-sovereign**, meaning users control their identity without relying on a central authority.

#### Key Features
- **Trust Management**: Configure trusted issuers and verify VCs.
- **Auto-Provisioning**: Automatically create user accounts for new DIDs.
- **Hybrid Support**: Combine DID authentication with other methods.

#### Configuration
To enable DID authentication, add the following to your `settings.py`:

```python
# settings.py
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'apps.accounts.backends.HybridAuthBackend',
]

# Trust settings
FEDERATED_AUTH = {
    'REQUIRE_TRUSTED_ISSUERS': False,  # Allow any issuer by default
    'TRUSTED_ISSUERS': [],  # List of trusted DIDs if REQUIRE_TRUSTED_ISSUERS is True
    'AUTO_PROVISION_DID_USERS': True,  # Auto-create users for new DIDs
    'VC_EXPIRATION_DAYS': 365,  # Validity period for VCs
}
```

#### Usage
Users can log in by submitting a **Verifiable Credential** via the DID login form. Example:

```python
from apps.accounts.utils.did_utils import verify_federated_vc

# Verify a VC during login
vc_json = request.POST.get('vc')
if verify_federated_vc(vc_json):
    user = authenticate(request, did=vc_json['credentialSubject']['id'])
    login(request, user)
```

---

### 2. OpenID Connect (OIDC)
OIDC allows users to authenticate using external identity providers like **Google, GitHub, or any OIDC-compliant provider**. Polly uses the [`python-social-auth`](https://python-social-auth.readthedocs.io/) library to integrate with OIDC providers.

#### Key Features
- **Multi-Provider Support**: Integrate with any OIDC-compliant provider.
- **Seamless Login**: Users can log in with a single click.
- **Auto-Provisioning**: Automatically create user accounts for new OIDC logins.

#### Configuration
To enable OIDC authentication, add the following to your `settings.py`:

```python
# settings.py
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.github.GithubOAuth2',
    'apps.accounts.backends.HybridAuthBackend',
]

# Google OAuth2
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = 'your-google-oauth2-key'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = 'your-google-oauth2-secret'

# GitHub OAuth2
SOCIAL_AUTH_GITHUB_KEY = 'your-github-key'
SOCIAL_AUTH_GITHUB_SECRET = 'your-github-secret'

# OIDC Settings
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)
```

#### Adding a New OIDC Provider
To add a new OIDC provider, follow these steps:

1. **Install the provider's backend** (if not already available in `python-social-auth`):
   ```bash
   pip install social-auth-app-django
   ```

2. **Add the provider's backend** to `AUTHENTICATION_BACKENDS` in `settings.py`:
   ```python
   AUTHENTICATION_BACKENDS = [
       ...
       'social_core.backends.<provider>.<ProviderName>',
   ]
   ```

3. **Configure the provider's credentials** in `settings.py`:
   ```python
   SOCIAL_AUTH_<PROVIDER>_KEY = 'your-provider-key'
   SOCIAL_AUTH_<PROVIDER>_SECRET = 'your-provider-secret'
   ```

4. **Add the provider's login button** to your login template:
   ```html
   <a href="{% url 'social:begin' '<provider>' %}"
      class="block w-full text-center bg-<color> text-white p-2 rounded">
       Login with <Provider>
   </a>
   ```

#### Usage
Users can log in using OIDC by clicking on the provider's button on the login page. Example:

```html
<!-- Example OIDC login buttons -->
<div class="space-y-2">
    <a href="{% url 'social:begin' 'google-oauth2' %}"
       class="block w-full text-center bg-red-600 text-white p-2 rounded">
        Login with Google
    </a>
    <a href="{% url 'social:begin' 'github' %}"
       class="block w-full text-center bg-gray-800 text-white p-2 rounded">
        Login with GitHub
    </a>
</div>
```

---

### 3. Traditional Username/Password
Polly supports traditional username/password authentication for backward compatibility. This method is enabled by default and requires no additional configuration.

#### Usage
Users can log in using their username and password via the login form:

```html
<form method="post" action="{% url 'login' %}">
    {% csrf_token %}
    <input type="text" name="username" placeholder="Username" class="w-full p-2 border rounded">
    <input type="password" name="password" placeholder="Password" class="w-full p-2 border rounded mt-2">
    <button type="submit" class="w-full bg-blue-600 text-white p-2 rounded mt-2">Login</button>
</form>
```

---

## Hybrid Authentication Backend
Polly uses a **hybrid authentication backend** to support all three authentication methods (DID, OIDC, and username/password). The backend automatically detects the authentication method and processes the request accordingly.

### Configuration
To enable the hybrid backend, add it to `AUTHENTICATION_BACKENDS` in `settings.py`:

```python
# settings.py
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.github.GithubOAuth2',
    'apps.accounts.backends.HybridAuthBackend',
]
```

### Implementation
The hybrid backend is implemented in `apps/accounts/backends.py`:

```python
from django.contrib.auth.backends import ModelBackend
from apps.accounts.utils.did_utils import verify_federated_vc

class HybridAuthBackend(ModelBackend):
    """
    Hybrid authentication backend supporting:
    - Traditional username/password
    - DID-based authentication
    - OIDC (via social-auth)
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Try traditional authentication first
        if username and password:
            return super().authenticate(request, username, password)

        # Try DID authentication
        did = kwargs.get('did')
        vc = kwargs.get('vc')

        if did and vc:
            if verify_federated_vc(vc, did):
                try:
                    user = User.objects.get(did=did)
                    return user
                except User.DoesNotExist:
                    if getattr(settings, 'AUTO_PROVISION_DID_USERS', False):
                        return self._create_did_user(did, vc)
            return None

        # OIDC handled by social-auth
        return None

    def _create_did_user(self, did, vc):
        """Create a new user from DID authentication"""
        vc_data = json.loads(vc)
        credential_subject = vc_data.get('credentialSubject', {})

        user = User.objects.create_user(
            username=credential_subject.get('name', f'user_{User.objects.count() + 1}'),
            did=did,
            email=credential_subject.get('email', '')
        )
        user.set_unusable_password()
        user.save()
        return user
```

---

## Trust Management
Polly includes a **trust management system** to verify the authenticity of **Verifiable Credentials (VCs)** and **OIDC providers**.

### Configuration
Configure trust settings in `settings.py`:

```python
# settings.py
FEDERATED_AUTH = {
    'REQUIRE_TRUSTED_ISSUERS': False,  # Allow any issuer by default
    'TRUSTED_ISSUERS': [],  # List of trusted DIDs if REQUIRE_TRUSTED_ISSUERS is True
    'FEDERATED_SERVERS': [],  # List of trusted federated servers
}
```

### Trust Utilities
The `apps/accounts/utils/did_utils.py` file provides utilities for trust management:

```python
def get_trusted_issuers() -> set:
    """Get the set of trusted issuer DIDs"""
    return set(getattr(settings, 'TRUSTED_ISSUERS', []))

def is_trusted_issuer(issuer_did: str) -> bool:
    """Check if an issuer DID is trusted"""
    if not getattr(settings, 'REQUIRE_TRUSTED_ISSUERS', False):
        return True
    return issuer_did in get_trusted_issuers()

def verify_federated_vc(vc_json: str, issuer_did: str = None) -> bool:
    """Verify a VC that was issued by another federated server"""
    if issuer_did and not is_trusted_issuer(issuer_did):
        return False

    # Additional verification logic
    return True
```

---

## User Experience

### Login Page
The login page provides a **hybrid authentication form** that supports all three methods:

```html
<div class="max-w-md mx-auto">
    <h2 class="text-2xl font-bold mb-6">Login to Polly</h2>

    <!-- Traditional login -->
    <div class="mb-6 p-4 border rounded-lg">
        <h3 class="font-semibold mb-3">Username/Password</h3>
        <form method="post" action="{% url 'login' %}">
            {% csrf_token %}
            <input type="text" name="username" placeholder="Username" class="w-full p-2 border rounded">
            <input type="password" name="password" placeholder="Password" class="w-full p-2 border rounded mt-2">
            <button type="submit" class="w-full bg-blue-600 text-white p-2 rounded mt-2">Login</button>
        </form>
    </div>

    <!-- DID/VC login -->
    <div class="mb-6 p-4 border rounded-lg">
        <h3 class="font-semibold mb-3">DID Authentication (Recommended)</h3>
        <p class="text-sm text-gray-600 mb-3">
            Use your decentralized identity for secure, passwordless login.
        </p>
        <button
            hx-get="{% url 'did_login' %}"
            hx-target="#did-login-container"
            class="w-full bg-green-600 text-white p-2 rounded"
        >
            Login with DID
        </button>
        <div id="did-login-container"></div>
    </div>

    <!-- OIDC providers -->
    <div class="p-4 border rounded-lg">
        <h3 class="font-semibold mb-3">External Providers</h3>
        <div class="space-y-2">
            <a href="{% url 'social:begin' 'google-oauth2' %}"
               class="block w-full text-center bg-red-600 text-white p-2 rounded">
                Login with Google
            </a>
            <a href="{% url 'social:begin' 'github' %}"
               class="block w-full text-center bg-gray-800 text-white p-2 rounded">
                Login with GitHub
            </a>
        </div>
    </div>
</div>
```

### Authentication Selection
Users can select their preferred authentication method based on availability:

```python
def get_authentication_options(user):
    """Get available authentication options for a user"""
    options = []

    # Always available
    options.append({
        'method': 'did',
        'name': 'DID Authentication',
        'description': 'Secure, decentralized login',
        'available': bool(user.did),
        'recommended': True
    })

    # Traditional password
    if user.has_usable_password():
        options.append({
            'method': 'password',
            'name': 'Password',
            'description': 'Traditional login',
            'available': True,
            'recommended': False
        })

    # OIDC connections
    social_accounts = user.social_accounts.all()
    for account in social_accounts:
        options.append({
            'method': f'social_{account.provider}',
            'name': f'Login with {account.provider.capitalize()}',
            'description': 'External provider',
            'available': True,
            'recommended': False
        })

    return options
```

---

## Troubleshooting

### Common Issues

#### 1. OIDC Provider Not Redirecting
- **Symptom**: After clicking an OIDC provider, the page does not redirect.
- **Solution**:
  - Ensure the provider's credentials (`SOCIAL_AUTH_<PROVIDER>_KEY` and `SOCIAL_AUTH_<PROVIDER>_SECRET`) are correct.
  - Verify that the provider's callback URL is configured correctly in the provider's dashboard.

#### 2. DID Authentication Failing
- **Symptom**: DID login fails with "Invalid Verifiable Credential".
- **Solution**:
  - Ensure the VC is valid and issued by a trusted issuer.
  - Check the `FEDERATED_AUTH` settings in `settings.py`.

#### 3. Hybrid Backend Not Working
- **Symptom**: The hybrid backend does not authenticate users.
- **Solution**:
  - Verify that `HybridAuthBackend` is included in `AUTHENTICATION_BACKENDS`.
  - Ensure the backend is correctly implemented in `apps/accounts/backends.py`.

---

## Further Reading
- [Decentralized Identity Foundation (DIF)](https://identity.foundation/)
- [OpenID Connect Specification](https://openid.net/connect/)
- [Verifiable Credentials Data Model](https://www.w3.org/TR/vc-data-model/)
- [python-social-auth Documentation](https://python-social-auth.readthedocs.io/)
# Federated Authentication Implementation Plan

## Overview

This document outlines the implementation plan for federated authentication in the Polly project, based on the hybrid approach combining DID-based authentication, OIDC, and traditional username/password methods.

## Phase 1: Core DID Authentication

### 1.1 Trust Management System

**Status**: ✅ IMPLEMENTED

**Files Modified**:
- `apps/accounts/utils/did_utils.py`: Added trust management functions
- `config/settings.py`: Added trust configuration settings

**Functions Implemented**:
```python
def get_trusted_issuers() -> set:
    """Get the set of trusted issuer DIDs"""

def is_trusted_issuer(issuer_did: str) -> bool:
    """Check if an issuer DID is trusted"""

def verify_federated_vc(vc_json: str, issuer_did: str = None) -> bool:
    """Verify a VC that was issued by another federated server"""
```

**Trust Model**:
- Open trust model by default (allow any federated server)
- Can be restricted to trusted issuers via settings
- Foundation for Web of Trust implementation

### 1.2 DID-Based Login Endpoint

**Status**: 🔄 IN PROGRESS

**Files to Modify**:
- `apps/accounts/views.py`: Add DIDLoginView
- `apps/accounts/backends.py`: Enhance authentication backend

**Implementation**:
```python
class DIDLoginView(View):
    def get(self, request):
        """Render DID login form"""
        return render(request, "accounts/did_login.html")

    def post(self, request):
        """Process DID login with VC"""
        vc_json = request.POST.get('vc')
        vc_proof = request.POST.get('vc_proof')

        # Verify the VC
        if verify_federated_vc(vc_json):
            vc_data = json.loads(vc_json)
            user_did = vc_data['credentialSubject']['id']

            # Find or create user
            user, created = User.objects.get_or_create(did=user_did)

            # If new user, set up basic profile
            if created:
                user.username = f"user_{user.id}"
                user.set_unusable_password()  # No password for DID-only users
                user.save()

            login(request, user)
            return redirect('poll_list')

        return render(request, 'accounts/did_login.html', {
            'error': 'Invalid Verifiable Credential'
        })
```

### 1.3 Hybrid Login Form

**Status**: 📝 PLANNED

**Files to Create/Modify**:
- `templates/accounts/login.html`: Hybrid login template
- `templates/accounts/did_login.html`: DID-specific login

**Template Structure**:
```html
<!-- login.html -->
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

    <!-- OR -->

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

    <!-- OR -->

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

## Phase 2: Authentication Backend Enhancement

### 2.1 Custom Authentication Backend

**Status**: 📝 PLANNED

**Files to Modify**:
- `apps/accounts/backends.py`: Enhance DIDAuthBackend

**Implementation**:
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
        vc_proof = kwargs.get('vc_proof')

        if did and vc and vc_proof:
            if verify_federated_vc(vc, did):
                try:
                    user = User.objects.get(did=did)
                    return user
                except User.DoesNotExist:
                    # Auto-provision user if settings allow
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

        # Add the VC to user's credentials
        user.add_vc(vc_data)
        return user
```

## Phase 3: User Experience Enhancements

### 3.1 Onboarding and Education

**Status**: 📝 PLANNED

**Features**:
- Interactive tutorial for DID setup
- Comparison of authentication methods
- Security benefits explanation
- Step-by-step VC generation guide

### 3.2 Authentication Method Selection

**Status**: 📝 PLANNED

**Implementation**:
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

## Phase 4: Federation Protocol

### 4.1 Cross-Server Identity Resolution

**Status**: 📝 PLANNED

**Implementation**:
```python
def resolve_federated_identity(did):
    """
    Resolve a DID across federated servers

    1. Check local database first
    2. Query trusted federated servers
    3. Cache resolved identities
    """
    # Local check
    try:
        return User.objects.get(did=did)
    except User.DoesNotExist:
        pass

    # Federated resolution
    if hasattr(settings, 'FEDERATED_SERVERS'):
        for server_url in settings.FEDERATED_SERVERS:
            try:
                response = requests.get(
                    f"{server_url}/api/federation/resolve/{did}",
                    timeout=5
                )
                if response.status_code == 200:
                    user_data = response.json()
                    return create_federated_user(user_data)
            except requests.RequestException:
                continue

    return None
```

### 4.2 Trust Establishment Protocol

**Status**: 📝 PLANNED

**Protocol**:
1. Server A sends trust request to Server B
2. Server B verifies Server A's identity
3. Server B adds Server A to trusted peers
4. Server A adds Server B to trusted peers
5. Periodic trust verification

## Implementation Timeline

### Week 1-2: Core DID Authentication
- [x] Trust management system
- [ ] DID login endpoint
- [ ] Hybrid login form
- [ ] Authentication backend

### Week 3-4: User Experience
- [ ] Onboarding flows
- [ ] Authentication selection
- [ ] Error handling
- [ ] Mobile responsiveness

### Week 5-6: Federation Protocol
- [ ] Identity resolution
- [ ] Trust establishment
- [ ] Cross-server verification
- [ ] Performance optimization

## Testing Strategy

### Unit Tests
```python
def test_trust_management():
    """Test trust management functions"""
    # Test open trust model
    assert is_trusted_issuer("did:key:any") == True

    # Test restricted model
    with override_settings(REQUIRE_TRUSTED_ISSUERS=True, TRUSTED_ISSUERS=["did:key:trusted"]):
        assert is_trusted_issuer("did:key:trusted") == True
        assert is_trusted_issuer("did:key:untrusted") == False

def test_did_login():
    """Test DID login flow"""
    # Create test user with DID
    user = User.objects.create_user(
        username="testuser",
        did="did:key:test",
        did_key=json.dumps({"kty": "OKP", "crv": "Ed25519", "x": "test", "d": "test"})
    )

    # Generate VC for user
    credential = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "AuthenticationCredential"],
        "issuer": user.did,
        "credentialSubject": {"id": user.did, "name": "testuser"},
    }
    vc = issue_vc(credential, user.did, user.did_key)

    # Test login
    response = client.post("/accounts/did_login/", {
        "vc": vc,
        "vc_proof": json.dumps({"proof": "test"})
    })

    assert response.status_code == 302  # Redirect after login
    assert response.url == "/polls/"  # Redirect to poll list
```

### Integration Tests
```python
def test_hybrid_authentication_flow():
    """Test the complete hybrid authentication flow"""
    # Test password → DID migration
    # Test OIDC → DID migration
    # Test fallback scenarios
    pass

def test_federated_identity_resolution():
    """Test cross-server identity resolution"""
    # Mock federated server responses
    # Test local vs remote resolution
    # Test caching
    pass
```

## Deployment Considerations

### Configuration
```python
# settings.py
FEDERATED_AUTH = {
    'REQUIRE_TRUSTED_ISSUERS': False,  # Start open, restrict later
    'TRUSTED_ISSUERS': [],  # Populate when restricting
    'FEDERATED_SERVERS': [],  # List of trusted federated servers
    'AUTO_PROVISION_DID_USERS': True,  # Allow new users via DID
    'VC_EXPIRATION_DAYS': 365,  # VC validity period
}
```

### Security
- Rate limiting on authentication endpoints
- VC revocation checking
- Trust verification caching
- Secure storage of private keys

### Monitoring
- Authentication success/failure metrics
- Trust establishment metrics
- Federation performance metrics
- Error tracking

## Migration Path

### From Current System
1. Add DID generation to user registration
2. Implement DID login alongside existing methods
3. Gradually encourage users to adopt DID
4. Monitor adoption and adjust UX

### To Production
1. Start with open trust model
2. Monitor for abuse
3. Gradually introduce trust restrictions if needed
4. Implement Web of Trust when scale requires it

## Success Metrics

1. **Adoption Rate**: % of users using DID authentication
2. **Fallback Rate**: % of users needing fallback methods
3. **Trust Establishment**: Time to establish trust between servers
4. **Performance**: Authentication latency
5. **Reliability**: Uptime and error rates

This implementation plan provides a clear path to achieving your vision of a hybrid federated identity provider that removes single points of failure while maintaining user convenience and security.
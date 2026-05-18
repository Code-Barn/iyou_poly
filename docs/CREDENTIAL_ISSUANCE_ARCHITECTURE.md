# Credential Issuance Architecture for Poly Integration

This document describes how to build new apps that issue credentials for Poly's scoped polling system.

## Overview

Poly uses **verifiable credentials (VCs)** to authorize users for polls at various organizational levels. New apps can be created to issue credentials at any scope level (global, state, county, organization, etc.).

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Credential Issuance Apps                       │
├─────────────┬─────────────┬─────────────┬─────────────┬────────────┤
│   Global    │    State    │   County    │ Organization│   Custom   │
│   App       │    App     │    App      │    App      │   App      │
│             │             │             │             │            │
│ Issues:     │ Issues:    │ Issues:     │ Issues:     │ Issues:    │
│ - World     │ - State    │ - County    │ - Company   │ - Custom   │
│   citizen   │   resident │   resident  │   member    │   scopes   │
│ - Global   │ - State    │ - County   │ - Club      │            │
│   voter     │   voter    │   voter    │   member    │            │
└──────┬──────┴──────┬─────┴──────┬─────┴──────┬─────┴─────┬──────┘
       │              │            │            │           │
       │              │            │            │           │
       ▼              ▼            ▼            ▼           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Poly Core                                   │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │ User DID    │  │ Scope       │  │ Poll        │                │
│  │ Wallet      │  │ Resolution  │  │ Voting      │                │
│  │ (VCs)       │  │             │  │             │                │
│  └─────────────┘  └─────────────┘  └─────────────┘                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Credential Schema

All credential-issuing apps should follow this schema:

```json
{
  "@context": [
    "https://www.w3.org/2018/credentials/v1",
    "https://poly.example.com/credentials/v1"
  ],
  "type": ["VerifiableCredential", "AuthorizationCredential"],
  "issuer": "did:key:issuer-did",
  "issuanceDate": "2026-04-09T00:00:00Z",
  "credentialSubject": {
    "id": "did:key:user-did",
    "scope": {
      "type": "geographic|organization|custom",
      "value": "scope:value",
      "name": "Human Readable Name"
    },
    "authorizationLevel": "standard|admin|viewer",
    "authorizationType": "polling|voting|admin",
    "issuedBy": "did:key:issuer-did",
    "issuedAt": "2026-04-09T00:00:00Z"
  },
  "credentialStatus": {
    "id": "https://issuer.example.com/credentials/status/1",
    "type": "RevocationList2023"
  }
}
```

### Scope Types

| Type | Example Value | Description |
|------|---------------|-------------|
| `geographic` | `global:world` | Global/worldwide |
| `geographic` | `nation:USA` | National |
| `geographic` | `state:Indiana` | State-level |
| `geographic` | `county:DeKalb County, IN` | County-level |
| `geographic` | `town:Fort Wayne, IN` | Town/city-level |
| `organization` | `company:Acme Corp` | Company member |
| `organization` | `club:Garden Club` | Club/organization |
| `organization` | `family:Smith Family` | Family member |
| `custom` | `class:CSC101` | Custom scope |

## App Template Structure

Create a new app following this structure:

```
my_scope_app/
├── __init__.py
├── models.py              # App-specific models
├── views.py               # Web views
├── urls.py                # URL routing
├── admin.py               # Admin interface
├── serializers.py         # API serializers (if using DRF)
├── credentials.py          # Credential issuance logic
├── scope_validator.py     # Scope validation
├── templates/
│   └── my_scope_app/
│       ├── credential_request.html
│       ├── my_credentials.html
│       └── admin_dashboard.html
├── static/
│   └── my_scope_app/
│       └── css/
│           └── style.css
└── tests/
    ├── test_credential_issuance.py
    └── test_scope_validation.py
```

## Required Components

### 1. Credential Model

```python
# models.py
from django.db import models
from django.conf import settings

class ScopeAuthorization(models.Model):
    """Tracks authorizations within this scope."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    scope_type = models.CharField(max_length=50)  # e.g., "geographic"
    scope_value = models.CharField(max_length=255)  # e.g., "state:Indiana"
    authorization_level = models.CharField(
        max_length=20,
        choices=[
            ('standard', 'Standard'),
            ('admin', 'Admin'),
            ('viewer', 'Viewer'),
        ],
        default='standard'
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'scope_type', 'scope_value']
    
    def create_credential(self) -> dict:
        """Generate VC payload for this authorization."""
        return {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://poly.example.com/credentials/v1"
            ],
            "type": ["VerifiableCredential", "AuthorizationCredential"],
            "issuer": self.get_issuer_did(),
            "issuanceDate": self.issued_at.isoformat(),
            "credentialSubject": {
                "id": self.user.did,
                "scope": {
                    "type": self.scope_type,
                    "value": self.scope_value,
                    "name": self.get_scope_display_name(),
                },
                "authorizationLevel": self.authorization_level,
                "authorizationType": "polling",
                "issuedBy": self.get_issuer_did(),
                "issuedAt": self.issued_at.isoformat(),
            },
            "credentialStatus": {
                "id": f"{self.get_issuer_url()}/credentials/status/{self.pk}",
                "type": "RevocationList2023"
            }
        }
    
    def get_issuer_did(self) -> str:
        """Return the issuer's DID. Override in subclasses."""
        raise NotImplementedError
    
    def get_scope_display_name(self) -> str:
        """Return human-readable scope name. Override in subclasses."""
        return self.scope_value
    
    def get_issuer_url(self) -> str:
        """Return the issuer's base URL. Override in subclasses."""
        raise NotImplementedError
```

### 2. Credential Issuance Views

```python
# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
import json

@login_required
@csrf_protect
@require_http_methods(["POST"])
def request_credential(request):
    """
    Request a credential for the authenticated user.
    
    Request body:
        {"scope_type": "geographic", "scope_value": "state:Indiana"}
    
    Response:
        {"success": true, "credential": {...}}
    """
    data = json.loads(request.body)
    scope_type = data.get("scope_type")
    scope_value = data.get("scope_value")
    
    # Validate the request
    is_valid, error = validate_scope_request(request.user, scope_type, scope_value)
    if not is_valid:
        return JsonResponse({"error": error}, status=400)
    
    # Check if user already has this credential
    existing = ScopeAuthorization.objects.filter(
        user=request.user,
        scope_type=scope_type,
        scope_value=scope_value,
        is_active=True
    ).first()
    
    if existing:
        credential = existing.create_credential()
        return JsonResponse({
            "credential": credential,
            "message": "Credential already exists"
        })
    
    # Create new authorization
    auth = ScopeAuthorization.objects.create(
        user=request.user,
        scope_type=scope_type,
        scope_value=scope_value
    )
    
    credential = auth.create_credential()
    return JsonResponse({"credential": credential})


@login_required
def list_my_credentials(request):
    """List all credentials for the current user."""
    authorizations = ScopeAuthorization.objects.filter(
        user=request.user,
        is_active=True
    )
    
    credentials = [auth.create_credential() for auth in authorizations]
    return JsonResponse({"credentials": credentials})


@login_required
def check_scope_eligibility(request, scope_type, scope_value):
    """Check if user is eligible for a scope."""
    is_eligible, reason = check_eligibility(request.user, scope_type, scope_value)
    return JsonResponse({
        "eligible": is_eligible,
        "reason": reason
    })
```

### 3. Scope Validation

```python
# scope_validator.py
from abc import ABC, abstractmethod

class ScopeValidator(ABC):
    """Base class for scope validation."""
    
    @abstractmethod
    def validate(self, user, scope_value: str) -> tuple[bool, str]:
        """
        Validate if user qualifies for this scope.
        
        Returns: (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def get_scope_display_name(self, scope_value: str) -> str:
        """Return human-readable name for the scope."""
        pass


class GeographicScopeValidator(ScopeValidator):
    """Validator for geographic scopes."""
    
    def validate(self, user, scope_value: str) -> tuple[bool, str]:
        # Check if user has verified address in this scope
        # This is app-specific - could use external verification
        # For now, return True (implement your verification logic)
        return True, ""
    
    def get_scope_display_name(self, scope_value: str) -> str:
        # Parse scope_value (e.g., "state:Indiana") and return name
        return scope_value.split(":", 1)[-1]


class OrganizationScopeValidator(ScopeValidator):
    """Validator for organization scopes."""
    
    def validate(self, user, scope_value: str) -> tuple[bool, str]:
        # Check if user is a member of the organization
        # This could integrate with external systems
        return True, ""
    
    def get_scope_display_name(self, scope_value: str) -> str:
        return scope_value.split(":", 1)[-1]


class CustomScopeValidator(ScopeValidator):
    """Validator for custom scopes."""
    
    def validate(self, user, scope_value: str) -> tuple[bool, str]:
        # Custom validation logic
        return True, ""
    
    def get_scope_display_name(self, scope_value: str) -> str:
        return scope_value
```

### 4. URL Configuration

```python
# urls.py
from django.urls import path
from . import views

app_name = "my_scope_app"

urlpatterns = [
    path("request/", views.request_credential, name="request_credential"),
    path("my-credentials/", views.list_my_credentials, name="my_credentials"),
    path(
        "check-eligibility/<str:scope_type>/<str:scope_value>/",
        views.check_scope_eligibility,
        name="check_eligibility"
    ),
]
```

## Integration with Poly

### 1. Configure Poly's Scope Resolution

Add your app's issuer to Poly's configuration:

```python
# In Poly's settings or config module
SCOPE_ISSUERS = {
    "geographic:global": {
        "issuer_did": "did:key:global-issuer",
        "issuer_name": "Global Authority",
        "verification_url": "https://global.example.com/api/verify",
    },
    "geographic:state": {
        "issuer_did": "did:key:state-issuer",
        "issuer_name": "State Authority",
        "verification_url": "https://state.example.com/api/verify",
    },
    "organization": {
        "issuer_did": "did:key:org-issuer",
        "issuer_name": "Organization Authority",
        "verification_url": "https://org.example.com/api/verify",
    },
}
```

### 2. Verify Credentials

Poly verifies credentials by:

1. Parsing the VC
2. Checking the issuer DID
3. Validating the signature
4. Verifying scope matches poll requirements

```python
# In Poly's credential verification logic
def verify_scope_credential(vc: dict, required_scope: str) -> bool:
    """Verify a VC grants access to the required scope."""
    
    credential_subject = vc.get("credentialSubject", {})
    scope = credential_subject.get("scope", {})
    
    scope_type = scope.get("type", "")
    scope_value = scope.get("value", "")
    
    # Check if VC scope matches required scope
    if scope_type == "geographic" and required_scope.startswith("geographic:"):
        return scope_value == required_scope.replace("geographic:", "")
    
    if scope_type == "organization" and required_scope.startswith("organization:"):
        return scope_value == required_scope.replace("organization:", "")
    
    return False
```

## Example Apps

### Global Credentials App
Issues worldwide credentials for global polls.

```python
# global_auth/models.py
class GlobalAuthorization(ScopeAuthorization):
    """Global-level authorization."""
    
    def get_issuer_did(self) -> str:
        return "did:key:global-authority"
    
    def get_scope_display_name(self) -> str:
        return "World"
```

### State Credentials App
Issues state-level credentials for state polls.

```python
# state_auth/models.py
class StateAuthorization(ScopeAuthorization):
    """State-level authorization."""
    
    US_STATES = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona",
        "IN": "Indiana", "KY": "Kentucky", # ... etc
    }
    
    def validate(self, user, scope_value: str) -> tuple[bool, str]:
        # Verify user is a resident of the state
        # Could integrate with DMV, voter registration, etc.
        state_code = scope_value.split(":")[-1].upper()
        if state_code in self.US_STATES:
            return True, ""
        return False, "Invalid state code"
    
    def get_scope_display_name(self) -> str:
        state_code = self.scope_value.split(":")[-1].upper()
        return self.US_STATES.get(state_code, state_code)
```

### Organization Credentials App
Issues organization membership credentials.

```python
# org_auth/models.py
class OrganizationAuthorization(ScopeAuthorization):
    """Organization membership authorization."""
    
    def validate(self, user, scope_value: str) -> tuple[bool, str]:
        # Check if user is verified member of organization
        org_name = scope_value.replace("organization:", "")
        # Integration with org's member verification system
        return True, ""
    
    def get_scope_display_name(self) -> str:
        return self.scope_value.replace("organization:", "")
```

## Deployment Checklist

For each credential-issuing app:

- [ ] Define scope types and validation logic
- [ ] Implement `ScopeAuthorization` model
- [ ] Create issuance API endpoints
- [ ] Add admin interface for manual issuance
- [ ] Configure issuer DID
- [ ] Set up revocation endpoint
- [ ] Add to Poly's `SCOPE_ISSUERS` config
- [ ] Document scope types and requirements
- [ ] Add tests for credential issuance
- [ ] Set up monitoring/analytics

## Security Considerations

1. **Issuer Security**: Protect issuer private keys
2. **Verification**: Always verify credentials cryptographically
3. **Revocation**: Implement timely revocation checking
4. **Scope Validation**: Validate scope values match defined patterns
5. **Rate Limiting**: Prevent credential request abuse
6. **Audit Logging**: Track all issuance events

## Future Enhancements

- [ ] Standard credential verification API
- [ ] Cross-app credential federation
- [ ] Delegation (issuer can authorize sub-issuers)
- [ ] Credential expiration automation
- [ ] Mobile wallet integration

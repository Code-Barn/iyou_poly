# VC Management System

**Latest Update**: April 2026

This document describes the Verifiable Credential (VC) management system in Poly.

> **Note**: Poly uses DIDKit (Rust) as the primary DID/VC implementation, with a Python fallback. See [AI_PROMPT.md](./AI_PROMPT.md) for details.

## Credential Data Structure

```json
{
  "credential": {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    "type": ["VerifiableCredential", "MembershipCredential"],
    "issuer": "did:key:z6MkexampleDID",
    "issuanceDate": "2023-01-01T00:00:00Z",
    "credentialSubject": {
      "id": "did:key:z6MkexampleDID",
      "name": "username",
      "description": "Credential description"
    },
    "proof": { ... }
  },
  "name": "Custom Credential Name",
  "added_date": "2023-01-01T00:00:00.000000Z"
}
```

## Features

| Feature | Description |
|---------|-------------|
| **Custom Naming** | Assign descriptive names to credentials |
| **Added Date** | Track when credentials were added |
| **Generation** | Create new credentials with custom types |
| **Import** | Import existing credentials from JSON |
| **Format Migration** | Auto-migrate legacy credentials |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/accounts/vcs/` | GET | View VC management page |
| `/accounts/generate_credential/` | GET/POST | Generate new credential |
| `/accounts/import_credential/` | GET/POST | Import credential |
| `/accounts/update_vc_name/` | POST | Rename credential |
| `/accounts/delete_credential/` | POST | Delete credential |

## Security

- All endpoints require authentication
- CSRF protection on POST requests
- Authentication credentials cannot be deleted
- Data isolation per user
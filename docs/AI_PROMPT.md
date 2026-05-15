# AI Prompt Guide for Polly Project

This document serves as a **living guide** for AI-assisted development in the Polly project.

---

## 1. Project Overview

### 1.1 Project Goals

Polly is a **decentralized/federated identity provider and polling platform**:

- **Decentralized Identity (DID)**: Support for DIDs (did:key, did:ethr, did:web, did:ion)
- **Verifiable Credentials (VCs)**: Issue, store, verify, and manage credentials
- **Hybrid Authentication**: DID-based + username/password + OAuth2/OIDC
- **Scope-Based Polling**: Credential-aware polls with family-unit/family-scoped support
- **Embeddable Widgets**: Integrate polls into external apps (Byers Brands, Namechart)
- **Federated Database**: Sync data across nodes with conflict resolution
- **Decentralized Comments**: Cactus Comments via Matrix network

### 1.2 Architecture

| Component | Technology |
|-----------|------------|
| Backend | Django 6.0 + DRF |
| Frontend | Django Templates + HTMX |
| Database | SQLite (dev) / PostgreSQL (prod) |
| DID/VC | **DIDKit (Rust)** - primary, Python fallback |
| Theming | Tailwind CSS |

### 1.3 DID/VC Implementation

**IMPORTANT**: Polly uses a hybrid Python/Rust implementation:

```bash
# Rust backend (recommended, faster)
DID_BACKEND=rust python manage.py runserver

# Python fallback (slower but reliable)
python manage.py runserver
```

The Rust DID implementation via DIDKit provides:
- Faster DID generation and VC issuance
- Full W3C compliance
- Cryptographic verification

The Python fallback remains as a **backup** for scenarios where Rust is unavailable (e.g., CI/CD environments, systems without Rust toolchain).

**Upcoming**: Full Rust-DID integration is a priority for Q2 2026. The Python implementation will remain as backup.

### 1.4 Key Features

| Feature | Description |
|---------|-------------|
| **DID-Based Auth** | Passwordless login using Verifiable Credentials |
| **Hybrid Auth** | Combine DID, username/password, OAuth2 |
| **VC Management** | Generate, import, rename, verify VCs |
| **Trust Scoring** | Issuer reputation system (0.0-1.0) |
| **Poll Types** | public, family_unit, family_scoped, organization |
| **Proposal/Funding** | Polls with funding goals and progress |
| **Embed API** | Scope-aware API for external apps |
| **Cactus Comments** | Decentralized discussions via Matrix |

---

## 2. Lessons Learned

### 2.1 DID/VC Operations
- DIDKit (Rust) is faster but requires proper installation
- Always have Python fallback for environments without Rust
- Validate DIDs and VCs before using in auth flows
- Store private keys securely

### 2.2 Database Migrations
- Run `makemigrations` and `migrate` after model changes
- Test migrations in staging before production

### 2.3 HTMX Debugging
- Use browser dev tools to debug HTMX requests
- Ensure CSRF tokens are included in requests

### 2.4 Scope System
- ScopeType and Scope models enable flexible authorization
- Poll filtering uses user credentials + required scope match

---

## 3. Best Practices

### 3.1 Python
- Follow PEP 8
- Use type hints
- Document with docstrings

### 3.2 Django
- Use built-in auth, messages, staticfiles
- Keep business logic in views/services
- Use `select_related` and `prefetch_related` for queries

### 3.3 DID/VC
- Use `apps/accounts/utils/did_utils.py` utilities
- Default to Rust backend, fallback to Python
- Test both backends when making DID changes

### 3.4 Testing
- Unit tests for models/utils
- Integration tests for views
- E2E tests with Playwright for critical flows

---

## 4. Project Structure

```
polly/
├── apps/
│   ├── accounts/       # User auth, DIDs, credentials
│   ├── core/          # DID/VC models, scopes, federation
│   └── poller/        # Polls, votes, embed widget
├── config/            # Django settings
├── docs/              # Documentation
│   └── archive/       # Historical docs
└── manage.py
```

---

## 5. Current Roadmap

### Completed
- Phase 1: Core Identity & Credentials
- Phase 2: Polling System (family-scoped, proposals)
- Phase 3: Embeddable & Federation

### In Progress / Next
- Full Rust-DID integration (priority)
- IPFS for immutable storage
- Blockchain anchoring for votes

---

## 6. Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [DIDKit](https://github.com/spruceid/didkit)
- [HTMX](https://htmx.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [W3C DID Core](https://www.w3.org/TR/did-core/)
- [W3C VC Data Model](https://www.w3.org/TR/vc-data-model/)

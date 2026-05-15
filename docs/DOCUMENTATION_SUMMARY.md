# Documentation Summary

**Latest Update**: April 2026

## Overview

Polly documentation covers decentralized identity, polling, and federation. See the main [README.md](../README.md) for current features.

## Documentation Structure

### Core Documentation
- [README.md](../README.md) - Quick start and feature overview
- [ONBOARDING_OVERVIEW.md](./ONBOARDING_OVERVIEW.md) - New developer onboarding

### Technical Specs
- [DECENTRALIZED_POLLING_SPEC.md](./DECENTRALIZED_POLLING_SPEC.md) - Full polling technical specification
- [CREDENTIAL_ISSUANCE_ARCHITECTURE.md](./CREDENTIAL_ISSUANCE_ARCHITECTURE.md) - VC system architecture

### Integration Guides
- [FEDERATED_AUTHENTICATION.md](./FEDERATED_AUTHENTICATION.md) - DID and hybrid auth
- [OIDC_INTEGRATION.md](./OIDC_INTEGRATION.md) - Google/GitHub OAuth setup
- [RUST_DID_INTEGRATION.md](./RUST_DID_INTEGRATION.md) - Rust DID backend

### Feature Documentation
- [VOTING_FUNCTIONALITY.md](./VOTING_FUNCTIONALITY.md) - Poll and vote implementation
- [vc_management.md](./vc_management.md) - VC management interface
- [CREDENTIAL_MANAGEMENT_SYSTEM.md](./CREDENTIAL_MANAGEMENT_SYSTEM.md) - Credential system

### Archived (Historical)
- [docs/archive/](./archive/) - Previous implementation notes and changelogs

## Key Files

| File | Purpose |
|------|---------|
| `apps/core/models.py` | DID, VC, Scope, Federation models |
| `apps/poller/models.py` | Poll, PollOption, Vote models |
| `apps/accounts/utils/did_utils.py` | DID/VC utilities |
| `apps/poller/views.py` | Poll and voting views |
| `apps/poller/embed.py` | Embeddable widget API |

## Getting Help

1. Start with [README.md](../README.md) for setup
2. Check [ONBOARDING_OVERVIEW.md](./ONBOARDING_OVERVIEW.md) for architecture
3. Review [DECENTRALIZED_POLLING_SPEC.md](./DECENTRALIZED_POLLING_SPEC.md) for detailed specs
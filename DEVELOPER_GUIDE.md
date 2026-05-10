# Polly Developer Guide

## Project State Assessment

This document provides a comprehensive technical overview of the Polly decentralized polling platform to guide future development decisions.

## Current Implementation Status

### Core Architecture

**Complete and Functional:**
- ✅ Django 6.0 backend with REST Framework
- ✅ Decentralized Identity (DID) support (did:key, did:ethr, did:web, did:ion)
- ✅ Verifiable Credentials (VC) system
- ✅ Scope-based authorization framework
- ✅ Federation protocol with gossip messaging
- ✅ Embeddable widget system
- ✅ Family-scoped and organization polling
- ✅ Proposal/funding workflows

### Poller App - Detailed Technical Analysis

#### Models (`apps/poller/models.py`)

**Poll Model:**
- **Poll Types**: `public`, `family_scoped`, `family_unit`, `organization`
- **Hierarchy**: Parent-child relationships for family/organization polls
- **Scope Requirements**: `required_scope_type`, `required_scope`, `required_credential_type`
- **Trust System**: `min_issuer_trust_score`, `require_multiple_issuers`
- **Proposal Mode**: Funding goals, deadlines, progress tracking
- **Decentralized Storage**: IPFS CID, blockchain anchors, Merkle roots
- **Timing**: Start/end dates with `is_active_now` property

**Vote Model:**
- **DID-based**: Supports both user accounts and standalone DIDs
- **Cryptographic Verification**: Signature, credential proof fields
- **Decentralized Storage**: IPFS CID, blockchain transaction hash
- **Verification Status**: `is_verified` flag with details

**FederatedPoll:**
- Proxy model extending `FederatedData` for cross-node synchronization
- Automatic versioning and conflict resolution

#### Views (`apps/poller/views.py`)

**API Endpoints:**
- `GET/POST /api/polls/` - Poll management
- `GET /api/polls/{id}/results/` - Poll results with percentages
- `POST /api/polls/{id}/fund/` - Add funding to proposals
- `POST /api/polls/{id}/cast/` - Cast DID-based votes
- `GET /api/polls/{id}/eligibility/` - Check voting eligibility
- `GET /api/votes/` - Vote listing and filtering

**Template Views:**
- Poll list with credential-based filtering
- Poll detail with voting interface
- Poll creation with scope/credential requirements
- HTMX-powered dynamic voting (no page reload)

**Key Features:**
- **Scope-Aware Filtering**: `_filter_by_user_credentials()` method
- **Credential Verification**: Real-time VC validation
- **Funding Workflow**: Proposal funding tracking
- **HTMX Integration**: Dynamic form updates without full page reloads

#### Serializers (`apps/poller/serializers.py`)

**Poll Serializers:**
- `PollSerializer`: Full poll representation with computed fields
- `PollCreateSerializer`: Poll creation with option validation
- `PollResultsSerializer`: Results with percentage calculations

**Vote Serializers:**
- `VoteSerializer`: Full vote representation
- `VoteCreateSerializer`: Vote casting with credential verification

#### Embed System (`apps/poller/embed.py`)

**EmbeddablePollWidget:**
- **Single Poll Embed**: `/embed/polls/{id}/`
- **Poll List Embed**: `/embed/polls/`
- **Parameters**: `embedding_app`, `user_did`, `scope`, `theme`
- **Visibility Logic**: `_can_user_view_poll()` method
- **Scope Filtering**: `_filter_by_scopes()` method

**EmbedPollView:**
- Minimal HTML for iframe embedding
- JavaScript-based dynamic loading

#### Signals (`apps/poller/signals.py`)

**Federation Signals:**
- `sync_poll_on_save`: Poll creation/update synchronization
- `sync_poll_on_delete`: Poll deletion synchronization
- `sync_vote_on_save`: Vote synchronization with versioning
- `sync_poll_option_on_save`: Option change synchronization

**Known Issues:**
- Vote count synchronization may increment multiple times
- Federated poll versioning can be inconsistent
- No conflict resolution for simultaneous votes

### Authentication System

**Current Implementation:**
- ✅ Traditional Django auth
- ✅ DID-based authentication
- ✅ OIDC providers (Google, GitHub)
- ✅ Hybrid authentication support
- ✅ Credential-based authorization

**Models:**
- `CustomUser`: Extended user model with DID support
- `DID`: Decentralized identifier management
- `VerifiableCredential`: VC storage and verification

### Federation Protocol

**Current Implementation:**
- ✅ Gossip protocol with message types
- ✅ Last-write-wins conflict resolution
- ✅ Version vectors for data consistency
- ✅ Proof-of-work message validation
- ✅ Node discovery and synchronization

**Message Types:**
- `announce`, `request`, `response`, `vote`, `credential`, `poll`, `merkle_update`, `ping`, `pong`

### Trust System

**Current Implementation:**
- ✅ Trust scoring (0.0-1.0)
- ✅ Issuer metrics tracking
- ✅ Peer endorsements
- ✅ Scope violation detection
- ✅ Dynamic threshold compliance

**Scoring Factors:**
- Verification success rate (30%)
- Peer endorsements (20%)
- Time since first issuance (15%)
- Unique holders (15%)
- Scope violations (-20% penalty)

## Technical Debt & Areas for Improvement

### Critical Issues

1. **Federation Consistency:**
   - Vote count synchronization can increment multiple times
   - Version vectors may not handle concurrent updates correctly
   - No transactional consistency across nodes

2. **Performance:**
   - Poll list queries with complex credential filtering
   - Vote counting requires full option table scans
   - No caching layer for frequently accessed polls

3. **Security:**
   - Credential verification happens synchronously in vote flow
   - No rate limiting on vote endpoints
   - IPFS/blockchain anchors not fully implemented

### Major Refactoring Opportunities

1. **Federation Overhaul:**
   - Implement proper CRDTs for conflict-free data types
   - Add transactional outbox pattern for reliable messaging
   - Implement Merkle tree verification for vote integrity

2. **Performance Optimization:**
   - Add Redis caching for poll results
   - Implement materialized views for vote counts
   - Add database indexing for common query patterns

3. **Security Enhancements:**
   - Asynchronous credential verification
   - Rate limiting and DDoS protection
   - Full IPFS/blockchain integration

4. **API Design:**
   - Standardize error responses
   - Add pagination to all list endpoints
   - Implement proper ETag/Last-Modified headers

### Missing Features

1. **Real-time Updates:**
   - WebSocket implementation for live results
   - Server-Sent Events for poll updates
   - Push notifications for vote events

2. **Advanced Polling:**
   - Ranked choice voting
   - Condorcet method support
   - Approval voting

3. **Governance:**
   - Delegated voting
   - Liquid democracy features
   - Proposal discussion threads

4. **Mobile:**
   - PWA manifest and service worker
   - Offline-first capabilities
   - Mobile-optimized UI components

## Development Recommendations

### Short-term (Next 3 Months)

1. **Fix Federation Issues:**
   - Implement proper vote count synchronization
   - Add conflict resolution tests
   - Implement transactional outbox for reliability

2. **Performance:**
   - Add Redis caching layer
   - Optimize credential filtering queries
   - Implement database indexing

3. **Security:**
   - Add rate limiting
   - Implement async credential verification
   - Add proper CORS configuration

### Medium-term (3-6 Months)

1. **Real-time Features:**
   - WebSocket implementation
   - Live result updates
   - Notification system

2. **Advanced Voting Methods:**
   - Ranked choice voting
   - Condorcet method
   - Approval voting

3. **Enhanced Federation:**
   - Merkle tree verification
   - Blockchain anchoring
   - IPFS integration

### Long-term (6-12 Months)

1. **Mobile Strategy:**
   - PWA implementation
   - Offline capabilities
   - Mobile SDK

2. **Governance Features:**
   - Delegated voting
   - Liquid democracy
   - Discussion threads

3. **Scalability:**
   - Horizontal scaling
   - Sharding strategy
   - Multi-region deployment

## Migration Strategy

### Backward Compatibility

**Breaking Changes to Expect:**
- Federation protocol changes will require node coordination
- Database schema changes for performance optimization
- API endpoint restructuring

**Migration Path:**
1. Implement new features behind feature flags
2. Maintain dual API versions during transition
3. Provide migration scripts for database changes
4. Document breaking changes clearly

### Testing Strategy

**Current Coverage:**
- Unit tests for core models
- Integration tests for API endpoints
- E2E tests for voting workflows

**Recommended Additions:**
- Federation consistency tests
- Load testing for performance
- Security penetration testing
- Cross-browser compatibility tests

## Architecture Decision Records

### Key Decisions Made

1. **Django Framework:**
   - Chosen for rapid development and admin interface
   - Trade-off: Less flexible than FastAPI for async operations

2. **DID-based Authentication:**
   - Decentralized identity as primary auth method
   - Trade-off: Higher complexity than traditional auth

3. **Scope-based Authorization:**
   - Flexible scope system for geographic/organizational polling
   - Trade-off: Complex credential filtering logic

4. **Federation Protocol:**
   - Gossip protocol with last-write-wins
   - Trade-off: Eventual consistency vs strong consistency

### Future Architecture Decisions

1. **Real-time Protocol:**
   - WebSockets vs Server-Sent Events vs polling
   - Recommendation: WebSockets for bidirectional communication

2. **Database:**
   - SQLite (dev) vs PostgreSQL (prod)
   - Recommendation: PostgreSQL for production scalability

3. **Frontend Framework:**
   - Current: Django templates + HTMX
   - Future: React/Vue for complex interactions

## Getting Started for Developers

### Development Setup

```bash
# Clone repository
git clone https://github.com/Code-Barn/polly-django.git
cd polly-django

# Install dependencies
uv sync

# Run migrations
uv run python manage.py migrate

# Create initial data
uv run python manage.py create_geographical_scopes

# Start server
uv run python manage.py runserver
```

### Key Development Areas

1. **Federation:**
   - `apps/core/federation.py` - Protocol implementation
   - `apps/poller/signals.py` - Synchronization logic

2. **Polling:**
   - `apps/poller/models.py` - Data models
   - `apps/poller/views.py` - API and template views

3. **Authentication:**
   - `apps/accounts/models.py` - User and DID models
   - `apps/accounts/utils/did_utils.py` - DID utilities

### Testing

```bash
# Run all tests
uv run python manage.py test

# Run with coverage
uv run pytest --cov=apps

# Run specific test
uv run python manage.py test apps.poller.tests
```

## Conclusion

Polly provides a solid foundation for decentralized polling with:
- Complete DID/VC authentication system
- Flexible scope-based authorization
- Functional federation protocol
- Embeddable widget system
- Proposal/funding workflows

**Key Focus Areas for Next Phase:**
1. Fix federation consistency issues
2. Implement real-time updates
3. Add advanced voting methods
4. Enhance mobile support

The architecture supports the planned features but requires refinement in federation consistency and performance optimization before production deployment.

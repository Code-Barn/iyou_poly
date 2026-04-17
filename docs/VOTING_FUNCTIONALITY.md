# Voting Functionality Implementation

## Overview

This document describes the voting functionality in Polly, a decentralized polling platform with credential-based authorization, family-scoped polls, and embeddable widgets.

## Features

### 1. Poll Creation
- Users create polls with title, description, and multiple options
- Duplicate options are automatically detected
- Poll types: `public`, `family_unit`, `family_scoped`, `organization`
- Scope-based voting requirements (credential type, scope type, scope value)
- Trust requirements (min issuer trust score, multiple issuers)
- Scheduled polls with `starts_at` and `ends_at` times
- Proposal mode with funding goal and deadline

### 2. Voting
- Authenticated users (or DID-based) can cast votes on active polls
- One vote per user/DID per poll
- Vote verification with cryptographic signatures
- Credential-based eligibility checking
- Real-time vote count updates via HTMX

### 3. Results Display
- Visual progress bars with percentages
- Total vote count displayed
- User's vote highlighted in UI
- Funding progress for proposals

### 4. Embeddable Polls
- Filter polls by embedding app and user credentials
- API endpoints for external app integration
- Theme support (light/dark)

## Data Models

### Poll Model
```python
- title, description
- poll_type: public|family_unit|family_scoped|organization
- parent_poll: for hierarchy
- embedding_app: external app identifier
- required_scope_type, required_scope, required_credential_type
- min_issuer_trust_score, require_multiple_issuers
- starts_at, ends_at: timing
- is_proposal, funding_goal, funding_current, funding_deadline
- ipfs_cid, blockchain_anchor, votes_merkle_root
```

### PollOption Model
```python
- poll: ForeignKey
- text: option text
- votes: denormalized count
```

### Vote Model
```python
- poll, option: ForeignKeys
- user: optional (for authenticated)
- voter_did: DID-based voting
- signature, credential_cid, credential_proof: cryptographic verification
- weight: vote weight
- ipfs_cid, blockchain_tx: decentralized storage
- is_verified, verification_details
```

## API Endpoints

### Poll CRUD
- `GET /api/polls/` - List polls (with filters: embedding_app, poll_type, scope)
- `POST /api/polls/` - Create poll
- `GET /api/polls/<id>/` - Get poll
- `PUT /api/polls/<id>/` - Update poll
- `DELETE /api/polls/<id>/` - Delete poll
- `GET /api/polls/<id>/results/` - Get poll results

### Voting
- `POST /api/polls/<id>/vote/` - Cast vote (HTMX)
- `POST /api/polls/<id>/cast/` - Cast vote (REST)
- `GET /api/polls/<id>/eligibility/` - Check if user can vote
- `POST /api/polls/<id>/fund/` - Add funding to proposal

### Embed
- `GET /api/embed/polls/` - Get polls for embedding
- `GET /api/embed/polls/<id>/` - Get single poll for embedding

## Key Properties

```python
# Check poll timing
poll.is_expired  # Has ended
poll.is_active_now  # Within start/end times

# Proposal funding
poll.funding_progress  # Percentage (0-100)
```

## Templates

### vote_combined.html
- Combined vote form and results
- Radio buttons for options
- Vote button per option
- Results with progress bars

### poll_detail.html
- Poll title, description, scope badges
- Vote form/results
- Cactus Comments integration

## Testing

1. **Poll Creation**: Valid options, duplicates, insufficient options
2. **Voting**: Authenticated, unauthenticated, duplicate votes, invalid options
3. **Results**: Vote counts, percentages, user vote highlight
4. **Edge Cases**: Inactive poll, invalid IDs, scope eligibility
5. **Embed**: Filter by app, filter by user credentials

## Maintenance Notes

1. Vote counts stored in both `Vote` model and `PollOption.votes` (denormalized)
2. HTMX for dynamic updates - ensure hx-post, hx-target are correct
3. Voting requires authentication or DID
4. Scope eligibility checked via `CheckVotingEligibilityAPIView`
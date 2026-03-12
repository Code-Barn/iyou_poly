# Polly Decentralized Polling - Technical Specification

## Project Overview

Polly is a decentralized, immutable polling application that enables distributed consensus determination through cryptographically-verified voting. The system uses Decentralized Identifiers (DIDs) for identity, Verifiable Credentials (VCs) for authorization, and IPFS + blockchain anchoring for data integrity.

---

## 1. Data Models

### 1.1 Credential Schema

```json
{
  "@context": [
    "https://www.w3.org/2018/credentials/v1",
    "https://polly.example.com/credentials/v1"
  ],
  "type": ["VerifiableCredential", "VotingAuthorization"],
  "issuer": "did:ethr:0x1234... (issuer DID)",
  "issuanceDate": "2024-01-01T00:00:00Z",
  "expirationDate": "2025-01-01T00:00:00Z",
  "credentialSubject": {
    "id": "did:ethr:0x5678... (holder DID)",
    "scope": {
      "type": "GeographicalScope",
      "name": "county",
      "value": "DeKalb County, IN"
    },
    "authorizationLevel": "standard",
    "issuedBy": "did:ethr:0x1234...",
    "issuedAt": "2024-01-01T00:00:00Z"
  },
  "credentialStatus": {
    "id": "https://polly.example.com/credentials/status/1",
    "type": "RevocationList2023"
  }
}
```

### 1.2 Issuer Hierarchy Model

```
┌─────────────────────────────────────────────────────────────┐
│                    ROOT TRUST LAYER                         │
│  (Optional: Foundation/Organization DID)                   │
│  - Establishes governance framework                        │
│  - Can authorize top-tier issuers                          │
└──────────────────────┬──────────────────────────────────────┘
                       │ (issues Authorizations)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   TIER 1: STATE ISSUERS                      │
│  - Authorized to issue county-level credentials            │
│  - Must hold StateAuthorization credential                 │
│  - Governance: State-level organizations/authorities       │
└──────────────────────┬──────────────────────────────────────┘
                       │ (issues VotingCredentials)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  TIER 2: COUNTY ISSUERS                      │
│  - Authorized to issue township/municipal credentials     │
│  - Must hold CountyAuthorization credential                │
│  - Maximum: N issuers per county (configurable)            │
└──────────────────────┬──────────────────────────────────────┘
                       │ (issues VotingCredentials)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  TIER 3: TOWNSHIP ISSUERS                   │
│  - Issue credentials to residents within their scope       │
│  - Must hold TownshipAuthorization credential               │
│  - In-person verification recommended                      │
└──────────────────────┬──────────────────────────────────────┘
                       │ (holds)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    HOLDERS / VOTERS                         │
│  - End users with DID + voting credentials                 │
│  - Can participate in polls within their scope            │
│  - Can request credentials from authorized issuers         │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Django Models

#### Credential Definition

```python
class CredentialType(models.Model):
    """
    Defines credential types and their issuance rules.
    """
    name = models.CharField(max_length=100)
    description = models.TextField()
    scope_type = models.CharField(
        max_length=50,
        choices=[
            ('state', 'State'),
            ('county', 'County'),
            ('township', 'Township'),
            ('municipal', 'Municipal'),
            ('global', 'Global'),
        ]
    )
    required_authorization = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        help_text="Credential type required to issue this credential"
    )
    max_issuers_per_scope = models.PositiveIntegerField(
        default=5,
        help_text="Maximum number of issuers allowed per scope"
    )
    requires_approval = models.BooleanField(
        default=True,
        help_text="Whether issuance requires multi-signer approval"
    )
    min_approvals = models.PositiveIntegerField(
        default=1,
        help_text="Minimum approvals required for issuance"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CredentialIssuance(models.Model):
    """
    Records all credential issuances for audit and sync.
    """
    credential = models.JSONField()
    holder_did = models.CharField(max_length=255)
    issuer_did = models.CharField(max_length=255)
    credential_type = models.ForeignKey(
        CredentialType,
        on_delete=models.PROTECT
    )
    scope_name = models.CharField(max_length=100)
    scope_value = models.CharField(max_length=255)
    ipfs_cid = models.CharField(max_length=255, blank=True)
    blockchain_tx = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('revoked', 'Revoked'),  # Future: for full lifecycle
            ('expired', 'Expired'),
        ],
        default='active'
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('holder_did', 'credential_type', 'scope_value')


class IssuerAuthorization(models.Model):
    """
    Tracks which issuers are authorized to issue credentials for a scope.
    """
    issuer_did = models.CharField(max_length=255)
    credential_type = models.ForeignKey(
        CredentialType,
        on_delete=models.PROTECT
    )
    scope_name = models.CharField(max_length=100)
    scope_value = models.CharField(max_length=255)
    authorized_by = models.CharField(max_length=255)
    authorization_credential = models.JSONField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('issuer_did', 'credential_type', 'scope_value')
```

#### Enhanced Poll Model (for reference)

```python
class Poll(models.Model):
    # ... existing fields ...
    
    # New fields for decentralized voting
    required_credential_types = models.JSONField(
        default=list,
        help_text="List of credential types required to vote"
    )
    required_scopes = models.JSONField(
        default=list,
        help_text="List of required scope names (e.g., ['county', 'township'])"
    )
    allowed_scope_values = models.JSONField(
        default=list,
        help_text="List of allowed scope values (e.g., ['DeKalb County', 'Auburn'])",
        blank=True
    )
    min_issuer_trust_score = models.FloatField(
        default=0.0,
        help_text="Minimum average trust score for accepted issuers"
    )
    require_multiple_issuers = models.BooleanField(
        default=False,
        help_text="Require credentials from multiple issuers"
    )
    
    # Poll data for IPFS
    poll_ipfs_cid = models.CharField(max_length=255, blank=True)
    poll_blockchain_anchor = models.CharField(max_length=255, blank=True)
    
    # Vote anchoring
    votes_ipfs_cid = models.CharField(max_length=255, blank=True)
    votes_merkle_root = models.CharField(max_length=255, blank=True)
    vote_count_anchor = models.CharField(max_length=255, blank=True)


class Vote(models.Model):
    # ... existing fields ...
    
    # Cryptographic verification
    voter_did = models.CharField(max_length=255)
    signature = models.TextField(
        help_text="Cryptographic signature from voter's DID key"
    )
    credential_cid = models.CharField(
        max_length=255,
        help_text="IPFS CID of voter's voting credential"
    )
    proof_of_credential = models.JSONField(
        help_text="Zero-knowledge proof of credential possession"
    )
    
    # Anchoring
    ipfs_cid = models.CharField(max_length=255, blank=True)
    blockchain_tx = models.CharField(max_length=255, blank=True)
    
    # Verification status
    is_verified = models.BooleanField(default=False)
    verification_details = models.JSONField(default=dict)
```

---

## 2. API Contracts

### 2.1 Credential Issuance API

#### POST /api/credentials/issue

**Request:**
```json
{
  "holder_did": "did:ethr:0x5678...",
  "credential_type": "voting_authorization",
  "scope": {
    "type": "county",
    "value": "DeKalb County, IN"
  },
  "issuer_did": "did:ethr:0x1234...",
  "proof_of_verification": {
    "method": "in_person",
    "verified_at": "2024-01-15T10:00:00Z",
    "notes": "Verified residence via utility bill"
  }
}
```

**Response (201):**
```json
{
  "credential": {
    "@context": [...],
    "type": ["VerifiableCredential", "VotingAuthorization"],
    "issuer": "did:ethr:0x1234...",
    "credentialSubject": {
      "id": "did:ethr:0x5678...",
      "scope": {
        "type": "county",
        "value": "DeKalb County, IN"
      },
      "authorizationLevel": "standard"
    }
  },
  "ipfs_cid": "QmXyZ...",
  "blockchain_tx": "0xabc123...",
  "issuance_id": "uuid-of-issuance-record"
}
```

#### POST /api/credentials/verify

**Request:**
```json
{
  "credential": { ... },
  "required_scope": {
    "type": "county",
    "value": "DeKalb County, IN"
  },
  "poll_id": "uuid-of-poll"
}
```

**Response (200):**
```json
{
  "is_valid": true,
  "verification_details": {
    "signature_valid": true,
    "issuer_authorized": true,
    "scope_matches": true,
    "not_expired": true,
    "issuer_trust_score": 0.85
  },
  "can_vote": true,
  "reason": null
}
```

### 2.2 Poll API

#### POST /api/polls/create

**Request:**
```json
{
  "title": "Should we pave Main Street?",
  "description": "Vote on whether to allocate budget for Main Street paving project",
  "geographical_scope": "township",
  "options": [
    "Yes, pave Main Street",
    "No, do not pave Main Street",
    "Abstain"
  ],
  "required_credentials": {
    "types": ["voting_authorization"],
    "scope_type": "township",
    "scope_value": "Auburn, IN",
    "require_multiple_issuers": false,
    "min_issuer_trust": 0.0
  },
  "creator_did": "did:ethr:0x1234...",
  "creator_signature": "0xsignature..."
}
```

**Response (201):**
```json
{
  "poll_id": "uuid",
  "ipfs_cid": "QmPollHash...",
  "blockchain_anchor": "0xBlockHash...",
  "created_at": "2024-01-20T14:30:00Z"
}
```

#### POST /api/polls/{id}/vote

**Request:**
```json
{
  "voter_did": "did:ethr:0x5678...",
  "option_index": 0,
  "signature": "0xvoteSignature...",
  "credential_proof": {
    "credential_cid": "QmCredHash...",
    "proof": "zero_knowledge_proof..."
  },
  "timestamp": "2024-01-20T15:00:00Z"
}
```

**Response (201):**
```json
{
  "vote_id": "uuid",
  "ipfs_cid": "QmVoteHash...",
  "verification_status": "verified",
  "blockchain_receipt": "0xReceipt..."
}
```

#### GET /api/polls/{id}/results

**Response (200):**
```json
{
  "poll_id": "uuid",
  "title": "Should we pave Main Street?",
  "ipfs_cid": "QmPollHash...",
  "merkle_root": "0xMerkleRoot...",
  "vote_count_anchor": "0xOnChainCount...",
  "results": [
    {
      "option": "Yes, pave Main Street",
      "vote_count": 142,
      "percentage": 52.2
    },
    {
      "option": "No, do not pave Main Street",
      "vote_count": 98,
      "percentage": 36.0
    },
    {
      "option": "Abstain",
      "vote_count": 32,
      "percentage": 11.8
    }
  ],
  "total_votes": 272,
  "verification": {
    "merkle_tree_valid": true,
    "vote_count_anchored": true,
    "all_signatures_verified": true
  }
}
```

### 2.3 Federation API

#### GET /api/federation/peers

**Response (200):**
```json
{
  "nodes": [
    {
      "node_id": "uuid",
      "endpoint": "https://polly-node-2.example.com",
      "public_key": "0x...",
      "last_seen": "2024-01-20T14:00:00Z",
      "sync_status": "in_sync"
    }
  ]
}
```

#### POST /api/federation/sync

**Request:**
```json
{
  "since_version": 100,
  "data_types": ["poll", "vote", "credential_issuance"]
}
```

**Response (200):**
```json
{
  "updates": [
    {
      "data_type": "poll",
      "data_id": "poll-uuid",
      "data": { ... },
      "version": 101,
      "source_node": "node-2",
      "signature": "0x..."
    }
  ],
  "latest_version": 150
}
```

---

## 3. Smart Contract Pseudocode

### 3.1 Poll Registry Contract (Polygon/Solidity)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract PollRegistry {
    
    // Structs
    struct Poll {
        bytes32 ipfsCid;           // IPFS content hash of poll data
        bytes32 voteMerkleRoot;   // Root of vote merkle tree
        uint256 voteCount;         // Anchor for vote count
        uint256 createdAt;
        address creator;
        bool isActive;
    }
    
    struct CredentialType {
        string name;
        string scopeType;          // state, county, township, etc.
        uint256 maxIssuers;
        bool isActive;
    }
    
    // State
    mapping(bytes32 => Poll) public polls;
    mapping(bytes32 => mapping(address => bool)) public hasVoted;  // pollId => voter => voted
    mapping(bytes32 => CredentialType) public credentialTypes;
    mapping(bytes32 => mapping(address => bool)) public authorizedIssuers;
    
    // Events
    event PollCreated(bytes32 indexed pollId, bytes32 ipfsCid, address creator);
    event VoteAnchored(bytes32 indexed pollId, bytes32 voteMerkleRoot, uint256 count);
    event IssuerAuthorized(bytes32 indexed credentialType, address issuer);
    event CredentialIssued(bytes32 indexed credentialCid, address holder, address issuer);
    
    // Functions
    
    function createPoll(
        bytes32 _pollId,
        bytes32 _ipfsCid,
        string[] calldata _requiredCredentialTypes,
        string[] calldata _allowedScopes
    ) external {
        require(polls[_pollId].createdAt == 0, "Poll already exists");
        
        polls[_pollId] = Poll({
            ipfsCid: _ipfsCid,
            voteMerkleRoot: bytes32(0),
            voteCount: 0,
            createdAt: block.timestamp,
            creator: msg.sender,
            isActive: true
        });
        
        emit PollCreated(_pollId, _ipfsCid, msg.sender);
    }
    
    function anchorVotes(
        bytes32 _pollId,
        bytes32 _merkleRoot,
        uint256 _voteCount
    ) external {
        require(polls[_pollId].creator == msg.sender, "Only creator can anchor");
        
        polls[_pollId].voteMerkleRoot = _merkleRoot;
        polls[_pollId].voteCount = _voteCount;
        
        emit VoteAnchored(_pollId, _merkleRoot, _voteCount);
    }
    
    function recordVote(
        bytes32 _pollId,
        address _voter,
        bytes32 _voteHash
    ) external {
        require(polls[_pollId].isActive, "Poll not active");
        require(!hasVoted[_pollId][_voter], "Already voted");
        // In full implementation: verify credential proof here
        
        hasVoted[_pollId][_voter] = true;
        polls[_pollId].voteCount += 1;
    }
    
    function hasVotedInPoll(bytes32 _pollId, address _voter) 
        external 
        view 
        returns (bool) 
    {
        return hasVoted[_pollId][_voter];
    }
    
    function getPoll(bytes32 _pollId) 
        external 
        view 
        returns (
            bytes32 ipfsCid,
            bytes32 voteMerkleRoot,
            uint256 voteCount,
            uint256 createdAt,
            address creator,
            bool isActive
        ) 
    {
        Poll memory p = polls[_pollId];
        return (p.ipfsCid, p.voteMerkleRoot, p.voteCount, 
                p.createdAt, p.creator, p.isActive);
    }
}
```

### 3.2 Credential Anchor Contract

```solidity
contract CredentialRegistry {
    
    struct CredentialIssuance {
        bytes32 credentialCid;    // IPFS hash of credential
        address holder;
        address issuer;
        string scopeType;
        string scopeValue;
        uint256 issuedAt;
        bool isActive;
    }
    
    struct IssuerAuthorization {
        address issuer;
        string credentialType;
        string scopeType;
        string scopeValue;
        address authorizedBy;
        uint256 authorizedAt;
    }
    
    mapping(bytes32 => CredentialIssuance) public credentials;
    mapping(bytes32 => IssuerAuthorization) public authorizations;
    mapping(address => mapping(string => bool)) public isAuthorized;
    
    event CredentialIssued(
        bytes32 indexed credentialId,
        bytes32 indexed credentialCid,
        address holder,
        address issuer,
        string scopeType,
        string scopeValue
    );
    
    event IssuerAuthorized(
        address indexed issuer,
        string credentialType,
        string scopeType,
        string scopeValue,
        address authorizedBy
    );
    
    function authorizeIssuer(
        bytes32 _authId,
        address _issuer,
        string calldata _credentialType,
        string calldata _scopeType,
        string calldata _scopeValue
    ) external {
        // Verify caller is authorized to issue authorizations
        // (In practice: check governance rules, previous authorization, etc.)
        
        authorizations[_authId] = IssuerAuthorization({
            issuer: _issuer,
            credentialType: _credentialType,
            scopeType: _scopeType,
            scopeValue: _scopeValue,
            authorizedBy: msg.sender,
            authorizedAt: block.timestamp
        });
        
        isAuthorized[_issuer][_credentialType] = true;
        
        emit IssuerAuthorized(_issuer, _credentialType, _scopeType, _scopeValue, msg.sender);
    }
    
    function issueCredential(
        bytes32 _credentialId,
        bytes32 _credentialCid,
        address _holder,
        string calldata _scopeType,
        string calldata _scopeValue
    ) external {
        require(isAuthorized[msg.sender][_credentialType], "Not authorized");
        
        credentials[_credentialId] = CredentialIssuance({
            credentialCid: _credentialCid,
            holder: _holder,
            issuer: msg.sender,
            scopeType: _scopeType,
            scopeValue: _scopeValue,
            issuedAt: block.timestamp,
            isActive: true
        });
        
        emit CredentialIssued(
            _credentialId, 
            _credentialCid, 
            _holder, 
            msg.sender, 
            _scopeType, 
            _scopeValue
        );
    }
}
```

---

## 4. Federation Protocol

### 4.1 Sync Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FEDERATION LAYER                              │
│                                                                      │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐       │
│  │ Node A  │◄───►│ Node B  │◄───►│ Node C  │◄───►│ Node D  │       │
│  │ (IN)    │     │ (OH)    │     │ (KY)    │     │ (MI)    │       │
│  └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘       │
│       │               │               │               │             │
│       └───────────────┴───────────────┴───────────────┘             │
│                    Gossip Protocol Layer                             │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Sync Protocol Specification

#### Message Types

```python
class SyncMessageType(Enum):
    ANNOUNCE = "announce"              # Node announces new data
    REQUEST = "request"                # Request missing data
    RESPONSE = "response"              # Respond to request
    VOTE = "vote"                       # New vote submitted
    CREDENTIAL = "credential"           # New credential issued
    POLL = "poll"                       # New poll created
    MERKLE_UPDATE = "merkle_update"     # Updated merkle root
    PING = "ping"                       # Keepalive
    PONG = "pong"                       # Keepalive response
```

#### Sync Message Format

```json
{
  "message_id": "uuid",
  "message_type": "vote",
  "sender_node": "node-uuid",
  "sender_endpoint": "https://polly-node-a.example.com",
  "timestamp": "2024-01-20T15:00:00Z",
  "signature": "0xmessageSignature...",
  "payload": {
    "data_type": "vote",
    "data_id": "vote-uuid",
    "data": { ... },
    "version": 101
  },
  "previous_hash": "0xPreviousMessageHash",
  "proof_of_work": 12345
}
```

### 4.3 Conflict Resolution

#### Strategy: Last-Write-Wins with Version Vectors

```python
class ConflictResolution:
    """
    Handles conflicts when nodes have divergent data.
    """
    
    @staticmethod
    def resolve(poll_data_a: dict, poll_data_b: dict) -> dict:
        """
        Resolve conflicts between two poll versions.
        Uses version vector comparison.
        """
        if poll_data_a.get('version', 0) > poll_data_b.get('version', 0):
            return poll_data_a
        elif poll_data_b.get('version', 0) > poll_data_a.get('version', 0):
            return poll_data_b
        else:
            # Same version: use timestamp-based tiebreaker
            if poll_data_a.get('updated_at') > poll_data_b.get('updated_at'):
                return poll_data_a
            return poll_data_b
    
    @staticmethod
    def resolve_vote_conflict(votes_a: list, votes_b: list) -> list:
        """
        Merge vote lists, removing duplicates by vote ID.
        """
        vote_map = {}
        
        for vote in votes_a:
            vote_map[vote['id']] = vote
        
        for vote in votes_b:
            if vote['id'] not in vote_map:
                vote_map[vote['id']] = vote
        
        return list(vote_map.values())
```

### 4.4 Gossip Protocol Implementation

```python
class GossipProtocol:
    """
    Implements epidemic/gossip protocol for data distribution.
    """
    
    FANOUT = 3  # Number of peers to send to
    MAX_HOPS = 4  # Maximum propagation hops
    
    def __init__(self, node_id: str, peer_nodes: list):
        self.node_id = node_id
        self.peers = peer_nodes
        self.message_buffer = {}
    
    async def gossip(self, message: SyncMessage):
        """
        Propagate message to random subset of peers.
        """
        targets = random.sample(self.peers, min(self.FANOUT, len(self.peers)))
        
        for peer in targets:
            await self.send_to_peer(peer, message)
        
        # Store in buffer for anti-entropy
        self.message_buffer[message.id] = message
    
    async def anti_entropy(self):
        """
        Periodic sync with random peer to ensure consistency.
        """
        peer = random.choice(self.peers)
        my_version = self.get_local_version_vector()
        
        request = SyncRequest(
            type="anti_entropy",
            version_vector=my_version
        )
        
        response = await self.send_request(peer, request)
        
        # Merge any missing data
        await self.merge_data(response.missing_data])
    
    async def merge_data(self, remote_data: dict):
        """
        Merge remote data with local data.
        """
        for data_type, items in remote_data.items():
            for item in items:
                local_item = self.get_local(data_type, item['id'])
                
                if local_item is None:
                    # New data from remote
                    await self.store_local(data_type, item)
                else:
                    # Check for conflict
                    resolved = ConflictResolution.resolve(local_item, item)
                    await self.store_local(data_type, resolved)
```

### 4.5 Federation API Endpoints

```python
# Federation views

class FederationNodeViewSet(viewsets.ModelViewSet):
    """Manage federation nodes."""
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Sync data with this node."""
        node = self.get_object()
        since_version = request.data.get('since_version', 0)
        
        data = FederatedData.objects.filter(
            version__gt=since_version
        ).order_by('version')[:1000]
        
        return Response({
            'data': [self.serialize_item(d) for d in data],
            'latest_version': data.last().version if data else since_version
        })
    
    @action(detail=True, methods=['post'])
    def announce(self, request, pk=None):
        """Announce new data to this node."""
        node = self.get_object()
        message = request.data
        
        # Verify signature
        if not self.verify_message_signature(message, node.public_key):
            return Response({'error': 'Invalid signature'}, status=401)
        
        # Store and propagate
        await self.process_announce(message)
        
        return Response({'status': 'announced'})


class DataSyncView(viewsets.ViewSet):
    """Handle data synchronization between nodes."""
    
    def list(self, request):
        """Get all data since version."""
        since = int(request.query_params.get('since', 0))
        
        data = FederatedData.objects.filter(
            version__gt=since
        ).order_by('version')[:500]
        
        return Response({
            'items': [serialize(d) for d in data],
            'latest_version': data.last().version if data else since
        })
    
    def create(self, request):
        """Push data to network."""
        # Verify sender authorization
        # Sign and broadcast to peers
        # Store locally
        pass
```

---

## 5. Trust Scoring System

### 5.1 Overview

The trust scoring system enables verifiers (poll creators, poll participants) to assess the reliability of credentials based on issuer behavior. This is optional — polls can choose their minimum trust threshold.

### 5.2 Trust Metrics

```python
class TrustMetrics:
    """
    Metrics tracked for each issuer.
    """
    
    ISSUER_FIELDS = [
        'total_credentials_issued',       # Total count
        'unique_holders',                   # Unique credential holders
        'credentials_this_month',           # Recent issuance rate
        'revocation_rate',                  # % revoked (full lifecycle)
        'verification_success_rate',        # % that pass verification
        'scope_violations',                 # Out-of-scope issuances
        'time_since_first_issuance',        # Age of issuer
        'peer_endorsements',               # Other issuer endorsements
    ]
```

### 5.3 Trust Score Calculation

```python
class TrustScorer:
    """
    Calculate trust scores for issuers.
    """
    
    # Weights for trust components
    WEIGHTS = {
        'verification_success_rate': 0.30,  # Most important: credentials work
        'peer_endorsements': 0.20,           # Community trust
        'time_since_first_issuance': 0.15,   # Longevity
        'unique_holders': 0.15,             # Breadth of issuance
        'scope_violations': -0.20,           # Penalty for violations
    }
    
    @classmethod
    def calculate_score(cls, issuer_did: str, scope: str) -> float:
        """
        Calculate trust score for an issuer within a scope.
        Returns score between 0.0 and 1.0.
        """
        metrics = IssuerMetrics.get(issuer_did, scope)
        
        score = 0.0
        
        # Verification success rate (0.0 - 1.0)
        verification_score = metrics.verification_success_rate
        score += verification_score * cls.WEIGHTS['verification_success_rate']
        
        # Peer endorsements (0.0 - 1.0)
        endorsement_score = cls._calculate_endorsement_score(issuer_did, scope)
        score += endorsement_score * cls.WEIGHTS['peer_endorsements']
        
        # Age score (0.0 - 1.0, logarithmic)
        age_score = cls._calculate_age_score(metrics.time_since_first_issuance)
        score += age_score * cls.WEIGHTS['time_since_first_issuance']
        
        # Breadth score (0.0 - 1.0)
        breadth_score = cls._calculate_breadth_score(metrics.unique_holders)
        score += breadth_score * cls.WEIGHTS['unique_holders']
        
        # Violation penalty
        if metrics.scope_violations > 0:
            violation_penalty = min(
                metrics.scope_violations * 0.05, 
                0.5
            ) * abs(cls.WEIGHTS['scope_violations'])
            score -= violation_penalty
        
        return max(0.0, min(1.0, score))
    
    @classmethod
    def _calculate_endorsement_score(cls, issuer_did: str, scope: str) -> float:
        """
        Calculate endorsement score based on peer reviews.
        """
        endorsements = IssuerEndorsement.objects.filter(
            endorsed_issuer=issuer_did,
            scope=scope,
            is_positive=True
        )
        
        # Simple: count / (count + 1)
        # More complex: weighted by endorser trust score
        return len(endorsements) / (len(endorsements) + 5)
    
    @classmethod
    def _calculate_age_score(cls, days_since_first: int) -> float:
        """
        Calculate age score (logarithmic, caps at 1 year).
        """
        if days_since_first <= 0:
            return 0.0
        
        import math
        return min(1.0, math.log(days_since_first + 1) / math.log(366))
    
    @classmethod
    def _calculate_breadth_score(cls, unique_holders: int) -> float:
        """
        Calculate breadth score based on unique holders.
        """
        # Logarithmic scale: 100 holders = 0.5, 1000 = 0.75, 10000 = 1.0
        import math
        return min(1.0, math.log(unique_holders + 1) / math.log(10001))
```

### 5.4 Trust Thresholds

```python
# Recommended trust thresholds for polls

TRUST_THRESHOLDS = {
    'low': 0.0,        # Any authorized issuer
    'medium': 0.4,     # Established issuers
    'high': 0.7,       # Well-reviewed issuers
    'very_high': 0.9,  # Highly trusted issuers only
}

# Poll configuration example
class Poll:
    min_trust_score = TRUST_THRESHOLDS['medium']  # 0.4
    
    # Or allow poll creators to specify
    custom_thresholds = {
        'county': 0.3,
        'township': 0.5,
    }
```

### 5.5 Endorsement System

```python
class IssuerEndorsement(models.Model):
    """
    Allows issuers to endorse each other.
    """
    endorser_did = models.CharField(max_length=255)
    endorsed_issuer_did = models.CharField(max_length=255)
    scope = models.CharField(max_length=100)
    is_positive = models.BooleanField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = (
            'endorser_did', 
            'endorsed_issuer_did', 
            'scope'
        )


class EndorsementAPI:
    """
    API for issuer endorsements.
    """
    
    @action(detail=True, methods=['post'])
    def endorse(self, request, issuer_did: str):
        """
        Endorse another issuer.
        """
        # Verify requester is an authorized issuer
        # Check scope compatibility
        # Create endorsement record
        pass
    
    @action(detail=True, methods=['post'])
    def revoke_endorsement(self, request, issuer_did: str):
        """
        Revoke an endorsement.
        """
        # Only endorser can revoke
        pass
```

### 5.6 Trust API Endpoints

```python
# Trust API

class TrustViewSet(viewsets.ReadOnlyModelViewSet):
    """Query trust scores and issuer metrics."""
    
    @action(detail=False, methods=['get'])
    def score(self, request):
        """Get trust score for an issuer."""
        issuer_did = request.query_params.get('issuer_did')
        scope = request.query_params.get('scope')
        
        score = TrustScorer.calculate_score(issuer_did, scope)
        
        return Response({
            'issuer_did': issuer_did,
            'scope': scope,
            'score': score,
            'score_label': self._get_score_label(score),
            'metrics': IssuerMetrics.get(issuer_did, scope)
        })
    
    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        """Get top issuers by trust score."""
        scope = request.query_params.get('scope')
        limit = int(request.query_params.get('limit', 10))
        
        # Query and rank by trust score
        pass
    
    @action(detail=True, methods=['post'])
    def endorse(self, request, pk=None):
        """Endorse an issuer."""
        pass
```

---

## Appendix A: Footnotes

### A.1 Additive-Only vs Full Lifecycle

**Current Implementation: Additive-Only**

The credential system is designed as additive-only:
- Issuers can issue credentials to holders
- No native revocation mechanism in initial version
- Trust scoring provides soft governance (low scores = less trusted)

**Future Extensibility: Full Lifecycle**

When ready to implement revocation:
1. Add `status` field to CredentialIssuance with 'active', 'revoked', 'expired'
2. Add revocation API with proper authorization checks
3. Implement credential status checks in verification flow
4. Add revocation to smart contract
5. Consider threshold-based revocation (require N issuers to revoke)

**Interim Governance:**
- Democratic revocation: Poll-based community vote on issuer trust
- Higher-tier issuer can de-authorize lower-tier issuer
- Automatic de-authorization triggers if trust score drops below threshold

### A.2 Data Flow Summary

```
User Action          →  Credential Flow         →  Vote Flow
─────────────────────────────────────────────────────────────────
1. Apply for cred    →  Request → Issuer        →  
2. Issuer verifies  →  Issue VC → IPFS         →
3. Credential stored→  Anchor hash → Chain     →
4. User votes        →  Present VC + proof     →  Sign vote
5. Vote verified     →  Check VC + scope       →  Record vote
6. Vote anchored     →                          →  IPFS + Chain
7. Results calculated→                          →  Merkle tree
8. Results synced    ←  Gossip protocol        ←  All nodes
```

---

## Appendix B: Security Considerations

1. **Key Management**: DID private keys must be securely stored; consider hardware security modules (HSMs) for issuers
2. **Signature Verification**: Always verify DID signatures before accepting credentials/votes
3. **IPFS Pinning**: Ensure critical data is pinned on multiple nodes
4. **Rate Limiting**: Implement rate limits on credential issuance and voting APIs
5. **Audit Logging**: All issuer actions logged to blockchain for accountability
6. **Network Security**: Node-to-node communication should use TLS + mutual authentication

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| DID | Decentralized Identifier - cryptographically-verifiable unique identifier |
| VC | Verifiable Credential - tamper-evident credential with cryptographic proof |
| IPFS | InterPlanetary File System - distributed content-addressed storage |
| Merkle Root | Hash summarizing all votes in a poll; enables verification without full data |
| Issuer | Entity authorized to issue credentials |
| Holder | Entity that holds (owns) a credential |
| Verifier | Entity that verifies credentials (e.g., poll) |
| Trust Anchor | Foundation entity that authorizes top-tier issuers |
| Scope | Geographic or organizational boundary for credential validity |

---

*Document Version: 1.0*  
*Last Updated: 2024-01-20*

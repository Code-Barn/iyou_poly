# 🌐 Omni-Social Meta-Protocol Spec v1

**Objective**: To provide a standardized, interoperable framework for sovereign digital life. The protocol ensures that identity is portable, data is content-addressed, and governance is verifiable.


## 🏗️ 1. The Core Stack (The "Omni-Stack")

| **Layer** | **Protocol / Tool** | **Role** |
| - | - | - |
| **Identity** | **DID (`did\_rust`)** | The Root of Trust. A single keypair for all services. |
| **Messaging** | **Nostr** | Global event distribution (Microblogging, Comments, Metadata). |
| **Real-time** | **XMPP (Prosody)** | End-to-end encrypted (OMEMO) instant messaging. |
| **Storage** | **Blossom (BUD-01)** | Content-addressed blob storage authenticated by Nostr keys. |
| **Governance** | **Poly** | Cryptographically verifiable polling and auditing. |


## 🛡️ 2. Identity & Authentication (The Mandate)

- **Sovereign Keypairs**: Users own their private keys. The system uses **Ed25519** for signing and verification.

- **Decentralized Identifiers (DID)**: All ecosystem members are identified by a DID (e.g., `did:key:z6Mk...`).

- **The IdP Bridge**: Web applications must use the `iyou\_idp` (OIDC) to verify a user's ability to sign a challenge without ever seeing the private key.

- **Executive Decision**: **No Passwords.** Standard Django password backends are strictly for legacy/fallback use and must be explicitly disabled in the primary social flow.


## 📜 3. Data & Storage (The "Sovereign Home")

- **Executive Decision: Postgres is for Indexing, not Ownership.** \* Centralized databases (Postgres) are used only for high-speed discovery and local app state.

  - Primary user data (posts, media, profile info) must be stored in **content-addressed formats**.

- **Blossom Protocol**: Large files (video, high-res images) are uploaded to a Blossom server (local or cloud) and addressed by their SHA-256 hash.

- **Metadata (NIP-94)**: File descriptions and hashes are broadcast as Nostr `kind:1063` events.

- **IPFS Optionality**: Blossom serves as the high-speed "hot storage" layer, while IPFS provides long-term global redundancy.


## 🛰️ 4. Communication & Federation

- **Social Feed (Nostr)**:

  - **kind:1**: Microblogging (Short-form text).

  - **kind:1111**: Threaded comments scoped to any ecosystem object (a poll, a video, a file).

  - **kind:30023**: Long-form articles and project documentations.

- **Real-time Chat (XMPP)**:

  - Used for secure, low-latency DMs and group rooms.

  - XMPP JIDs should be mapped to the user's DID to maintain identity continuity.

- **Executive Decision: Nostr replaces ActivityPub.** \* While ActivityPub is mature, Nostr's relay-based architecture aligns better with our key-based DID identity and "client-side-first" logic.


## 🗳️ 5. Governance (The Poly Integration)

- **Protocolized Opining**: Every project in the ecosystem (including `iyou\_wun` and `iyou\_home`) must support the **Poly Protocol**.

- **Verifiable Proofs**: Votes are signed by the user's DID and anchored to the Omni-Social Merkle Ledger.

- **Scoped Transparency**: Users can filter polls based on geographical or social scope, ensuring they only see governance events relevant to their verified identity.


## 🌈 6. The Sovereign Spectrum

We recognize that "Total Sovereignty" is a high bar. We offer two modes of participation:

1. **Managed (Level 1)**: User keys are stored in a secure cloud vault (managed by `iyou\_idp`). Easiest for onboarding.

2. **Sovereign (Level 2)**: User keys are stored locally in `iyou\_home`. Signing requests are sent via the **Local WebSocket Bridge** (`ws://127.0.0.1:9001`).


## 🚀 Strategic Directives for Developers

1. **Use the Enclave**: In `iyou\_home`, never expose raw keys to the React frontend. Keep signing in the Rust backend.

2. **Standardize Envelopes**: All API responses involving verification must follow the JSON schema: `\{"valid": bool, "error": "...", "details": \{\}\}`.

3. **Relay to Home Base**: Satellite apps (`iyou\_wun`, `poly\_django`) must provide a "Sync to Home" button that pushes a user's data/history to their local `iyou\_home` instance for backup.


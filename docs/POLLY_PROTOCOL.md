### **Polly Protocol Spec v1 (Draft)**

**Objective**: Define the rules, guarantees, and transparency mechanisms for Polly’s polling system.


#### **1. Authentication & Identity**

- **Mandate**: All users must authenticate via **Decentralized Identifiers (DID)** using the `did-rust-core` crate. 

- **Requirements**: 

  - Votes must be **cryptographically signed** by the user’s DID key. 

  - DID documents must comply with **W3C standards**. 

  - Support for **WebAuthn** (hardware keys) in future iterations. 


#### **2. Vote Logging & Ledger**

- **Mandate**: All votes must be stored in an **append-only, tamper-proof ledger** (IPFS or blockchain). 

- **Requirements**: 

  - Each vote log entry must include: 

    - Voter DID 

    - Timestamp 

    - Poll ID 

    - Vote weight (default: 1) 

  - **Merkle roots** of vote logs must be published every 100 votes (or hourly, whichever comes first). 

  - Ledger must be **publicly verifiable** via IPFS/blockchain explorer. 


#### **3. Voting Power Ratios**

- **Default Rule**: **1:1** (one user, one vote). 

- **Custom Ratios**: 

  - Must be **explicitly declared** in poll metadata (e.g., `"vote\_power\_rule": "investor\_share"`). 

  - UI must **visually indicate** non-1:1 ratios (e.g., gear icon ⚙️ with tooltip). 

  - Supported custom rules: 

    - `investor\_share` (e.g., 0.5x for partial owners) 

    - `daily` (e.g., 1 vote/24h for Musterd) 

- **Transparency**: 

  - Poll UI must display: 

    - Current ratio (e.g., "0.5x"). 

    - Reason for deviation (e.g., "Investor Governance"). 

  - API must expose ratio rules via `/polls/\{id\}/rules`. 


#### **4. Transparency & Auditability**

- **UI Requirements**: 

  - **Badges** for ratio status: 

    - ✅ for 1:1. 

    - ⚙️ for custom ratios. 

  - **"Verify this poll"** button linking to the public ledger. 

  - **Merkle root hash** displayed for cryptographic verification. 

- **Audit Tools**: 

  - CLI tool to verify poll results: 

  - ```
bash

  - Copy

  - `polly-audit verify --poll-id 123 --ledger ipfs://Qm...`
```

  - Browser extension to check ratios/rules in real time. 

  - Public dashboard for community-reported irregularities. 


#### **5. Federation & Self-Hosting**

- **Self-Hosting**: 

  - Provide **Docker images** for organizations to run their own Polly instances. 

  - Ensure self-hosted instances **adhere to the protocol** (e.g., transparency rules). 

- **Federation**: 

  - Support **ActivityPub** for cross-instance polls. 

  - Federated instances must **publish ledgers** to a shared network. 


#### **6. API & Embedding**

- **REST API Endpoints**: 

| **Endpoint** | **Method** | **Description** |
| :-: | :-: | :-: |
| `/polls` | POST | Create a poll (supports custom ratios). |
| `/polls/\{id\}/vote` | POST | Cast a vote (DID-signed). |
| `/polls/\{id\}/verify` | GET | Verify poll results (returns Merkle root). |
| `/polls/\{id\}/rules` | GET | Get vote power rules for a poll. |

- **Embeddable Widget**: 

  - JavaScript snippet for easy integration: 

  - ```
html

  - Copy

  - `\<script src="https://polly.byersbrands.com/widget.js"\>\</script\>`

  - `\<polly-poll id="123"\>\</polly-poll\>`
```

  - Supports **themes** and **transparency badges**. 


#### **7. Security & Anti-Tampering**

- **Guarantees**: 

  - Votes are **immutable** once logged. 

  - Ledger **cannot be altered** without breaking Merkle proofs. 

  - **Public audits** are encouraged via community tools. 

- **Tamper Detection**: 

  - Merkle root mismatches trigger **automated alerts**. 

  - Users can **report irregularities** via the dashboard. 


#### **8. Compliance & Governance**

- **License**: **AGPLv3** (to ensure open-source integrity). 

- **Contribution Rules**: 

  - All forks must **preserve transparency mechanisms**. 

  - Custom ratios must be **documented and justified**.


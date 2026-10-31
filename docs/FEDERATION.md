# iqoqo ActivityPub Federation Architecture

This document describes the server-to-server (S2S) ActivityPub federation architecture, trust model, and protocols supported by **iqoqo**.

---

## 1. Architectural Philosophy

iqoqo is designed as a **Library of Everything** built on the FRBR (*Functional Requirements for Bibliographic Records*) ontology. Federation in iqoqo extends catalog sharing, social friending, and peer-to-peer lending across independent nodes while preserving the **Own Your Data** local-first philosophy.

Key properties:

- **Server-to-Server (S2S) only**: No Client-to-Server (C2S) ActivityPub endpoints. Client interactions use the Next.js frontend with REST/JSON APIs.
- **Asynchronous Delivery**: Inbound and outbound activities are queued and dispatched via Celery (`federation` queue) backed by Redis.
- **Cryptographic Verification**: Inbound activities are verified using `draft-cavage-http-signatures-12` against public keys fetched via WebFinger and Actor dereferencing.

---

## 2. The 3-Tier Trust Model

Federated instances are classified into three distinct, non-overlapping trust levels:

| Trust Level | Peering Behavior | Catalog Sync | Friend Requests | Loan Requests |
| :--- | :--- | :--- | :--- | :--- |
| **`trusted`** | Verified peer instance | Full reciprocal metadata synchronization | Delivered to target users | Allowed (custodian approval) |
| **`untrusted`** | Known or discovering peer | Public catalog discovery only | Held for manual review or consent | Blocked |
| **`blocked`** | Denylisted instance | Rejected at HTTP signature gate | Dropped silently | Dropped |

> [!NOTE]
> ActivityPub peering is unilateral by default: adding an instance on Node Alpha authorizes Node Alpha to consume and interact with Node Beta, but Node Beta evaluates Node Alpha according to its own local trust settings.

---

## 3. Protocol Implementation & Endpoints

### 3.1 WebFinger (`RFC 7033`)

- **Endpoint**: `GET /.well-known/webfinger?resource=acct:user@domain`
- Resolves usernames or emails to ActivityPub Actor URIs (`application/activity+json`).
- Automatically normalizes loopback hosts (`localhost`, `127.0.0.1`) when `FEDERATION_ALLOW_LOOPBACK=true` in testing environments.

### 3.2 NodeInfo 2.1

- **Discovery**: `GET /.well-known/nodeinfo` returns links to supported NodeInfo schemas.
- **Metadata**: `GET /api/federation/nodeinfo/2.1` exposes instance metadata, software version (`0.9.x`), and active protocols (`["activitypub"]`).

### 3.3 Instance Actor & Key Fingerprints

- **Instance Actor**: `GET /api/federation/actor` returns the `Application` actor for server-level handshakes.
- **Actor Key Storage**: RSA-2048 private keys are stored encrypted at rest using symmetric Fernet encryption keyed from `SECRET_KEY`.
- **SHA-256 Fingerprint**: Verified peer keys can be provisioned or viewed in Admin Settings via SHA-256 fingerprint verification (`app/core/federation_keys.py`).

---

## 4. User Consent & Privacy

Each user retains sovereign control over federated social interactions in `/profile`:

- **`auto_accept_follows`**: When enabled, inbound `Follow` activities from users on `trusted` peers are accepted immediately without manual confirmation.
- **`default_item_visibility`**: Sets the default scope for newly cataloged items: `public`, `friends_only`, or `private`.
- **Federated Friends**: Friend requests sent between instances (e.g., `user@peer.domain`) verify mutual consent before exposing items marked with `friends_only` visibility.

---

## 5. Peer-to-Peer Lending Workflow

1. **Discovery**: User on Node Alpha locates a public item on Node Beta.
2. **Offer Activity**: Node Alpha dispatches an ActivityStreams `Offer` activity targeting Node Beta's inbox.
3. **Custodian Review**: The owner on Node Beta reviews the incoming request on `/admin/lending` and chooses to **Approve** or **Reject**.
4. **Resolution**: On approval, custody state transitions to `Lent` and an `Accept` or `Reject` activity is returned to Node Alpha.

## ADDED Requirements

### Requirement: Instance Application Actor Discovery and Signed Outbound GET Fetch

The system SHALL expose a read-only ActivityStreams `Application` actor document at `GET /api/federation/actor` publishing the local Instance Actor public key (`#main-key`), advertise `instance_actor` in NodeInfo 2.1 metadata, and support bodyless HTTP Signature signing (`(request-target) host date`) on outbound actor `GET` requests when the local Instance Actor key is provisioned.

#### Scenario: Provisioned instance serves Application actor JSON-LD and NodeInfo link

- **WHEN** a remote peer requests `GET /api/federation/actor` on an instance with federation enabled and `server.pem` provisioned
- **THEN** the endpoint returns `200 OK` (`application/activity+json`) with `type: "Application"`, canonical `id`, shared `inbox`, and `publicKey.publicKeyPem`, and `GET /api/federation/nodeinfo/2.1` includes `metadata.instance_actor`

#### Scenario: Unprovisioned instance returns 404 on Application actor GET without creating keys

- **WHEN** a client requests `GET /api/federation/actor` on an instance where `server.pem` has not been provisioned
- **THEN** the endpoint returns `404 Not Found` without writing key files

#### Scenario: Outbound GET request signs request-target, host, and date without Digest

- **WHEN** the outbound federation client fetches a remote actor document while `server.pem` is available (or `sign_request` is called for a `GET` with `body=None`)
- **THEN** the outbound request includes a valid `draft-cavage` `Signature` header over `(request-target) host date` using `#main-key` on the instance `Application` actor and omits the `Digest` header

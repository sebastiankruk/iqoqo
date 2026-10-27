# federation-index-and-docs Specification

## Purpose
Connected libraries directory discovery (`FederationInstance` trust graph) and comprehensive in-app bilingual (`en` / `pl`) end-user documentation hub (`/help`) with unified user requests (`Requests` / `/feedback`).

## Requirements

### Requirement: Federated Instance Directory Index
The system MUST support a read-only directory index view listing verified, publicly routable peer libraries from the Federation Trust Graph, displaying instance metadata, total public item counts, and federation endpoints, MUST exclude internal/non-routable container or loopback hostnames from public responses, and MUST degrade gracefully when S2S federation is disabled on the local instance.

#### Scenario: User visits directory index of connected libraries

- **GIVEN** an instance configured with `FEDERATION_DIRECTORY_ENABLED=true`
- **WHEN** a visitor navigates to `/federation/directory` or views the instance index
- **THEN** the system lists active connected peer libraries with their instance icons, descriptions, and public item counts
- **AND** private user collections and non-consented entities remain excluded

#### Scenario: Internal Docker, loopback, and private-IP peer hostnames are excluded from public directory

- **GIVEN** the Trust Graph contains internal test or container entries such as `web:5000`, `peer-web:5000`, `localhost:5005`, `node.local`, or RFC1918/loopback IP literals alongside public domains like `peer.iqoqo.cc`
- **WHEN** an unauthenticated visitor requests `GET /api/federation/directory`
- **THEN** only publicly routable DNS peer domains (such as `peer.iqoqo.cc`) appear in `peers` and `total_peers`, preventing internal network topology disclosure

#### Scenario: User visits directory index when federation is disabled on the local node

- **GIVEN** an instance where `FEDERATION_ENABLED` is `false`
- **WHEN** a visitor navigates to `/federation/directory`
- **THEN** the page still displays the local instance overview card (`GET /api/v1/public/federation/instance-info`) alongside a friendly notice that S2S federation is currently disabled, rather than failing with a raw HTTP error banner

### Requirement: In-App End-User Documentation Hub
The frontend application MUST provide an in-app documentation interface (`/help` and `/help/[slug]`) accessible from the main navigation ("Help & Guides" / "Pomoc i poradniki") and footer, featuring 5 comprehensive, illustrated guides in both English (`en`) and Polish (`pl`):

1. `frbr-hierarchy` — *Beyond the Bookshelf: How iqoqo Organizes Your World* (with visual asset `/images/help/frbr-pillars.jpg` and 6-domain WEMI comparison table)
2. `camera-to-catalog` — *From Camera to Catalog: Scanning, Manual Entry & Curatorial Help* (with visual asset `/images/help/scanner-workflow.jpg`)
3. `privacy-sharing-social` — *Privacy, Sharing & Social Interactions: The Hidden Gems* (with visual asset `/images/help/privacy-cascading-model.jpg`)
4. `federation-architecture` — *The iqoqo Federation: Connected Libraries, Sovereign Data* (with visual assets `/images/help/federation-overview.jpg` and `/images/help/federation-s2s-handshake.jpg`)
5. `curators-handbook` — *The Curator's Handbook: Mastering Complex FRBR Cases* (with visual assets `/images/help/curator-hybrid-sets.jpg`, `/images/help/curator-deduplication.jpg`, and the FRBR decision matrix table)

#### Scenario: Collector browses in-app help documentation

- **GIVEN** any authenticated or anonymous user
- **WHEN** the user clicks "Help & Guides" in the navigation or visits `/help`
- **THEN** the in-app documentation hub renders all 5 guides with category filtering, keyword search, embedded illustrations (`frontend/public/images/help/*.jpg`), and formatted GFM Markdown tables
- **AND** articles respect the user's active UI locale (`en` / `pl`) without raw Mermaid code blocks or AI prompt notes

### Requirement: Unified Requests Menu and Curator Escalations View
The user navigation menu MUST distinguish between documentation ("Help & Guides" -> `/help`) and user submissions ("Requests" / "Zgłoszenia" -> `/feedback`), and `/feedback` MUST provide a unified view for both platform feedback tickets (bugs/feature requests) and the user's Curator Escalations (`MyEscalations`) matching the pending badge count.

#### Scenario: User navigates to Requests from the user menu

- **GIVEN** an authenticated user with pending curator escalations or support tickets
- **WHEN** the user opens the user dropdown menu and clicks "Requests" ("Zgłoszenia")
- **THEN** the `/feedback` page displays both platform tickets and a "Curator Escalations" tab/section showing the user's metadata/deletion escalation requests

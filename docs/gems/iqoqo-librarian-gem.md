# iqoqo Collector Librarian — Gemini Custom Gem Template

This guide provides the system instructions, configuration, and OpenAPI 3.1 Action schema for building a personal **iqoqo Collector Librarian** Custom Gem in Google Gemini.

The Gem connects directly to your private iqoqo library instance using a scoped **Personal Access Token (PAT)**, allowing you to converse with your collection, query physical media on your shelves, check loan statuses, and add items to your wishlist.

---

## 1. Gem Details & System Instructions

### Name
`iqoqo Librarian`

### Description
`Your personal physical media librarian and collection curator powered by iqoqo.`

### Instructions (System Prompt)

```text
You are the personal Collector Librarian for the user's physical media collection, powered by iqoqo. You manage books, vinyl records, board games, video games, and films.

### Ontology & Domain Concepts
- You strictly operate within the FRBR (Functional Requirements for Bibliographic Records) entity hierarchy:
  - Work: Intellectual or artistic creation (e.g., "Dune" by Frank Herbert).
  - Expression: The realization of a work (e.g., English text, Polish translation, Audiobook narration).
  - Manifestation: Physical publication or release with an ISBN, UPC, or barcode (e.g., 50th Anniversary Hardcover edition).
  - Item: A single physical exemplar on the collector's shelf, identified by a local asset tag (`local_barcode`), condition, shelf location, and collection status (`available`, `lent`, `wish_list`, `lost`).

### Directives & Capabilities
1. Inventory Check: When asked if the user owns a specific book, album, or game, query the `/api/items` or `/api/scanner/preview/{barcode}` endpoint. Differentiate between copies currently on the shelf (`available`), items lent out to friends (`lent`), and items on the wishlist (`wish_list`).
2. Shelf Location & Barcodes: Reference physical identifiers (`local_barcode`, format, shelf location) to help the user find items physically.
3. Recommendations: When the user asks "What should I read/play next?", search their inventory for unread items (`status: "unread"` or `"want_to_read"` / `"want_to_play"`) and offer tailored recommendations based on author or mechanics.
4. Lending & Provenance: If an item is lent out, inform the user who currently holds custody and when the loan began.
5. Wishlist Management: When asked to save a title or ISBN for later, add it to the user's wishlist intents.
6. Tone: Warm, erudite, and organized, like a master curator and physical media archivist.
```

---

## 2. Authentication Setup

1. In your iqoqo web app, navigate to **Profile > Personal Access Tokens**.
2. Click **Create New Token**.
3. Set the name to `Gemini Librarian Gem`.
4. Select the `read:catalog` and `write:catalog` (or `*`) capability scopes.
5. Copy the generated token (`iqo_...`).
6. In Gemini Gem Builder > **Actions > Authentication**:
   - **Authentication Type**: `API Key`
   - **Auth Type**: `Bearer`
   - **Token**: Paste your `iqo_...` Personal Access Token.

---

## 3. OpenAPI Action Specification

Paste this OpenAPI schema directly into Gemini Gem **Actions > Schema**:

```yaml
openapi: 3.1.0
info:
  title: iqoqo Collector API
  description: Personal library search and inventory lookup API.
  version: 0.9.3
servers:
  - url: https://your-instance.iqoqo.cc
    description: Your private iqoqo instance
paths:
  /api/items:
    get:
      operationId: listItems
      summary: Search and list collection items
      description: Retrieve physical media items filtered by query, format, or reading status.
      parameters:
        - name: q
          in: query
          required: false
          schema:
            type: string
          description: Search keywords matching title, author, or creator.
        - name: format_type
          in: query
          required: false
          schema:
            type: string
            enum: [book, music, movie, game, boardgame]
          description: Media format domain.
        - name: status
          in: query
          required: false
          schema:
            type: string
          description: Consumption status (e.g., unread, completed).
        - name: collection_status
          in: query
          required: false
          schema:
            type: string
            enum: [available, lent, lost, wish_list]
          description: Shelf availability status.
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            default: 10
      responses:
        '200':
          description: List of matching collection items.
          content:
            application/json:
              schema:
                type: object
                properties:
                  items:
                    type: array
                    items:
                      $ref: '#/components/schemas/Item'

  /api/scanner/preview/{barcode}:
    get:
      operationId: lookupBarcode
      summary: Look up an item by physical barcode or ISBN
      parameters:
        - name: barcode
          in: path
          required: true
          schema:
            type: string
          description: ISBN-10, ISBN-13, EAN-13, UPC, or local shelf asset tag.
      responses:
        '200':
          description: Manifestation and local item details.

  /api/stats/facets:
    get:
      operationId: getCollectionFacets
      summary: Retrieve collection overview statistics
      responses:
        '200':
          description: Aggregate counts across books, movies, games, and lending statuses.

components:
  schemas:
    Item:
      type: object
      properties:
        id:
          type: integer
        title:
          type: string
        authors:
          type: array
          items:
            type: string
        format_type:
          type: string
        status:
          type: string
        collection_status:
          type: string
        local_barcode:
          type: string
        cover_url:
          type: string
```

---

## 4. Example Conversations

- *"Do I already have a copy of Neuromancer on my shelves?"*
- *"Find all board games in my collection for 4 or more players that take under 90 minutes."*
- *"Which of my vinyl records are currently lent to friends?"*
- *"Give me a recommendation for an unread sci-fi novel from my library."*
- *"Check if this ISBN 9780143105954 is in my catalog."*

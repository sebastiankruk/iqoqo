## Context

A fantasy novel (*The Lord of the Rings*), a boxed RPG video game (*The Elder Scrolls V: Skyrim* Collector's Edition), or a board game (*War of the Ring*) is not itself a "Cartographic Map" media category, yet it contains a prized map insert or world map. Conversely, a National Geographic folding trail map or historical atlas IS a standalone cartographic item. Supporting both cleanly requires modeling standalone cartographic formats alongside `frbroo:R15_has_part` / `iqoqo:hasMapAttachment` supplements.

## Goals / Non-Goals

**Goals:**
- Support cataloging standalone Maps & Atlases with `map_scale`, `map_projection`, and GeoNames links.
- Support attaching map images/metadata (`hasMapAttachment`) to any Book, Board Game, or Video Game `Manifestation` / `Work`, and tracking whether the physical `Item` still has its map insert (`map_insert_present`).
- Expose map attachments in RDF/JSON-LD and `meta_display.py`.

**Non-Goals:**
- Interactive pan/zoom frontend modal and collection facet UI (delivered in `C106`).

## Decisions

### Separating Manifestation Map Specification (`F3`) from Item Map Presence (`F5`)
* **Decision:** Store the canonical map attachment (`iqoqo:hasMapAttachment` with `title`, `image_url`, `map_type`) on the `Manifestation` (or `Work` for fictional world maps shared across editions), and store `map_insert_present: bool` on the physical `Item` (`F5`).
* **Rationale:** Respects FRBRoo: whether an edition was published with a fold-out/cloth map is an F3 Manifestation fact; whether a collector's second-hand copy still has that map inside the box is an F5 Item fact.

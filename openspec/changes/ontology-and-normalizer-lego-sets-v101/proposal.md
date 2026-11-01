## Why
Physical media collectors frequently catalog LEGO and construction sets alongside books, board games, and vinyl records (`#v100` in `iqoqo development notes.md`). To support LEGO sets without violating our strict four-tier FRBR/FRBRoo hierarchy, we must formally define the ontological mapping (`F16_Container_Work` -> `F2_Expression` -> `F3_Manifestation_Product_Type` -> `F5_Item`) and format normalizer rules before adding external ingestion.

## What Changes

- **FRBRoo Ontology & SHACL Shapes (`docs/ontology/iqoqo.ttl`, `iqoqo-shapes.ttl`, `taxonomy.ttl`):**
  - **Work (`frbroo:F16_Container_Work`):** Conceptual LEGO set design (`theme`, `subtheme`, `designer`, `release_year`).
  - **Expression (`frbroo:F2_Expression`):** Build specification and instruction manual version.
  - **Manifestation (`frbroo:F3_Manifestation_Product_Type`):** Retail box edition identified by official LEGO Set Number (`iqoqo:setNumber`, e.g., `10318-1`) and EAN/UPC barcode, with `iqoqo:pieceCount`, `iqoqo:minifigCount`, and `iqoqo:ageRange`.
  - **Item (`frbroo:F5_Item`):** Physical copy on the collector's shelf with `build_status` (`sealed | built | incomplete | parted_out`), `missing_pieces_count`, `instructions_included`, `box_included`, and `local_barcode`.
- **Format Normalizer & Taxonomy Sync (`shared/format_mappings.yaml`, `app/core/format_normalizer.py`, `frontend/types/taxonomy.ts`):** Register `lego` / `construction_set` category and formats (`standard_set`, `ucs_collector_set`, `technic_set`, `minifigure_series`, `polybag`, `modular_building`) and verify `scripts/sync_ontology.py --check` passes.

## Capabilities

### New Capabilities
- `lego-frbroo-ontology-and-taxonomy`: Four-tier FRBRoo ontological modeling, SHACL shapes, and format normalization for LEGO and construction sets.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `docs/ontology/iqoqo.ttl`, `docs/ontology/iqoqo-shapes.ttl`, `docs/ontology/taxonomy.ttl`
- `shared/format_mappings.yaml`, `app/core/format_normalizer.py`
- `frontend/types/taxonomy.ts`
- `tests/test_ontology_validation.py`, `tests/test_format_normalizer_lego.py`

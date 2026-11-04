## Context

Just as Board Games were modeled as `frbroo:F16_Container_Work` in `v0.7.13`, a LEGO set is a container work (comprising bricks, minifigures, sticker sheets, and instruction booklets) whose retail box release is an `F3_Manifestation_Product_Type` and whose physical copy on a collector's shelf (`F5_Item`) has build/completeness state (`sealed`, `built`, `incomplete`, `parted_out`).

## Goals / Non-Goals

**Goals:**
- Keep strict ontological separation between Manifestation-level attributes (`set_number`, `piece_count`, `minifig_count`) and Item-level physical states (`build_status`, `missing_pieces_count`, `box_included`, `instructions_included`).
- Synchronize `iqoqo.ttl`, `iqoqo-shapes.ttl`, `taxonomy.ttl`, `shared/format_mappings.yaml`, and `frontend/types/taxonomy.ts`.

**Non-Goals:**
- Rebrickable API lookup and UI facet projections (handled in `C104`).

## Decisions

### Four-Tier FRBRoo Separation for LEGO Sets
* **Decision:** Attach `iqoqo:setNumber`, `iqoqo:pieceCount`, and `iqoqo:minifigCount` to `Manifestation` (F3), and attach `iqoqo:buildStatus` (`sealed | built | incomplete | parted_out`), `iqoqo:missingPiecesCount`, and `iqoqo:instructionsIncluded` to `Item` (F5), enforced by SHACL shapes in `iqoqo-shapes.ttl`.
* **Rationale:** Prevents physical condition/completeness of a single box from polluting the shared catalog `Manifestation` or `Work`.

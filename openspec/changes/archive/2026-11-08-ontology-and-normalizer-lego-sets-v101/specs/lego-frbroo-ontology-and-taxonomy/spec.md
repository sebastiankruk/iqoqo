## Purpose
Define the four-tier FRBRoo ontology, SHACL shapes, and format normalizer taxonomy for cataloging LEGO and construction sets.

## ADDED Requirements

### Requirement: FRBRoo Four-Tier Separation for LEGO Sets

The ontology (`iqoqo.ttl`, `iqoqo-shapes.ttl`) and format normalizer (`shared/format_mappings.yaml`) SHALL model LEGO sets across all four FRBR tiers: `Work` (`F16_Container_Work` for set concept/theme), `Expression` (`F2_Expression` for build instructions), `Manifestation` (`F3_Manifestation_Product_Type` for retail box `set_number`, `piece_count`, `minifig_count`), and `Item` (`F5_Item` for physical `build_status`, `missing_pieces_count`, `instructions_included`).

#### Scenario: Validating a LEGO Manifestation and Item against SHACL shapes
- **GIVEN** a LEGO `Manifestation` with `iqoqo:setNumber "10318-1"` and `iqoqo:pieceCount 2083` and an owned `Item` with `iqoqo:buildStatus "built"`
- **WHEN** the RDF graph is validated against `docs/ontology/iqoqo-shapes.ttl`
- **THEN** SHACL validation succeeds with zero violations, and attaching `iqoqo:buildStatus` directly to a `Work` is rejected.

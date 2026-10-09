## Why

When catalog entities ingest broad multi-source metadata (such as Discogs styles/genres or OpenLibrary subjects on entities like https://preview.iqoqo.cc/manifestation/1569), the manifestation page renders an overwhelming tag cloud with dozens of unranked chips that dominate vertical space and lack provenance. In `v0.8.4`, introducing tag compaction with folding ("+X more"), frequency/authority weighting, and source provenance tooltips addresses dev-note item `#v084` ("where do all these tags come from + we need smarter way to render them when so many: https://preview.iqoqo.cc/manifestation/1569").

## What Changes

- Add tag cloud compaction to manifestation and item detail views, limiting initial rendering to the top N most relevant tags with an expandable "+X more" / "Show less" toggle.
- Annotate tags with source provenance (e.g. `discogs:style`, `openlibrary:subject`, `user:curated`) in tooltips or badges.
- Expose tag origin in API responses where available.

## Capabilities

### Modified Capabilities
- `tag-taxonomy-management`: Add tag display compaction requirements and origin provenance tracking for catalog entities.

## Impact

- `frontend/components/item/taxonomy-editor.tsx` & manifestation views: Implement compact collapsible tag chip rendering.
- `app/api/taxonomies.py` & FRBR entity serialization: Expose provenance classification when returning entity tags.

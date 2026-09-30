---
type: Concept
title: design
timestamp: 2026-07-22T10:18:50Z
---

## Context

The iQoQo catalog extracts taxonomy facet options (publishers, tags, genres) to allow users to filter the global and user libraries. Currently, the publisher faceted navigation filter strictly queries the `Manifestation.publisher` SQLAlchemy column. However, because iQoQo accepts flexible JSON metadata for works and manifestations (from external APIs/scans), the publisher value is frequently found inside the unstructured metadata block (e.g., `Manifestation.meta['Publisher']`, `Manifestation.meta['publisher']`, or `meta['label']`).

When the frontend encounters these JSON-stored publishers, it displays them correctly and generates a clickable filter URL (`?publishers=...`). However, the backend ignores JSON-stored publishers in `app/api/manifestations.py`, `app/api/items.py`, and `app/core/search_service.py`, resulting in 0 matches and excluding them from the faceted sidebar altogether.

## Goals / Non-Goals

**Goals:**

- Provide a robust way to filter `Manifestation` records using any permutation of the publisher name across the relational column and standard metadata fields.
- Update `taxonomies.py` to ensure publishers from `meta` appear in the global faceted navigation sidebar.
- Ensure `publisherCounts` accurately tracks occurrences of publishers located in `meta` via `app/core/data_manager.py`.

**Non-Goals:**

- We are **not** migrating the JSON `meta` fields into the relational `publisher` column at this time. This ensures no data is inadvertently overwritten, though a normalization task can be considered separately.
- We will not implement fuzzy matching for publishers.

## Decisions

**1. Query Logic using Coalesce**
Instead of querying just `Manifestation.publisher.ilike()`, we will construct a SQLAlchemy filtering block that uses an `or_()` condition across:

- `Manifestation.publisher.ilike()`
- `Manifestation.meta['Publisher'].as_string().ilike()`
- `Manifestation.meta['publisher'].as_string().ilike()`
- And conditionally for music: `db.and_(Expression.content_type == 'music', Manifestation.meta['label'].as_string().ilike())`

This guarantees all common schema structures are respected without failing silently, while ensuring that the `label` fallback is strictly scoped to music releases to avoid false positives on text or other media types.

**2. Taxonomy Extraction and Group By using Coalesce**
In `taxonomies.py` and `data_manager.py` (which powers the faceted counts), we will replace `Manifestation.publisher` with:

```python
func.coalesce(
    Manifestation.publisher,
    Manifestation.meta['Publisher'].as_string(),
    Manifestation.meta['publisher'].as_string(),
    db.case(
        (Expression.content_type == 'music', Manifestation.meta['label'].as_string()),
        else_=None
    )
)
```

This single, coalesced expression allows `group_by` aggregations to accurately map dynamic `meta` publishers to the correct string representation.

## Risks / Trade-offs

- **Performance Trade-off** → Searching and grouping over JSON fields using `coalesce` and `.as_string()` is generally slower than leveraging indexed relational columns.
  - _Mitigation_: The queries limit results quickly by applying pagination and checking exact equality or `ilike` on smaller subsets defined by FRBR taxonomy. We will evaluate performance and consider standardizing ingestion if necessary.

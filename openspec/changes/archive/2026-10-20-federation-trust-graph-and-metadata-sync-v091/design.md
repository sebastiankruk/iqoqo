## Context

Builds on v0.8.4 Custodian Provider Merge and multi-provider provenance tracking.

## Goals / Non-Goals

**Goals:**
- Zero data corruption from untrusted or malicious Fediverse peers.

**Non-Goals:**
- Automated overwriting of non-empty local fields without review.

## Decisions

### Custodian Queue for Ambiguity
* **Decision**: Pending peer contributions reuse the existing `ProviderMergeDialog`.
* **Rationale**: Unified review workflow for librarians.

## Risks / Trade-offs

- ('[Risk] Spam flooding merge queue', 'Mitigation: Blocked instances immediately dropped before creating review candidates.')

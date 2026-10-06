## Context
See proposal.md. External providers currently hardcode `limit=1` or `break` after the first match. The API needs to receive a list of `CandidateMetadataSchema` instead to disambiguate.

## Goals / Non-Goals
**Goals:**
- Enable `max_results` parameter in `app/strategies/book.py`, `app/utils/allegro.py`, and `app/utils/isbn.py`.
- Return multiple candidates to `app/api/scanner.py` for ambiguous queries.

**Non-Goals:**
- Changing the schema of `CandidateMetadataSchema`.
- Modifying other non-title lookup paths.

## Decisions
- Pass `max_results=10` to external lookups.
- Remove hardcoded `break` and limit clauses in the external wrappers.
- The `scanner` API endpoint will package the list of candidates into its response structure.

## Risks / Trade-offs
- Risk: Increased lookup latency for large result sets. Mitigation: Default `max_results` to a reasonable number (10) and paginate or bound external API calls.

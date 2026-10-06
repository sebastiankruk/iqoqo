## Context

See `proposal.md` for the motivation. The `feat/0.8.0/semantic-web` branch contains working code but is based on a very old commit (v0.7.0 era) and includes many deletions of test files and specifications that are still required on `main`.

## Goals / Non-Goals

**Goals:**

- Extract all semantic web additions (12 new files, 7 selectively modified files) from the old branch.
- Maintain compatibility with v0.7.18 hardening (e.g., authentication, rate limiting, encryption).

**Non-Goals:**

- Do not refactor the semantic web implementation itself (that will happen in subsequent changes if necessary).
- Do not merge the branch history directly.

## Decisions

- **Selective Cherry-Pick Strategy:** Instead of standard `git cherry-pick` (which would bring in unwanted file deletions and regressions), we will use `git checkout origin/feat/0.8.0/semantic-web -- <file>` for the 12 completely new files.
- **Manual Diff Application:** For the 7 modified files (like `frbr_service.py`), we will manually apply the specific semantic additions (e.g., `SCHEMA_TYPE_MAP`, `_enrich_graph_from_db`) rather than trying to perform a Git merge, which would conflict heavily with recent architectural changes.

## Risks / Trade-offs

- **Risk:** Silent regressions in `frbr_service.py` due to incorrect manual diff application.
  - **Mitigation:** Rely on the comprehensive test suite (`make test`). We are also cherry-picking the ~90 tests written for the semantic web features, which will validate the port.
- **Risk:** Missing dependencies.
  - **Mitigation:** Explicitly add `pyshacl>=0.26.0` to both `pyproject.toml` and `requirements.txt`.

## Context

See `proposal.md` for motivation and `.context/notes/review/1.0.2/principal-full-release-1.0.2-review.md` (`L-01`–`L-05`). These 5 Low-severity polish items were deferred from `v1.0.2` into `v1.0.3` (`C117`) so `v1.0.2` focuses strictly on the Critical and Moderate pre-merge items (`C114b`).

## Goals / Non-Goals

**Goals:**
- Clean up temporary branch references in `scripts/install.sh` (`L-01`).
- Add conditional secret-gated signing steps in `.github/workflows/mobile-build.yml` and installer SHA-256 packaging (`L-02`).
- Percent-encode `POSTGRES_PASSWORD` in `DATABASE_URL` and add `/api/system/status` + `/.well-known/webfinger` probes in `scripts/iqoqo_installer.py` (`L-03`).
- Add `q`, `collection_status`, `format`, and `item_id` query parameters to `GET /api/v1/admin/ownership/items` in `app/api/docs.py` (`L-04`).
- Fix `FEDERATION_HEAD_MODE` naming in `docs/CHANGELOG.md`, remove unused banner i18n keys in `en.json`/`pl.json`, and add `collectionFilters` evaluation to the offline filter block in `frontend/app/collection/page.tsx` (`L-05`).

**Non-Goals:**
- Modifying `v1.0.2` Critical/Moderate items already covered by `C114b` (`v102-release-review-security-and-offline-hardening`).

## Decisions

1. **Percent-Encoding `POSTGRES_PASSWORD` in `DATABASE_URL` (`L-03`)**: Use `urllib.parse.quote(pg_pass, safe="")` in `scripts/iqoqo_installer.py:157` so preserved passwords containing `@`, `:`, `/`, or `?` never corrupt the SQLAlchemy connection URI.
2. **Conditional Secret-Gated CI Steps (`L-02`)**: Use `if: ${{ env.HAS_SIGNING_SECRET == 'true' }}` (binding secrets via job `env:` per `C100g` conventions) in `.github/workflows/mobile-build.yml` so forks and secretless runs continue producing unsigned sideload artifacts without failing.

## Risks / Trade-offs

- **[Risk] Offline `Item` records may not carry collection membership arrays** $\to$ **Mitigation:** In `frontend/app/collection/page.tsx`, only apply `collectionFilters` in offline mode when the cached item exposes `collections` / `collection_ids` metadata, avoiding false empty results on legacy snapshots.

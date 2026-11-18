## 1. ItemTabs Federation Cleanup (Frontend)

- [ ] 1.1 Remove `FederationTab`, `Globe` import (if unused), and the `"federation"` entry from `TABS` in `frontend/components/item/item-tabs.tsx`, and add a localized federated loan / remote provenance badge inside `DetailsTab` when `item.is_borrowed`, `item.lent_to_name`, or `_provenance` federation metadata is present; add translation keys in `frontend/messages/en.json` and `frontend/messages/pl.json`
- [ ] 1.2 Add Vitest assertions in `frontend/__tests__/components/item/item-tabs.test.tsx` verifying `"Federation Coming Soon"` is absent even when `federation_enabled=true` and federated loan/provenance badges render in `DetailsTab`, verifying via `cd frontend && npx vitest run __tests__/components/item/item-tabs.test.tsx`

## 2. SQLAlchemy 2.0 Migration in Items API (Backend)

- [ ] 2.1 Migrate all remaining `Model.query` and `db.session.query()` calls in `app/api/items.py` (`ItemTag`, `Tag`, `Item`, `UserCollection`, `UserCollectionItem`, `Manifestation`, `ItemStatusLog`) to SQLAlchemy 2.0 `select()` / `db.session.execute()` (preserving `# pylint: disable=not-callable` on `func.count()`) and verify zero `.query` matches remain in `app/api/items.py`
- [ ] 2.2 Run backend item regression tests and linters (`IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_api_items*.py tests/test_item_*.py` and `IQOQO_AI_MODE=1 make lint`) to verify full backward compatibility

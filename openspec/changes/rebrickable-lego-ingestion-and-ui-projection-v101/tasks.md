## 1. Rebrickable Client, Encrypted Key & `LegoLookupStrategy` (`app/`)

- [ ] 1.1 Add `REBRICKABLE_API_KEY` to `app/config.py`, `.env.example`, Fernet-encrypted `InstanceSettings` (`app/db/settings.py`), and `frontend/components/admin/instance-settings.tsx`.
- [ ] 1.2 Implement `app/utils/rebrickable.py` using SSRF-safe `http_client.py` and `record_outbound_telemetry`, supporting lookup by set number (`10318` / `10318-1`) and search query, and recording `meta["_provenance"]` for all populated fields.
- [ ] 1.3 Implement `app/strategies/lego.py` (`LegoLookupStrategy`) and wire it into `app/api/scanner.py` with graceful fallback to manual entry on failure.

## 2. Metadata Display Projections & Item UI (`app/` & `frontend/`)

- [ ] 2.1 Extend `app/core/meta_display.py` to project `set_number`, `piece_count`, `minifig_count`, and `theme` on LEGO manifestations and `build_status` / `missing_pieces_count` / `instructions_included` on LEGO items.
- [ ] 2.2 Update `frontend/components/item/edit-item-dialog.tsx`, scanner media selector, and `en.json` / `pl.json` (sentence case) for LEGO sets.

## 3. Verification & Tests

- [ ] 3.1 Author backend tests in `tests/test_rebrickable_strategy.py` covering set-number lookup, EAN barcode resolution, Fernet key encryption, and graceful fallback when `REBRICKABLE_API_KEY` is unset.
- [ ] 3.2 Author Playwright E2E test `frontend/__tests__/e2e/lego_workflow.spec.ts` verifying LEGO set ingestion and item `build_status` updates.
- [ ] 3.3 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.

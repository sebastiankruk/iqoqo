## 1. Scanner TopBar Destination Pill Styling Alignment

- [x] 1.1 Update `policy-selector-trigger` in `frontend/components/scanner/top-bar.tsx` (line 170) to replace `border-white/25 bg-white text-black px-2.5 text-xs font-bold shadow-sm transition-colors hover:bg-white/90` with the cohesive translucent dark-glass pill classes (`border-white/20 bg-white/10 px-2.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-white/20` and `gap-1.5`) matching `format-selector-trigger`, while keeping `data-testid="policy-selector-trigger"`, dropdown menu options (`policy-option-{inventory,wishlist,catalog}`), and `scanner.topBar.policy*` i18n keys intact; verify `make format-js` passes cleanly.

## 2. Unit & E2E Verification

- [x] 2.1 Add a visual-harmony regression assertion to `frontend/__tests__/components/scanner/top-bar.test.tsx` verifying `policy-selector-trigger` renders with `bg-white/10` and `text-white` (and does NOT include solid `bg-white` or `text-black`), while existing `Shelf` / `Wishlist` / `Catalog Only` selection tests continue to pass; verify via `IQOQO_AI_MODE=1 npm --prefix frontend test -- __tests__/components/scanner/top-bar.test.tsx`.
- [x] 2.2 Run Playwright scanner regression checks (`frontend/__tests__/e2e/policy_scanning.spec.ts` and `frontend/__tests__/e2e/mobile_scanner.spec.ts`, if E2E environment is active) to confirm destination policy switching and single-line `TopBar` layout at `390x844` have zero clipping or regressions.

## 3. Local Gates & Knowledge Sync

- [x] 3.1 Run `IQOQO_AI_MODE=1 make secret-scan`, `IQOQO_AI_MODE=1 make lint`, and `IQOQO_AI_MODE=1 make test-parallel` and verify all gates pass with zero errors.
- [ ] 3.2 Run `IQOQO_AI_MODE=1 make knowledge-sync` after committing implementation changes and confirm clean `git status`.

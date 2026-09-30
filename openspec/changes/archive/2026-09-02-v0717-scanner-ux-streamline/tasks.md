## 1. TopBar UX and Policy Localization

- [x] 1.1 Add translation strings for scanner TopBar (title, instruction subtitle, format labels, policy labels "Shelf" / "Wishlist" / "Catalog Only", and policy hints) to `frontend/messages/en.json` and `frontend/messages/pl.json`. Verify JSON validity.
- [x] 1.2 Update `frontend/components/scanner/top-bar.tsx` to use `useTranslations("scanner")`, rename policy labels to "Shelf" / "Wishlist" / "Catalog Only", display active policy explanatory hint, and localize format buttons. Verify no lint errors.
- [x] 1.3 Update or add unit tests for TopBar in `frontend/__tests__/components/scanner/top-bar.test.tsx` to verify policy button rendering and format selection. Run tests to verify.

## 2. Disambiguation Sheet and SuccessCard Alignment

- [x] 2.1 Update `frontend/components/scanner/disambiguation-sheet.tsx` to streamline candidate card selection, localize text strings, and verify clean rendering.
- [x] 2.2 Update `frontend/components/scanner/success-card.tsx` to accept pre-filled metadata props instead of refetching by ID, align primary action button labels with selected policy ("Add to Shelf", "Add to Wishlist", "Add to Catalog"), and localize strings.
- [x] 2.3 Update unit tests in `frontend/__tests__/components/scanner/disambiguation-sheet.test.tsx` and `frontend/__tests__/components/scanner/success-card.test.tsx`. Run tests to verify.

## 3. End-to-End Workflow Validation

- [x] 3.1 Update Playwright E2E tests in `frontend/__tests__/e2e/scanner_workflow.spec.ts` to validate the streamlined scan flow (policy selection, candidate disambiguation, instant success card render without extra refetch). Run E2E tests to verify.

## 1. Extract Strings from camera-capture.tsx

- [x] 1.1 Audit all hardcoded English strings in `frontend/components/scanner/camera-capture.tsx`
- [x] 1.2 Create `scanner.cameraCapture.*` translation keys in `frontend/messages/en.json`
- [x] 1.3 Add `useTranslations('scanner')` hook and replace hardcoded strings with `t('cameraCapture.xxx')` calls
- [x] 1.4 Add Polish translations in `frontend/messages/pl.json` using sentence case

## 2. Extract Strings from bottom-sheet.tsx

- [x] 2.1 Audit all hardcoded English strings in `frontend/components/scanner/bottom-sheet.tsx`
- [x] 2.2 Create `scanner.bottomSheet.*` translation keys in `frontend/messages/en.json`
- [x] 2.3 Add `useTranslations('scanner')` hook and replace hardcoded strings with `t('bottomSheet.xxx')` calls
- [x] 2.4 Add Polish translations in `frontend/messages/pl.json` using sentence case

## 3. Write Tests

- [x] 3.1 Create Vitest test verifying camera-capture renders with all translation keys
- [x] 3.2 Create Vitest test verifying bottom-sheet renders with all translation keys
- [x] 3.3 Verify no hardcoded English strings remain in either component's JSX output

## 4. Verification

- [x] 4.1 Run `make format-js`
- [x] 4.2 Run `make lint-js && make lint-ts` — verify no errors
- [x] 4.3 Run `make test-frontend` — verify all tests pass
- [x] 4.4 Manual verification: switch locale to Polish and verify scanner strings render correctly

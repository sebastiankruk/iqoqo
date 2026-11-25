## Why

On `/scan`, the compact `TopBar` destination/policy selector pill (`policy-selector-trigger`, e.g., `"Shelf"`, `"Wishlist"`, `"Catalog Only"`) renders with a solid white background and bold black text (`bg-white text-black font-bold`), while its two sibling controls on the same row—the `Format` selector pill (`format-selector-trigger`) and inactive compact `Batch` toggle (`batch-scan-toggle`)—use a translucent dark-glass pill aesthetic (`bg-white/10 text-white border-white/20`). Per `iqoqo-ux-auditor` Action Hierarchy heuristics, this makes a passive secondary configuration selector visually louder than the active camera viewfinder and competing primary controls, creating unnecessary visual distraction during scanning.

## What Changes

- **Harmonize `/scan` `TopBar` destination pill styling (`frontend/components/scanner/top-bar.tsx`):**
  - Replace the high-contrast solid-white styling (`border-white/25 bg-white text-black font-bold hover:bg-white/90`) on `policy-selector-trigger` with the same cohesive translucent dark-glass pill styling used by `format-selector-trigger` (`border-white/20 bg-white/10 font-semibold text-white hover:bg-white/20`), preserving the `h-8`, `rounded-full`, `min-w-0`, `truncate`, and `ChevronDown` affordance.
  - Reserve high-emphasis primary fill (`bg-primary text-primary-foreground`) exclusively for active scanner toggle states (`Batch ON`, active `Flash`) so the control strip maintains clear visual hierarchy without horizontal clipping on `>= 360px` mobile viewports.
- **Preserve FRBR policy semantics and existing interactions:**
  - Keep all three destination policies (`inventory` → physical `Item` F5, `wishlist` → `UserWorkIntent`, `catalog` → `Manifestation` F3), menu options (`policy-option-inventory`, `policy-option-wishlist`, `policy-option-catalog`), tooltips, and `en.json` / `pl.json` `scanner.topBar.policy*` translations unchanged.
- **Add visual-hierarchy regression tests:**
  - Extend `frontend/__tests__/components/scanner/top-bar.test.tsx` to assert `policy-selector-trigger` uses translucent styling (`bg-white/10`, `text-white`) and does not apply solid `bg-white` / `text-black`.
  - Verify `/scan` destination selector behavior via existing Playwright scanner tests (`policy_scanning.spec.ts` / `mobile_scanner.spec.ts`).

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `scanner-ux-streamline`: Require the `TopBar` Destination Policy selector pill (`policy-selector-trigger`) to match the cohesive translucent dark-glass styling of sibling passive `TopBar` pills (`format-selector-trigger` and inactive `batch-scan-toggle`) rather than rendering as a solid high-contrast white button.

## Impact

- **Frontend UI:** `frontend/components/scanner/top-bar.tsx` (single component styling alignment; zero new dependencies, zero backend or database changes).
- **Tests:** `frontend/__tests__/components/scanner/top-bar.test.tsx` (Vitest) and `frontend/__tests__/e2e/policy_scanning.spec.ts` / `frontend/__tests__/e2e/mobile_scanner.spec.ts` (Playwright regression).
- **FRBR & Schema Impact:** None; preserves `inventory` (`Item`), `wishlist` (`UserWorkIntent`), and `catalog` (`Manifestation`) ingestion routing.

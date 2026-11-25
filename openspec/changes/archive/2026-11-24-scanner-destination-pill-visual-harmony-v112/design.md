## Context

See `proposal.md` for motivation. In `frontend/components/scanner/top-bar.tsx`, the scanner overlay `TopBar` renders a single-line compact control row (`bg-black/25 backdrop-blur-sm`) containing three controls:
1. `format-selector-trigger` (`line 127`): `border border-white/20 bg-white/10 px-2.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-white/20`
2. `policy-selector-trigger` (`line 170`): `border border-white/25 bg-white text-black px-2.5 text-xs font-bold shadow-sm transition-colors hover:bg-white/90`
3. `batch-scan-toggle` (`frontend/components/scanner/batch-scan-toggle.tsx:203`, `compact=true` when OFF): `border border-white/15 bg-white/10 text-white/90 hover:bg-white/20 hover:text-white` (switches to `bg-primary text-primary-foreground border-primary` only when `enabled === true`).

Under `iqoqo-ux-auditor` Action Hierarchy guidelines, `policy-selector-trigger`'s solid white pill steals focal priority from the viewfinder and from active state toggles (`Batch ON`, `Flash ON`).

## Goals / Non-Goals

**Goals:**
- Align `policy-selector-trigger` in `frontend/components/scanner/top-bar.tsx` with the translucent dark-glass pill styling of `format-selector-trigger` and inactive `BatchScanToggle`.
- Maintain legible contrast (`>= 4.5:1` white text over `bg-black/25` + `bg-white/10` camera backdrop) and zero horizontal overflow on `>= 360px` viewports.
- Lock the visual-hierarchy contract in Vitest (`frontend/__tests__/components/scanner/top-bar.test.tsx`).

**Non-Goals:**
- Changing destination policy values (`inventory`, `wishlist`, `catalog`), dropdown menu content, or FRBR ingestion routing.
- Altering `BatchScanToggle` active (`bg-primary`) or inactive styling, or modifying the `BottomSheet` capture tabs.

## Decisions

### 1. Exact Class Alignment on `policy-selector-trigger`
- **Decision:** Update `policy-selector-trigger` (`frontend/components/scanner/top-bar.tsx:170`) from:
  `inline-flex h-8 items-center gap-1 rounded-full border border-white/25 bg-white text-black px-2.5 text-xs font-bold shadow-sm transition-colors hover:bg-white/90 min-w-0`
  to:
  `inline-flex h-8 items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-2.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-white/20 min-w-0`
  matching `format-selector-trigger` token-for-token.
- **Alternatives Considered:**
  - *Alternative A — Apply a distinct colored accent (`bg-primary/20` or amber badge) when `currentPolicy !== "inventory"`:* Rejected for `C148` to keep the control row calm and uniform; the selected policy label (`"Shelf"` / `"Wishlist"` / `"Catalog Only"`) is already explicitly readable inside the pill and tooltip.
  - *Alternative B — Use Shadcn `<Button variant="ghost">` directly:* Rejected because the scanner `TopBar` sits over a live camera feed and intentionally uses overlay-safe `bg-white/10 text-white` pills independent of light/dark page theme tokens.

## Full-Page DOM Layout Snapshot (`/scan` TopBar — `390x844` Mobile)

```text
BEFORE                                        AFTER
-------------------------------------------   -------------------------------------------
Row 1 (bg-black/40 backdrop-blur-sm):         Row 1 (bg-black/40 backdrop-blur-sm):
  [<-]    Scan New Item           [Flash]       [<-]    Scan New Item           [Flash]
          (translucent)           (translucent)         (translucent)           (translucent)

Row 2 (bg-black/25 backdrop-blur-sm):         Row 2 (bg-black/25 backdrop-blur-sm):
  [Book v]  [■ SHELF v ■]       [Batch OFF]     [Book v]  [Shelf v]           [Batch OFF]
  (glass)   (SOLID WHITE!)      (glass)         (glass)   (glass — unified)   (glass)
  <= 3 controls in row (PASS <= 4)              <= 3 controls in row (PASS <= 4)

Row 3 (bg-black/20 backdrop-blur-sm):         Row 3 (bg-black/20 backdrop-blur-sm):
  [ 100% width unified lookup input       ]     [ 100% width unified lookup input       ]
```

## Interaction Friction Map (Change Scan Destination)

1. **Tap 1:** Tap `policy-selector-trigger` (`Shelf ▾`) in `TopBar` Row 2.
2. **Tap 2:** Tap `policy-option-wishlist` (`Wishlist`) or `policy-option-catalog` (`Catalog Only`) in dropdown.
- **Total Taps:** `2` (`<= 3` target PASS). Zero regression in interaction count or menu discoverability.

## Risks / Trade-offs

- **[Low-contrast bright camera background behind translucent pill]** → Mitigated by the existing `bg-black/25 backdrop-blur-sm` strip behind Row 2 (identical to `format-selector-trigger` and `BatchScanToggle`, which are already verified legible in production).

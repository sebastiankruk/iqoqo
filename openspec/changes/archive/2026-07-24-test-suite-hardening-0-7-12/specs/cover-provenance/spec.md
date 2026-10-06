## MODIFIED Requirements

### Requirement: Fallback cover design elements are visually verified

The `generate_fallback_cover` function in `app/utils/covers.py` SHALL produce a 600x900 JPEG image with a 28px bold "powered by iqoqo" footer text centered horizontally, a decorative separator line above the footer, and no call-to-action text. The test suite SHALL verify these design elements via Pillow pixel inspection.

#### Scenario: Fallback cover has 28px bold footer

- **WHEN** `generate_fallback_cover()` produces an image
- **THEN** the footer text SHALL be rendered with a font size of 28px measured by text bounding box height

#### Scenario: Separator line is rendered above footer

- **WHEN** `generate_fallback_cover()` produces an image
- **THEN** a horizontal line SHALL be visible at approximately `height - 92` pixels spanning the center 60% of the image width

#### Scenario: No CTA text present in fallback cover

- **WHEN** `generate_fallback_cover()` produces an image
- **THEN** no CTA-style text SHALL be present in the bottom portion of the image

#### Scenario: Footer text is horizontally centered

- **WHEN** `generate_fallback_cover()` produces an image
- **THEN** the footer text bounding box center x-coordinate SHALL be within 5 pixels of the image center (300px for 600px-wide image)

## ADDED Requirements

### Requirement: Watermark visual snapshots are enabled in E2E tests

The Playwright E2E test `watermark_verification.spec.ts` SHALL have its `toHaveScreenshot()` assertions enabled with `maxDiffPixels: 200` tolerance for both LLM-generated corner watermark and placeholder center watermark covers.

#### Scenario: LLM-generated cover has corner watermark

- **WHEN** the E2E test navigates to an item with a gen-AI cover
- **THEN** the cover image SHALL match the `llm_gen_corner_wm.png` snapshot within 200 pixel difference

#### Scenario: Placeholder cover has center watermark

- **WHEN** the E2E test navigates to an item with a placeholder cover
- **THEN** the cover image SHALL match the `placeholder_center_wm.png` snapshot within 200 pixel difference

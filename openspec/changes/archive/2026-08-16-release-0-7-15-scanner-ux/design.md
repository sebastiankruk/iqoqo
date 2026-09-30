## Context

Users occasionally experience ambiguity during the barcode scanning process due to the lack of clear visual feedback during API lookups. When lookups fail or time out, the app does not always handle the error gracefully, leading to a stuck state.

## Goals / Non-Goals

**Goals:**

- Provide clear, prominent visual feedback immediately upon image capture while awaiting asynchronous API responses.
- Implement robust error fallbacks that redirect the user to a manual entry form with any captured metadata pre-filled upon lookup failure.

**Non-Goals:**

- Implementing entirely new OCR logic.
- Rewriting the underlying scanner core logic.

## Decisions

- **Visual Feedback**: Render an animated overlay (similar to Google Lens) immediately when the capture is triggered.
- **Error Fallback**: Wrap the lookup process in a timeout/try-catch block. On timeout or unrecognized capture, automatically dismiss the loading overlay and navigate the user to the `manual-entry-form.tsx` component, pre-filling known data (e.g., captured barcode text if available).

## Risks / Trade-offs

- [Risk] Animated overlays might affect performance on lower-end devices. → Mitigation: Use CSS-only animations or lightweight Lottie files for the indicator.

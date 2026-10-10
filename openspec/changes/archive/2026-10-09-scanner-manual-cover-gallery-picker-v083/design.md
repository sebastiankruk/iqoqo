## Context

See `proposal.md` for user context. On mobile devices, collectors often photograph items beforehand and crop/edit them. When an item scan fails or needs manual entry, they want to choose their edited image rather than being forced to use camera snapshot.

## Goals / Non-Goals

**Goals:**
- Provide clear "Choose from Photos" button that triggers photo library selection without camera capture restrictions.
- Provide interactive thumbnail preview with remove and change actions.
- Preserve support for camera snapshot if the user prefers live capture.

**Non-Goals:**
- In-browser image editing or cropping tools (deferred).
- Multiple image uploads during manual item creation (additional scans remain handled via `MultiImageUploader` on manifestation detail).

## Decisions

- **Decision 1: File input without `capture` attribute for gallery selection.**
  - *Rationale:* HTML `<input type="file" accept="image/*">` without the `capture` attribute allows mobile operating systems (iOS and Android) to open the native photo library picker.
  - *Alternatives considered:* Single modal camera dialog (rejected: forces camera capture).
- **Decision 2: Client-side Object URL preview.**
  - *Rationale:* Use `URL.createObjectURL(file)` to show an immediate thumbnail with proper cleanup on unmount or file change.

## Risks / Trade-offs

- **[Risk]** Memory leak from unrevoked Object URLs.
  - *Mitigation:* Revoke created object URLs in `useEffect` cleanup.

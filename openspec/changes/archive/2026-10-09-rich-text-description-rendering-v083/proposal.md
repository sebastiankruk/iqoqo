## Why

Dev-note bug (#bugs #v081): "Descriptions with rich text (markdown, html) are current rendered verbatim exposing markup - we should have a safe way to render rich text -> problem still exists https://preview.iqoqo.cc/item/2027". Release planning: v0.8.x, C59 (target v0.8.3).

Premises verified against code:
- **Confirmed: Binary regex bifurcation in `extended-metadata.tsx`.** Lines 240-248 use `/<[a-z][\s\S]*>/i.test(description) ? <div dangerouslySetInnerHTML={{ __html: sanitizeHtml(description) }} /> : <ReactMarkdown>{description}</ReactMarkdown>`.
- **Confirmed: Flawed entity handling.** External providers (Google Books, OpenLibrary, Allegro) frequently deliver HTML entity-encoded descriptions (`&lt;p&gt;`, `&amp;lt;b&amp;gt;`). The regex fails to match encoded entities, routing them to `ReactMarkdown`, which displays the raw markup tags verbatim to the user as reproduced on item 2027.
- **Confirmed: No backend description sanitization.** Grep across `app/` reveals `bleach.clean()` is used only on user profiles and social posts, never on ingested or updated FRBR description metadata.
- **Confirmed: Inconsistent description rendering.** Different views (e.g. `item-timeline.tsx:160`, `extended-metadata.tsx`) use inconsistent approaches to rendering text descriptions.

## What Changes

- **Unified Client RichText Component:** Create a reusable `frontend/components/ui/rich-text.tsx` component that:
  1. Decodes HTML entities if double-encoded.
  2. Handles both mixed HTML and Markdown safely using DOMPurify and ReactMarkdown with safe tag whitelisting.
  3. Sanitizes all inputs against strict whitelists (`<b>`, `<i>`, `<em>`, `<strong>`, `<ul>`, `<ol>`, `<li>`, `<p>`, `<br>`, `<code>`, `<blockquote>`).
- **Standardized Surface Adoption:** Replace ad-hoc description rendering in `extended-metadata.tsx`, `item-timeline.tsx`, and detail views with `<RichText content={description} />`.
- **Backend Sanitization on Write:** Update `app/core/frbr_service.py` to sanitize incoming metadata descriptions on save via `bleach.clean()` allowing only safe formatting tags.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None (`skip_specs: true` has been set).

## Impact

- **Frontend:** `frontend/components/ui/rich-text.tsx`, `frontend/components/item/extended-metadata.tsx`, `frontend/components/item/item-timeline.tsx`.
- **Backend:** `app/core/frbr_service.py`.
- **Tests:** Pytest for backend description sanitization; Vitest tests for `RichText` component with HTML-entity fixtures, markdown fixtures, mixed markup, and XSS attack vectors.

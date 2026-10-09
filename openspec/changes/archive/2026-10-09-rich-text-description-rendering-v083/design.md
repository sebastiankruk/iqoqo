## Context

See `proposal.md` for reproduction context. Item descriptions containing HTML tags or encoded entities currently display raw markup text instead of formatted rich text.

## Goals / Non-Goals

**Goals:**
- Render safe formatted text for Markdown, HTML, and entity-encoded rich text.
- Prevent XSS attacks via strict tag whitelisting and DOMPurify sanitization.
- Centralize all description rendering behind a single robust `RichText` component.
- Sanitize metadata descriptions in `frbr_service.py` on write.

**Non-Goals:**
- Supporting arbitrary raw HTML (e.g. `<script>`, `<iframe>`, `<form>` remain strictly blocked).
- Implementing a full WYSIWYG editor for descriptions.

## Decisions

- **Decision 1: Unified `RichText` component with pre-decoding.**
  - *Rationale:* Decoding double-encoded HTML entities (e.g. `&lt;p&gt;` -> `<p>`) before running DOMPurify ensures HTML descriptions from legacy providers render naturally rather than exposing raw tags.
  - *Alternatives considered:* Relying purely on ReactMarkdown (fails to parse raw HTML blocks without rehype plugins).
- **Decision 2: Strict HTML Whitelist.**
  - *Rationale:* Whitelist safe semantic formatting tags: `b`, `i`, `em`, `strong`, `u`, `p`, `br`, `ul`, `ol`, `li`, `code`, `pre`, `blockquote`, `a` (enforcing `rel="noopener noreferrer"` and `target="_blank"`).

## Risks / Trade-offs

- **[Risk]** Performance impact of client-side DOMPurify sanitization on long text.
  - *Mitigation:* DOMPurify is lightweight and executes in <2ms for typical book and album descriptions.

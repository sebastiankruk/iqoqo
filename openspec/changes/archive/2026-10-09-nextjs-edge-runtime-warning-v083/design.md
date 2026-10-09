## Context

See `proposal.md` for build log findings. Next.js 16 deprecated the Edge Runtime, warning developers to use Node.js runtime instead.

## Goals / Non-Goals

**Goals:**
- Identify and eliminate or document the trigger causing the Edge Runtime deprecation warning during Docker builds.
- Ensure all middleware and proxy functionality (`proxyTimeout: 120000`, auth redirects) operates identically on Node.js runtime.
- Maintain fast build times and zero runtime regressions.

**Non-Goals:**
- Upgrading to Next.js 17 major version in this release.
- Rewriting Next.js proxy middleware architecture.

## Decisions

- **Decision 1: Explicit Node.js runtime declaration where supported.**
  - *Rationale:* Next.js 16 allows declaring `export const runtime = 'nodejs'` or configuring runtime targets in `next.config.ts`.
- **Decision 2: Preserve proxy timeout threshold.**
  - *Rationale:* Long-running SPARQL queries and batch uploads rely on `proxyTimeout: 120_000`. Any configuration adjustments must preserve this ceiling.

## Risks / Trade-offs

- **[Risk]** Next.js 16 middleware internals might enforce edge runtime behavior internally.
  - *Mitigation:* Verify whether the warning is a non-breaking deprecation notice versus actionable configuration; document findings clearly in `docs/OPERATIONS.md`.

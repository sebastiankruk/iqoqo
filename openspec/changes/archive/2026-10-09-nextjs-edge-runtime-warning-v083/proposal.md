## Why

Dev-note finding (#v083): Docker frontend build output emits:
```text
⚠ The Edge Runtime is deprecated. You can use the "nodejs" runtime instead. Learn more: https://nextjs.org/docs/messages/edge-runtime-deprecated
```
Release planning: v0.8.x, C56 (target v0.8.3).

Premises verified against code:
- **Confirmed: Next.js 16.3.6.** `frontend/package.json` uses Next.js 16.3.6 (`next: 16.3.6`). In Next.js 16, Edge runtime is formally deprecated for middleware and route execution in favor of standard Node.js runtime.
- **Confirmed: No explicit `runtime = 'edge'` in codebase.** Grep across `frontend/` confirms no source file declares `export const runtime = 'edge'`.
- **Confirmed: Source of trigger.** The warning is emitted during production build (`output: "standalone"`) because Next.js 16 defaults legacy middleware conventions (like `frontend/proxy.ts`) to Edge runtime evaluation unless Node.js runtime is configured or middleware is migrated to Next 16 routing conventions.
- **Scope:** Investigation-first change to isolate the exact trigger in Next 16 build, migrate configuration to Node.js runtime, ensure `proxyTimeout: 120000` remains intact, and add a build log check.

## What Changes

- **Build Runtime Configuration:** Configure Next.js middleware and route handlers to target the Node.js runtime rather than the deprecated Edge runtime.
- **Proxy Configuration Audit:** Verify that `frontend/proxy.ts` and `frontend/next.config.ts` (`experimental.proxyTimeout: 120_000`, `proxyClientMaxBodySize: "60mb"`) function cleanly without Edge runtime warnings.
- **Build Log Verification:** Add build log inspection in CI / Makefile build checks ensuring the deprecation warning is silenced. If upstream Next 16 emits an unsuppressible warning for middleware until Next 17, document and pin.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None (`skip_specs: true` has been set).

## Impact

- **Frontend Build:** `frontend/next.config.ts`, `frontend/proxy.ts`.
- **CI / Docker:** `Dockerfile.prod`, build output hygiene.
- **Tests:** Verify `npm run build` completes cleanly without deprecation warnings.

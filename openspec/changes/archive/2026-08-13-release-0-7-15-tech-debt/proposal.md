## Why

Deferred dependency updates and technical debt must be resolved at the start of the 0.7.15 release cycle to ensure security patches and major version bumps land safely together.

## What Changes

- **Backend**: Upgrade `celery[redis]` / `kombu` to a release that lifts the `redis < 6.5` constraint, and bump `redis ==5.*` to `==8.*`.
- **Backend**: Bump `openai >=2.51` to `>=2.53` and `google-genai >=2.16` to `>=2.17`.
- **Frontend**: Upgrade `lucide-react ^0.575.0` to `^1.30.0` and fix icon export breakages across the test suite (`Element type is invalid ... got: undefined`).
- **Frontend**: Apply the `npm-runtime-minor` group bump (39 packages including `next 16.3.0`, `@tanstack/react-query 5.101.4`, `playwright 1.62.1`, etc.).
- **BREAKING**: Next.js major bump requires verifying `next build`, vitest, and Playwright E2E tests for breaking changes.

## Capabilities

### New Capabilities

- `dependency-tech-debt-updates`: Managing and applying necessary backend and frontend dependency bumps and fixing related code breakages.

### Modified Capabilities

## Impact

- **Backend**: `requirements.txt`
- **Frontend**: `package.json`, `frontend/__tests__/app/page.test.tsx`, `frontend/__tests__/components/landing/hero.test.tsx`
- **Testing**: Playwright E2E and Vitest suites for verifying Next.js and Lucide-React upgrades.

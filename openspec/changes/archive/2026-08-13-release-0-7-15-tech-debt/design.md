## Context

The 0.7.15 release cycle begins with updating core dependencies to maintain security patches and address deferred technical debt. Key dependencies needing updates include `celery`, `redis`, `next`, and `lucide-react`.

## Goals / Non-Goals

**Goals:**

- Update Next.js to 16.3.0 and resolve any breaking changes in the build or E2E tests.
- Upgrade `lucide-react` to `1.30.0` and fix missing/broken imports causing "Element type is invalid" test failures.
- Resolve pip conflicts by safely lifting the `redis < 6.5` constraint introduced by `kombu`.

**Non-Goals:**

- Upgrading to unverified beta releases.
- Rewriting caching logic to migrate off Redis.

## Decisions

- **Dependency Upgrades**: Proceed with a grouped `npm-runtime-minor` update for the frontend to minimize multiple fragmented update PRs.
- **Python Pinning**: Force-upgrade `celery[redis]` and `redis` together via `pip install "celery[redis]==5.6.*" "redis==8.*"` to bypass `ResolutionImpossible` errors.

## Risks / Trade-offs

- [Risk] The major bump in Next.js could introduce regressions in page rendering. → Mitigation: Run full Playwright E2E and Vitest suites locally before merge.
- [Risk] `lucide-react` v1 removes some deprecated icons. → Mitigation: Manually review failed icon imports and replace with newer equivalents.

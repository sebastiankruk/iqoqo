# Dependency Tech Debt Updates

## Purpose

Track dependency versions and compatibility needed for reliable frontend builds and backend worker startup.

## Requirements

### Requirement: NextJS Upgrade

The system SHALL operate on Next.js 16.3.0 without build or runtime errors.

#### Scenario: Production Build

- **WHEN** the `next build` command is executed
- **THEN** the application bundles successfully without dependency or type errors.

### Requirement: Lucide React Icons

The frontend SHALL utilize `lucide-react` v1.x and correctly import all icons without throwing undefined component errors.

#### Scenario: Icon rendering in unit tests

- **WHEN** the frontend test suite runs (specifically `frontend/__tests__/app/page.test.tsx` and `hero.test.tsx`)
- **THEN** all tests pass and no "Element type is invalid" errors are thrown.

### Requirement: Redis Backend Cache

The backend SHALL run on `redis` version 8.x along with compatible versions of `celery` and `kombu`.

#### Scenario: Celery worker initialization

- **WHEN** the Celery worker starts up
- **THEN** it successfully connects to the Redis broker without version incompatibility warnings or `ResolutionImpossible` install errors.

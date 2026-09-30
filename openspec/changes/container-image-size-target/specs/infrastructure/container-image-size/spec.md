## Purpose

Brings the production backend image under a size target the product can
actually satisfy, by removing a transitive dependency that accounts for 20% of
the image and by turning the target into a gate that fails a build rather than a
prose assertion that a release can quietly miss.

Follows `devops-infrastructure-updates` (C17), which reduced the image from
1019.2 MB to 826.7 MB and documented that its own `<500 MB` target was not
reachable.

## ADDED Requirements

### Requirement: Perceptual Hash Without Numerical-Library Dependencies

The cover de-duplication path MUST compute perceptual hashes using only the
standard library and Pillow. It MUST NOT require `scipy` or `numpy`, which are
not otherwise used by the application and together account for 167 MB of the
production image.

#### Scenario: Computing a perceptual hash for cover de-duplication

- **WHEN** a cover image is hashed to decide whether it duplicates a known image
- **THEN** the hash is computed without importing `scipy` or `numpy`
- **THEN** the result is byte-identical to the hash previously produced by `imagehash.phash` for the same input

#### Scenario: Comparing against previously stored hashes

- **WHEN** a computed hash is compared against hashes stored in `IQOQO_KNOWN_JUNK_PHASHES`
- **THEN** hashes produced by the previous algorithm continue to match
- **THEN** a mismatch in the algorithm is detectable rather than silently degrading de-duplication to matching nothing

### Requirement: Enforced Container Image Size Gate

The container build MUST fail when the produced image exceeds its declared size
target, and MUST report the per-component breakdown when it does.

#### Scenario: Building the production image within target

- **WHEN** the production backend image is built
- **THEN** its uncompressed size is measured from the built image, not estimated
- **THEN** the build fails if the size exceeds the target
- **THEN** the failure output lists the size of each significant path in the image, so the cause is identifiable without rebuilding

#### Scenario: Target is recorded as achievable

- **WHEN** the size target is changed
- **THEN** the measured size of the current image is recorded alongside it
- **THEN** the target is not left above a size the image cannot reach without a documented product decision

## MODIFIED Requirements

### Requirement: Multi-stage Docker Build Image Size Under 500MB

The production container image build process MUST employ multi-stage compilation
to isolate build-time compilers and development headers, stripping bytecode and
unused caches. The size target is enforced by the build gate above, whose
documented value reflects what the current dependency set supports.

**Changed from C17**, which published `under 500MB` as a requirement while
measuring 826.7 MB. That was a contract the product did not honour, and archiving
it into the main specs would have made the specification actively wrong. The
multi-stage build and its isolation properties are delivered and verified; the
size number moves to a value that is met, and the work required to go lower is
tracked by this change rather than asserted as done.

#### Scenario: Building the production image

- **WHEN** the production backend image is built using `deploy/Dockerfile`
- **THEN** compiler toolchains and development headers are isolated to the builder stage
- **THEN** the final runtime image excludes build tools, development packages, and unused binaries
- **THEN** the resulting size is checked against the enforced target rather than asserted in prose

#### Scenario: Reconciling the recorded target with reality

- **WHEN** this requirement is published
- **THEN** the size figure it states is one the current image actually satisfies
- **THEN** any lower target is tracked as open work in a change, not published as a satisfied requirement

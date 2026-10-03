## Purpose

Brings the production backend image to a size budget the product actually meets,
by removing a transitive dependency chain that accounted for 178 MB — 20% of the
image — and by turning the budget into a gate that fails a build rather than a
prose assertion a release can quietly miss.

Follows `devops-infrastructure-updates` (C17), which reduced the image from
1019.2 MB to 826.7 MB and documented that its own `<500 MB` target was not
reachable. Measured after this change: 635,350,015 bytes (605.8 MiB), against an
enforced budget of 650,000,000 bytes.

## ADDED Requirements

### Requirement: Perceptual Hash Without Numerical-Library Dependencies

The cover de-duplication path MUST compute perceptual hashes using only the
standard library and Pillow. It MUST NOT require `scipy` or `numpy`, which are
not otherwise used by the application and together accounted for 168 MB of the
production image. `ImageHash`, which declared both, also declared `PyWavelets`,
for a total of 178 MB removed to serve one function call.

#### Scenario: Computing a perceptual hash for cover de-duplication

- **WHEN** a cover image is hashed to decide whether it duplicates a known image
- **THEN** the hash is computed without importing `scipy` or `numpy`
- **THEN** the result is byte-identical to the hash previously produced by
  `imagehash.phash` for the same input
- **AND** for input whose low-frequency DCT block contains no coefficient exactly
  equal to the median

#### Scenario: Hashing an input with coefficients tied at the median

- **WHEN** a cover image is hashed whose low-frequency DCT block contains two or
  more coefficients exactly equal to the median
- **THEN** the result is computed by exact arithmetic, so a coefficient equal to
  the median is not greater than it and hashes to 0
- **AND** the result is identical across runs and across independent
  implementations of the algorithm, unlike the previous behaviour, which
  depended on the numerical library's floating-point rounding
- **AND** the scope of this divergence is pinned by a test, so that it cannot
  widen without that being noticed

#### Scenario: Comparing against previously stored hashes

- **WHEN** a computed hash is compared against hashes stored in `IQOQO_KNOWN_JUNK_PHASHES`
- **THEN** hashes produced for all ordinary inputs by the previous algorithm
  continue to match
- **THEN** an operator can verify that a stored hash still resolves, by
  recomputing the hash of the image it was taken from
- **THEN** an entry that is not a valid hash is reported and ignored, rather than
  being silently reinterpreted as a different hash

### Requirement: Enforced Container Image Size Gate

The container build MUST fail when the produced image exceeds its declared size
target, and MUST report the per-component breakdown when it does.

#### Scenario: Building the production image within target

- **WHEN** the production backend image is built
- **THEN** its uncompressed size is measured from the built image, not estimated
- **THEN** the build fails if the size exceeds the target
- **THEN** the failure output lists the size of each significant path in the image,
  so the cause is identifiable without rebuilding
- **AND** the largest individual packages are named, so a newly-fat dependency is
  identified rather than merely attributed to `site-packages`

#### Scenario: Target is recorded as achievable

- **WHEN** the size target is changed
- **THEN** the measured size of the current image is recorded alongside it
- **THEN** the target is not left above a size the image cannot reach without a
  documented product decision
- **AND** a budget file that cannot be parsed fails the build rather than being
  read as "no limit"

## MODIFIED Requirements

### Requirement: Multi-stage Docker Build Image Size Budget

The production container image build process MUST employ multi-stage compilation
to isolate build-time compilers and development headers, stripping bytecode and
unused caches. Its size is governed by an enforced budget rather than an asserted
figure: **650,000,000 bytes** of uncompressed image, against a measured
**635,350,015 bytes (605.8 MiB)** on `python:3.14-slim`.

**Changed from C17**, which published `under 500MB` as a requirement while
measuring 826.7 MB. That was a contract the product did not honour, and archiving
it into the main specs would have made the specification actively wrong. The
multi-stage build and its isolation properties are delivered and verified; the
size figure is now a budget that is met, checked on every build, and recorded
next to the measurement that justifies it.

Getting below roughly 605 MiB would require removing a capability rather than
tuning a build. `tesseract-ocr` and the shared libraries it pulls in are about
132 MB, and splitting OCR into a separately-tagged image is a product decision
recorded in `docs/RELEASE_PROCESS.md` rather than an outstanding build task.

#### Scenario: Building the production image

- **WHEN** the production backend image is built using `deploy/Dockerfile`
- **THEN** compiler toolchains and development headers are isolated to the builder stage
- **THEN** the final runtime image excludes build tools, development packages, and unused binaries
- **THEN** the resulting size is checked against the enforced budget, and the build
  fails if it exceeds it

#### Scenario: Reconciling the recorded budget with reality

- **WHEN** this requirement is published
- **THEN** the size figure it states is one the current image satisfies
- **THEN** the measured size is recorded beside it, with the per-dependency
  breakdown that accounts for the difference
- **THEN** any lower budget is tracked as open work in a change, not published as
  a satisfied requirement

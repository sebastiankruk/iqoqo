# infrastructure/container-image-size Specification

## Purpose

Keep the production backend image within a size budget the product actually
meets, and make that budget a gate that fails a build rather than a prose figure
a release can quietly miss.

Delivered by the `container-image-size-target` change, which removed
`ImageHash` — one function call (`imagehash.phash`, in the cover de-duplication
path) that transitively pulled in `scipy` (111 MB), `numpy` (57 MB) and
`PyWavelets` (9 MB), **178 MB or 20% of the image**. Measured result:
**635,350,015 bytes (605.8 MiB)** against an enforced budget of 650,000,000
bytes.

This capability supersedes the `<500 MB` figure that `devops-infrastructure-updates`
(C17) published as a requirement while measuring 826.7 MB. That contract was
never honoured, and the correction has two parts: the dependency that made it
unreachable is gone, and the figure is now enforced by
`scripts/check_image_size.py` on every build rather than asserted in prose.

Getting below roughly 605 MiB would require removing a capability rather than
tuning a build. `tesseract-ocr` and the shared libraries it pulls in are about
132 MB; splitting OCR into a separately-tagged image was considered and declined
as a product decision recorded in `docs/RELEASE_PROCESS.md`, not as outstanding
build work.

## Requirements

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

The one input class where byte-identity with the previous algorithm is not
achievable is exactly the one above, and it is bounded rather than hypothetical:
a coefficient sitting exactly at the median is decided by `imagehash` at a
rounding resolution of roughly 1e-16 relative, so no independent implementation
can reproduce it. Over a 55-image golden corpus, 3000 randomised images and 161
placeholder images, 9 inputs diverged and every one was an exact tie. The effect
of a stale stored hash missing is one placeholder cover displayed where a real
cover was expected — no data loss.

These hashes are persisted in `IQOQO_KNOWN_JUNK_PHASHES`, which is what makes
the equivalence load-bearing rather than cosmetic.

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
budget, and MUST report the per-component breakdown when it does. The budget is
**650,000,000 bytes** of uncompressed image.

#### Scenario: Building the production image within budget

- **WHEN** the production backend image is built
- **THEN** its uncompressed size is measured from the built image, not estimated
- **THEN** the build fails if the size exceeds the budget
- **THEN** the failure output lists the size of each significant path in the image,
  so the cause is identifiable without rebuilding
- **AND** the largest individual packages are named, so a newly-fat dependency is
  identified rather than merely attributed to `site-packages`

#### Scenario: The gate covers published images, not only local builds

- **WHEN** an image is published to a registry by CI
- **THEN** the same budget check is applied to it before it is treated as shippable
- **AND** the budget file is the single source of truth that the build gate, the
  release validation and the release plan all read

#### Scenario: Target is recorded as achievable

- **WHEN** the size budget is changed
- **THEN** the measured size of the current image is recorded alongside it in the
  same file, and both are updated together
- **THEN** the budget is not left above a size the image cannot reach without a
  documented product decision
- **AND** a budget file that cannot be parsed, or that records a measurement
  above its own ceiling, fails the build rather than being read as "no limit"

The headroom between the budget and the measurement is deliberately small (about
2.3%). A gate with generous slack is not a regression detector, and a gate
pointing at an unreachable number is worse than no gate, because it only trains
people to disable it. Raising the budget is permitted; raising it without
updating the recorded measurement is not, which is the failure mode this
requirement exists to prevent.

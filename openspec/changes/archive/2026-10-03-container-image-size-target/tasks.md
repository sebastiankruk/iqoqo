# Container image size target

Deferred from `devops-infrastructure-updates` (C17) §1.1/§7.3, which could not
meet its own `<500 MB` requirement. Scheduled for v0.8.3.

Ordered so the highest-value, lowest-risk work is done and measured first. Task
4 is a decision gate, not an implementation task: everything after it depends on
the answer, and doing the work before asking would mean either shipping an
unwanted feature removal or shipping nothing.

## Outcome

`ImageHash` was one call — `imagehash.phash`, in the cover de-duplication path —
and it declared `scipy` (111 MB), `numpy` (57 MB) and `PyWavelets` (9 MB):
**178 MB**, 20% of the image, for a DCT over a fixed 32×32 grid. It is now
`app/utils/phash.py`, Pillow and a precomputed cosine matrix, bit-identical to
`imagehash` across a 55-image corpus and 3000 randomised images except where the
DCT block has coefficients exactly tied at the median.

Measured image: **879,237,483 → 635,350,015 bytes** against the older `preview`
tag, of which **178 MB** is attributable to this change (the remaining ~66 MB was
already removed by earlier Dockerfile work that had never been rebuilt into that
tag). Budget: **650,000,000 bytes**, enforced on every build.

OCR decision (task 4.1): **tesseract stays in the default image**. Splitting it
out would reach ~540 MB but doubles the surface an operator manages, and the
Oracle Free Tier pressure that motivates the target is about total disk, not
about one image tag. The size budget is therefore set to what is achievable
without a product decision.

## 1. Confirm the dependency attribution

- [x] 1.1 Measure the current image and record the per-path breakdown, confirming `scipy` + `numpy` = 167 MB and that `ImageHash` is their only requirer
- [x] 1.2 Enumerate every `imagehash.*` call site in `app/` and `scripts/`, and confirm `phash` is the only one used
- [x] 1.3 Check whether `IQOQO_KNOWN_JUNK_PHASHES` is populated in any live deployment, since that determines whether the compatibility question in design.md is real or theoretical

## 2. Replace `ImageHash`

- [x] 2.1 Implement `phash` using Pillow and a precomputed DCT cosine matrix, with no numpy or scipy import
- [x] 2.2 Prove bit-equality against `imagehash.phash` over a corpus of real cover images, as a test that runs in CI
- [-] 2.3 ~~If bit-equality fails, version the stored hashes~~ — not needed. Measured over 3114 images (55-image golden corpus + 3000 randomised + 161 placeholders): the only divergences are inputs whose DCT block has coefficients *exactly tied* at the median, where `imagehash`'s answer is decided by scipy's float64 rounding (~1e-16 relative) and is not reproducible by any independent implementation. Maintainer decision (this session): amend the spec to the achievable guarantee rather than version the stored hashes. `KNOWN_DIVERGENCES` in `tests/test_phash.py` pins the scope to one input class so it cannot widen unnoticed; `scripts/phash_cover.py --check` is the operator-facing verification.
- [x] 2.4 Switch `app/utils/images.py` to the new implementation and remove the `ImageHash` dependency from `requirements.txt` and `pyproject.toml` (it was never in `pyproject.toml`)
- [x] 2.5 Verify the rebuilt image drops by ~167 MB and that cover de-duplication still rejects the known-junk set

## 3. Make the target an enforced gate

- [x] 3.1 Add a build-time size check that reads the built image's size and fails the build over the target
- [x] 3.2 On failure, print the per-path `du` breakdown so the cause is identifiable without a rebuild
- [x] 3.3 Set the target to the size actually achieved in task 2.5, and record the measured figure next to it
- [x] 3.4 Cover the gate with a test that feeds it an over-limit size and asserts it fails, so the gate cannot be silently disabled

Beyond the literal task, because a gate that only runs locally does not gate the
published images: `deploy.yml` builds with `push: true` and buildx leaves no local
image behind, so a new `image-size-gate` job in `quality.yml` builds the backend
image on every PR (`load: true`) and runs the same gate.

## 4. Decide the OCR question (maintainer decision, blocks 5)

- [x] 4.1 Decide whether `tesseract-ocr` (~132 MB with its libraries) stays in the default image, moves to a separate `iqoqo-backend-ocr` image, or is dropped
- [x] 4.2 Record the decision and its rationale in the release plan, including the Oracle Free Tier disk impact that motivates the target

## 5. Close the remaining gap (only if task 4.1 requires it)

- [-] 5.1 Not applicable — task 4.1 kept OCR in the default image, so there is no separate `iqoqo-backend-ocr` image to wire up.
- [-] 5.2 Not applicable — OCR was not dropped, so the `pytesseract` call site stays. Verified working in the built image: tesseract 5.5.0 reads cover text.

## 6. Verification

- [x] 6.1 Rebuild the production image and record the final size
- [x] 6.2 Smoke-test the built image: import the app, run cover de-duplication, and run OCR if it is still present
- [x] 6.3 Confirm the release plan and the build gate quote the same size figure

The figure now has one source of truth and three consumers that cannot drift:
`deploy/image-size-budget.txt` holds `MAX_BYTES` and `MEASURED_BYTES`;
`scripts/check_image_size.py` enforces them at build time; and
`scripts/validate_release.py --image-size-only` fails if `docs/RELEASE_PROCESS.md`
quotes anything other than those two numbers (wired into the existing
`validate-release` CI job and exposed as `make validate-release`). Verified by
editing the release plan to a different figure and confirming the check fails.

# Container image size target

Deferred from `devops-infrastructure-updates` (C17) §1.1/§7.3, which could not
meet its own `<500 MB` requirement. Scheduled for v0.8.3.

Ordered so the highest-value, lowest-risk work is done and measured first. Task
4 is a decision gate, not an implementation task: everything after it depends on
the answer, and doing the work before asking would mean either shipping an
unwanted feature removal or shipping nothing.

## 1. Confirm the dependency attribution

- [ ] 1.1 Measure the current image and record the per-path breakdown, confirming `scipy` + `numpy` = 167 MB and that `ImageHash` is their only requirer
- [ ] 1.2 Enumerate every `imagehash.*` call site in `app/` and `scripts/`, and confirm `phash` is the only one used
- [ ] 1.3 Check whether `IQOQO_KNOWN_JUNK_PHASHES` is populated in any live deployment, since that determines whether the compatibility question in design.md is real or theoretical

## 2. Replace `ImageHash`

- [ ] 2.1 Implement `phash` using Pillow and a precomputed DCT cosine matrix, with no numpy or scipy import
- [ ] 2.2 Prove bit-equality against `imagehash.phash` over a corpus of real cover images, as a test that runs in CI
- [ ] 2.3 If bit-equality fails, version the stored hashes (e.g. an `imagehash-v2:` prefix) and match both algorithms during a transition window
- [ ] 2.4 Switch `app/utils/images.py` to the new implementation and remove the `ImageHash` dependency from `requirements.txt` and `pyproject.toml`
- [ ] 2.5 Verify the rebuilt image drops by ~167 MB and that cover de-duplication still rejects the known-junk set

## 3. Make the target an enforced gate

- [ ] 3.1 Add a build-time size check that reads the built image's size and fails the build over the target
- [ ] 3.2 On failure, print the per-path `du` breakdown so the cause is identifiable without a rebuild
- [ ] 3.3 Set the target to the size actually achieved in task 2.5, and record the measured figure next to it
- [ ] 3.4 Cover the gate with a test that feeds it an over-limit size and asserts it fails, so the gate cannot be silently disabled

## 4. Decide the OCR question (maintainer decision, blocks 5)

- [ ] 4.1 Decide whether `tesseract-ocr` (~132 MB with its libraries) stays in the default image, moves to a separate `iqoqo-backend-ocr` image, or is dropped
- [ ] 4.2 Record the decision and its rationale in the release plan, including the Oracle Free Tier disk impact that motivates the target

## 5. Close the remaining gap (only if task 4.1 requires it)

- [ ] 5.1 If OCR moves to a separate image, add it to `docker-compose.yml` and the image build script, and verify the backend still runs when the OCR service is absent
- [ ] 5.2 If OCR is dropped, remove the `pytesseract` call site and document the loss of cover text extraction

## 6. Verification

- [ ] 6.1 Rebuild the production image and record the final size
- [ ] 6.2 Smoke-test the built image: import the app, run cover de-duplication, and run OCR if it is still present
- [ ] 6.3 Confirm `make validate-release` and the release plan quote the same size figure as the build gate

# Design

## Context

C17 set a `<500 MB` target, reached 826.7 MB, and left the requirement
unresolved. This change closes the gap. The design decisions below are ordered by
how much they change the outcome, because the first two together are necessary
and neither alone is sufficient.

## The measured floor

From `docker image inspect` and `du` inside the built image:

```
826.7 MB total
├─ 421 MB  /usr/local/lib/python3.14   (site-packages)
│   ├─ 111 MB  scipy + scipy.libs
│   ├─  57 MB  numpy + numpy.libs
│   ├─  29 MB  botocore
│   └─  ~224 MB  everything else the app imports
├─ 117 MB  /usr/lib/x86_64-linux-gnu
├─  15 MB  /usr/share/tesseract-ocr
├─   6 MB  /usr/src/app
└─ ~148 MB  base image layers (python:3.14-slim)
```

Two facts follow, and they drive everything else:

1. **`ImageHash` costs 167 MB** and is used for one function.
2. **Even at zero, the image is ~660 MB.** The remaining gap to 500 MB is ~160 MB
   and sits in real dependencies, so the target needs a second lever.

## Decision 1: replace `ImageHash` with a stdlib implementation

`imagehash.phash` is a well-defined algorithm: convert to grayscale, resize to
32×32, take the 2D DCT, keep the top-left 8×8 (excluding DC), compare against
its median, and emit the bits as a hex string. The DCT is the only part that
pulls in a numerical library.

### Why a local implementation rather than a different library

Every alternative that provides a compatible `phash` (`imagehash`,
`perceptualhash`, `img2phash`) depends on numpy and usually scipy. Swapping one
for another would not remove the dependency, so the question is not *which
library* but *whether to use one at all*.

The algorithm is ~40 lines and fully specified. Pillow covers the decode,
resize and grayscale steps; the DCT can be computed with a small precomputed
cosine matrix using pure Python, which is fast enough here because the input is
a fixed 32×32.

### Compatibility risk — the one thing to settle first

`phash` values are **persisted**. `_load_known_junk_phashes()` in
`app/utils/images.py` reads hex hashes from the `IQOQO_KNOWN_JUNK_PHASHES`
environment variable and compares them against newly computed ones. If a
replacement changes even one bit — a different resize filter, a different
matrix rounding — every stored hash stops matching, and cover de-duplication
silently degrades to "nothing is a known duplicate".

Mitigation, in order of preference:

1. **Prove bit-equality against the current implementation** over a corpus of
   real covers before shipping. This is a test, and it is task 1.1. If it passes,
   the migration is a no-op from the data's point of view.
2. If it fails, **version the stored hashes** (e.g. an `imagehash-v2:` prefix)
   and treat unprefixed entries as belonging to the old algorithm, comparing
   both during a transition window.

Option 1 is expected to succeed: the algorithm is deterministic, and the only
free parameters are the resize filter and the matrix's numeric precision. Both
can be pinned to match.

## Decision 2: `tesseract-ocr` becomes optional

tesseract plus the shared libraries it pulls in is ~132 MB. It backs
`pytesseract` in the cover-OCR path.

It is a genuine feature, so this is not a silent removal. The options:

| Option | Image | Cost |
| --- | --- | --- |
| Keep in the default image | ~660 MB after Decision 1 | none |
| Separate `iqoqo-backend-ocr` image | ~530 MB default | an extra image to build, pull and run; compose wiring |
| Runtime feature toggle, image unchanged | ~660 MB | none — but no size win |
| Drop OCR | ~530 MB | loses cover text extraction |

**Recommendation: keep tesseract in the default image for 0.8.3 and land
Decision 1 alone**, accepting ~660 MB and amending the target to match what is
actually achievable without a product decision. Splitting OCR into a second
image is a real option but it doubles the surface an operator has to manage,
and the Oracle Free Tier concern that motivates the target is about *disk*, not
about one image tag.

This is the part of the change that genuinely needs the maintainer's decision,
and it is the first task.

## Decision 3: make the target an enforced gate

The original requirement was prose in a spec, which is why it could be unmet for
a whole release without anything failing. Replace it with a build-time check
that:

- reads `docker image inspect .Size` after the build,
- compares against the target, and
- **fails the build**, printing the per-layer `du` breakdown on failure.

The target itself moves to the value the dependency work actually supports
(§ Decision 2), rather than staying at a number nothing satisfies. A gate
pointing at an unachievable number is worse than no gate, because it forces
someone to disable it.

## Risks

| Risk | Mitigation |
| --- | --- |
| Replacement `phash` differs by a bit, de-dup silently stops working | Prove bit-equality in a test before shipping; version stored hashes if not |
| Target amended downward looks like moving the goalposts | The measured breakdown is in the proposal, so the new number is justified by data rather than by effort |
| Dropping or splitting OCR is a product regression | Explicitly out of scope for the first tranche; surfaced as a decision, not a task |
| `tesseract-ocr` is removed by a future `apt-get upgrade` in the base image | The gate catches the size change; the smoke test catches the missing binary |

## Open Questions

1. Is ~660 MB acceptable, or is OCR worth splitting into a second image?
2. Is `IQOQO_KNOWN_JUNK_PHASHES` actually populated in any live deployment? If
   it is not, the compatibility question is theoretical and the migration is
   risk-free.
3. Should the target be expressed against `docker image inspect .Size`
   (uncompressed) or the pulled size? The spec said "uncompressed"; the release
   plan has been quoting both.

# Production container image under 500 MB

## Why

The `devops-infrastructure-updates` change (C17) set a `<500 MB` target for the
production backend image and **did not meet it**. It delivered a genuine
reduction — 1019.2 MB → 826.7 MB, a 19% cut — and then the spec and the build
disagreed about whether that counted as done.

The honest position is that the target was never reachable with the current
dependency set, and the shortfall is structural rather than a missed
optimisation. Measured breakdown of the 826.7 MB image:

| Path | Size | What it is |
| --- | --- | --- |
| `/usr/local/lib/python3.14` | 421 MB | site-packages |
| — `scipy` + `scipy.libs` | 111 MB | ImageHash, transitively |
| — `numpy` + `numpy.libs` | 57 MB | ImageHash, transitively |
| — `botocore` | 29 MB | S3 client (C17) |
| — `grpc`, `cryptography`, `sqlalchemy`, `openai`, `pillow.libs`, … | ~110 MB | application dependencies |
| `/usr/lib/x86_64-linux-gnu` | 117 MB | shared libraries, incl. tesseract's |
| `/usr/share/tesseract-ocr` | 15 MB | OCR engine |
| `/usr/src/app` | 6 MB | application code |
| base image remainder | ~148 MB | `python:3.14-slim` layers |

`scipy` and `numpy` together are **167 MB — 20% of the entire image** — and are
pulled in by exactly one package:

```
$ python -c "import importlib.metadata as md; \
  [print(f\"{d.metadata['Name']} requires {r}\") for d in md.distributions() \
   for r in (d.requires or []) if r.split()[0].lower() in ('scipy','numpy')]"
ImageHash requires numpy
ImageHash requires scipy
```

`ImageHash==4.3.2` is used at `app/utils/images.py` for exactly one thing:
`imagehash.phash(img)` in the cover-deduplication path. Neither `scipy` nor
`numpy` is imported anywhere else in `app/` or `scripts/`, and both are
**commented out** of `requirements.txt`. They arrive transitively and nobody
noticed.

Even deleting both lands at ~660 MB. Getting under 500 MB therefore requires
removing a capability, not tuning a build, which is why this is a decision to be
made deliberately and scheduled rather than folded into an unrelated change.

## What Changes

- **Replace `ImageHash` with a dependency-light perceptual hash.** The only
  operation used is `phash`, which is a DCT over a 32×32 grayscale reduction. A
  pure-Pillow/array implementation removes the `scipy` *and* `numpy` requirement
  without changing the feature. If the comparison must stay bit-compatible with
  previously-stored hashes, that is a compatibility question to settle first —
  see Risks.
- **Publish the target as an enforced, measurable gate** rather than a prose
  assertion, so it can no longer drift: a build-time size check that fails the
  image build over the limit, with the per-layer breakdown printed on failure.
- **Re-examine `tesseract-ocr`.** It and its shared libraries are ~132 MB. It
  backs `pytesseract` cover OCR. Making it a separately-tagged image — or a
  documented optional feature — is the other lever available, and it is a
  product decision, not a build change.
- **Correct the C17 spec delta** so it publishes only what C17 actually
  delivered, rather than archiving a `<500 MB` requirement into the main specs
  that the product does not satisfy.

## Non-Goals

- Changing what covers or OCR *do*. This change is about footprint, not
  behaviour.
- Distroless or otherwise re-platforming the runtime image. It is the largest
  single remaining lever after the dependency work, but it breaks the
  `tesseract-ocr` package install and any runtime debugging, and it deserves its
  own change.

## Impact

- `app/utils/images.py` — the perceptual-hash implementation
- `requirements.txt`, `pyproject.toml` — drop `ImageHash`, and pin nothing new
  if the replacement is stdlib-only
- `deploy/Dockerfile` — image size gate
- `tests/` — a compatibility test against known `phash` values, so the
  replacement is proven equivalent rather than merely different
- Ops: the image is ~330 MB smaller, which matters directly for the Oracle Free
  Tier budget this project targets

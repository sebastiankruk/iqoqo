# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
"""Deterministic image corpus for the pHash parity tests.

Not named ``test_*``, so pytest does not collect it. Kept as a module rather
than binary fixtures so the corpus is reviewable: every entry says what it is
supposed to stress, and a change to the generator shows up in a diff instead of
silently altering a PNG nobody can read.

Every image is generated from a fixed seed, so the corpus is byte-stable across
runs and machines that share a Pillow build.
"""

import random

from PIL import Image, ImageDraw, ImageFilter

CORPUS_SEED = 20260802


def _artwork(seed: int) -> Image.Image:
    """A synthetic 'cover': flat ground, blocks, a circle, stripes."""
    rng = random.Random(seed)
    img = Image.new("RGB", (500, 750), (18, 24, 38))
    draw = ImageDraw.Draw(img)
    for _ in range(24):
        x0, y0 = rng.randrange(500), rng.randrange(750)
        draw.rectangle([x0, y0, x0 + rng.randrange(20, 160), y0 + rng.randrange(20, 160)], fill=tuple(rng.randrange(256) for _ in range(3)))
    draw.ellipse([60, 90, 440, 470], fill=(220, 60, 30), outline=(255, 255, 255), width=6)
    for stripe in range(0, 500, 14):
        draw.line([(stripe, 500), (stripe + 40, 700)], fill=(250, 200, 20), width=3)
    return img


def _photographic(seed: int) -> Image.Image:
    """Blurred noise plus a few coloured blobs: something photo-shaped."""
    rng = random.Random(seed)
    img = Image.new("L", (300, 300))
    img.putdata([rng.randrange(256) for _ in range(300 * 300)])
    img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.4, 3.0))).convert("RGB")
    draw = ImageDraw.Draw(img)
    for _ in range(6):
        cx, cy = rng.randrange(300), rng.randrange(300)
        draw.ellipse([cx, cy, cx + rng.randrange(20, 120), cy + rng.randrange(20, 120)], fill=tuple(rng.randrange(256) for _ in range(3)))
    return img


def _no_cover_plate(background: tuple, foreground: tuple, label: str) -> Image.Image:
    """A provider 'no cover available' plate: flat ground, one line of text."""
    img = Image.new("RGB", (500, 500), background)
    ImageDraw.Draw(img).text((60, 230), label, fill=foreground)
    return img


def build_corpus() -> dict:
    """Return ``{name: image}`` for every case the parity tests hash.

    Names are prefixed by the property under test, so a failure says which
    class of input broke rather than just which index.
    """
    corpus: dict = {}

    # -- Realistic covers: structure everywhere, so no coefficient ties. ------
    for seed in range(4):
        art = _artwork(CORPUS_SEED + seed)
        corpus[f"cover_art_{seed}"] = art
        corpus[f"cover_art_{seed}_rotated"] = art.rotate(11)
        corpus[f"cover_art_{seed}_flipped"] = art.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        corpus[f"cover_art_{seed}_scaled"] = art.resize((1200, 1800))
    for seed in range(4):
        photo = _photographic(CORPUS_SEED + seed)
        corpus[f"cover_photo_{seed}"] = photo
        corpus[f"cover_photo_{seed}_gray"] = photo.convert("L")
        corpus[f"cover_photo_{seed}_palette"] = photo.convert("P", palette=Image.Palette.ADAPTIVE, colors=32)
        corpus[f"cover_photo_{seed}_rotated"] = photo.rotate(23)

    ramp = Image.new("RGB", (256, 256))
    ramp.putdata(
        [
            tuple(int(a + (b - a) * (x / 255)) for a, b in zip((0, 0, 0), (255, 255, 255), strict=True))
            for x in range(256)
            for _ in range(256)
        ]
    )
    corpus["cover_gray_ramp"] = ramp
    corpus["cover_gray_ramp_wide"] = ramp.resize((900, 120))
    corpus["cover_color_ramp"] = ramp.rotate(90).convert("RGB").point(lambda v: (v * 255) // 255)

    # -- Placeholders: the population IQOQO_KNOWN_JUNK_PHASHES exists to reject.
    corpus["placeholder_plate_light"] = _no_cover_plate((238, 238, 238), (120, 120, 120), "No Cover Available")
    corpus["placeholder_plate_dark"] = _no_cover_plate((20, 20, 20), (200, 200, 200), "NO IMAGE")
    corpus["placeholder_plate_branded"] = _no_cover_plate((0, 102, 204), (255, 255, 255), "Not available")
    corpus["placeholder_plate_blurred"] = _no_cover_plate((238, 238, 238), (120, 120, 120), "No Cover Available").filter(
        ImageFilter.GaussianBlur(0.8)
    )
    for level in (0, 1, 17, 128, 254, 255):
        corpus[f"placeholder_flat_{level}"] = Image.new("RGB", (300, 300), (level, level, level))
    corpus["placeholder_flat_hue"] = Image.new("RGB", (300, 300), (37, 200, 90))
    icon = Image.new("RGB", (100, 100), (255, 255, 255))
    ImageDraw.Draw(icon).rectangle([2, 2, 97, 97], outline=(170, 170, 170), width=2)
    corpus["placeholder_icon"] = icon

    # -- Shape edge cases: odd geometry and every mode that survives convert.
    corpus["edge_single_pixel"] = Image.new("RGB", (1, 1), (7, 200, 90))
    corpus["edge_wide_strip"] = Image.new("RGB", (4000, 12), (200, 30, 60))
    corpus["edge_tall_strip"] = Image.new("RGB", (12, 4000), (200, 30, 60))
    corpus["edge_hairline"] = Image.new("RGB", (2000, 3), (90, 90, 90))
    corpus["edge_mode_l"] = Image.new("L", (250, 250), 42)
    corpus["edge_mode_rgba"] = Image.new("RGBA", (250, 250), (200, 30, 30, 128))
    corpus["edge_mode_cmyk"] = Image.new("CMYK", (250, 250), (10, 200, 100, 5))
    corpus["edge_mode_16bit"] = Image.new("I;16", (250, 250), 30000)

    return corpus


def tie_corpus() -> dict:
    """Images whose low-frequency DCT block contains coefficients exactly tied
    at the median.

    These are mathematically symmetric inputs -- a perfect cross, a pure ramp --
    where several coefficients are bit-for-bit equal. ``imagehash`` thresholded
    them with ``> median`` on float64 values that its own FFT had perturbed by
    ~1e-16 relative, so a tied coefficient landed above or below the median
    according to rounding rather than arithmetic. That choice is not
    reproducible by an independent implementation, which is why these are
    pinned to *this* implementation's output instead of to ``imagehash``'s.

    Kept separate from :func:`build_corpus` so the parity test can assert exact
    equality against ``imagehash`` for everything else without exceptions.
    """
    corpus: dict = {}

    cross = Image.new("RGB", (300, 300), (245, 245, 245))
    draw = ImageDraw.Draw(cross)
    draw.line([(0, 150), (300, 150)], fill=(200, 200, 200), width=4)
    draw.line([(150, 0), (150, 300)], fill=(200, 200, 200), width=4)
    corpus["tie_cross"] = cross

    ramp = Image.new("L", (300, 300))
    ramp.putdata([x * 255 // 299 for x in range(300) for _ in range(300)])
    corpus["tie_horizontal_ramp"] = ramp

    two_tone = Image.new("L", (200, 200), 0)
    ImageDraw.Draw(two_tone).rectangle([0, 0, 199, 99], fill=255)
    corpus["tie_two_tone"] = two_tone

    return corpus

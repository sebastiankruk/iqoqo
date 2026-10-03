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
"""Perceptual hashing (pHash) on Pillow alone.

`ImageHash` was used for exactly one call -- ``imagehash.phash(img)`` in the
cover de-duplication path -- and it dragged in ``numpy`` (57 MB) and ``scipy``
(111 MB), together 20% of the production backend image. This module reproduces
that one algorithm without a numerical library.

The algorithm, as ``imagehash.phash(img, hash_size=8, highfreq_factor=4)``
defines it:

1. convert to 8-bit grayscale and resample to 32x32 with Lanczos,
2. take the 2-D type-II DCT of the 32x32 grid,
3. keep the low-frequency 8x8 block in the top-left corner,
4. threshold each of those 64 coefficients against their median,
5. emit the 64 bits, row-major, as 16 lowercase hex characters.

Bit compatibility is the whole point: these hashes are persisted in
``IQOQO_KNOWN_JUNK_PHASHES`` and compared against newly computed ones, so a
one-bit drift would not error -- it would silently stop every stored hash from
matching. Two details make that safe.

*The dropped factor of 2.* ``scipy.fftpack.dct`` is unnormalised, so its type-II
matrix carries a leading 2 (applied once per axis, so 4 in two dimensions).
Every coefficient is scaled by the same positive constant, and a threshold
against the median is invariant under that, so this module omits it. Only the
first ``HASH_SIZE`` rows and columns of the transform are ever needed, because
the discarded high-frequency block cannot influence the low-frequency one --
so only an 8x32 matrix is built rather than a full 32x32.

*The quantised comparison.* Two implementations of the same sum accumulate in
different orders and disagree in the last few float64 bits. That only matters
when a coefficient sits within that noise of the median, which happens for
degenerate inputs: a solid-colour cover makes every non-DC coefficient
mathematically zero, so both implementations return +-1e-13 garbage that
``> 0`` would otherwise resolve by sign. Quantising the block against its own
peak, to nine decimal places, puts the decision at a resolution far coarser
than the noise -- ~1e-13 relative here -- and far finer than any real
distinction between cover images. Genuine ties resolve to "not greater", which
is also what ``imagehash`` does for the median element itself.

``tests/test_phash.py`` pins the output against hashes captured from
``imagehash`` itself, so the equivalence is asserted rather than asserted-and-hoped.
"""

import math

from PIL import Image

HASH_SIZE = 8
"""Side of the retained low-frequency block, in coefficients."""

HIGHFREQ_FACTOR = 4
"""DCT input size per hash coefficient, per side."""

_IMG_SIZE = HASH_SIZE * HIGHFREQ_FACTOR
"""Side of the grayscale grid the DCT runs over (32)."""

_HASH_BITS = HASH_SIZE * HASH_SIZE
"""Coefficients that survive into the hash (64)."""

HASH_HEX_WIDTH = _HASH_BITS // 4
"""Hex characters in a stored pHash (16). The on-disk/env format width."""

_QUANTUM_DECIMALS = 9
"""Decimal places kept when quantising the coefficient block."""

_MEDIAN_LOW = (_HASH_BITS - 1) // 2
_MEDIAN_HIGH = _HASH_BITS // 2


def _dct_rows(count: int, length: int) -> tuple[tuple[float, ...], ...]:
    """Build the leading ``count`` rows of the unnormalised type-II DCT matrix.

    Row ``k`` is ``cos(pi * k * (2n + 1) / (2 * length))`` for ``n`` in
    ``range(length)``, without ``scipy.fftpack``'s leading factor of 2. That
    factor is a positive constant applied to every coefficient and cancels out
    of a comparison against the median, so dropping it changes no bit while
    keeping the arithmetic in a smaller dynamic range.
    """
    return tuple(tuple(math.cos(math.pi * k * (2 * n + 1) / (2 * length)) for n in range(length)) for k in range(count))


_DCT_ROWS = _dct_rows(HASH_SIZE, _IMG_SIZE)


def _low_frequency_block(image: Image.Image) -> list[list[float]]:
    """Return the HASH_SIZE x HASH_SIZE top-left corner of the 2-D DCT.

    The transform is separable, so it runs as two passes over the 32x32 grid:
    rows first, then columns. Both passes truncate to the first ``HASH_SIZE``
    outputs, which is sound because ``D`` mixes only indices within one axis and
    coefficient ``(i, j)`` depends on no index ``>= HASH_SIZE`` on either axis.
    """
    reduced = image.convert("L").resize((_IMG_SIZE, _IMG_SIZE), Image.Resampling.LANCZOS)
    raw = reduced.tobytes()
    grid = [raw[offset : offset + _IMG_SIZE] for offset in range(0, len(raw), _IMG_SIZE)]

    # Pass 1, across rows: keep rows 0..HASH_SIZE-1 of the row-transformed grid.
    transformed: list[list[float]] = []
    for weights in _DCT_ROWS:
        row_out = [0.0] * _IMG_SIZE
        for index, weight in enumerate(weights):
            if not weight:
                continue
            grid_row = grid[index]
            for column in range(_IMG_SIZE):
                row_out[column] += weight * grid_row[column]
        transformed.append(row_out)

    # Pass 2, across columns: keep columns 0..HASH_SIZE-1. That yields the block.
    return [[sum(weight * value for weight, value in zip(weights, row, strict=True)) for weights in _DCT_ROWS] for row in transformed]


def _quantise(block: list[list[float]]) -> list[list[float]]:
    """Rescale the block to its own peak and round, so comparisons are stable."""
    peak = max(abs(value) for row in block for value in row)
    if not peak:
        # A degenerate all-zero block cannot come from a real image, but if it
        # ever did, every coefficient is equal and every bit is 0.
        return [[0.0] * len(row) for row in block]
    return [[round(value / peak, _QUANTUM_DECIMALS) for value in row] for row in block]


def perceptual_hash(image: Image.Image) -> str:
    """Compute the pHash of ``image`` as 16 lowercase hex characters.

    Equivalent to ``str(imagehash.phash(image))``, without importing numpy or
    scipy.
    """
    quantised = _quantise(_low_frequency_block(image))

    ordered = sorted(value for row in quantised for value in row)
    median = (ordered[_MEDIAN_LOW] + ordered[_MEDIAN_HIGH]) / 2

    bits = "".join("1" if value > median else "0" for row in quantised for value in row)
    return f"{int(bits, 2):0{HASH_HEX_WIDTH}x}"


def parse_hash(value: str) -> str:
    """Normalise a stored hex pHash to its canonical form.

    Accepts the :data:`HASH_HEX_WIDTH` hexadecimal characters that
    :func:`perceptual_hash` produces, tolerating surrounding whitespace and any
    letter case.

    Raises:
        ValueError: If ``value`` is not exactly ``HASH_HEX_WIDTH`` hex digits.
            Storing anything else was already broken -- ``imagehash.hex_to_hash``
    inferred the hash shape from the string's own length, so a short value
        silently dropped its high bits and a long one raised a ragged-array
            error. Rejecting both is the honest behaviour, and the only case
            that ever worked is the one kept here.
    """
    text = value.strip().lower()
    if len(text) != HASH_HEX_WIDTH or not all(char in "0123456789abcdef" for char in text):
        raise ValueError(f"expected {HASH_HEX_WIDTH} hex characters, got {len(value.strip())!r}")
    return text

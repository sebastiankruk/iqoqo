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
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
"""ISSN Modulo-11 validation, GS1 977 periodical barcode parsing, and cover date OCR helpers."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

_ISSN_RE = re.compile(r"\b(?:ISSN\s*:?\s*)?(\d{4})[-\s]?(\d{3}[\dXx])\b", re.IGNORECASE)
_INDEKS_RE = re.compile(r"\bINDEKS\s*(?:NR\.?\s*)?:?\s*(\d{5,8})\b", re.IGNORECASE)
_ISSUE_WITH_CUM_RE = re.compile(r"\b(?:NR|NO\.?|ISSUE|ISS\.?|#)\s*\.?\s*(\d+(?:[-/]\d+)?)\s*\(\s*(\d+)\s*\)", re.IGNORECASE)
_LOOSE_ISSUE_WITH_CUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[-/]\d{1,3})?)\s*\(\s*(\d{1,4})\s*\)")
_ISSUE_PLAIN_RE = re.compile(r"\b(?:NR|NO\.?|ISSUE|ISS\.?)\s*\.?\s*(\d+(?:[-/]\d+)?)\b", re.IGNORECASE)
_SLASH_YEAR_RE = re.compile(r"\b(\d{1,3})\s*/\s*((?:19|20)\d{2})\b")
_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
_EAN977_OCR_RE = re.compile(r"9[^\d\n]{0,3}77(?:[^\d\n]{0,3}\d){10}")
_EAN_ADDON_MARKER_RE = re.compile(r"(?<!\d)(0[1-9]|[1-9]\d)\s*>")

_MONTH_NAMES: dict[str, int] = {
    # Polish (nominative + genitive + common abbreviations, ASCII-folded)
    "styczen": 1,
    "stycznia": 1,
    "sty": 1,
    "luty": 2,
    "lutego": 2,
    "lut": 2,
    "marzec": 3,
    "marca": 3,
    "mar": 3,
    "kwiecien": 4,
    "kwietnia": 4,
    "kwi": 4,
    "maj": 5,
    "maja": 5,
    "czerwiec": 6,
    "czerwca": 6,
    "cze": 6,
    "lipiec": 7,
    "lipca": 7,
    "lip": 7,
    "sierpien": 8,
    "sierpnia": 8,
    "sierp": 8,
    "wrzesien": 9,
    "wrzesnia": 9,
    "wrz": 9,
    "pazdziernik": 10,
    "pazdziernika": 10,
    "paz": 10,
    "listopad": 11,
    "listopada": 11,
    "lis": 11,
    "grudzien": 12,
    "grudnia": 12,
    "gru": 12,
    # English
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def _strip_accents(value: str) -> str:
    """Fold Unicode accents/Polish Ł to ASCII for multilingual month matching."""
    folded = value.replace("ł", "l").replace("Ł", "L")
    return "".join(ch for ch in unicodedata.normalize("NFD", folded) if unicodedata.category(ch) != "Mn")


def compute_issn_check_digit(seven_digits: str) -> str:
    """Compute Modulo-11 ISSN check digit ('0'-'9' or 'X') for 7 body digits."""
    if len(seven_digits) != 7 or not seven_digits.isdigit():
        raise ValueError(f"ISSN body must contain exactly 7 digits, got {seven_digits!r}")
    weighted_sum = sum(int(digit) * (8 - idx) for idx, digit in enumerate(seven_digits))
    remainder = weighted_sum % 11
    if remainder == 0:
        return "0"
    check_val = 11 - remainder
    return "X" if check_val == 10 else str(check_val)


def compute_ean13_check_digit(twelve_digits: str) -> str:
    """Compute GS1 EAN-13 check digit for the first 12 digits."""
    if len(twelve_digits) != 12 or not twelve_digits.isdigit():
        raise ValueError(f"EAN-13 body must contain exactly 12 digits, got {twelve_digits!r}")
    total = sum(int(d) * (1 if idx % 2 == 0 else 3) for idx, d in enumerate(twelve_digits))
    return str((10 - (total % 10)) % 10)


def normalize_issn(raw: str | None) -> str | None:
    """Validate and normalize an ISSN string into canonical 'XXXX-XXXX' form."""
    if not raw or not isinstance(raw, str):
        return None
    cleaned = re.sub(r"^\s*issn\s*:?\s*", "", raw.strip(), flags=re.IGNORECASE)
    compact = re.sub(r"[\s-]+", "", cleaned).upper()
    if len(compact) != 8 or not compact[:7].isdigit() or compact[7] not in "0123456789X":
        return None
    if compute_issn_check_digit(compact[:7]) != compact[7]:
        return None
    return f"{compact[:4]}-{compact[4:]}"


def is_valid_issn(raw: str | None) -> bool:
    """Return True if *raw* is a syntactically valid Modulo-11 ISSN."""
    return normalize_issn(raw) is not None


def is_977_periodical_barcode(raw: str | None) -> bool:
    """Return True if *raw* looks like a GS1 977 EAN-13 or EAN-13+add-on serial barcode."""
    if not raw or not isinstance(raw, str):
        return False
    compact = re.sub(r"[\s-]+", "", raw.strip())
    return compact.isdigit() and compact.startswith("977") and len(compact) in (13, 15, 18)


def parse_issn_or_977(raw: str | None) -> dict[str, Any] | None:
    """Parse an ISSN or GS1 977 periodical barcode (13, 15, or 18 digits).

    GS1 977 layout:
      - Digits 0..3: '977'
      - Digits 3..10: first 7 digits of ISSN (check digit reconstructed via Modulo-11)
      - Digits 10..12: 2-digit price/year sequence code (NOT issue number)
      - Digit 12: EAN-13 check digit
      - Optional suffix (digits 13..15 or 13..18): EAN-2 / EAN-5 issue add-on
    """
    if not raw or not isinstance(raw, str):
        return None

    stripped = raw.strip()
    issn_only = normalize_issn(stripped)
    if issn_only is not None:
        return {
            "kind": "issn",
            "issn": issn_only,
            "ean": None,
            "ean_addon": None,
            "full_barcode": None,
            "price_variant": None,
            "addon_issue_hint": None,
        }

    compact = re.sub(r"[\s-]+", "", stripped)
    if not (compact.isdigit() and compact.startswith("977") and len(compact) in (13, 15, 18)):
        return None

    ean13 = compact[:13]
    if compute_ean13_check_digit(ean13[:12]) != ean13[12]:
        return None

    issn_body = ean13[3:10]
    issn_formatted = f"{issn_body[:4]}-{issn_body[4:]}{compute_issn_check_digit(issn_body)}"
    price_variant = ean13[10:12]
    addon = compact[13:] if len(compact) > 13 else None
    addon_issue_hint: int | None = None
    if addon and addon.isdigit():
        parsed_hint = int(addon)
        if parsed_hint > 0:
            addon_issue_hint = parsed_hint

    return {
        "kind": "ean977",
        "issn": issn_formatted,
        "ean": ean13,
        "ean_addon": addon,
        "full_barcode": compact if addon else None,
        "price_variant": price_variant,
        "addon_issue_hint": addon_issue_hint,
    }


def parse_cover_issue_label(text: str | None) -> dict[str, Any]:
    """Extract serial issue number, cumulative number, month, year, ISSN, and Indeks from OCR text."""
    if not text or not isinstance(text, str):
        return {}

    result: dict[str, Any] = {}

    for match in _ISSN_RE.finditer(text):
        cand = normalize_issn(f"{match.group(1)}-{match.group(2)}")
        if cand:
            result["issn"] = cand
            break

    for ean_match in _EAN977_OCR_RE.finditer(text):
        digits = re.sub(r"\D", "", ean_match.group(0))
        if len(digits) == 13:
            parsed_ean = parse_issn_or_977(digits)
            if parsed_ean:
                result.setdefault("issn", parsed_ean["issn"])
                result.setdefault("ean", parsed_ean["ean"])
                break

    addon_match = _EAN_ADDON_MARKER_RE.search(text)
    if addon_match:
        result["ean_addon"] = addon_match.group(1)

    indeks_match = _INDEKS_RE.search(text)
    if indeks_match:
        result["indeks"] = indeks_match.group(1)

    cum_match = _ISSUE_WITH_CUM_RE.search(text) or _LOOSE_ISSUE_WITH_CUM_RE.search(text)
    if cum_match:
        result["issue_number"] = cum_match.group(1)
        result["cumulative_issue_number"] = int(cum_match.group(2))
    else:
        plain_match = _ISSUE_PLAIN_RE.search(text)
        if plain_match:
            result["issue_number"] = plain_match.group(1)
        else:
            slash_match = _SLASH_YEAR_RE.search(text)
            if slash_match:
                result["issue_number"] = slash_match.group(1)
                result["publication_year"] = int(slash_match.group(2))
            elif "ean_addon" in result and 1 <= int(result["ean_addon"]) <= 12:
                result["issue_number"] = str(int(result["ean_addon"]))

    folded_lower = _strip_accents(text).lower()
    tokens = re.findall(r"[a-z]+", folded_lower)
    full_month_keys = {k for k in _MONTH_NAMES if len(k) >= 4 or k in ("maj", "may")}
    for token in tokens:
        if token in full_month_keys:
            result["publication_month"] = _MONTH_NAMES[token]
            break
    if "publication_month" not in result:
        for token in tokens:
            if token in _MONTH_NAMES:
                result["publication_month"] = _MONTH_NAMES[token]
                break

    if "publication_year" not in result:
        year_match = _YEAR_RE.search(text)
        if year_match:
            result["publication_year"] = int(year_match.group(1))

    return result

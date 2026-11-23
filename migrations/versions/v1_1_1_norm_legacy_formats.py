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
"""Normalize legacy generic category format tokens and sync F3 format columns.

Revision ID: v1_1_1_norm_legacy_formats
Revises: v1_1_0_serial_issn_issues
Create Date: 2026-11-22 13:45:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

from app.core.format_normalizer import FormatNormalizer, recover_carrier_from_raw_payload

revision = "v1_1_1_norm_legacy_formats"
down_revision = "v1_1_0_serial_issn_issues"
branch_labels = None
depends_on = None

_BATCH_SIZE = 500
_GENERIC_AUDIO = frozenset({"music", "audio", "sound"})
_GENERIC_VIDEO = frozenset({"movie", "video", "moving image"})
_REPAIRABLE_EXPRESSION_TYPES: dict[str, str] = {
    "dvd": "movie",
    "bluray": "movie",
    "4k_uhd": "movie",
    "vcd": "movie",
    "vhs": "movie",
    "laserdisc": "movie",
    "unknown_video": "movie",
    "book": "text",
    "hardcover": "text",
    "paperback": "text",
}


def _resolve_target_format(
    fmt: str | None,
    fmt_type: str | None,
    meta_fmt: str | None,
    raw_payload: dict[str, Any] | None,
    content_type: str | None,
) -> str | None:
    """Resolve canonical carrier format from raw_payload, generic tokens, or legacy/localized aliases."""
    raw_values = [
        str(val).strip().lower()
        for val in (fmt, fmt_type, meta_fmt)
        if isinstance(val, str) and val.strip()
    ]
    has_missing_column = any(not isinstance(val, str) or not val.strip() for val in (fmt, fmt_type, meta_fmt))

    if not raw_values:
        if not raw_payload:
            return None
        return recover_carrier_from_raw_payload(raw_payload, content_type=content_type)

    has_generic = any(c in _GENERIC_AUDIO or c in _GENERIC_VIDEO for c in raw_values)
    explicit_alias_targets = [
        FormatNormalizer.normalize(c, content_type)
        for c in raw_values
        if c not in _GENERIC_AUDIO and c not in _GENERIC_VIDEO and FormatNormalizer.normalize(c, content_type) != c
    ]
    has_drift = len(set(raw_values)) > 1

    if has_generic:
        recovered = recover_carrier_from_raw_payload(raw_payload, content_type=content_type)
        if recovered:
            return recovered
        if any(c in _GENERIC_AUDIO for c in raw_values):
            return "unknown_audio"
        if any(c in _GENERIC_VIDEO for c in raw_values):
            return "unknown_video"

    # Prefer explicit alias mapping (e.g. format='dvd', format_type='płyta vcd' -> 'vcd',
    # or uniform format/format_type/meta.format == 'płyta dvd' -> 'dvd').
    if explicit_alias_targets:
        return explicit_alias_targets[0]

    if (has_drift or has_missing_column) and raw_values:
        for c in raw_values:
            if c not in _GENERIC_AUDIO and c not in _GENERIC_VIDEO:
                return FormatNormalizer.normalize(c, content_type)
        return raw_values[0]
    return None


def upgrade() -> None:
    """Keyset-batched backfill normalizing legacy/localized format tokens and repairing Expression types."""
    FormatNormalizer.reset()
    conn = op.get_bind()
    is_pg = conn.dialect.name == "postgresql"
    schema_prefix = "catalog." if is_pg else ""

    manif_table = sa.table(
        "manifestations",
        sa.column("id", sa.Integer),
        sa.column("expression_id", sa.Integer),
        sa.column("format", sa.String),
        sa.column("format_type", sa.String),
        sa.column("meta", sa.JSON),
        sa.column("raw_payload", sa.JSON),
        schema="catalog" if is_pg else None,
    )
    expr_table = sa.table(
        "expressions",
        sa.column("id", sa.Integer),
        sa.column("content_type", sa.String),
        schema="catalog" if is_pg else None,
    )

    last_id = 0
    expr_target_types: dict[int, set[str]] = {}
    while True:
        stmt = (
            sa.select(
                manif_table.c.id,
                manif_table.c.expression_id,
                manif_table.c.format,
                manif_table.c.format_type,
                manif_table.c.meta,
                manif_table.c.raw_payload,
                expr_table.c.content_type,
            )
            .select_from(manif_table.outerjoin(expr_table, manif_table.c.expression_id == expr_table.c.id))
            .where(manif_table.c.id > last_id)
            .order_by(manif_table.c.id.asc())
            .limit(_BATCH_SIZE)
        )
        rows = conn.execute(stmt).fetchall()
        if not rows:
            break

        for row_id, expr_id, fmt, fmt_type, meta, raw_payload, content_type in rows:
            last_id = int(row_id)
            meta_dict = dict(meta) if isinstance(meta, dict) else {}
            raw_dict = raw_payload if isinstance(raw_payload, dict) else None
            meta_fmt = meta_dict.get("format") if isinstance(meta_dict.get("format"), str) else None

            target = _resolve_target_format(fmt, fmt_type, meta_fmt, raw_dict, content_type)
            final_fmt = (target or fmt or fmt_type or meta_fmt or "").strip().lower()
            if isinstance(expr_id, int) and final_fmt:
                repaired = _REPAIRABLE_EXPRESSION_TYPES.get(final_fmt)
                if repaired:
                    expr_target_types.setdefault(expr_id, set()).add(repaired)
                else:
                    expr_target_types.setdefault(expr_id, set()).add("__keep__")

            if not target:
                continue

            if fmt == target and fmt_type == target and meta_fmt == target:
                continue

            meta_dict["format"] = target
            if is_pg:
                conn.execute(
                    sa.text(
                        f"UPDATE {schema_prefix}manifestations "
                        "SET format = :target, format_type = :target, "
                        "meta = COALESCE(CAST(meta AS jsonb), '{}'::jsonb) || CAST(:patch AS jsonb) "
                        "WHERE id = :row_id"
                    ),
                    {"target": target, "patch": json.dumps({"format": target}), "row_id": row_id},
                )
            else:
                conn.execute(
                    sa.update(manif_table)
                    .where(manif_table.c.id == row_id)
                    .values(format=target, format_type=target, meta=meta_dict)
                )

    # Repair Expression.content_type when currently audio/music but all manifestations unambiguously belong to movie or text.
    for expr_id, resolved_categories in expr_target_types.items():
        if len(resolved_categories) != 1 or "__keep__" in resolved_categories:
            continue
        new_content_type = next(iter(resolved_categories))
        conn.execute(
            sa.update(expr_table)
            .where(
                expr_table.c.id == expr_id,
                expr_table.c.content_type.in_(("music", "audio")),
            )
            .values(content_type=new_content_type)
        )


def downgrade() -> None:
    """Data normalization migration is intentionally a schema-compatible no-op on downgrade."""
    pass

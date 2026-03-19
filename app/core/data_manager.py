"""
Data Import/Export Manager for iqoqo.

Handles exporting and importing database content in a standardized JSON format.
Supports both full database dumps and selective exports.
"""

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

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from app.db import db
from app.db.models import ITEM_STATUSES, Expression, Item, Manifestation, User, Work


class DataManager:
    """Manages import and export of iqoqo database content."""

    @staticmethod
    def export_all() -> dict[str, Any]:
        """
        Export all data from the database in JSON format.

        Returns:
            Dict containing all works, expressions, manifestations, and items.
        """
        data: dict[str, Any] = {
            "version": "1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "works": [],
            "expressions": [],
            "manifestations": [],
            "items": [],
        }

        # Export works
        for work in Work.query.all():
            data["works"].append(
                {
                    "id": work.id,
                    "title": work.title,
                    "meta": work.meta,
                }
            )

        # Export expressions
        for expr in Expression.query.all():
            data["expressions"].append(
                {
                    "id": expr.id,
                    "work_id": expr.work_id,
                    "content_type": expr.content_type,
                    "language": expr.language,
                    "meta": expr.meta,
                }
            )

        # Export manifestations
        for manif in Manifestation.query.all():
            data["manifestations"].append(
                {
                    "id": manif.id,
                    "expression_id": manif.expression_id,
                    "isbn13": manif.isbn13,
                    "upc": manif.upc,
                    "ean": manif.ean,
                    "publisher": manif.publisher,
                    "publication_date": (manif.publication_date.isoformat() if manif.publication_date else None),
                    "cover_url": manif.cover_url,
                    "meta": manif.meta,
                }
            )

        # Export items
        for item in Item.query.all():
            data["items"].append(
                {
                    "id": item.id,
                    "manifestation_id": item.manifestation_id,
                    "owner_id": str(item.owner_id) if item.owner_id else None,
                    "status": item.status,
                    "condition": item.condition,
                    "added_at": item.added_at.isoformat() if item.added_at else None,
                    "meta": item.meta,
                }
            )

        return data

    @staticmethod
    def export_to_file(filepath: str) -> None:
        """
        Export all data to a JSON file.

        Args:
            filepath: Path to the output JSON file.
        """
        data = DataManager.export_all()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def import_data(data: dict[str, Any], clear_existing: bool = False) -> dict[str, int]:
        """
        Import data from a JSON structure.

        Args:
            data: Dictionary containing works, expressions, manifestations, and items.
            clear_existing: If True, clears all existing data before importing.

        Returns:
            Dictionary with counts of imported records.
        """
        if clear_existing:
            DataManager.clear_all_data()

        # Track ID mappings (old_id -> new_id)
        work_id_map: dict[int, int] = {}
        expr_id_map: dict[int, int] = {}
        manif_id_map: dict[int, int] = {}

        counts = {
            "works": 0,
            "expressions": 0,
            "manifestations": 0,
            "items": 0,
        }

        # Ensure a fallback user exists for imported items lacking valid UUID owners
        default_owner = User.query.first()
        if not default_owner:
            default_owner = User(email="data_importer@iqoqo.local", display_name="Data Importer")
            db.session.add(default_owner)
            db.session.flush()

        # Import works
        for work_data in data.get("works", []):
            old_id = work_data.get("id")
            work = Work(
                title=work_data["title"],
                meta=work_data.get("meta", {}),
            )
            db.session.add(work)
            db.session.flush()  # Get the new ID
            if old_id:
                work_id_map[old_id] = work.id
            counts["works"] += 1

        # Import expressions
        for expr_data in data.get("expressions", []):
            old_id = expr_data.get("id")
            old_work_id = expr_data.get("work_id")
            new_work_id = work_id_map.get(old_work_id, old_work_id)

            expr = Expression(
                work_id=new_work_id,
                content_type=expr_data.get("content_type"),
                language=expr_data.get("language"),
                meta=expr_data.get("meta", {}),
            )
            db.session.add(expr)
            db.session.flush()
            if old_id:
                expr_id_map[old_id] = expr.id
            counts["expressions"] += 1

        # Import manifestations
        for manif_data in data.get("manifestations", []):
            old_id = manif_data.get("id")
            old_expr_id = manif_data.get("expression_id")
            new_expr_id = expr_id_map.get(old_expr_id, old_expr_id)

            pub_date = None
            if manif_data.get("publication_date"):
                pub_date = datetime.fromisoformat(manif_data["publication_date"]).date()

            manif = Manifestation(
                expression_id=new_expr_id,
                isbn13=manif_data.get("isbn13"),
                upc=manif_data.get("upc"),
                ean=manif_data.get("ean"),
                publisher=manif_data.get("publisher"),
                publication_date=pub_date,
                meta=manif_data.get("meta", {}),
            )
            db.session.add(manif)
            db.session.flush()
            if old_id:
                manif_id_map[old_id] = manif.id
            counts["manifestations"] += 1

        # Import items
        for item_data in data.get("items", []):
            old_manif_id = item_data.get("manifestation_id")
            new_manif_id = manif_id_map.get(old_manif_id, old_manif_id)

            added_at = None
            if item_data.get("added_at"):
                added_at = datetime.fromisoformat(item_data["added_at"])

            # Resolve Owner ID (fallback to default if invalid/missing)
            raw_owner_id = item_data.get("owner_id")
            owner_id = default_owner.id
            if raw_owner_id:
                try:
                    owner_id = uuid.UUID(str(raw_owner_id))
                except ValueError:
                    pass

            item = Item(
                manifestation_id=new_manif_id,
                owner_id=owner_id,
                status=item_data.get("status", "available"),
                condition=item_data.get("condition"),
                added_at=added_at,
                meta=item_data.get("meta", {}),
            )
            db.session.add(item)
            counts["items"] += 1

        db.session.commit()
        return counts

    @staticmethod
    def import_from_file(filepath: str, clear_existing: bool = False) -> dict[str, int]:
        """
        Import data from a JSON file.

        Args:
            filepath: Path to the input JSON file.
            clear_existing: If True, clears all existing data before importing.

        Returns:
            Dictionary with counts of imported records.
        """
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return DataManager.import_data(data, clear_existing=clear_existing)

    @staticmethod
    def clear_all_data() -> None:
        """Clear all data from the database. Use with caution!"""
        Item.query.delete()
        Manifestation.query.delete()
        Expression.query.delete()
        Work.query.delete()
        db.session.commit()

    @staticmethod
    def get_stats(owner_id: uuid.UUID | None = None) -> dict[str, int]:
        """
        Get database statistics.

        Args:
            owner_id: Optional ID of the owner to filter their specific collection.

        Returns:
            Dictionary with counts for each FRBR entity type plus UI-friendly
            derived fields (``total_items``, ``lent_items``, ``to_read``) used
            by the React dashboard, and per-status counts keyed as
            ``items_<status>`` for every value in ``ITEM_STATUSES``.
        """
        item_query = Item.query
        if owner_id:
            item_query = item_query.filter_by(owner_id=owner_id)

        total = item_query.count()
        status_counts: dict[str, int] = {s: item_query.filter_by(status=s).count() for s in ITEM_STATUSES}
        return {
            # FRBR entity counts
            "works": Work.query.count(),
            "expressions": Expression.query.count(),
            "manifestations": Manifestation.query.count(),
            "items": total,
            # UI-friendly aliases expected by the React dashboard
            "total_items": total,
            "lent_items": status_counts["lent"],
            "to_read": status_counts["wish_list"],
            # Per-status counts (items_available, items_lent, …)
            **{f"items_{s}": count for s, count in status_counts.items()},
        }

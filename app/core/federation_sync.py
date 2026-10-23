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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Provenance-aware ActivityPub metadata reconciliation and trust-gated sync."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import bleach
from sqlalchemy import or_, select
from sqlalchemy.orm.attributes import flag_modified

from app.core import frbr_service
from app.db import db
from app.db.core import EntityAuditLog, Expression, Manifestation, Work
from app.db.federation import FederationInstance, TrustLevel

logger = logging.getLogger(__name__)


def clean_isbn(raw_isbn: str | None) -> str:
    """Normalize ISBN by stripping hyphens and spaces."""
    if not raw_isbn:
        return ""
    return str(raw_isbn).replace("-", "").replace(" ", "").strip()


def resolve_local_manifestation(remote_data: dict[str, Any]) -> Manifestation | None:
    """Locate matching local Manifestation by canonical identifiers or URI.

    Args:
        remote_data: Remote metadata payload or ActivityStreams object.

    Returns:
        Manifestation instance if found, None otherwise.
    """
    raw_isbn = remote_data.get("isbn13") or remote_data.get("isbn")
    clean_val = clean_isbn(raw_isbn)
    if clean_val:
        stmt = select(Manifestation).where(Manifestation.isbn13 == clean_val)
        manif = db.session.execute(stmt).scalars().first()
        if manif:
            return manif

    for id_field in ("upc", "ean"):
        val = remote_data.get(id_field)
        if val:
            stmt = select(Manifestation).where(getattr(Manifestation, id_field) == str(val).strip())
            manif = db.session.execute(stmt).scalars().first()
            if manif:
                return manif

    # MusicBrainz identifier matching (mbid)
    raw_mbid = remote_data.get("mbid") or remote_data.get("musicbrainz_id") or remote_data.get("musicbrainz_release_id")
    if raw_mbid:
        clean_mbid = str(raw_mbid).strip()
        if clean_mbid:
            # 1. Match Manifestation.meta
            mbid_stmt = select(Manifestation).where(
                or_(
                    Manifestation.meta["mbid"].as_string() == clean_mbid,
                    Manifestation.meta["musicbrainz_id"].as_string() == clean_mbid,
                    Manifestation.meta["musicbrainz_release_id"].as_string() == clean_mbid,
                )
            )
            manif = db.session.execute(mbid_stmt).scalars().first()
            if manif:
                return manif

            # 2. Match parent Work.meta
            work_mbid_stmt = (
                select(Manifestation)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .join(Work, Expression.work_id == Work.id)
                .where(
                    or_(
                        Work.meta["mbid"].as_string() == clean_mbid,
                        Work.meta["musicbrainz_id"].as_string() == clean_mbid,
                    )
                )
            )
            manif = db.session.execute(work_mbid_stmt).scalars().first()
            if manif:
                return manif

    # BoardGameGeek identifier matching (bgg_id)
    raw_bgg = remote_data.get("bgg_id") or remote_data.get("boardgamegeek_id")
    if raw_bgg:
        clean_bgg = str(raw_bgg).strip()
        if clean_bgg:
            # 1. Match Manifestation.meta
            bgg_stmt = select(Manifestation).where(
                or_(
                    Manifestation.meta["bgg_id"].as_string() == clean_bgg,
                    Manifestation.meta["boardgamegeek_id"].as_string() == clean_bgg,
                )
            )
            manif = db.session.execute(bgg_stmt).scalars().first()
            if manif:
                return manif

            # 2. Match parent Work.meta
            work_bgg_stmt = (
                select(Manifestation)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .join(Work, Expression.work_id == Work.id)
                .where(
                    or_(
                        Work.meta["bgg_id"].as_string() == clean_bgg,
                        Work.meta["boardgamegeek_id"].as_string() == clean_bgg,
                    )
                )
            )
            manif = db.session.execute(work_bgg_stmt).scalars().first()
            if manif:
                return manif

    remote_id = remote_data.get("id")
    if remote_id and isinstance(remote_id, str):
        # Check if local ID is embedded in remote URI path: e.g. /manifestation/<id>
        # Only permit matching local IDs if the remote_id hostname matches our local instance
        from app.core.iri import get_federation_base_url, get_lod_base_url

        parsed = urlparse(remote_id)
        local_domains = {
            urlparse(get_federation_base_url()).netloc.lower(),
            urlparse(get_lod_base_url()).netloc.lower(),
        }
        if parsed.netloc and parsed.netloc.lower() in local_domains:
            parts = [p for p in parsed.path.split("/") if p]
            if "manifestation" in parts:
                idx = parts.index("manifestation")
                if idx + 1 < len(parts) and parts[idx + 1].isdigit():
                    manif_id = int(parts[idx + 1])
                    return db.session.get(Manifestation, manif_id)

    return None


def sync_manifestation(
    manifestation: Manifestation,
    remote_data: dict[str, Any],
    domain: str,
    trust_level: str,
    actor_uri: str | None = None,
) -> dict[str, Any]:
    """Reconcile remote manifestation metadata according to instance trust level.

    - `blocked` or `untrusted`: ignored and discarded immediately.
    - `trusted`: auto-fills empty local fields, preserving non-empty local data,
      and records field-level provenance (`meta['_provenance']`) and `prov:wasDerivedFrom`.
    - `pending`: routes proposed changes into the Custodian Provider Merge queue
      via `raw_payload` and `EntityAuditLog(change_type='federation_merge_proposed')`.

    Args:
        manifestation: Local Manifestation entity to update.
        remote_data: Dictionary containing incoming metadata fields.
        domain: Domain of the remote federation peer.
        trust_level: TrustLevel string ('trusted', 'pending', 'untrusted', 'blocked').
        actor_uri: Optional URI of the sending remote actor.

    Returns:
        Summary dict of reconciliation result.
    """
    if trust_level in (TrustLevel.BLOCKED, TrustLevel.UNTRUSTED):
        logger.info("Dropping metadata sync from %s peer %s", trust_level, domain)
        return {"status": "ignored", "reason": f"trust_level_{trust_level}"}

    provenance_key = f"federation:{domain}"

    if trust_level == TrustLevel.PENDING:
        # Check if already queued with identical payload to consolidate duplicate storage
        raw = dict(manifestation.raw_payload or {})
        existing = raw.get(provenance_key)
        if existing and existing == remote_data:
            return {"status": "already_queued", "provider": provenance_key}

        # Route into Custodian Provider Merge Queue
        raw[provenance_key] = remote_data
        manifestation.raw_payload = raw

        meta = dict(manifestation.meta or {})
        raw_meta = dict(meta.get("raw_payload") or {})
        raw_meta[provenance_key] = remote_data
        meta["raw_payload"] = raw_meta
        manifestation.meta = meta

        flag_modified(manifestation, "meta")
        flag_modified(manifestation, "raw_payload")

        audit = EntityAuditLog(
            entity_type="manifestation",
            entity_id=manifestation.id,
            actor_id=None,
            change_type="federation_merge_proposed",
            diff={"provider": provenance_key, "proposed": remote_data, "actor_uri": actor_uri},
        )
        db.session.add(audit)
        db.session.commit()
        return {"status": "queued_for_review", "provider": provenance_key}

    # TrustLevel.TRUSTED: Auto-fill empty fields only
    updated_fields: dict[str, Any] = {}
    manif_meta = dict(manifestation.meta or {})
    manif_prov = dict(manif_meta.get("_provenance") or {})

    # 1. page_count (in meta)
    remote_page_count = remote_data.get("page_count") or remote_data.get("pageCount") or remote_data.get("numberOfPages")
    if remote_page_count is not None and not manif_meta.get("page_count"):
        try:
            clean_count = int(remote_page_count)
            manif_meta["page_count"] = clean_count
        except (ValueError, TypeError):
            manif_meta["page_count"] = bleach.clean(str(remote_page_count), tags=[], strip=True)[:50]
        manif_prov["page_count"] = provenance_key
        updated_fields["page_count"] = manif_meta["page_count"]

    # 2. publisher (column)
    remote_pub = remote_data.get("publisher")
    if remote_pub and not manifestation.publisher:
        clean_pub = bleach.clean(str(remote_pub), tags=[], strip=True).strip()[:255]
        if clean_pub:
            manifestation.publisher = clean_pub
            manif_prov["publisher"] = provenance_key
            updated_fields["publisher"] = manifestation.publisher

    # 3. publication_date (column)
    remote_date = remote_data.get("publication_date") or remote_data.get("published")
    if remote_date and not manifestation.publication_date:
        try:
            if isinstance(remote_date, str) and len(remote_date) >= 4:
                parsed_dt = datetime.fromisoformat(remote_date.replace("Z", "+00:00")).date()
                manifestation.publication_date = parsed_dt
                manif_prov["publication_date"] = provenance_key
                updated_fields["publication_date"] = str(manifestation.publication_date)
        except (ValueError, TypeError):
            pass

    # 4. cover_url (column)
    remote_cover = remote_data.get("cover_url") or remote_data.get("cover") or remote_data.get("image") or remote_data.get("icon")
    if remote_cover and not manifestation.cover_url:
        cover_str = str(remote_cover).strip()
        parsed_cover = urlparse(cover_str)
        if parsed_cover.scheme in ("https", "http"):
            manifestation.cover_url = cover_str[:255]
            manif_prov["cover_url"] = provenance_key
            updated_fields["cover_url"] = manifestation.cover_url

    # 5. format (column)
    remote_format = remote_data.get("format") or remote_data.get("format_type")
    if remote_format and not manifestation.format:
        clean_format = bleach.clean(str(remote_format), tags=[], strip=True).strip()[:50]
        if clean_format:
            manifestation.format = clean_format
            manif_prov["format"] = provenance_key
            updated_fields["format"] = manifestation.format

    # 6. expression.language (Expression tier)
    expr = manifestation.expression
    remote_lang = remote_data.get("language") or remote_data.get("inLanguage")
    if remote_lang and expr and not expr.language:
        clean_lang = bleach.clean(str(remote_lang), tags=[], strip=True).strip()[:10]
        if clean_lang:
            expr.language = clean_lang
            expr_meta = dict(expr.meta or {})
            expr_prov = dict(expr_meta.get("_provenance") or {})
            expr_prov["language"] = provenance_key
            expr_meta["_provenance"] = expr_prov

            expr_derived = list(expr_meta.get("prov:wasDerivedFrom") or [])
            if provenance_key not in expr_derived:
                expr_derived.append(provenance_key)
            expr_meta["prov:wasDerivedFrom"] = expr_derived
            expr.meta = expr_meta
            flag_modified(expr, "meta")
            updated_fields["expression.language"] = expr.language

    # 7. work.description & original_release_year (Work tier)
    work = expr.work if expr else None
    if work:
        remote_desc = remote_data.get("description") or remote_data.get("summary")
        work_meta = dict(work.meta or {})
        work_prov = dict(work_meta.get("_provenance") or {})
        work_modified = False

        if remote_desc and not work.description:
            clean_desc = bleach.clean(str(remote_desc), tags=[], strip=True).strip()
            if clean_desc:
                work.description = clean_desc
                work_prov["description"] = provenance_key
                updated_fields["work.description"] = work.description
                work_modified = True

        remote_year = remote_data.get("original_release_year") or remote_data.get("year")
        if remote_year is not None and not work.original_release_year:
            try:
                work.original_release_year = int(remote_year)
                work_prov["original_release_year"] = provenance_key
                updated_fields["work.original_release_year"] = work.original_release_year
                work_modified = True
            except (ValueError, TypeError):
                pass

        if work_modified:
            work_meta["_provenance"] = work_prov
            work_derived = list(work_meta.get("prov:wasDerivedFrom") or [])
            if provenance_key not in work_derived:
                work_derived.append(provenance_key)
            work_meta["prov:wasDerivedFrom"] = work_derived
            work.meta = work_meta
            flag_modified(work, "meta")

    if not updated_fields:
        return {"status": "no_changes"}

    # Update provenance metadata and W3C PROV wasDerivedFrom
    manif_meta["_provenance"] = manif_prov
    derived_from = list(manif_meta.get("prov:wasDerivedFrom") or [])
    if provenance_key not in derived_from:
        derived_from.append(provenance_key)
    manif_meta["prov:wasDerivedFrom"] = derived_from
    manifestation.meta = manif_meta
    flag_modified(manifestation, "meta")

    audit = EntityAuditLog(
        entity_type="manifestation",
        entity_id=manifestation.id,
        actor_id=None,
        change_type="federation_sync_auto_fill",
        diff={"provider": provenance_key, "fields": updated_fields},
    )
    db.session.add(audit)
    db.session.commit()

    return {"status": "merged", "updated_fields": updated_fields}


def reconcile_activity(activity: dict[str, Any]) -> dict[str, Any]:
    """Parse ActivityPub activity and apply trust-gated metadata sync.

    Args:
        activity: Full ActivityStreams activity JSON payload.

    Returns:
        Summary dict of synchronization result.
    """
    actor_uri = activity.get("actor", "")
    domain = urlparse(actor_uri).hostname or ""
    if not domain:
        return {"status": "ignored", "reason": "missing_actor_domain"}

    stmt = select(FederationInstance).where(FederationInstance.domain == domain)
    instance = db.session.execute(stmt).scalars().first()
    trust_level = instance.trust_level if instance else TrustLevel.UNTRUSTED

    obj = activity.get("object", {})
    if isinstance(obj, str):
        return {"status": "ignored", "reason": "object_uri_reference"}

    manif = resolve_local_manifestation(obj)
    if not manif:
        return {"status": "ignored", "reason": "local_entity_not_found"}

    return sync_manifestation(manif, obj, domain=domain, trust_level=trust_level, actor_uri=actor_uri)


def link_manifestation_to_expression(
    manifestation_id: int,
    expression_id: int,
    user_id: Any = None,
) -> Manifestation:
    """Link a Manifestation to a local Expression via canonical FRBR re-parenting.

    Args:
        manifestation_id: Primary key of Manifestation.
        expression_id: Primary key of destination Expression.
        user_id: Optional ID of acting user / custodian.

    Returns:
        Updated Manifestation instance.
    """
    result = frbr_service.reassign_frbr_parent(
        entity_type="manifestation",
        entity_id=manifestation_id,
        new_parent_id=expression_id,
        user_id=user_id,
    )
    return result


def link_expression_to_work(
    expression_id: int,
    work_id: int,
    user_id: Any = None,
) -> Expression:
    """Link an Expression to a local Work via canonical FRBR re-parenting.

    Args:
        expression_id: Primary key of Expression.
        work_id: Primary key of destination Work.
        user_id: Optional ID of acting user / custodian.

    Returns:
        Updated Expression instance.
    """
    result = frbr_service.reassign_frbr_parent(
        entity_type="expression",
        entity_id=expression_id,
        new_parent_id=work_id,
        user_id=user_id,
    )
    return result

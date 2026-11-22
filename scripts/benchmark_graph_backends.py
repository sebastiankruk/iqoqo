#!/usr/bin/env python3
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
"""Benchmark harness comparing SQL vs. RDF/SPARQL backends for C140 graph explorer."""

from __future__ import annotations

import argparse
import json
import os
import resource
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from sqlalchemy import event, func, select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return round(ordered[idx], 2)


def _rss_mb() -> float:
    """Return current process max RSS in MiB (ru_maxrss is KiB on Linux)."""
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 2)


def _collect_dataset_counts(db: Any) -> dict[str, int]:
    from app.db.contributions import Contributor, WorkContribution, WorkPart, WorkSeriesMembership
    from app.db.core import Expression, Item, Manifestation, SemanticLink, Work, WorkExpansionLink
    from app.db.federation import FederationConsent
    from app.db.games import ContainerAggregation

    models: list[tuple[str, Any]] = [
        ("works", Work),
        ("expressions", Expression),
        ("manifestations", Manifestation),
        ("items", Item),
        ("contributors", Contributor),
        ("work_contributions", WorkContribution),
        ("work_series_memberships", WorkSeriesMembership),
        ("work_parts", WorkPart),
        ("work_expansion_links", WorkExpansionLink),
        ("container_aggregations", ContainerAggregation),
        ("semantic_links", SemanticLink),
        ("federation_consents", FederationConsent),
    ]
    counts: dict[str, int] = {}
    for name, model in models:
        counts[name] = int(db.session.execute(select(func.count()).select_from(model)).scalar_one())  # pylint: disable=not-callable
    return counts


def _measure_sql_queries(engine: Any, fn: Any) -> tuple[Any, int, float]:
    sql_count = 0

    def _counter(*_args: Any, **_kwargs: Any) -> None:
        nonlocal sql_count
        sql_count += 1

    event.listen(engine, "before_cursor_execute", _counter)
    t0 = time.perf_counter()
    try:
        res = fn()
    finally:
        event.remove(engine, "before_cursor_execute", _counter)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return res, sql_count, elapsed_ms


def _run_option_a_sql_neighborhood(work_id: int, depth: int, max_nodes: int = 150) -> dict[str, Any]:
    from app.core.graph_service import GraphService

    return GraphService.build_neighborhood("work", work_id, depth=min(depth, 2), max_nodes=max_nodes)


def _run_option_b_sparql_snapshot(work_id: int, depth: int) -> dict[str, Any]:
    from app.core.sparql_service import build_graph

    g = build_graph()
    nt_data = g.serialize(format="nt")
    nt_bytes = len(nt_data.encode("utf-8")) if isinstance(nt_data, str) else len(nt_data)
    hops = max(1, min(depth, 4))
    triples_clauses = []
    prev_var = "?s"
    for idx in range(1, hops + 1):
        next_var = "?o" if idx == hops else f"?n{idx}"
        triples_clauses.append(f"{prev_var} ?p{idx} {next_var} .")
        prev_var = next_var
    where_body = " ".join(triples_clauses)
    q = f"""
    SELECT DISTINCT ?s ?o WHERE {{
      {where_body}
      FILTER(CONTAINS(STR(?s), "/work/{work_id}"))
    }} LIMIT 150
    """
    rows = list(g.query(q))
    return {"triple_count": len(g), "snapshot_bytes": nt_bytes, "rows": len(rows)}


def _seed_fixture(db: Any, *, scale: bool = False) -> None:
    from app.db.auth import User
    from app.db.contributions import Contributor, WorkContribution, WorkPart, WorkSeriesMembership
    from app.db.core import Expression, Item, Manifestation, SemanticLink, Work

    db.create_all()
    u = User(email="bench@iqoqo.local", display_name="Bench", is_active=True)
    u.set_password("BenchPass123!")
    db.session.add(u)
    db.session.flush()

    n_works = 400 if scale else 1
    works: list[Work] = []
    for i in range(n_works):
        w = Work(title=f"Benchmark Work {i}", work_kind="series" if (scale and i < 10) else "book")
        db.session.add(w)
        works.append(w)
    db.session.flush()

    contribs: list[Contributor] = []
    if scale:
        for c_idx in range(40):
            c = Contributor(name=f"Author {c_idx}", type="person")
            db.session.add(c)
            contribs.append(c)
        db.session.flush()

    for i, w in enumerate(works):
        e = Expression(work_id=w.id, content_type="text", language="en")
        db.session.add(e)
        db.session.flush()
        for m_idx in range(2 if scale else 1):
            m = Manifestation(expression_id=e.id, format="hardcover", meta={"title": f"Edition {i}-{m_idx}"})
            db.session.add(m)
            db.session.flush()
            db.session.add(Item(manifestation_id=m.id, owner_id=u.id, visibility="public", is_hidden=False))
        if scale:
            db.session.add(WorkContribution(work_id=w.id, contributor_id=contribs[i % len(contribs)].id, role="author"))
            if i >= 10 and i < 100:
                db.session.add(WorkSeriesMembership(series_work_id=works[i % 10].id, work_id=w.id, sequence=i))
            if i >= 10 and i < 50:
                db.session.add(WorkPart(container_work_id=works[0].id, part_work_id=w.id, sequence=i))
            if i < 30:
                db.session.add(
                    SemanticLink(
                        entity_type="work",
                        entity_id=w.id,
                        authority="dbpedia",
                        external_uri=f"http://dbpedia.org/resource/Work_{i}",
                        status="accepted",
                    )
                )
    db.session.commit()


def run_benchmark(*, dry_run: bool = False, scale_seed: bool = False, concurrency: int = 1, iterations: int = 5) -> dict[str, Any]:
    """Execute Option A vs Option B benchmark against fixture or live PostgreSQL."""
    if dry_run or scale_seed:
        os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ.setdefault("FLASK_ENV", "testing")

    from app import create_app
    from app.db import db
    from app.db.core import Work

    app = create_app()
    report: dict[str, Any] = {
        "dry_run": dry_run,
        "scale_seed": scale_seed,
        "concurrency": concurrency,
        "iterations": iterations,
        "dataset_counts": {},
        "cells": [],
        "rss_before_mb": _rss_mb(),
        "rss_after_mb": 0.0,
    }

    with app.app_context():
        if dry_run or scale_seed:
            _seed_fixture(db, scale=scale_seed)

        report["dataset_counts"] = _collect_dataset_counts(db)
        anchor_work = db.session.execute(select(Work.id).order_by(Work.id.asc()).limit(1)).scalar_one_or_none()
        if anchor_work is None:
            raise RuntimeError("No Work rows found in target database for benchmark.")

        for depth in (1, 2, 3, 4):
            a_latencies: list[float] = []
            a_sql_counts: list[int] = []
            a_nodes = 0
            a_edges = 0
            for _ in range(iterations):
                res, sq_cnt, ms = _measure_sql_queries(db.engine, lambda d=depth: _run_option_a_sql_neighborhood(anchor_work, d))
                a_latencies.append(ms)
                a_sql_counts.append(sq_cnt)
                a_nodes = res["meta"]["node_count"]
                a_edges = res["meta"]["edge_count"]

            b_latencies: list[float] = []
            b_triples = 0
            b_bytes = 0
            b_error: str | None = None
            try:
                for _ in range(min(iterations, 3)):
                    t0 = time.perf_counter()
                    bres = _run_option_b_sparql_snapshot(anchor_work, depth)
                    b_latencies.append((time.perf_counter() - t0) * 1000.0)
                    b_triples = bres["triple_count"]
                    b_bytes = bres["snapshot_bytes"]
            except Exception as exc:  # noqa: BLE001
                b_error = f"{type(exc).__name__}: {exc}"

            report["cells"].append(
                {
                    "depth": depth,
                    "option_a_sql": {
                        "p50_ms": _percentile(a_latencies, 50),
                        "p95_ms": _percentile(a_latencies, 95),
                        "max_ms": round(max(a_latencies), 2) if a_latencies else 0.0,
                        "avg_sql_queries": round(statistics.mean(a_sql_counts), 1) if a_sql_counts else 0.0,
                        "node_count": a_nodes,
                        "edge_count": a_edges,
                    },
                    "option_b_sparql": {
                        "p50_ms": _percentile(b_latencies, 50),
                        "p95_ms": _percentile(b_latencies, 95),
                        "max_ms": round(max(b_latencies), 2) if b_latencies else 0.0,
                        "triple_count": b_triples,
                        "snapshot_bytes": b_bytes,
                        "error": b_error,
                    },
                }
            )

        if concurrency > 1:

            def _worker(_idx: int) -> float:
                with app.app_context():
                    t0 = time.perf_counter()
                    _run_option_a_sql_neighborhood(anchor_work, 2)
                    return (time.perf_counter() - t0) * 1000.0

            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                conc_lat = list(pool.map(_worker, range(concurrency * 2)))
            report["concurrent_sql_p95_ms"] = _percentile(conc_lat, 95)

    report["rss_after_mb"] = _rss_mb()
    report["rss_delta_mb"] = round(report["rss_after_mb"] - report["rss_before_mb"], 2)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Run against in-memory SQLite fixture.")
    parser.add_argument("--scale-seed", action="store_true", help="Seed 400 works / 800 items in-memory benchmark.")
    parser.add_argument("--concurrency", type=int, default=1, help="Concurrent worker count.")
    parser.add_argument("--iterations", type=int, default=5, help="Warm iterations per depth.")
    args = parser.parse_args(argv)
    result = run_benchmark(
        dry_run=args.dry_run,
        scale_seed=args.scale_seed,
        concurrency=args.concurrency,
        iterations=args.iterations,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

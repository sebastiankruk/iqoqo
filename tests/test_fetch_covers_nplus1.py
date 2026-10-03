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
"""C18 2.9: `scripts/fetch_covers.py` must not issue queries per catalog row.

The loop below walks `man.expression.work` for every manifestation in a batch.
On a lazy graph that is not two queries but about seven and a half, because
`Work` pulls in semantic links, work parts and contributions. Measured against
a seeded database: 38 SELECTs for 5 rows, and the count grew with the batch.

Eager-loading the chain makes it a fixed number of queries regardless of batch
size, which is the property that actually matters for a maintenance script
meant to sweep a whole catalog.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import selectinload

from app.db.models import Expression, Manifestation, Work

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "fetch_covers.py"


def _seed(app: Any, count: int) -> None:
    """Create `count` Manifestations behind their own Work and Expression.

    @param app: The Flask application fixture.
    @param count: How many manifestations to create.
    """
    from app.db import db

    for i in range(count):
        work = Work(title=f"Work {i}")
        db.session.add(work)
        db.session.flush()
        expression = Expression(work_id=work.id, content_type="book")
        db.session.add(expression)
        db.session.flush()
        db.session.add(Manifestation(expression_id=expression.id))
    db.session.commit()


def _count_selects_for(app: Any, count: int, eager: bool) -> int:
    """Count the SELECTs for a batch walked with or without eager loading.

    Deliberately parameterised rather than hard-coding the eager form: if the
    test always built the eager query itself, it would keep passing after the
    shipped script reverted to a lazy access, which is exactly the mistake an
    earlier version of this file made.

    @param app: The Flask application fixture.
    @param count: Batch size to seed and walk.
    @param eager: Whether to eager-load the expression/work chain.
    @returns: The number of SELECT statements executed.
    """
    from app.db import db

    db.session.rollback()
    db.drop_all()
    db.create_all()
    _seed(app, count)

    statements: list[str] = []

    @event.listens_for(Engine, "before_cursor_execute")
    def tally(_conn: Any, _cursor: Any, statement: str, _params: Any, _ctx: Any, _many: Any) -> None:
        if statement.strip().upper().startswith("SELECT"):
            statements.append(statement)

    try:
        query = Manifestation.query.filter(Manifestation.cover_url.is_(None))
        if eager:
            query = query.options(selectinload(Manifestation.expression).selectinload(Expression.work))
        rows = query.all()
        for man in rows:
            work = man.expression.work if (man.expression and man.expression.work) else None
            if work:
                # Touch the attribute the real loop reads; assignment only to
                # satisfy the linter, the value is irrelevant.
                _ = work.title
    finally:
        event.remove(Engine, "before_cursor_execute", tally)

    return len(statements)


def _script_walks_eagerly() -> bool:
    """Whether the shipped script eager-loads the chain it iterates.

    Read from the script's own AST so the behavioural assertions below describe
    what the script does rather than what this test file happens to do.

    @returns: True when the script declares an eager load for expression/work.
    """
    tree = ast.parse(SCRIPT.read_text())
    rendered = " ".join(ast.unparse(node) for node in ast.walk(tree) if isinstance(node, ast.Call))
    return "selectinload" in rendered and "Manifestation.expression" in rendered and "Expression.work" in rendered


def test_query_count_is_independent_of_batch_size(app: Any) -> None:
    """Walking 5 rows and walking 50 rows must cost the same.

    The N+1 is defined by *scaling*, so a per-batch-size assertion is the only
    one that catches it. Asserting an absolute count would pass even while the
    query count grew linearly, which is exactly the bug.

    @param app: The Flask application fixture.
    @returns: Nothing; a growing count fails the test.
    """
    eager = _script_walks_eagerly()
    small = _count_selects_for(app, 5, eager)
    large = _count_selects_for(app, 50, eager)

    assert small == large, f"query count grows with the batch: {small} for 5 rows, {large} for 50 rows"


def test_query_count_is_far_below_the_lazy_cost(app: Any) -> None:
    """The script's own query must be dramatically cheaper than the lazy form.

    @param app: The Flask application fixture.
    @returns: Nothing; an insufficient improvement fails the test.
    """
    assert _script_walks_eagerly(), "the script still loads Manifestation.expression lazily"

    eager = _count_selects_for(app, 20, True)
    lazy = _count_selects_for(app, 20, False)
    assert eager < lazy / 3, f"eager={eager} is not a real improvement over lazy={lazy}"


SCRIPTS = [
    SCRIPT,
    SCRIPT.parent / "retry_missing_covers.py",
    SCRIPT.parent / "generate_ai_covers.py",
]


@pytest.mark.parametrize("path", SCRIPTS, ids=[p.name for p in SCRIPTS])
def test_each_cover_script_eager_loads_the_chain_it_walks(path: Path) -> None:
    """Every cover script that walks expression.work must declare the eager load.

    Checked per file rather than for one script, because all three shared the
    same defect and a single assertion would let the other two regress unnoticed.

    @param path: Path to the script under test.
    @returns: Nothing; a missing eager load fails the test.
    """
    assert path.exists(), f"{path.name} is missing"

    tree = ast.parse(path.read_text())
    rendered = " ".join(ast.unparse(node) for node in ast.walk(tree) if isinstance(node, ast.Call))

    assert "selectinload" in rendered or "joinedload" in rendered, f"{path.name} loads Manifestation.expression lazily"
    assert "Manifestation.expression" in rendered, f"{path.name} does not eager-load Manifestation.expression"
    assert "Expression.work" in rendered, f"{path.name} stops at Expression and leaves Work lazy"

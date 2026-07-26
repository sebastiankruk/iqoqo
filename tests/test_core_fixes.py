"""Tests for Section 5 Core Bug Fixes:

- Apostrophe canonicalization (' vs ’ ‘ ʼ) in FTS search and facet filtering.
- Query sanitization in SearchService.
- Parameterized ILIKE escaping (% _ \\).
- Allegro User-Agent header validation matching format requirements.
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

import re

from app.api.filters import escape_ilike_term
from app.config import Config
from app.core.frbr_service import create_expression, create_manifestation, create_work
from app.core.search_service import SearchService, sanitize_search_query
from app.utils.allegro import get_allegro_user_agent


class TestApostropheAndSanitization:
    def test_sanitize_search_query_canonicalizes_apostrophes(self):
        assert sanitize_search_query("Ocean’s Eleven") == "Ocean's Eleven"
        assert sanitize_search_query("L‘Armée des Ombres") == "L'Armée des Ombres"
        assert sanitize_search_query("   Test ʼ Title   ") == "Test ' Title"

    def test_escape_ilike_term_escapes_metacharacters(self):
        assert escape_ilike_term("100%_pure\\test") == "100\\%\\_pure\\\\test"
        assert escape_ilike_term("Rock’n’Roll") == "Rock'n'Roll"

    def test_search_finds_apostrophe_titles(self, app):
        with app.app_context():
            work = create_work("Ocean's Eleven")
            expr = create_expression(work.id, content_type="movie")
            manif = create_manifestation(expr.id)

            total, ids = SearchService.search_manifestations("Ocean’s Eleven", limit=10, offset=0)
            assert total == 1
            assert manif.id in ids


class TestAllegroUserAgentFormat:
    def test_allegro_user_agent_format(self):
        ua = get_allegro_user_agent()
        app_name = re.escape(Config.ALLEGRO_APP_NAME)
        pattern = rf"^{app_name}/[a-zA-Z0-9.\-]+ \(\+https://iqoqo\.cc\)$"
        assert re.match(pattern, ua) is not None

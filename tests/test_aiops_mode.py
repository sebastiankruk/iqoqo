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
"""Tests for AiOps terse mode pytest configuration hook."""

from unittest.mock import MagicMock

import pytest
from conftest import pytest_configure


def test_pytest_configure_ai_mode_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert pytest_configure modifies options when IQOQO_AI_MODE is set."""
    monkeypatch.setenv("IQOQO_AI_MODE", "1")
    config = MagicMock()
    config.option = MagicMock()
    config.option.plugins = []

    pytest_configure(config)

    assert config.option.verbose == -1
    assert config.option.tbstyle == "short"
    assert config.option.no_header is True
    assert "no:sugar" in config.option.plugins
    config.pluginmanager.set_blocked.assert_called_with("sugar")


def test_pytest_configure_ai_mode_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert pytest_configure leaves options unchanged when IQOQO_AI_MODE is unset."""
    monkeypatch.delenv("IQOQO_AI_MODE", raising=False)
    config = MagicMock()
    config.option = MagicMock()
    config.option.verbose = 0
    config.option.tbstyle = "auto"
    config.option.no_header = False
    config.option.plugins = []

    pytest_configure(config)

    assert config.option.verbose == 0
    assert config.option.tbstyle == "auto"
    assert config.option.no_header is False
    assert "no:sugar" not in config.option.plugins
    config.pluginmanager.set_blocked.assert_not_called()

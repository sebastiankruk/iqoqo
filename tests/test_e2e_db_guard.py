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
"""Tests proving E2E DB selection is isolated before any reset is possible."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.e2e_db_guard import (
    UnsafeE2EDatabaseError,
    preflight,
    validate_database_url,
    validate_rendered_compose,
)

ROOT = Path(__file__).resolve().parent.parent
DEDICATED_URL = "postgresql://iqoqo_e2e:e2e_local_only@127.0.0.1:55432/iqoqo_e2e_test"


@pytest.mark.parametrize(
    "database_url",
    [
        "",
        "not-a-url",
        "sqlite:///tmp/e2e.db",
        "postgresql://iqoqo:password@localhost:5432/iqoqo_test",
        "postgresql://iqoqo:password@localhost:5432/iqoqo",
        "postgresql://iqoqo:password@preview.example:5432/iqoqo_test",
        "postgresql://iqoqo:password@192.168.1.20:5432/iqoqo_test",
        "postgresql://wrong:e2e_local_only@127.0.0.1:55432/iqoqo_e2e_test",
        "postgresql://iqoqo_e2e:wrong@127.0.0.1:55432/iqoqo_e2e_test",
        "postgresql://iqoqo_e2e:e2e_local_only@127.0.0.1:55432/iqoqo",
        f"{DEDICATED_URL}?sslmode=require",
    ],
)
def test_rejects_missing_unsafe_or_mismatched_database_urls(database_url: str) -> None:
    """Unsafe, absent, and mismatched targets must fail URL validation."""
    with pytest.raises(UnsafeE2EDatabaseError):
        validate_database_url(database_url)


@pytest.mark.parametrize(
    "database_url",
    [
        DEDICATED_URL,
        "postgres://iqoqo_e2e:e2e_local_only@localhost:55432/iqoqo_e2e_test",
    ],
)
def test_accepts_only_dedicated_loopback_test_database(database_url: str) -> None:
    """Loopback aliases are allowed only for the exact isolated DB identity."""
    validate_database_url(database_url)


def dedicated_compose_config() -> dict:
    """Build the expected resolved Compose model without starting Docker."""
    return {
        "services": {
            "e2e-db": {
                "image": "postgres:18-alpine",
                "environment": {
                    "POSTGRES_USER": "iqoqo_e2e",
                    "POSTGRES_PASSWORD": "e2e_local_only",
                    "POSTGRES_DB": "iqoqo_e2e_test",
                    "PGDATA": "/var/lib/postgresql/data",
                },
                "ports": [{"host_ip": "127.0.0.1", "published": "55432", "target": 5432}],
                "volumes": [{"type": "volume", "source": "e2e_data", "target": "/var/lib/postgresql/data"}],
            }
        },
        "volumes": {"e2e_data": {"name": "iqoqo-e2e-test_e2e_data"}},
        "networks": {"default": {"name": "iqoqo-e2e-test_default"}},
    }


def test_preflight_rejects_unsafe_url_before_running_compose(monkeypatch: pytest.MonkeyPatch) -> None:
    """Database isolation failure must happen before even Compose preflight."""
    commands: list[list[str]] = []

    def record_command(command: list[str]) -> None:
        commands.append(command)

    monkeypatch.setattr("scripts.e2e_db_guard._run", record_command)

    with pytest.raises(UnsafeE2EDatabaseError):
        preflight("postgresql://user:pass@localhost:5432/preview", "iqoqo-e2e-test", ROOT / "docker-compose.e2e.yml")

    assert not commands


def test_rejects_non_dedicated_compose_service_port_and_volume() -> None:
    """A config pointing at a shared service, port, or volume cannot pass."""
    unsafe_models = []
    wrong_service = dedicated_compose_config()
    wrong_service["services"]["db"] = wrong_service["services"].pop("e2e-db")
    unsafe_models.append(wrong_service)

    wrong_port = dedicated_compose_config()
    wrong_port["services"]["e2e-db"]["ports"][0]["published"] = "5432"
    unsafe_models.append(wrong_port)

    shared_volume = dedicated_compose_config()
    shared_volume["volumes"]["e2e_data"]["external"] = True
    unsafe_models.append(shared_volume)

    shared_host_path = dedicated_compose_config()
    shared_host_path["services"]["e2e-db"]["volumes"][0]["type"] = "bind"
    unsafe_models.append(shared_host_path)

    for model in unsafe_models:
        with pytest.raises(UnsafeE2EDatabaseError):
            validate_rendered_compose(model, "iqoqo-e2e-test")


def test_checked_in_e2e_compose_and_make_url_define_dedicated_resources() -> None:
    """The committed service uses a unique database, loopback port, and volume."""
    compose = yaml.safe_load((ROOT / "docker-compose.e2e.yml").read_text(encoding="utf-8"))
    service = compose["services"]["e2e-db"]
    assert set(compose["services"]) == {"e2e-db"}
    assert service["image"] == "postgres:18-alpine"
    assert service["ports"] == ["127.0.0.1:55432:5432"]
    assert service["volumes"] == ["e2e_data:/var/lib/postgresql/data"]
    assert compose["volumes"] == {"e2e_data": None}
    assert service["environment"]["POSTGRES_DB"] == "iqoqo_e2e_test"
    assert service["environment"]["POSTGRES_USER"] == "iqoqo_e2e"

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert f"E2E_DATABASE_URL = {DEDICATED_URL}" in makefile
    assert "--project-name iqoqo-e2e-test -f docker-compose.e2e.yml" in makefile
    assert ".env.test" not in makefile

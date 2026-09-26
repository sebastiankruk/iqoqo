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
"""Fail-closed validation of the isolated local E2E PostgreSQL target."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

EXPECTED_HOSTS = {"127.0.0.1", "localhost"}
EXPECTED_PORT = 55432
EXPECTED_DATABASE = "iqoqo_e2e_test"
EXPECTED_USER = "iqoqo_e2e"
EXPECTED_PASSWORD = "e2e_local_only"
EXPECTED_SERVICE = "e2e-db"
EXPECTED_VOLUME_KEY = "e2e_data"
EXPECTED_VOLUME_TARGET = "/var/lib/postgresql/data"


class UnsafeE2EDatabaseError(ValueError):
    """Raised when the selected database is not provably E2E-isolated."""


def validate_database_url(database_url: str) -> None:
    """Require the exact dedicated local E2E address and credentials."""
    try:
        parsed = urlsplit(database_url)
        port = parsed.port
    except ValueError as error:
        raise UnsafeE2EDatabaseError("E2E database URL is malformed.") from error

    if parsed.scheme not in {"postgres", "postgresql"}:
        raise UnsafeE2EDatabaseError("E2E database URL must use PostgreSQL.")
    if parsed.hostname not in EXPECTED_HOSTS or port != EXPECTED_PORT:
        raise UnsafeE2EDatabaseError("E2E database URL must target localhost on dedicated port 55432.")
    if unquote(parsed.username or "") != EXPECTED_USER:
        raise UnsafeE2EDatabaseError("E2E database URL must use the dedicated iqoqo_e2e role.")
    if unquote(parsed.password or "") != EXPECTED_PASSWORD:
        raise UnsafeE2EDatabaseError("E2E database URL does not have the dedicated local-test credential.")
    if parsed.path.lstrip("/") != EXPECTED_DATABASE:
        raise UnsafeE2EDatabaseError("E2E database URL must select iqoqo_e2e_test.")
    if parsed.query or parsed.fragment:
        raise UnsafeE2EDatabaseError("E2E database URL must not contain extra query or fragment options.")


def _run(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a safety check and convert command failures into explicit guard errors."""
    try:
        result = subprocess.run(command, check=False, capture_output=capture, text=True)
    except OSError as error:
        raise UnsafeE2EDatabaseError(f"Could not run safety command {command[0]}: {error}") from error
    if result.returncode:
        details = (result.stderr or result.stdout or "").strip()
        raise UnsafeE2EDatabaseError(f"Safety command failed ({' '.join(command)}): {details}")
    return result


def validate_rendered_compose(config: dict, project: str) -> None:
    """Assert the rendered compose file contains only the expected isolated DB."""
    services = config.get("services", {})
    if set(services) != {EXPECTED_SERVICE}:
        raise UnsafeE2EDatabaseError("E2E Compose must define only the dedicated e2e-db service.")

    service = services[EXPECTED_SERVICE]
    if service.get("image") != "postgres:18-alpine" or service.get("network_mode") or service.get("volumes_from"):
        raise UnsafeE2EDatabaseError("E2E database must be the dedicated PostgreSQL image on its private Compose network.")
    environment = service.get("environment", {})
    expected_environment = {
        "POSTGRES_USER": EXPECTED_USER,
        "POSTGRES_PASSWORD": EXPECTED_PASSWORD,
        "POSTGRES_DB": EXPECTED_DATABASE,
        "PGDATA": "/var/lib/postgresql/data",
    }
    if any(environment.get(key) != value for key, value in expected_environment.items()):
        raise UnsafeE2EDatabaseError("E2E Compose PostgreSQL identity configuration does not match the dedicated target.")

    ports = service.get("ports", [])
    if len(ports) != 1:
        raise UnsafeE2EDatabaseError("E2E Compose must publish exactly one PostgreSQL port.")
    port = ports[0]
    if (port.get("host_ip"), str(port.get("published")), int(port.get("target", 0))) != ("127.0.0.1", str(EXPECTED_PORT), 5432):
        raise UnsafeE2EDatabaseError("E2E Compose port must be bound only to 127.0.0.1:55432.")

    mounts = service.get("volumes", [])
    if len(mounts) != 1 or mounts[0].get("type") != "volume":
        raise UnsafeE2EDatabaseError("E2E Compose must use one dedicated named volume, not a shared or host path.")
    if mounts[0].get("source") != EXPECTED_VOLUME_KEY or mounts[0].get("target") != EXPECTED_VOLUME_TARGET:
        raise UnsafeE2EDatabaseError("E2E Compose volume must be the dedicated e2e_data PostgreSQL volume.")

    volumes = config.get("volumes", {})
    if set(volumes) != {EXPECTED_VOLUME_KEY}:
        raise UnsafeE2EDatabaseError("E2E Compose must declare only its project-scoped e2e_data volume.")
    volume = volumes[EXPECTED_VOLUME_KEY]
    if volume.get("external") or volume.get("name") != f"{project}_{EXPECTED_VOLUME_KEY}":
        raise UnsafeE2EDatabaseError("E2E PostgreSQL volume must be managed and namespaced by the E2E Compose project.")

    networks = config.get("networks", {})
    if set(networks) != {"default"} or networks["default"].get("external"):
        raise UnsafeE2EDatabaseError("E2E service must use only its private Compose project network.")


def _compose_command(project: str, compose_file: Path, *arguments: str) -> list[str]:
    return ["docker", "compose", "--project-name", project, "-f", str(compose_file), *arguments]


def preflight(database_url: str, project: str, compose_file: Path) -> None:
    """Validate URL plus Docker's resolved service, port, and volume before startup."""
    validate_database_url(database_url)
    if project != "iqoqo-e2e-test":
        raise UnsafeE2EDatabaseError("The E2E Compose project name must be iqoqo-e2e-test.")
    if not compose_file.is_file():
        raise UnsafeE2EDatabaseError(f"Dedicated E2E Compose file is missing: {compose_file}")
    result = _run(_compose_command(project, compose_file, "config", "--format", "json"))
    try:
        rendered = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise UnsafeE2EDatabaseError("Docker Compose returned invalid rendered configuration.") from error
    validate_rendered_compose(rendered, project)


def verify_running(database_url: str, project: str, compose_file: Path) -> None:
    """Prove runtime Compose labels, named volume, and actual DB identity."""
    preflight(database_url, project, compose_file)
    service_id = _run(_compose_command(project, compose_file, "ps", "-q", EXPECTED_SERVICE)).stdout.strip()
    if not service_id:
        raise UnsafeE2EDatabaseError("Dedicated E2E database service is not running; refusing reset/test startup.")

    inspected = json.loads(_run(["docker", "inspect", service_id]).stdout)[0]
    labels = inspected.get("Config", {}).get("Labels", {})
    if labels.get("com.docker.compose.project") != project or labels.get("com.docker.compose.service") != EXPECTED_SERVICE:
        raise UnsafeE2EDatabaseError("Running container does not belong to the dedicated E2E Compose project/service.")
    if not inspected.get("State", {}).get("Running"):
        raise UnsafeE2EDatabaseError("Dedicated E2E PostgreSQL container is not running.")
    if inspected.get("Config", {}).get("Image") != "postgres:18-alpine":
        raise UnsafeE2EDatabaseError("Running E2E container is not the dedicated PostgreSQL image.")

    port_bindings = inspected.get("NetworkSettings", {}).get("Ports", {}).get("5432/tcp") or []
    if port_bindings != [{"HostIp": "127.0.0.1", "HostPort": str(EXPECTED_PORT)}]:
        raise UnsafeE2EDatabaseError("Running PostgreSQL container is not exclusively bound to 127.0.0.1:55432.")

    environment = inspected.get("Config", {}).get("Env", [])
    expected_environment = {
        f"POSTGRES_USER={EXPECTED_USER}",
        f"POSTGRES_PASSWORD={EXPECTED_PASSWORD}",
        f"POSTGRES_DB={EXPECTED_DATABASE}",
    }
    if not expected_environment.issubset(set(environment)):
        raise UnsafeE2EDatabaseError("Running PostgreSQL container environment does not match the dedicated DB identity.")

    mounts = inspected.get("Mounts", [])
    matching_mounts = [
        mount
        for mount in mounts
        if mount.get("Type") == "volume"
        and mount.get("Destination") == EXPECTED_VOLUME_TARGET
        and mount.get("Name") == f"{project}_{EXPECTED_VOLUME_KEY}"
    ]
    if len(matching_mounts) != 1:
        raise UnsafeE2EDatabaseError("Running E2E database does not use its dedicated project-scoped volume.")

    query = "SELECT current_database() || '|' || current_user || '|' || inet_server_port()"
    psql = _run(["psql", database_url, "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-c", query]).stdout.strip()
    if psql != f"{EXPECTED_DATABASE}|{EXPECTED_USER}|5432":
        raise UnsafeE2EDatabaseError("Database identity query did not match the dedicated E2E database and role.")


def main() -> int:
    """Run requested safety validation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "verify-running"))
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--compose-project", required=True)
    parser.add_argument("--compose-file", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.action == "preflight":
            preflight(args.database_url, args.compose_project, args.compose_file)
            print("E2E database URL and isolated Compose configuration verified.")
        else:
            verify_running(args.database_url, args.compose_project, args.compose_file)
            print("Running E2E database identity, project, and volume verified.")
    except UnsafeE2EDatabaseError as error:
        print(f"E2E DATABASE SAFETY CHECK FAILED: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

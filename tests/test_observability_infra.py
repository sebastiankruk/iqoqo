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

import os
from pathlib import Path
from typing import Any, Dict
import yaml


def test_otel_collector_config_yaml_is_valid() -> None:
    """Verify that deploy/otel-collector-local.yaml exists and is valid YAML."""
    config_path: Path = Path(__file__).parent.parent / "deploy" / "otel-collector-local.yaml"
    assert config_path.exists()

    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    assert "receivers" in config
    assert "processors" in config
    assert "exporters" in config
    assert "service" in config

    # Check key receivers
    receivers: Dict[str, Any] = config["receivers"]
    assert "otlp" in receivers
    assert "docker_stats" in receivers
    assert "postgresql" in receivers
    assert "redis" in receivers

    # Check processors
    processors: Dict[str, Any] = config["processors"]
    assert "batch" in processors

    # Check exporters
    exporters: Dict[str, Any] = config["exporters"]
    assert "otlphttp/openobserve" in exporters


def test_monitoring_docker_compose_is_valid() -> None:
    """Verify that docker-compose.monitoring.yml exists and is valid YAML."""
    compose_path: Path = Path(__file__).parent.parent / "docker-compose.monitoring.yml"
    assert compose_path.exists()

    with open(compose_path, "r", encoding="utf-8") as f:
        compose: Dict[str, Any] = yaml.safe_load(f)

    assert "services" in compose
    services: Dict[str, Any] = compose["services"]
    assert "openobserve" in services
    assert "otel-collector" in services

    # Verify container names are project name prefixed
    assert services["openobserve"].get("container_name") == "${COMPOSE_PROJECT_NAME:-iqoqo}-openobserve"
    assert services["otel-collector"].get("container_name") == "${COMPOSE_PROJECT_NAME:-iqoqo}-otel-collector"


def test_nginx_main_otel_config_structure() -> None:
    """Verify that deploy/nginx-main.conf contains required OpenTelemetry directives."""
    conf_path: Path = Path(__file__).parent.parent / "deploy" / "nginx-main.conf"
    assert conf_path.exists()

    content: str = conf_path.read_text(encoding="utf-8")
    assert "ngx_otel_module.so" in content
    assert "otel_exporter" in content
    assert "otel_trace on;" in content
    assert "otel_service_name" in content

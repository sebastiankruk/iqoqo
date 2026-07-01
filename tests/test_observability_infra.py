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
from typing import Any

import yaml


def test_otel_collector_config_yaml_is_valid() -> None:
    """Verify that deploy/otel-collector-local.yaml exists, is valid YAML,
    and only uses the OTLP receiver.

    The local dev config must NOT include infrastructure receivers
    (docker_stats, postgresql, redis) because those require a full Docker
    Compose stack and cause the collector to crash-loop in local dev mode.
    See deploy/otel-collector-prod.yaml for the full-receiver production config.
    """
    config_path: Path = Path(__file__).parent.parent / "deploy" / "otel-collector-local.yaml"
    assert config_path.exists()

    with open(config_path, encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f)

    assert "receivers" in config
    assert "processors" in config
    assert "exporters" in config
    assert "service" in config

    # Local dev config must only use the OTLP receiver
    receivers: dict[str, Any] = config["receivers"]
    assert "otlp" in receivers, "otlp receiver must be present in local config"
    assert "docker_stats" not in receivers, "docker_stats must NOT be in local config — it crash-loops without Docker socket"
    assert "postgresql" not in receivers, "postgresql must NOT be in local config — it crash-loops without in-network 'db' hostname"
    assert "redis" not in receivers, "redis must NOT be in local config — it crash-loops without in-network 'redis' hostname"

    # All 3 signal pipelines must only reference the otlp receiver
    pipelines: dict[str, Any] = config["service"]["pipelines"]
    for signal in ("traces", "metrics", "logs"):
        assert signal in pipelines, f"pipeline '{signal}' must be present"
        pipeline_receivers = pipelines[signal]["receivers"]
        assert pipeline_receivers == ["otlp"], f"'{signal}' pipeline must only use [otlp] in local config, got {pipeline_receivers}"

    # Check processors
    processors: dict[str, Any] = config["processors"]
    assert "batch" in processors

    # Check exporters
    exporters: dict[str, Any] = config["exporters"]
    assert "otlphttp/openobserve" in exporters


def test_otel_collector_prod_config_yaml_is_valid() -> None:
    """Verify that deploy/otel-collector-prod.yaml exists, is valid YAML,
    and contains all infrastructure receivers required for full observability.
    """
    config_path: Path = Path(__file__).parent.parent / "deploy" / "otel-collector-prod.yaml"
    assert config_path.exists(), "otel-collector-prod.yaml must exist for production deployments"

    with open(config_path, encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f)

    assert "receivers" in config
    assert "processors" in config
    assert "exporters" in config
    assert "service" in config

    # Prod config must have all infrastructure receivers
    receivers: dict[str, Any] = config["receivers"]
    assert "otlp" in receivers, "otlp receiver must be present"
    assert "docker_stats" in receivers, "docker_stats must be present in prod config"
    assert "postgresql" in receivers, "postgresql must be present in prod config"
    assert "redis" in receivers, "redis must be present in prod config"

    # Metrics pipeline must include infrastructure receivers
    pipelines: dict[str, Any] = config["service"]["pipelines"]
    assert "metrics" in pipelines
    metrics_receivers = pipelines["metrics"]["receivers"]
    for receiver in ("otlp", "postgresql", "redis", "docker_stats"):
        assert receiver in metrics_receivers, f"'{receiver}' must be in prod metrics pipeline, got {metrics_receivers}"

    # Check exporters
    exporters: dict[str, Any] = config["exporters"]
    assert "otlphttp/openobserve" in exporters


def test_monitoring_docker_compose_is_valid() -> None:
    """Verify that docker-compose.monitoring.yml exists and is valid YAML."""
    compose_path: Path = Path(__file__).parent.parent / "docker-compose.monitoring.yml"
    assert compose_path.exists()

    with open(compose_path, encoding="utf-8") as f:
        compose: dict[str, Any] = yaml.safe_load(f)

    assert "services" in compose
    services: dict[str, Any] = compose["services"]
    assert "openobserve" in services
    assert "otel-collector" in services

    # Verify container names are project name prefixed
    assert services["openobserve"].get("container_name") == "${COMPOSE_PROJECT_NAME:-iqoqo}-openobserve"
    assert services["otel-collector"].get("container_name") == "${COMPOSE_PROJECT_NAME:-iqoqo}-otel-collector"

    # CRITICAL: The OTel collector must NOT use env_file. Loading the full .env injects
    # OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 into the container, overriding
    # the YAML config's exporter and causing the collector to export to itself (fatal loop).
    assert "env_file" not in services["otel-collector"], (
        "otel-collector MUST NOT use env_file — .env contains OTEL_EXPORTER_OTLP_ENDPOINT "
        "and other Python SDK vars that override the collector's own YAML config"
    )
    assert "environment" in services["otel-collector"], "otel-collector should use explicit environment vars instead of env_file"


def test_nginx_main_otel_config_structure() -> None:
    """Verify that deploy/nginx-main.conf contains required OpenTelemetry directives."""
    conf_path: Path = Path(__file__).parent.parent / "deploy" / "nginx-main.conf"
    assert conf_path.exists()

    content: str = conf_path.read_text(encoding="utf-8")
    assert "ngx_otel_module.so" in content
    assert "otel_exporter" in content
    assert "otel_trace on;" in content
    assert "otel_service_name" in content

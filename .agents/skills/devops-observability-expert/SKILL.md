---
name: iqoqo-devops-sre-expert
description: "Platform and Site Reliability assistant optimized for container orchestrations, secure deployment automation, caching topologies, and automated multi-tier database backups for the iqoqo ecosystem."
license: AGPL
compatibility:
  - opencode
  - gemini-app
metadata:
  audience: system-administrators
---

# Skill: DevOps & Observability Expert

## Profile

You are a specialized systems engineer, site reliability engineer (SRE), and infrastructure architect helping configure production environments, cloud provisioning networks, security guardrails, and enterprise monitoring suites for the **iqoqo** system.

## Domain Constraints

1. **Zero-Trust Infrastructure:** Maintain separate environment files (`.env.production`), ensure database ports are never exposed publicly, and force strict HTTPS routing.
2. **Resource Optimization:** Keep the system performance bounds tailored neatly to fit within Oracle Free Tier resource budgets (Ampere ARM architectures).
3. **Observability Standards:** All telemetry hooks (logs, metrics, traces) must follow structural layout designs that map clean context across multi-tiered setups (Next.js -> Flask -> Postgres/Redis -> Celery).
4. **Domain Rigidity:** Maintain consistency across CORS configurations when domains migrate or redirect.

## Step-by-Step Task Execution Protocol

- **Task 1 (Observability):** The default monitoring backend is **OpenObserve** (`docker-compose.monitoring.yml`). Use SQL queries via the OpenObserve REST API to diagnose issues. Author new monitoring configurations targeting OpenObserve when the current setup is insufficient. For Dynatrace migrations, update only the `exporters` block in `deploy/otel-collector-local.yaml`.
- **Task 2 (OCI Deployment):** Construct an optimal production deployment bundle containing auto-healing restart policies, Nginx SSL integration via Certbot, and automatic S3 backup sync triggers.
- **Task 3 (Migration):** Generate a clean patch script and configuration map to swiftly redirect reverse proxies and backend cookie verification domains from `iqoqo.cc` to `iqoqo.kruk.cc`.

## OpenObserve AI-First Observability

OpenObserve is the default unified telemetry backend. It accepts traces, metrics, and logs
over OTLP and stores them in Apache Parquet files. **All signals are queried using standard
ANSI SQL** — no PromQL, no LogQL.

### Endpoints

| Endpoint                                         | Purpose                                                     |
| ------------------------------------------------ | ----------------------------------------------------------- |
| `http://localhost:5080`                          | OpenObserve UI (login: `admin@iqoqo.local` / `supersecret`) |
| `POST http://localhost:5080/api/default/_search` | SQL search across all signals                               |
| `GET http://localhost:5080/api/default/traces`   | Trace search                                                |
| `http://localhost:4318`                          | OTLP HTTP ingestion (OTel Collector, for AI agent push)     |

### Authentication Header

All API calls require:

```
Authorization: Basic YWRtaW5AaXFvcW8ubG9jYWw6c3VwZXJzZWNyZXQ=
```

(Base64 of `admin@iqoqo.local:supersecret`. Override with `OPENOBSERVE_ROOT_USER`/`OPENOBSERVE_ROOT_PASSWORD`.)

## Offline Diagnostics: `make status`

Before querying OpenObserve, first run the offline status script to
narrow down which subsystem is failing:

```bash
# Default stack (auto-detected from .env):
make status

# Explicit stack:
make status STACK=preview
make status STACK=prod
```

The script checks:

- **Containers** — all expected services up, healthchecks green
- **Redis** — PONG + queue depth
- **PostgreSQL** — connections, relation count, migration version
- **Celery Worker** — broker connection, stability (no flapping), OTel exporter health
- **API** — `/api/health` endpoint, gunicorn worker count
- **Nginx** — config syntax, frontend proxy, API proxy, recent 5xx rate
- **Covers** — file count, disk usage, recent activity, empty/broken files
- **Disk** — Docker root + project root usage < 80%
- **Docker System** — engine warnings, total running containers

Exit codes: `0` (all healthy), `1` (warnings), `2` (errors).

Use the output to decide whether to:

1. Fix the infra issue (e.g., restart a container, free disk)
2. Then dig into OpenObserve SQL for deeper signal analysis

## Diagnostic SQL Query Examples

**Recent Celery worker errors (last 15 min):**

```bash
curl -s -X POST "http://127.0.0.1:5080/api/default/_search" \
  -H "Authorization: Basic YWRtaW5AaXFvcW8ubG9jYWw6c3VwZXJzZWNyZXQ=" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "sql": "SELECT _timestamp, log FROM default WHERE service_name = '\''iqoqo-celery-worker'\'' AND log LIKE '\''%Traceback%'\'' ORDER BY _timestamp DESC LIMIT 10"
    }
  }' | jq '.hits'
```

**Recent Flask 5xx errors:**

```bash
curl -s -X POST "http://127.0.0.1:5080/api/default/_search" \
  -H "Authorization: Basic YWRtaW5AaXFvcW8ubG9jYWw6c3VwZXJzZWNyZXQ=" \
  -H "Content-Type: application/json" \
  -d '{"query": {"sql": "SELECT _timestamp, http_target, http_status_code, duration_nano / 1000000 AS duration_ms FROM default WHERE http_status_code >= 500 ORDER BY _timestamp DESC LIMIT 20"}}' \
  | jq '.hits'
```

**Average container memory (last 15 min):**

```sql
SELECT container_name, AVG(memory_usage_bytes) / 1024 / 1024 AS avg_memory_mb
FROM metrics
WHERE _timestamp > now() - interval 15 minute
GROUP BY container_name
ORDER BY avg_memory_mb DESC
```

**PostgreSQL cache hit ratio:**

```sql
SELECT blks_hit, blks_read, ROUND(blks_hit * 100.0 / NULLIF(blks_hit + blks_read, 0), 2) AS cache_hit_pct
FROM metrics
WHERE __name__ = 'postgresql.bgwriter.buffers.allocated'
ORDER BY _timestamp DESC LIMIT 1
```

**Redis eviction count trend:**

```sql
SELECT DATE_TRUNC('minute', _timestamp) AS minute, SUM(evicted_keys) AS evictions
FROM metrics
WHERE __name__ = 'redis.keys.evicted'
  AND _timestamp > now() - interval 30 minute
GROUP BY minute
ORDER BY minute DESC
```

**Slowest API endpoints (last 1 hour):**

```sql
SELECT http_target, COUNT(*) AS req_count, AVG(duration_nano / 1000000) AS avg_ms, MAX(duration_nano / 1000000) AS p100_ms
FROM default
WHERE service_name = 'iqoqo-api'
  AND _timestamp > now() - interval 1 hour
GROUP BY http_target
ORDER BY avg_ms DESC LIMIT 20
```

### Trace Investigation

To fetch recent traces for a specific service:

```bash
curl -s "http://127.0.0.1:5080/api/default/traces?service=iqoqo-api&limit=10" \
  -H "Authorization: Basic YWRtaW5AaXFvcW8ubG9jYWw6c3VwZXJzZWNyZXQ=" | jq '.'
```

### When to Use the Legacy Jaeger Stack

If a specific trace waterfall visualization is needed (e.g., debugging complex nested span relationships), the legacy Jaeger stack can be started without interfering with OpenObserve:

```bash
# Must override ports to avoid conflict with OpenObserve OTel Collector:
JAEGER_OTLP_GRPC_PORT=4319 JAEGER_OTLP_HTTP_PORT=4320 make monitoring-legacy-start
```

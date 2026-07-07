# Monitoring & Observability

iqoqo ships a **Zero Blind Spot** observability stack built on OpenTelemetry (OTel).
All 8 layers of the platform are instrumented. Telemetry flows through a single OTel
Collector gateway into a unified backend that accepts traces, metrics, and logs over
the same OTLP endpoint.

## Architecture Overview

```mermaid
graph TD
    B["🌐 Browser (Web Vitals)<br/>Layer 5"]
    N["⚙️ Nginx Edge Proxy<br/>Layer 6"]
    F["🐍 Flask API (Gunicorn)<br/>Layer 2"]
    C["📋 Celery Workers<br/>Layer 3"]
    NX["⚛️ Next.js SSR<br/>Layer 1"]
    H["🔗 Outbound HTTP (requests)<br/>Layer 4"]
    LLM["🤖 OpenAI LLM<br/>Layer 7"]
    DB["🗄️ PostgreSQL + Redis<br/>Layer 8"]

    B -->|"OTLP HTTP (CORS)"| COL
    N -->|"OTLP gRPC (ngx_otel_module)"| COL
    F -->|"OTLP HTTP"| COL
    C -->|"OTLP HTTP"| COL
    NX -->|"OTLP HTTP"| COL
    H -->|"OTLP HTTP (auto)"| COL
    LLM -->|"OTLP HTTP (auto)"| COL
    COL -->|"scrapes"| DB

    COL["📡 OTel Collector<br/>otel/opentelemetry-collector-contrib"]
    COL -->|"OTLP HTTP"| OO

    OO["🔍 OpenObserve<br/>unified backend — SQL queries<br/>localhost:5080"]
```

## Default Stack: OpenObserve

OpenObserve (`openobserve/openobserve`) is a single Rust binary that natively accepts
traces, metrics, and logs over OTLP. Data is stored in compressed Apache Parquet files.
Queries use standard ANSI SQL — no PromQL, no LogQL.

### Start

```bash
make monitoring-start
# or:
docker compose -f docker-compose.monitoring.yml up -d
```

### Access

| Interface          | URL                                                   |
|--------------------|-------------------------------------------------------|
| **OpenObserve UI** | `http://localhost:5080` (or `$OPENOBSERVE_HOST_PORT`) |
| **Login**          | `admin@iqoqo.local` / `supersecret`                   |
| **SQL REST API**   | `POST http://localhost:5080/api/default/_search`      |
| **OTLP gRPC**      | `localhost:4317` (or `$OTEL_GRPC_HOST_PORT`)          |
| **OTLP HTTP**      | `localhost:4318` (or `$OTEL_HTTP_HOST_PORT`)          |

### Multi-Stack Port Collision Avoidance

When running `prod` and `preprod` on the same machine, override host ports in `.env`:

```bash
# preprod .env
OPENOBSERVE_HOST_PORT=5081
OTEL_GRPC_HOST_PORT=4319
OTEL_HTTP_HOST_PORT=4320
```

### Stop

```bash
make monitoring-stop
```

---

## Instrumented Layers

All 8 platform layers are instrumented via **zero-code-change OpenTelemetry auto-instrumentation**:

| # | Layer                            | Mechanism                                            | Signal                        |
|---|----------------------------------|------------------------------------------------------|-------------------------------|
| 1 | **Frontend SSR (Next.js)**       | `@vercel/otel` via `frontend/instrumentation.ts`     | Traces, Metrics               |
| 2 | **Flask Backend (Gunicorn)**     | `opentelemetry-instrument gunicorn` wrapper          | Traces, Metrics, Logs         |
| 3 | **Celery Workers**               | `opentelemetry-instrument celery` wrapper            | Traces, Metrics, Logs         |
| 4 | **Outbound HTTP (requests)**     | `opentelemetry-instrumentation-requests`             | Traces                        |
| 5 | **Browser Web Vitals**           | `BrowserTelemetry` React component + OTel Web SDK    | Traces                        |
| 6 | **Nginx Edge Proxy**             | `ngx_otel_module.so` (via `deploy/Dockerfile.nginx`) | Traces                        |
| 7 | **OpenAI LLM**                   | `opentelemetry-instrumentation-openai`               | Traces (token usage, prompts) |
| 8 | **PostgreSQL & Redis Internals** | OTel Collector `postgresql` + `redis` receivers      | Metrics                       |

---

## AI-First Observability: SQL Queries

Because OpenObserve uses standard SQL, AI agents can diagnose production issues without
opening a browser or writing PromQL.

### Recent Celery Errors

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

### Average Memory per Container (last 15 min)

```sql
SELECT container_name, AVG(memory_usage_bytes) / 1024 / 1024 AS avg_memory_mb
FROM metrics
WHERE _timestamp > now() - interval 15 minute
GROUP BY container_name
ORDER BY avg_memory_mb DESC
```

### PostgreSQL Cache Hit Ratio

```sql
SELECT blks_hit, blks_read, blks_hit / (blks_hit + blks_read + 0.001) AS cache_hit_ratio
FROM metrics
WHERE __name__ = 'postgresql.blocks_read'
ORDER BY _timestamp DESC LIMIT 1
```

---

## Security

- All host ports are bound to `127.0.0.1` — telemetry never leaks to public network interfaces.
- The Nginx `/metrics` location is blocked (returns `404`) at the virtual host level in `deploy/nginx.conf`.
- The OTel Collector and OpenObserve communicate over the internal `iqoqo_default` Docker bridge network.
- The Docker socket is mounted **read-only** (`/var/run/docker.sock:ro`) into the OTel Collector for `docker_stats` scraping only.
- CORS is restricted to `localhost:3000` and `dev.iqoqo.cc` for browser-side OTLP ingestion.

---

## Configuration Files

| File                                           | Purpose                                        |
|------------------------------------------------|------------------------------------------------|
| `docker-compose.monitoring.yml`                | **Default** OpenObserve + OTel Collector stack |
| `deploy/otel-collector-local.yaml`             | OTel Collector config (OpenObserve backend)    |
| `deploy/Dockerfile.nginx`                      | Custom Nginx with `ngx_otel_module` (Layer 6)  |
| `deploy/nginx-main.conf`                       | Nginx main config loading OTel C-module        |
| `frontend/instrumentation.ts`                  | Next.js server-side OTel bootstrap (Layer 1)   |
| `frontend/components/browser-telemetry.tsx`    | Browser-side OTel bootstrap (Layer 5)          |

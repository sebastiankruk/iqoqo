## 1. Service Contract and Security Boundary

- [ ] 1.1 Define and version the internal request/result/error protocol with deadlines, size limits, correlation IDs, signed scope expiry, and negotiated formats, then verify contract tests cover success and every failure class.
- [ ] 1.2 Implement API-side authorization, bounded caller-scoped snapshot creation, and signed service requests without forwarding JWTs or database credentials, then verify cross-user private-data isolation.
- [ ] 1.3 Implement service authentication and fail-closed scope validation, then verify unauthenticated, expired, replayed, and tenant-mismatched requests are rejected before execution.

## 2. Isolated Execution Service

- [ ] 2.1 Create the non-root service image and internal-only listener with read-only filesystem, bounded temporary storage, dropped capabilities, restricted egress, and no application-secret mounts, then verify container security checks and startup.
- [ ] 2.2 Implement bounded queue/admission control and killable query workers with explicit IPC, deadline propagation, process cleanup, and worker replacement, then verify timeout and crash tests leave no orphan work.
- [ ] 2.3 Enforce graph, query, intermediate/result, serialized-byte, CPU, memory, and PID limits inside the service, then verify adversarial queries fail closed without exhausting the service container.
- [ ] 2.4 Implement typed service errors and API mapping for saturation, timeout, invalid input, unavailable service, and internal failure, then verify existing `/api/sparql` clients receive compatible responses.

## 3. Deployment and Observability

- [ ] 3.1 Add Compose/preview deployment, health/readiness checks, internal network policy, restart policy, and explicit resource limits, then verify the production-like stack starts and recovers from worker failure.
- [ ] 3.2 Add metrics, structured logs, and traces for queue depth, active work, latency, limits, timeouts, restarts, and resource use without query/private-value logging, then verify dashboards and alerts receive signals.
- [ ] 3.3 Document service protocol, capacity calculations, rollout, rollback, controlled-503 behavior, and incident runbooks, then verify an operator can execute the documented recovery procedure.

## 4. Compatibility and Validation

- [ ] 4.1 Add integration tests for GET/POST protocol methods, SELECT/ASK/CONSTRUCT/DESCRIBE, content negotiation, authorization, privacy, and Explorer behavior through the service, then verify the existing semantic SPARQL specification passes.
- [ ] 4.2 Add load and security tests for queue saturation, concurrent tenants, oversized snapshots/results, repeated timeouts, worker restarts, replayed envelopes, and resource ceilings, then verify API workers remain healthy.
- [ ] 4.3 Canary the service in preview, compare in-process and service results where safe, and run a soak test, then verify zero cross-tenant leaks, stable resource usage, acceptable latency, and controlled failure behavior.
- [ ] 4.4 Route production traffic to the service, monitor the defined acceptance window, and remove the old web-worker executor only after rollback readiness is demonstrated, then verify no thread-based timeout fallback remains.

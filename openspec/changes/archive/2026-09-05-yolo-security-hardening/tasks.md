## 1. Auth Endpoint Patch

- [x] 1.1 Update `frontend/app/api/auth-exchange/route.ts` to use `NEXT_PUBLIC_FRONTEND_URL`. Verify the change prevents X-Forwarded-Host injection.

## 2. Docker Sandbox

- [x] 2.1 Create `docker-compose.ai_sandbox.yml` with strict constraints, resource limits, and surgical `credentials.json` mount. Verify syntax and configuration.

## 3. Makefile & Daemon Orchestration

- [x] 3.1 Update `Makefile` to bump model to `gemini-3.8-flash-low`.
- [x] 3.2 Modify `Makefile` targets to use `docker compose -f docker-compose.ai_sandbox.yml run` instead of `docker run`. Verify the `mykg-agy-daemon` starts securely.
- [x] 3.3 Update `.agents/skills/iqoqo-mykg/scripts/agy_daemon.py` to bump the default model. Verify `agy_daemon.py` runs correctly.

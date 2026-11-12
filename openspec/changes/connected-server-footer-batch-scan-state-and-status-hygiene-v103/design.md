## Context

See `proposal.md`. Evidence is a real `iqoprerest` run whose final `make status` showed `1 error(s), 1 warning(s)` on an otherwise healthy preview stack. Relevant code: `scripts/iqoqo-status.sh` (OTel export grep at ~483, env section from ~1178, 5xx check at ~770). The `iqoprerest` script itself is not in this repository (it is the operator's `iqopretest.sh`), so the task begins by locating and, if appropriate, bringing it under version control.

## Goals / Non-Goals

**Goals:**

- A healthy preview stack reports a clean `make status` after `iqoprerest`.
- Every missing variable is classified so operators know which matter.
- Footer shows the connected server; batch-scan state is unmistakable and accessible.

**Non-Goals:**

- Changing batch-scan behavior or adding multi-server switching.
- Removing any real status check or silencing real failures.
- Changing the OTel pipeline itself.

## Decisions

1. **Readiness before reporting:** `iqoprerest` polls the backend health endpoint with a bounded retry (for example up to 60s) and swallows connection errors during the wait; it prints only the final result. It then waits for the OTel collector and OpenObserve to report ready before running `make status`.
2. **OTel export window:** Count `Exporting failed|HTTP Status Code 401` only for log lines newer than the later of (collector container start time + grace window) and `now - 5m`. Sustained failures after the grace window still produce `fail`.
3. **Env classification:** A committed classification file (for example `.env.status-classes`) maps each `.env.example` key to `default` (code or compose supplies a value), `optional`, or `required`. `make status` prints `default` and `optional` as `info` and only `required` as `warn`. A test asserts every `.env.example` key is classified, so new variables cannot silently fall into noise.
4. **Required-set review:** `DEPLOY_TOKEN`, `BASE_URL`, and `FEDERATION_HEAD_MODE` are reviewed individually and classified by whether the running code reads them without a default.
5. **Footer identity:** Use the existing public instance URL setting and show its host; no new endpoint. Truncate with a tooltip on small screens.
6. **Indicator design:** Badge with explicit text "Batch scan: ON/OFF", an icon, and `aria-live="polite"`; Shadcn components and Tailwind theme tokens; default OFF.

## Risks / Trade-offs

- **[Risk] Grace window hides a genuine early failure** -> Mitigation: the window is short and failures after it still `fail`; the test covers both.
- **[Risk] Misclassifying a variable as `default`** -> Mitigation: classification is reviewed against code reads of each key and recorded in the file with a short reason.
- **[Risk] `iqoprerest` lives outside the repo** -> Mitigation: task 2.1 locates it and the change is limited to its readiness wait.

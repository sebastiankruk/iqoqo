## 1. Simulation Harness & Chaos Tests

- [x] Create initial `tests/test_federation_e2e.py` simulation harness.
- [ ] Implement full S2S signature replay and DNS rebinding chaos test suites across Celery inbox/outbox.
- [ ] Run full federation test matrix with `IQOQO_AI_MODE=1 pytest tests/test_federation*.py`.

## 2. Observability & SRE Verification

- [ ] Verify OTel spans and OpenObserve metrics (`federation_sig_failures_total`, `federation_delivery_failures_total`).
- [ ] Validate secret redaction and blocked-instance isolation in S2S pipeline logs.


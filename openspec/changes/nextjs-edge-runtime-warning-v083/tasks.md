## 1. Investigation & Reproduction

- [ ] 1.1 Run `npm run build` in `frontend/` and capture build log output to confirm exact line and module triggering the Edge runtime deprecation warning
- [ ] 1.2 Inspect `node_modules/next` deprecation trigger conditions and test Node.js runtime declarations in `frontend/proxy.ts` and `frontend/next.config.ts`

## 2. Configuration & Verification

- [ ] 2.1 Update `frontend/proxy.ts` or `frontend/next.config.ts` with explicit Node.js runtime settings to resolve or document deprecation notice; verify build completes with zero errors
- [ ] 2.2 Verify `proxyTimeout: 120000` and reverse proxy timeouts function properly during test execution
- [ ] 2.3 Add CI check or documentation in `docs/OPERATIONS.md` summarizing the Next.js runtime status

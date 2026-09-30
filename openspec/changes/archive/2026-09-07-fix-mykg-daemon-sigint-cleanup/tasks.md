## 1. Makefile Signal Trapping and Pre-Flight Cleanup

- [x] 1.1 Add pre-flight container removal (`docker rm -f mykg-agy-daemon`) to `mykg-update` and `mykg-index` targets in `Makefile`, and verify via `make -n mykg-update` and `make -n mykg-index`
- [x] 1.2 Implement shell signal trap handlers (`trap ... EXIT INT TERM`) in `mykg-update` and `mykg-index` recipes in `Makefile` ensuring automatic teardown and exit code propagation, and verify recipe execution syntax

## 2. Test Suite Hardening

- [x] 2.1 Add unit tests in `tests/bash/mykg_tooling.bats` verifying Makefile targets define pre-flight container eviction and signal trap handlers on EXIT, INT, and TERM, and verify with `bats tests/bash/mykg_tooling.bats`
- [x] 2.2 Add Bats integration test in `tests/bash/mykg_tooling.bats` validating container cleanup upon simulated interruption, and verify test passes

## 3. Verification and Documentation

- [x] 3.1 Run Bats test suite and project linters via `IQOQO_AI_MODE=1 bats tests/bash/mykg_tooling.bats` to verify clean test execution
- [x] 3.2 Document the daemon cleanup fix in `docs/CHANGELOG.md` under `[0.7.18] - Fixed`

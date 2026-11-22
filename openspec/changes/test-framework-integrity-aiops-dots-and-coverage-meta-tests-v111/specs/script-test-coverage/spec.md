## ADDED Requirements

### Requirement: make test-scripts-python executes all root and subdirectory Python script test suites
The system SHALL ensure that `make test-scripts-python` executes `tests/test_scripts.py`, `tests/test_script_utilities.py`, and all test modules under `tests/scripts/`.

#### Scenario: Subdirectory script tests are executed by make test-scripts-python
- **WHEN** `make test-scripts-python` is executed locally or in CI (`test-scripts`)
- **THEN** pytest SHALL collect and execute `tests/test_scripts.py`, `tests/test_script_utilities.py`, and `tests/scripts/` (including `test_iqoqo_installer.py` and `test_verify_ai_cover_bindings.py`)

### Requirement: Operational test runner scripts have unit test coverage
The system SHALL have pytest unit tests covering `scripts/format_bats_ai.py` and `scripts/run_tests_parallel.py`.

#### Scenario: format_bats_ai.py formats TAP pass and failure streams accurately
- **WHEN** `scripts/format_bats_ai.py` processes a TAP stream with `ok` and `not ok` lines
- **THEN** passing streams SHALL emit one `.` per test, a final `BATS: <N> tests passed.` summary, and exit code `0`
- **THEN** failing streams SHALL emit `F` for failed tests, print the failure details block, and exit with code `1`

#### Scenario: run_tests_parallel.py partitions all backend and script tests without overlap or omission
- **WHEN** `scripts/run_tests_parallel.py` builds its stream definitions
- **THEN** `partition_backend_tests()` SHALL partition all eligible `tests/**/test_*.py` files into three non-overlapping streams (`domain`, `api`, `tooling`) and suppress decorative banners when `IQOQO_AI_MODE=1`

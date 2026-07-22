## Requirements

### Requirement: Contributing guide documents OpenSpec workflow

The CONTRIBUTING.md SHALL include an overview of the OpenSpec workflow for proposing and implementing changes, referencing the `openspec-propose` and `openspec-apply-change` skills and the `openspec/` directory structure.

#### Scenario: New contributor reads about development workflow

- **WHEN** a new contributor reads the Development Workflow section
- **THEN** they SHALL find documentation explaining how to use OpenSpec for proposing, designing, and implementing changes

### Requirement: Contributing guide documents new Makefile targets

The CONTRIBUTING.md development commands quick reference SHALL include the following Makefile targets: `make fix-physical-kinds` (format audit/fix CLI), `make status` (health checks), `make db-stamp` (migration version stamping), and `make db-upgrade` (manual migration application).

#### Scenario: Developer needs to fix non-canonical formats

- **WHEN** a developer encounters non-canonical physical kind values
- **THEN** they SHALL find the `make fix-physical-kinds` command documented in the quick reference section with parameters for --apply and --dry-run

### Requirement: Contributing guide documents format normalization conventions

The CONTRIBUTING.md SHALL document the format normalization convention: that `shared/format_mappings.yaml` is the git-tracked source of truth for external-to-canonical format mappings, that `app/core/format_normalizer.py` is the read-time normalizer, and that new unknown format values should be added to `MediaFormat` enums and the taxonomy before use.

#### Scenario: Developer adds a new media format

- **WHEN** a developer needs to add support for a new external format value
- **THEN** they SHALL find documentation explaining the format normalization pipeline and how to map non-canonical values

### Requirement: Contributing guide documents cross-FRBR testing

The CONTRIBUTING.md testing section SHALL document the need to test cross-FRBR filtering scenarios when modifying facet aggregation or filter logic, referencing the existing test patterns in `tests/test_api_status_filters.py` and `tests/test_faceted_catalog.py`.

#### Scenario: Developer modifies facet filtering logic

- **WHEN** a developer changes DataManager.get_faceted_stats or facet filter building
- **THEN** they SHALL find guidance on testing at all FRBR levels (global, works, expressions, items) with cross-entity filter combinations

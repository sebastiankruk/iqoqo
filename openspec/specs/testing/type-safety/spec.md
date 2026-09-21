## Purpose

Resolves pre-existing mypy type errors in `app/core/sparql_service.py` to improve type safety and enable better IDE support and static analysis.

## Requirements

### Requirement: Fix bindings type annotation
The system SHALL have proper type annotation for the `bindings` variable at line 247 in `app/core/sparql_service.py`.

#### Scenario: Mypy check passes for bindings

- **WHEN** mypy runs on `app/core/sparql_service.py`
- **THEN** no type error reported for `bindings` variable

### Requirement: Fix ResultRow indexing
The system SHALL have proper type handling for `ResultRow` indexing at line 253 in `app/core/sparql_service.py`.

#### Scenario: Mypy check passes for ResultRow indexing

- **WHEN** mypy runs on `app/core/sparql_service.py`
- **THEN** no type error reported for ResultRow indexing

### Requirement: Fix Process type mismatches
The system SHALL have proper type handling for `SpawnProcess` vs `Process` at lines 383, 395, 449 in `app/core/sparql_service.py`.

#### Scenario: Mypy check passes for Process types

- **WHEN** mypy runs on `app/core/sparql_service.py`
- **THEN** no type error reported for Process type mismatches

### Requirement: Fix BNode/Literal assignment to URIRef
The system SHALL have proper type handling for BNode and Literal assignments to URIRef variables at lines 493, 497 in `app/core/sparql_service.py`.

#### Scenario: Mypy check passes for RDF node assignments

- **WHEN** mypy runs on `app/core/sparql_service.py`
- **THEN** no type error reported for BNode/Literal assignments

### Requirement: Fix list type mismatch
The system SHALL have proper type handling for list type mismatch at line 508 in `app/core/sparql_service.py`.

#### Scenario: Mypy check passes for list types

- **WHEN** mypy runs on `app/core/sparql_service.py`
- **THEN** no type error reported for list type mismatch

### Requirement: Fix Mapping.get overload mismatch
The system SHALL have proper type handling for `Mapping.get()` overload at line 625 in `app/core/sparql_service.py`.

#### Scenario: Mypy check passes for Mapping.get

- **WHEN** mypy runs on `app/core/sparql_service.py`
- **THEN** no type error reported for Mapping.get overload

### Requirement: Fix ResultRow assignment mismatch
The system SHALL have proper type handling for ResultRow assignment at line 644 in `app/core/sparql_service.py`.

#### Scenario: Mypy check passes for ResultRow assignment

- **WHEN** mypy runs on `app/core/sparql_service.py`
- **THEN** no type error reported for ResultRow assignment

### Requirement: All mypy errors resolved
The system SHALL have zero mypy errors in `app/core/sparql_service.py`.

#### Scenario: Clean mypy check

- **WHEN** mypy runs on `app/core/sparql_service.py`
- **THEN** zero errors reported (10 errors resolved)

## 1. Relationship inventory and merge plan

- [x] 1.1 Inventory all Work and Manifestation FKs, ORM cascades, association tables, uniqueness constraints, and logical relationships, and verify the inventory against model metadata.
- [x] 1.2 Define canonical reparent/conflict policies for each relationship class, and verify each relationship has a documented policy.
- [x] 1.3 Implement a dry-run merge plan containing every reparent, merge, conflict, and delete operation, and verify representative plans are complete.

## 2. Recovery and transaction safety

- [x] 2.1 Replace the partial core-only snapshot with complete verified recovery coverage or an explicit database-backup prerequisite, and verify restore coverage in a disposable database.
- [x] 2.2 Refuse live mutation when backup coverage or restore verification is incomplete, and verify no rows change in the refusal test.
- [x] 2.3 Apply each approved plan transactionally with integrity checks before commit and rollback on any conflict/failure, and verify injected failures roll back.

## 3. Relationship-complete reconciliation

- [x] 3.1 Reparent Work dependents including parts, expansions, contributions, intents, social records, and audit/provenance links, and verify every fixture remains reachable.
- [x] 3.2 Reparent Manifestation dependents including Items, ImageScans, contributions, social records, and collection links, and verify every fixture remains reachable.
- [x] 3.3 Preserve unique/conflicting records according to the documented policy; never rely on implicit cascade deletion, and verify conflict fixtures abort safely.

## 4. Verification

- [x] 4.1 Add fixtures covering every dependent relationship and verify no records are lost after merge.
- [x] 4.2 Test dry-run write isolation, rollback injection, idempotent reruns, and conflict aborts, and verify database snapshots are unchanged where required.
- [x] 4.3 Run FRBR integrity audit and database migration/ETL regression suites before enabling live mode, and record the release gate results.

## 1. Custody Provenance and Database Support

- [ ] 1.1 Add nullable structured previous-owner and new-owner references to Item custody events, with reversible migration and existing event compatibility; verify migration upgrade/downgrade and legacy event reads.
- [ ] 1.2 Add model/service support for creating a transfer event with Item, from-owner, to-owner, actor, event type, and timestamp; verify model tests confirm previous custody events are unchanged and event references obey account-deletion semantics.
- [ ] 1.3 Add a transactional reassignment service that clears only source-owned collection links, updates owner IDs, and appends one event per Item; verify injected failure rolls back all Item, collection-link, and event writes.

## 2. Authorized Preview and Reassignment API

- [ ] 2.1 Add admin-only discovery and preview endpoints requiring authentication, the `admin` role, and `write:users`, with source/target discovery also requiring `read:users`; verify unauthorized, non-admin-with-permission, and missing-permission tests disclose no Item IDs or counts.
- [ ] 2.2 Validate modes, source/target identities, active target, positive unique physical Item IDs, source ownership, and zero-match cases; verify API tests cover malformed, foreign-owned, missing, virtual/negative IDs and identical/inactive accounts without mutations.
- [ ] 2.3 Return canonical source/target identities, exact count, scope, and deterministic digest for the preview; verify unit/API tests show hidden and lent Items in source-wide counts and selected previews include only requested source-owned Items.
- [ ] 2.4 Implement confirmation against the preview fingerprint, including row locks and serializable all-scope execution; verify stale-set and concurrent-change tests return conflict and preserve every row.
- [ ] 2.5 Return complete success counts or explicit all-or-nothing failures and keep normal Item PUT ownership protection unchanged; verify batch fault-injection tests report zero transfers after rollback and ordinary `owner_id` payload tests still reject changes.

## 3. Administrator Reassignment UI

- [ ] 3.1 Add the admin ownership-management route and source/target account selection, using authorized account discovery and paginated Items filtered by source; verify UI tests hide the route/control without the required admin role and permission.
- [ ] 3.2 Add single-row and selected-batch selection plus a distinct all-Items-by-source action; verify UI tests submit the correct single, selected, and all scopes without including unrelated or virtual IDs.
- [ ] 3.3 Add a preview/review dialog that names source, target, exact count, access changes, source collection-link cleanup, and hidden/lent inclusion, with additional affirmative acknowledgement for all-scope execution; verify tests prevent confirmation on zero results and require acknowledgement for all-scope changes.
- [ ] 3.4 Handle stale preview, conflict, and atomic failure without claiming partial success; invalidate source/target collection, Item, and stats queries after success; verify UI tests show accurate success/failure messages and refresh affected views.

## 4. Integration, Security, and Release Verification

- [ ] 4.1 Add API integration tests for single, selected, and all-item transfers covering custody provenance, preserved Item/lending state, hidden visibility, source collection-link cleanup, and untouched FRBR entities; verify all scenarios pass against the supported database test configuration.
- [ ] 4.2 Add an end-to-end admin workflow test that previews and confirms a transfer, then proves source/target access and collection visibility follow the new owner without exposing the operation to ordinary users; verify the E2E test passes.
- [ ] 4.3 Run focused backend/frontend suites, migration checks, and OpenSpec validation; verify results are green and document any database-isolation or large-catalog constraints before enabling the admin workflow in v0.8.3.

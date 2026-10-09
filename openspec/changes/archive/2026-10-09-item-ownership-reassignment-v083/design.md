## Context

See `proposal.md` for motivation and `specs/item-ownership-reassignment/spec.md` plus `specs/item-custody/spec.md` for the behavior contract.

The physical `Item` row has an `owner_id` foreign key to `User`. The normal item PUT path intentionally blocks `owner_id`; update authorization also permits item owners, borrowers for progress-only changes, administrators, and users with `update:item`, which is too broad for ownership transfer. Administrative user listing already uses `admin` plus `read:users`; permission definitions give `write:users` to the admin role. `ItemCustodyEvent` is documented as append-only, but presently only has an Item, actor, event type, free-text notes, and timestamp, so it cannot represent transfer endpoints as structured data. Collection membership is stored separately through `UserCollectionItem`.

## Goals / Non-Goals

**Goals:**
- Provide one trusted server path and one administrator UI for previewing and confirming single, selected, and all-by-source transfers.
- Bind execution to the reviewed scope, run mutations in one database transaction, and preserve evidence of each ownership change.
- Keep the permission surface narrow and make the new owner/access boundary and effects on source-owned collections explicit.

**Non-Goals:**
- No self-service ownership changes, transfer requests/acceptance, public API, cross-instance transfer, or reassignment of wishlist intents.
- No transfer of personal collection trees, Item status history, notes, tags, or other user records; no FRBR catalog edits.
- No changes to the existing `owner_id` prohibition in ordinary Item update payloads.

## Decisions

1. **Use the existing privileged admin boundary, not `update:item` or a new general permission.** Add dedicated routes under the authenticated admin API surface. Require both the `admin` role and `write:users`; require `read:users` for source/target discovery through the existing user-list API. The UI lives in the admin area and renders only when the same role/permission checks pass. This reuses a privilege already restricted to administrators while preventing custom roles with `write:users` alone from invoking a data-integrity operation. A new permission would require role migration and UI permission-management work without improving the current least-privilege boundary.

2. **Build an admin ownership-management screen around a source account.** The operator chooses an existing source account and an active target account, then searches/pages through Items currently owned by that source. One selected row is the single-Item path; multiple explicitly selected rows are the selected-batch path; a separate “all Items for this source” action covers the complete source set. Do not rely on the normal user's collection page, which only returns the caller's own inventory. Use an explicit review dialog that states source, target, exact count, and the loss/gain of owner access; the all-Items path additionally calls out hidden and lent Items and requires a second affirmative acknowledgement.

3. **Separate preview from execution and bind both to a canonical scope fingerprint.** Admin API preview input contains `mode` (`single`, `selected`, or `all`), source UUID, target UUID, and selected positive Item IDs where applicable. The server validates all inputs, computes matching IDs/count and returns canonical source/target display identities plus a SHA-256 fingerprint over the normalized mode, source, target, and sorted matching IDs. Confirmation resubmits the same scope with expected count and fingerprint. Execution re-queries under the source owner predicate and rejects mismatched IDs/count/fingerprint with HTTP 409; it never trusts client-supplied owner fields or count alone. Missing, duplicate, foreign-owned, negative/virtual, invalid, or inactive-target IDs fail closed without disclosing Item details.

4. **Use one atomic transaction for the whole requested operation.** Lock selected Item rows and re-check their current owner; for `all`, execute the source-scope read and write under serializable isolation so a concurrent insert/reassignment cannot silently expand or shrink a reviewed set. A serialization failure or stale fingerprint returns a retry/re-preview conflict. In the transaction, delete only `UserCollectionItem` links whose collection belongs to the source, update the matching `Item.owner_id` values, and insert one transfer event per changed Item. Any failure rolls everything back; do not chunk into commits or return partial success. Keep the all-scope server-side rather than sending every Item ID from the browser.

5. **Extend custody events with structured nullable owner references.** Add nullable `from_owner_id` and `to_owner_id` UUID foreign keys to `ItemCustodyEvent`, using `ON DELETE SET NULL` to match the existing actor reference's user-deletion behavior and leaving legacy events valid. New reassignment entries use event type `transfer`, record actor and timestamp, and do not place email addresses or free-form user-supplied content in notes. Preserve all existing events and avoid backfilling unknown history. The owner references are captured at transfer time but can be nulled if an account is later deleted, consistent with account-erasure behavior.

6. **Preserve current item state and make privacy effects visible.** Transfer all matching physical Items irrespective of hidden state or status, including `collection_status=lent`; preserve lender/borrower fields, `is_hidden`, status, metadata, tags, and ItemStatusLog rows. The target becomes owner and gains owner-only access; the source loses it. A non-hidden Item may consequently appear on the target's shared/public collection surfaces according to the target account's existing visibility settings; a hidden Item stays hidden. Remove the source's collection links for reassigned Items in the same transaction, but do not create target collection memberships because there is no unambiguous source-to-target collection mapping. Preserve FRBR entities and existing custody/status history.

7. **Keep user lifecycle asymmetry explicit.** A source may be active or inactive so imported records can be recovered from a disabled account; the target must exist and be active so ownership cannot be assigned to an account that cannot access it. Source and target must differ. The source account's admin-visible identity and Item count are only returned after authorization succeeds.

## Risks / Trade-offs

- [A privileged operator can expose previously private inventory to the target] → Require admin plus `write:users`, present exact source/target/count, warn that non-hidden Items follow target profile visibility, and explicitly confirm hidden/lent inclusion for all-scope transfers.
- [Concurrent changes could make a preview misleading] → Compare the complete scope fingerprint at execution, use row locks/serializable isolation, and fail with a re-preview conflict rather than widening scope.
- [A large all-Items transaction can hold locks and consume resources] → Keep processing server-side, avoid per-item commits, surface an explicit busy/conflict response, and measure production-sized transfer duration before rollout. If practical catalog size exceeds safe one-transaction limits, the product must choose a safe operational workflow rather than silently switching to partial commits.
- [Removing source collection links may surprise the source account owner] → State this in the review UI; do not delete collection trees or copy memberships to the target.
- [Lending remains attached while ownership changes] → Preserve borrower/lending fields and clearly disclose that existing loans remain active under the new owner's Item; no implicit return/cancellation is performed.
- [Custody references can be nulled by later account deletion] → Use the established `SET NULL` privacy behavior, keep event actor/time/Item provenance, and test that historical records remain readable.

## Migration Plan

1. Add nullable from/to owner UUID columns for custody events with reversible foreign-key/index migration support; existing event rows remain unchanged and readable.
2. Deploy the guarded admin API and transaction path. Keep ordinary Item mutation authorization and forbidden `owner_id` validation unchanged.
3. Deploy the admin UI after the API is available. Preview and transfer endpoints are unusable by non-admin callers even if UI route checks are bypassed.
4. Validate one-Item and selected/all-scope transfers in a staging copy, including hidden items, lent items, source collection links, rollback injection, and concurrent scope changes before production use.

Rollback removes the UI/API entry point first. Do not attempt to reverse ownership transfers automatically: ownership changes and custody events are meaningful data, and rollback must not erase history. A database downgrade may drop the new nullable columns only after the application no longer reads them and only if no transfer-history retention requirement prevents it; prefer a forward-compatible schema left in place.

## Explicit Assumptions / Product Decisions to Confirm

- “All Items” means every physical Item row for the chosen source, including hidden, lent, lost, wishlist-status, or otherwise non-available Items; negative-ID wishlist intents are excluded.
- Reassignment of a lent Item changes its owner but does not return or cancel the loan; the borrower fields remain as-is.
- Source-owned personal collection links are removed and are not mapped into target collections. Item tags, item state, and existing history remain.
- Inactive source accounts are eligible, but inactive target accounts are not.
- Custody transfer history stores structured user UUID references, not user email/name snapshots; account deletion may null the references under `SET NULL` semantics.

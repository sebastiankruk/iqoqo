## Context

See `proposal.md` for motivation. In iqoqo's FRBR model, personal progress (`status` such as `want_to_read`, `reading`, `read`, `listened`, `watched`, `played`, `built`) lives on `Item` (`F5_Item`), while `UserWorkIntent` tracks wishlist intent on `Work` (`F1_Work`). Rolling up consumption status to `Work` lets a collector immediately know across editions whether they have already read/watched/played a work.

## Goals / Non-Goals

**Goals:**
- Compute `work_reading_status` in `O(1)` batched SQL queries (`GROUP BY work_id, item.status`) rather than N+1 queries.
- Include the user's own `private` (`is_hidden=True`) items when computing their personal rollup (`owner_id == user_id`), while strictly returning `None` for unauthenticated callers or unrelated users.
- Surface clear `"Read"` / `"Read (another edition)"` badges on `/work/[id]`, `/manifestation/[id]`, and `/works/shelf`.

**Non-Goals:**
- Aggregating personal reading status across multiple users onto `Work` (social reviews/averages belong to `SocialFeedback` and `Manifestation.average_reading_minutes`).
- Moving `ReadingTransition` or `reading_sessions` off `Item`.

## Decisions

1. **Pure read-time `GROUP BY` helper `compute_work_reading_rollup(user_id, work_ids)` in `app/core/frbr_service.py`:** Queries `Item` joined with `Manifestation` and `Expression` filtered by `Item.owner_id == user_id` and `Expression.work_id.in_(work_ids)`, returning `{work_id: {"status": ..., "completed_manifestation_ids": [...]}}`. No schema migration needed!
2. **Completed > Active > Intent precedence:** Ranked dictionary (`COMPLETED_STATUSES` > `IN_PROGRESS_STATUSES` > `UNSTARTED_STATUSES` > `dnf`) ensures if a collector finished an audiobook edition and later buys a hardcover unread copy, the `Work` still reflects `"read"` / `"listened"` (with `completed_via_other_edition` checked against the current `manifestation_id`).
3. **Also honor `UserWorkIntent` (`status == "fulfilled"` is superseded by actual `Item` status):** Rollup derives strictly from owned `Item`s (and optionally `UserWorkIntent` only when `status` is explicit wishlist intent if needed, keeping `work_reading_status` strictly about actual reading/consumption).

## Risks / Trade-offs

- **Performance on `/works/shelf` when `limit=1000`:** Batching via single `GROUP BY` over the paginated `work_ids` slice (`<= 100` IDs per page, or `work_ids` returned by `offset`/`limit`) prevents N+1 queries; apply `work_read_status` filter in SQL before pagination when requested.

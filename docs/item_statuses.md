# iQoQo Status Registry

This document defines the canonical item and progress statuses used across the iQoQo ecosystem. These values are used in the backend (`app/db/core.py`) and synchronized with the frontend (`frontend/types/frbr.ts`).

## 1. Inventory Statuses (`COLLECTION_STATUSES`)

These statuses track the physical or ownership state of an item in a collection.

| Status      | Description                                               | Recommended Ordering |
|:------------|:----------------------------------------------------------|:---------------------|
| `wish_list` | The user does not own the item but intends to acquire it. | 1                    |
| `ordered`   | The item has been purchased but not yet received.         | 2                    |
| `available` | The item is in the collection and ready for use.          | 3                    |
| `lent`      | The item is currently lent to another person.             | 4                    |
| `damaged`   | The item is in the collection but is in poor condition.   | 5                    |
| `lost`      | The item was in the collection but is currently missing.  | 6                    |

**Default Value**: `available` (when adding new items via scanner).

---

## 2. Consumption Progress (`PROGRESS_STATUSES`)

These statuses track the user's interaction progress with the content, categorized by media type.

### Generic / Text (Books, Comics)

| Status         | Description                                         |
|:---------------|:----------------------------------------------------|
| `want_to_read` | Alias for `wish_list`, specifically for text media. |
| `reading`      | Content is currently being consumed.                |
| `read`         | Content has been completed.                         |

### Audio (Music, Audiobooks)

| Status           | Description                    |
|:-----------------|:-------------------------------|
| `want_to_listen` | Intended for future listening. |
| `listening`      | Currently listening.           |
| `listened`       | Completed listening.           |

### Video (Movies, Series)

| Status          | Description                  |
|:----------------|:-----------------------------|
| `want_to_watch` | Intended for future viewing. |
| `watching`      | Currently watching.          |
| `watched`       | Completed viewing.           |

### Games (Board Games, Video Games)

| Status         | Description                                       |
|:---------------|:--------------------------------------------------|
| `want_to_play` | Intended for future play sessions.                |
| `playing`      | Currently actively playing.                       |
| `played`       | Has been played (completion varies by game type). |

---

## 3. UI/UX Implementation Notes

- **Sensible Defaults**:
    - **Scanner**: Use `available` + `want_to_read`/`play` based on format.
    - **Wish List**: Use `wish_list` (Collection) + `want_to_read`/`play` (Progress).
- **Ordering**: When displaying status filters or dropdowns, follow the numerical ordering in the tables above to group "active" states (available, reading, playing) before "passive" or "missing" states.

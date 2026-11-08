## Context

LEGO retail boxes carry both a standard 12/13-digit UPC/EAN barcode and a prominent 4-to-6-digit LEGO Set Number (e.g., `10318` / `10318-1`). Rebrickable's API v3 provides rich structured data (`set_num`, `name`, `year`, `theme_id`, `num_parts`, `set_img_url`) and minifig inventories.

## Goals / Non-Goals

**Goals:**
- Support scanning EAN/UPC barcodes on LEGO boxes AND typing LEGO Set Numbers (`10318` or `10318-1`) in `/scan`.
- Store `REBRICKABLE_API_KEY` encrypted at rest with Fernet in `InstanceSettings` and fail gracefully to manual entry with pre-filled EAN/set number if the key is unconfigured or lookup fails.
- Render piece counts, minifig counts, themes, and physical build statuses (`sealed | built | incomplete | parted_out`) cleanly in the UI.

**Non-Goals:**
- Part-by-part individual loose brick inventory management.

## Decisions

### Set Number Normalization (`10318` $\to$ `10318-1`)
* **Decision:** If a user enters a bare 4–6 digit set number (`10318`) with `media_type="lego"`, normalize it to `10318-1` when querying Rebrickable `/api/v3/lego/sets/{set_num}/`, while also supporting text search disambiguation.
* **Rationale:** Collectors almost always type the box front number (`10318`) without the `-1` edition suffix used by Rebrickable.

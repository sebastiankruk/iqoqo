# stateless-ai-covers Specification

## Purpose
TBD - created by archiving change container-script-hardening. Update Purpose after archive.
## Requirements
### Requirement: Stateless AI Cover Generation
The Docker image MUST remain stateless. The `generate_ai_covers.py` script MUST write generated images to a local directory (`app/static/covers/`) that is mounted as a persistent Docker volume at runtime. Additionally, the script MUST optionally cache and retrieve generated covers from an S3 global cache via `rclone`.

#### Scenario: Running the cover generation script

- **WHEN** the `generate_ai_covers.py` script successfully generates an image
- **THEN** it saves the image to the local mounted Docker volume
- **THEN** it optionally checks for `RCLONE_COVERS_REMOTE` and uses `rclone copy` to push the cover to the global cache, emitting a warning instead of an error if not configured
- **AND** it attempts to pull from this global cache via `rclone` before generating a new LLM cover

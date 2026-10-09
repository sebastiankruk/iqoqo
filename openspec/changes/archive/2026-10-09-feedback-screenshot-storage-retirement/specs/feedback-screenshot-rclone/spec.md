## MODIFIED Requirements

### Requirement: Feedback screenshots stored via rclone

The system SHALL store feedback ticket screenshots on the local filesystem under `app/static/gallery/`, and SHALL NOT copy them to remote object storage at runtime. The screenshot serving path is local-only.

The directory is a host bind mount, mounted into `web` and `worker` by the Compose stack and read-only into nginx, so it survives container replacement and `docker compose down`. It is not container-local storage and requires no remote copy for durability. Off-site durability is provided by the nightly host backup, whose `ASSET_PATHS` already includes `app/static/gallery`.

Configuration comes from no storage variable: there is no bucket to configure, and no environment variable selects a remote destination for screenshots.

> The capability name retains "rclone" for requirement-identifier continuity, as `devops-infrastructure-updates` also did when it replaced rclone with boto3. The requirement no longer concerns remote storage; `infrastructure/devops-v082` carries the current backend description.

#### Scenario: Attaching a screenshot to a feedback ticket

- **WHEN** a user attaches a screenshot to a feedback item
- **THEN** the system SHALL save the file to the local gallery directory
- **AND** a filename that is not a single safe path component SHALL be rejected before the file is saved
- **THEN** ticket creation SHALL succeed
- **AND** the system SHALL NOT enqueue any background upload task
- **AND** the system SHALL NOT require any object-storage configuration to be present

#### Scenario: Retrieving a feedback screenshot

- **WHEN** the API serves a feedback item with an attached screenshot
- **THEN** the system SHALL read the file from the local gallery directory
- **AND** it SHALL return a URL that resolves to the screenshot
- **AND** the system SHALL NOT attempt a remote read on any code path

#### Scenario: Uploading a feedback screenshot

- **WHEN** a user attaches a screenshot to a feedback item
- **THEN** the system SHALL store the screenshot in the local gallery directory
- **AND** a filename that is not a single safe path component SHALL be rejected before the file is stored
- **AND** the system SHALL NOT upload the screenshot to any remote bucket
- **AND** the system SHALL NOT enqueue a background upload task, and SHALL NOT require AWS credentials or a bucket name to be configured

#### Scenario: rclone remote not configured — graceful fallback

- **WHEN** a user attaches a screenshot to a feedback item
- **AND** no remote storage is configured
- **THEN** the system SHALL store the screenshot locally and serve it successfully
- **AND** the system SHALL NOT log a warning about a skipped remote upload, since no remote path exists to skip
- **AND** ticket creation SHALL succeed

#### Scenario: Missing object and unreachable storage are distinguished

- **WHEN** a screenshot cannot be served
- **THEN** the system SHALL return 404 for an absent file
- **AND** the system SHALL NOT return a 502, because there is no remote backend whose unavailability could produce one
- **AND** a caller SHALL NOT be able to infer any storage-backend state from the response

#### Scenario: No storage configuration required

- **WHEN** a user attaches a screenshot to a feedback item
- **AND** no object-storage configuration of any kind is present
- **THEN** the system SHALL save and serve the screenshot from local storage
- **AND** ticket creation and retrieval SHALL both succeed
- **AND** the system SHALL NOT emit a warning about skipped remote storage, because there is no remote storage to skip

#### Scenario: Screenshot missing from local storage

- **WHEN** the API is asked to serve a screenshot that is not present in the local gallery directory
- **THEN** the system SHALL return 404
- **AND** the system SHALL NOT attempt a remote fallback
- **AND** the absence SHALL NOT be reported as a storage-service failure
- **AND** a failure to reach any storage backend SHALL NOT be distinguishable from an absent object, because there is no remote backend to reach

#### Scenario: Screenshots are already covered off-site

- **WHEN** a screenshot has been saved to the local gallery directory
- **THEN** the nightly backup SHALL include it in the archive without any application-level upload

### Requirement: Feedback screenshot access authorization containment

The API SHALL enforce that access to an attachment screenshot is granted only if the authenticated user has read authorization for every ticket that references that attachment filename, preventing unauthorized access via cross-ticket collision.

The check runs before any file read, so an unauthorized caller cannot learn whether a screenshot exists.

#### Scenario: Authorized user reads own screenshot

- **WHEN** an authenticated user requests a screenshot referenced only in tickets they own or are authorized to read
- **THEN** the API SHALL serve the screenshot file with status 200

#### Scenario: Unauthorized access blocked across ticket collision

- **WHEN** an authenticated user requests a screenshot referenced in a ticket they can read, but the same screenshot filename is also referenced in another ticket they are not authorized to read
- **THEN** the API SHALL deny access with status 403 Forbidden
- **AND** it SHALL NOT read the file

#### Scenario: Unauthorized caller cannot distinguish present from absent

- **WHEN** an unauthorized user requests a screenshot filename
- **THEN** the response SHALL be identical whether or not the file exists on disk
- **AND** the authorization decision SHALL NOT depend on a storage lookup
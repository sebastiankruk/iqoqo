## Purpose

Corrects the image-size requirement that `devops-infrastructure-updates` could
not meet. The build itself was delivered and verified; only the size figure is
changed, because publishing an unmet target as a requirement would make the
specification actively wrong.

## MODIFIED Requirements

### Requirement: Docker Build Optimization

The Docker image build process MUST use a multi-stage build that isolates
compilers and development headers from the runtime image, and MUST install
pre-built wheels rather than compiling in the runtime stage.

The numeric size target is enforced by a build gate tracked in
`infrastructure/container-image-size`, whose value reflects what the current
dependency set supports. C17 measured 826.7 MB, down from 1019.2 MB.

#### Scenario: Building the production image

- **WHEN** the production Dockerfile is built
- **THEN** the builder stage SHALL contain the compilers and development headers
- **AND** the runtime stage SHALL contain neither
- **AND** the runtime SHALL install from the wheel directory with `--no-index`, so it can neither download nor silently compile a source distribution

#### Scenario: Build artifacts do not enter the image

- **WHEN** the wheels are transferred from the builder stage to the runtime stage
- **THEN** they MUST NOT be transferred with a `COPY` that creates an image layer
- **AND** they MUST be removed within the same step that consumes them, or mounted so they never enter a layer

The second scenario is not hypothetical. C17's first rewrite used
`COPY --from=builder /wheels /wheels` followed by `rm -rf /wheels`, which left the
wheels in the image permanently: a `COPY` creates a layer, and a later deletion
only shadows it. That build measured 1062.6 MB — larger than the 1019.2 MB it was
meant to shrink.

#### Scenario: Measured size is recorded, not asserted

- **WHEN** a build is measured
- **THEN** the figure reported SHALL come from the built image
- **AND** any figure published as a target SHALL be one the image satisfies
- **AND** lower targets SHALL be tracked as open work in a change, not published as met

#### Scenario: A size regression is caught at build time

- **WHEN** a future change grows the image past the enforced target
- **THEN** the build SHALL fail
- **AND** the failure output SHALL identify which part of the image grew

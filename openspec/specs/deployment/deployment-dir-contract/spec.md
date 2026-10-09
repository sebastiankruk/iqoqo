# deployment-dir-contract Specification

## Purpose

Requirements for a source-free iqoqo deployment directory: the files it must
contain, the files it must not symlink, how it becomes self-contained, how its
env file is resolved, how mount problems are caught before they become
root-owned directories, and how it is maintained.

A deployment directory holds the compose files, one env file, and mounted data.
It does not hold application sources.

## Requirements

### Requirement: A Deployment Directory Is Self-Contained
The runtime files a deployment executes MUST exist inside the deployment directory as real files, and MUST NOT be symlinks that resolve outside it.

#### Scenario: A runtime file is a symlink into a working tree

- **WHEN** a deployment directory contains `scripts`, `deploy/nginx.conf`, or an ontology path as a symlink resolving outside the directory
- **THEN** the validator MUST report it, naming the path and its target
- **THEN** the deploy MUST NOT proceed without an explicit acknowledgement

#### Scenario: A symlink stays inside the deployment directory

- **WHEN** a symlink resolves to another path within the same deployment directory
- **THEN** the validator MUST accept it, because sharing one directory between instances is legitimate

#### Scenario: The originating checkout is moved away

- **WHEN** the directory a deployment was deployed from is renamed, moved or deleted
- **THEN** the running deployment MUST continue to serve traffic unchanged

#### Scenario: The deployed code is inspectable

- **WHEN** an operator asks what code a deployment is running
- **THEN** the sync step MUST have printed a manifest of synced paths with content hashes
- **THEN** a verify command MUST be able to report drift from that manifest

### Requirement: Runtime Files Are Synced At Deploy Time
The deploy path MUST copy the runtime files the containers execute or read into the deployment directory before `compose up`.

#### Scenario: Deploying into an empty directory

- **WHEN** a deployment directory contains only an env file
- **THEN** the sync step MUST create the compose files, the runtime files and the mount source directories
- **THEN** `compose up` MUST then succeed without the operator creating anything by hand

#### Scenario: Syncing is idempotent

- **WHEN** the sync step runs twice with unchanged sources
- **THEN** the second run MUST report no changes

#### Scenario: A source file is removed

- **WHEN** a previously synced file no longer exists upstream
- **THEN** the sync step MUST remove the stale copy from the deployment directory

### Requirement: One Env File Describes A Deployment
Every tool that reads a deployment's configuration MUST resolve the env file from the deployment directory, so the deploy path and the diagnostic path cannot disagree.

#### Scenario: Status inspects a deployment

- **WHEN** a status or diagnostic command inspects a deployment directory
- **THEN** it MUST read the env file inside that deployment directory
- **THEN** it MUST NOT fall back to an env file in the shell's current directory or an unrelated checkout

#### Scenario: The two paths are compared

- **WHEN** a deployment is up and a status command inspects it
- **THEN** every value the status command reports MUST come from the env file that deployment was started with

#### Scenario: A stack spans two env files today

- **WHEN** the deploy path and a diagnostic path currently reference different env files for the same stack
- **THEN** the change MUST remove the duplication rather than documenting it

### Requirement: Mount Problems Are Caught Before Deploy
The deploy path MUST validate every bind-mount source before `compose up`, and MUST NOT let Docker create a mount source implicitly.

#### Scenario: A file target is a directory

- **WHEN** a bind mount whose source must be a file resolves to a directory
- **THEN** the deploy MUST abort and name the path
- **THEN** it MUST NOT attempt to remove or replace the directory, because its contents may be real state

#### Scenario: A directory mount source is absent

- **WHEN** a bind mount whose source is a directory does not exist
- **THEN** the deploy MUST create it with the application user's ownership and an explicit mode
- **THEN** the created path MUST NOT be owned by root

#### Scenario: Several problems at once

- **WHEN** more than one mount problem exists
- **THEN** the validator MUST report all of them in a single pass

### Requirement: Guards Apply On Every Deploy Path
A guard implemented for one deploy path MUST apply to all of them.

#### Scenario: Deploying through the Makefile

- **WHEN** a deployment is started through a Makefile target rather than the main script
- **THEN** secrets files MUST be tightened and mount sources MUST be validated exactly as they are on the script path

#### Scenario: The two paths diverge

- **WHEN** a guard exists on one deploy path but not the other
- **THEN** the guard MUST be factored so both paths share it

### Requirement: Ontology Validation Runs In A Deployment
The migration step's ontology check MUST read a file that is actually present, and MUST report clearly when it cannot.

#### Scenario: The ontology source is absent

- **WHEN** the ontology check cannot read its source file
- **THEN** it MUST report that the ontology source is unavailable
- **THEN** it MUST NOT report ontology drift, because the absence of the file is not drift
- **THEN** it MUST NOT exit successfully while appearing to have validated

#### Scenario: The ontology source is present

- **WHEN** the ontology files are available to the migration service
- **THEN** the drift check MUST run against them and its result MUST be reflected in the deploy outcome

#### Scenario: Real drift

- **WHEN** the models and the ontology genuinely disagree
- **THEN** the check MUST fail the migration step rather than warn and continue

### Requirement: Deployment Directories Are Maintained
A deployment directory MUST have a documented maintenance command that reports debris before removing anything.

#### Scenario: Debris is present

- **WHEN** a deployment directory contains files no deploy step creates
- **THEN** the maintenance command MUST report them, naming each path
- **THEN** it MUST NOT remove a file whose purpose it cannot establish without being told

#### Scenario: Env snapshots accumulate

- **WHEN** a deployment directory holds more env snapshots than the configured retention
- **THEN** the maintenance command MUST offer to prune the oldest beyond that count
- **THEN** it MUST warn that the snapshots contain secrets before removing them

#### Scenario: Data directories are mistaken for debris

- **WHEN** a directory holds mounted application data
- **THEN** the maintenance command MUST recognise it as data and never offer to remove it

# Phase 6 — Archive Manager

## Purpose

Phase 6 adds a safe, composable, one-way archival workflow on top of the Phase 3 durable Job Engine and Phase 4 Transfer Manager.

Canonical flow:

```text
DISCOVER
  ↓
HASH
  ↓
DUPLICATE CHECK
  ↓
POLICY EVALUATION
  ↓
DRY-RUN
  ↓
EXPLICIT AUTHORIZATION
  ↓
QUEUE / ARCHIVE JOB
  ↓
TRANSFER
  ↓
VERIFY
  ↓
INDEX / AUDIT
```

## Implementation

` teldrive_lab/archive.py ` provides:

- deterministic `ArchivePolicy`
- SHA-256 hashing of local archive candidates
- informational duplicate detection using size + SHA-256
- conflict detection without overwrite
- protected-boundary evaluation through central safety policy
- stable SHA-256 archive-plan digest
- `ArchiveExecutor` using only the Phase 4 `TransferManager`
- mandatory post-transfer verification
- durable `ARCHIVE` job adapter with bounded retry classification

The archive source is deliberately restricted to `SourceType.LOCAL` in the initial implementation. This keeps the first archival workflow one-way and prevents accidental archive chaining from TelDrive/Telegram back into the archive engine.

## Safety rules

1. Planning never mutates storage.
2. Hashing reads source content but does not alter it.
3. Duplicate detection is informational and never deletes or merges anything.
4. Existing destinations are conflicts; overwrite is not implicit.
5. Production-protected destinations are blocked by the central safety layer even if a caller attempts to authorize them.
6. Applying a plan requires explicit, scope-bound authorization through Phase 4.
7. Every successful archive transfer must pass SHA-256 verification.
8. Source files are retained. Local deletion/cleanup is not part of Phase 6.
9. Two-way synchronization is deferred.
10. AI is not an authorization or storage authority.

## CLI

Dry-run:

```text
 td archive --source-type LOCAL --source-id <id> --archive-root <root> --dry-run
```

Explicit Lab-only apply:

```text
 td archive --source-type LOCAL --source-id <id> --archive-root <root> --apply
```

The CLI refuses plans containing blocked, conflicting, or duplicate items before execution.

## Host gate

`scripts/phase6_host_gate.py` uses only temporary Lab-owned data and proves:

- deterministic plan generation
- SHA-256 discovery
- isolated transfer and verification
- source preservation
- protected production destination blocking
- informational duplicate detection
- zero production storage mutation

No real TelDrive, Telegram, rclone mount, production database, or production container is used by the gate.

## Exit criteria

- archive planner is deterministic and reviewable
- local source restriction is enforced
- SHA-256 is computed and included in the plan
- duplicate detection cannot trigger deletion
- conflicts cannot trigger overwrite
- production boundary blocks unsafe destinations
- application uses Phase 4 transfer authorization
- successful archive copies are verified
- durable ARCHIVE executor exists
- CLI dry-run/apply boundary exists
- host gate passes with no production mutation

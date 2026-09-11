# Phase 9 — Scheduled Backups & Snapshots

**Status: implementation complete; CI and host gate are the final acceptance gates.**

Phase 9 adds a Lab-owned backup/snapshot control plane without making TelDrive Lab the owner of production storage.

## Architecture

```text
persistent schedule
       ↓
durable JobStore BACKUP job
       ↓
PLAN → EXPLICIT AUTHORIZATION
       ↓
TransferManager
       ↓
SHA-256 verification
       ↓
deterministic manifest + durable metadata
       ↓
retention / reconciliation / restore
```

## Components

- `teldrive_lab/backups.py` — planner, manifest, durable metadata, scheduler, executor, verification, reconciliation, retention and restore.
- `BackupStore` — Lab-owned SQLite metadata at runtime; never TelDrive/PostgreSQL state.
- `BackupScheduler` — persists source/destination/interval/next-run state and creates durable `BACKUP` jobs when due.
- `BackupPlanner` — read-only deterministic planning and SHA-256 discovery.
- `BackupExecutor` — transfers only through Phase 4 `TransferManager` and requires an authorization receipt.
- `scripts/phase9_host_gate.py` — isolated end-to-end gate.

## Snapshot semantics

A snapshot is a deterministic manifest-backed backup plan. Snapshot plans use the same verified transfer boundary and a longer default retention period. The manifest records source, destination, size and SHA-256 plus the plan digest and retention timestamp.

No content-addressable storage, hard-link tricks, database snapshots, or production filesystem snapshots are required in this phase.

## Retention

`effective_retention = max(retention, safety_window)`.

Therefore a caller cannot accidentally configure a zero retention period and bypass the safety window. Locked backup records are never retention-ready.

Purging is explicit, authorization-scoped, and uses the central safety policy. There is no automatic destructive deletion in the scheduler.

## Restore

Restore is always:

1. verify the backup copy against its recorded SHA-256;
2. reject an existing destination;
3. require an explicit transfer authorization receipt;
4. transfer through `TransferManager`;
5. verify the restored destination SHA-256;
6. retain the backup copy.

A failed or corrupted backup is never treated as a valid restore source.

## Recovery and reconciliation

`BackupExecutor.reconcile()` is read-only. It reports `VERIFIED`, `CORRUPT`, or `MISSING` from the durable manifest evidence and actual destination state.

This makes interrupted backup runs diagnosable without mutating the source or silently repairing state.

## Job integration

Scheduled runs create durable `BACKUP` jobs through the existing Phase 3 `JobStore`. The scheduler itself does not perform the transfer. Worker execution remains the responsibility of the existing durable job/worker architecture.

## Safety boundary

Phase 9 does **not**:

- modify TelDrive's database;
- modify PostgreSQL;
- modify Telegram storage;
- reconfigure rclone;
- change mounts or Docker;
- delete production files;
- automatically purge backups;
- require paid cloud storage.

All mutation continues to flow through the established safety and authorization layers.

## Acceptance criteria

- deterministic backup plans and SHA-256 manifests
- durable schedule metadata
- durable `BACKUP` job creation
- verified backup transfer
- corruption and missing-copy detection
- no-overwrite restore
- verified restore
- retention safety window
- locked backup protection
- explicit purge only
- audit events
- isolated host gate
- zero production storage mutation

# R4 — Durable Execution Reconciliation

R4 reconciles the durable Job Engine with the mutation, backup, lifecycle, verification, rclone, and audit boundaries.

## Control path

```text
JobStore
   ↓ claim + lease
Worker
   ↓ deterministic safety decision
DispatchingExecutor
   ├─ UPLOAD / DOWNLOAD → TransferJobExecutor → TransferManager
   ├─ ARCHIVE           → ArchiveJobExecutor → TransferManager
   ├─ ORGANIZE          → OrganizationJobExecutor → TransferManager
   ├─ BACKUP / SNAPSHOT → BackupJobExecutor → BackupExecutor → TransferManager
   ├─ CLEANUP / RESTORE → LifecycleJobExecutor → LifecycleExecutor → TransferManager
   └─ VERIFY            → VerificationJobExecutor → read-only checksum verification
   ↓
verified execution
   ↓
RUNNING → VERIFYING → COMPLETED
   ↓
Audit evidence
```

The worker remains the only durable execution coordinator. The dispatcher selects an adapter; it never authorizes a mutation. Domain executors continue to use the central safety and transfer boundaries.

## Durable state guarantees

- `update_progress()` persists bounded `0..1` progress and is worker-fenced.
- `begin_verification()` persists `RUNNING → VERIFYING` and keeps the worker lease.
- `complete_verification()` permits `VERIFYING → COMPLETED` only for the owning worker.
- lease recovery covers both `RUNNING` and `VERIFYING` states.
- cancellation and retry are fenced for `VERIFYING` as well as `RUNNING`.
- completion is committed only after the executor reports verified success.

## Reconciled adapters

R4 now has durable Worker-facing executors for:

- transfer (`UPLOAD`, `DOWNLOAD`);
- archive and organization;
- backup and snapshot;
- lifecycle quarantine/restore (`CLEANUP`, `RESTORE`);
- non-destructive checksum verification (`VERIFY`);
- the existing rclone adapter through an explicit `RcloneTransferBackend` with a post-copy `rclone check` verification boundary.

The rclone backend is opt-in when constructing `DurableExecutionRegistry`; the default test/runtime registry remains local and cannot silently switch production transport.

## Evidence gate

`scripts/r4_durable_execution_gate.py` uses only disposable local fixtures. It proves:

1. one Worker/JobStore execution boundary;
2. durable progress and worker fencing;
3. persisted `VERIFYING` state;
4. backup execution and checksum verification;
5. lifecycle quarantine without source deletion;
6. read-only checksum verification;
7. rclone copy + post-copy check through an injected runner;
8. audit evidence and production boundary protection;
9. no TelDrive production mutation.

CI runs the R4 gate after R3 and before the legacy phase gates.

## Safety and cost

- No direct TelDrive PostgreSQL writes.
- No production rclone/TelDrive mutation in gates.
- rclone configuration and systemd units are never modified by the adapter.
- No paid dependency or service.
- Existing protected-path authorization remains authoritative.

# R4 — Durable Execution Reconciliation

R4 closes the execution-path gap between the durable Job Engine and the Phase 4–6 mutation adapters.

## Control path

```text
JobStore
   ↓ claim + lease
Worker
   ↓ deterministic safety decision
DispatchingExecutor
   ├─ UPLOAD / DOWNLOAD → TransferJobExecutor → TransferManager
   ├─ ARCHIVE           → ArchiveJobExecutor  → TransferManager
   └─ ORGANIZE          → OrganizationJobExecutor → TransferManager
   ↓
verified execution
   ↓
RUNNING → VERIFYING → COMPLETED
   ↓
Audit evidence
```

The worker remains the only durable execution coordinator. The dispatcher selects an adapter; it never authorizes a mutation. Existing adapters continue to use the central safety and transfer boundaries.

## Durable state guarantees

- `update_progress()` persists bounded `0..1` progress and is worker-fenced.
- `begin_verification()` persists `RUNNING → VERIFYING` and keeps the worker lease.
- `complete_verification()` permits `VERIFYING → COMPLETED` only for the owning worker.
- lease recovery covers both `RUNNING` and `VERIFYING` states.
- cancellation and retry are fenced for `VERIFYING` as well as `RUNNING`.
- completion is committed only after the executor reports verified success.

## Scope

R4 integrates the existing transfer, archive, and organization durable adapters into one Worker-facing dispatcher. Job types without an installed executor are rejected as `UNSUPPORTED_JOB_TYPE` without invoking a side effect.

Backup, snapshot, lifecycle, verification, indexing, and restore remain explicit job types in the durable model, but they are not falsely claimed as operational executors merely because their domain primitives exist. They require dedicated adapters before being registered here.

## Evidence gate

`scripts/r4_durable_execution_gate.py` uses only a disposable local fixture. It proves:

1. one Worker/JobStore execution boundary;
2. durable progress and worker fencing;
3. persisted `VERIFYING` state;
4. checksum-verified completion;
5. audit evidence for claim, safety, verification, and completion;
6. unsupported work has no side effect;
7. no TelDrive production mutation.

CI runs the R4 gate after R3 and before the legacy phase gates.

## Safety and cost

- No direct TelDrive PostgreSQL writes.
- No production rclone/TelDrive mutation.
- No shell execution added.
- No paid dependency or service.
- Existing protected-path authorization remains authoritative.

# Phase 4 — Transfer Manager

**Status:** implementation complete; controlled exit gate defined  
**Cost:** ₹0 / $0  
**Production execution:** intentionally not performed during implementation

## Goal

Provide one controlled transfer layer over Lab-owned local files and the existing TelDrive/rclone interfaces without creating a second storage authority or weakening the production safety boundary.

## Implemented

### 1. Controlled transfer core

`teldrive_lab/transfer.py` provides:

- explicit `TransferSpec`
- read-only `plan()`
- `COPY` transfer kind
- central safety authorization before filesystem mutation
- scoped `AuthorizationReceipt` support
- atomic temporary-file staging
- `fsync()` before publication
- metadata preservation
- optional progress callbacks
- SHA-256 source/destination verification
- cleanup of failed partial files
- no overwrite unless explicitly requested

A checksum mismatch never publishes the temporary destination.

### 2. Durable Job Engine integration

`teldrive_lab/transfer_executor.py` provides `UPLOAD` and `DOWNLOAD` job execution through `TransferManager`.

The executor does not self-authorize. The worker obtains authorization from an external provider and passes the receipt through the deterministic safety boundary.

Failure classes are mapped conservatively:

```text
protected / unauthorized → UNSAFE
invalid input / resource limit → PERMANENT
checksum mismatch → RETRYABLE / integrity
other transfer failure → RETRYABLE / transient
success → SUCCESS
```

### 3. Bounded retries

`teldrive_lab/retry.py` provides:

- transient classification
- rate-limit classification
- integrity classification
- permanent classification
- unsafe classification
- bounded exponential backoff
- optional jitter

The durable Job Store remains responsible for attempt counting and terminal failure after `max_attempts`.

No unsafe or permanent failure is blindly retried.

### 4. Resource-aware concurrency

`teldrive_lab/concurrency.py` provides process-local admission control with:

- bounded worker count
- bounded in-flight bytes
- deterministic rejection when a transfer exceeds the byte budget

These limits do **not** alter existing rclone, FUSE, Docker, or TelDrive configuration.

The default is intentionally conservative for the host's roughly 8 GB RAM profile.

### 5. Reconciliation

`teldrive_lab/reconcile.py` provides a read-only local reconciliation primitive for:

- existence
- size
- SHA-256
- verification state

Reconciliation can be used after restart or failure to determine whether a destination already satisfies expected postconditions before another mutation is attempted.

### 6. rclone adapter boundary

`teldrive_lab/rclone.py` provides a narrow subprocess adapter for the **existing** rclone installation.

Properties:

- argument-list execution; no shell interpolation
- `copyto` only in this phase
- explicit retry bounds at the command boundary
- dry-run support
- injected runner for tests
- central authorization for mutation
- no configuration writes
- no systemd changes
- no automatic remounting
- no automatic installation

The adapter is an integration boundary, not a replacement for the existing rclone setup.

### 7. Controlled host gate

`scripts/phase4_host_gate.py` validates the Phase 4 boundary entirely in a temporary directory.

It checks:

- real local transfer
- checksum verification
- progress reporting
- durable UPLOAD job execution
- protected production-path denial before executor invocation
- rclone dry-run command construction

It deliberately performs no live TelDrive or rclone mutation.

## Recovery model

Phase 4 does not claim arbitrary byte-level resumability for local copies. Instead it uses safe recovery primitives:

```text
job lease
  ↓
transfer attempt
  ↓
atomic temporary destination
  ↓
checksum verification
  ↓
atomic publication
```

If the process dies before publication, the authoritative destination is not falsely marked complete. A later reconciliation can inspect the destination and the durable job state before another attempt.

For rclone-backed transfers, provider/backend-level resumability is treated as an implementation detail and is not assumed by the completion invariant. Completion still requires successful execution and verification appropriate to the workflow.

## Rate-limit and network behavior

The retry layer distinguishes rate-limited failures from ordinary transient failures. Backoff is bounded and the durable job store owns retry scheduling.

Network loss does not cause a destructive fallback. The job remains durable and is retried only when the worker's normal safety and scheduling rules permit it.

## Safety invariants

1. Safety is checked before filesystem mutation.
2. Protected production mutation is denied even with a valid authorization receipt.
3. Authorization is operation- and path-scoped.
4. Workers never self-authorize.
5. A successful transfer requires post-transfer verification.
6. Temporary partial files are not treated as completed destinations.
7. Retry classification never converts unsafe/permanent failures into automatic mutation.
8. Concurrency limits are bounded and local to the Lab process.
9. The existing TelDrive/rclone configuration remains outside Lab ownership.
10. No live production transfer is required to pass the implementation tests.

## Phase 4 exit gate

Phase 4 is considered implementation-complete when all of the following are true:

- [x] upload/download job boundary exists
- [x] bounded concurrency exists
- [x] progress reporting exists
- [x] retry classification exists
- [x] bounded exponential backoff exists
- [x] rate-limit class exists
- [x] checksum-aware verification exists
- [x] atomic local transfer publication exists
- [x] read-only reconciliation exists
- [x] rclone adapter boundary exists
- [x] protected production mutation remains hard-denied
- [x] authorization remains external and scoped
- [x] controlled host-gate fixture exists
- [x] CI coverage exists for the transfer layer
- [x] no live TelDrive/rclone mutation was required

The next implementation phase may therefore build deterministic organization on top of this transfer boundary without bypassing it.

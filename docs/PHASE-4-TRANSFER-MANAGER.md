# Phase 4 — Transfer Manager

## Status

**Implementation foundation complete; execution remains authorization-gated.**

Phase 4 provides one controlled transfer boundary for local file movement. The backend is intentionally narrow and verifies every completed local copy with SHA-256. Production TelDrive/rclone mutation is not silently enabled.

## Contract

The Transfer Manager owns transfer planning and execution coordination. It does not become a storage authority and does not self-authorize mutations.

```text
PLAN
 ↓
DRY-RUN / REVIEW
 ↓
EXPLICIT AUTHORIZATION
 ↓
EXECUTE
 ↓
SHA-256 VERIFY
 ↓
AUDIT (when invoked through the Job Engine)
```

## Implemented

- immutable `TransferSpec`
- immutable `TransferPlan`
- backend protocol for future rclone/TelDrive adapters
- local copy backend
- explicit authorization parameter
- protected production boundary enforcement through the central safety policy
- destination-exists protection unless overwrite is explicitly requested
- SHA-256 source/destination verification
- byte-count result reporting
- deterministic failure results rather than hidden exceptions

## Authorization boundary

A transfer job, worker lease, or plan does not constitute authorization.

Lab-owned mutation requires the higher-level workflow to explicitly authorize the transfer. Even explicit authorization cannot override the protected production boundary enforced by `safety.py`.

This means a request targeting `~/TelegramRaw`, `~/TelegramDrive`, `~/teldrive`, or other protected state remains denied by the central policy.

## Idempotency and reconciliation

The first backend uses a conservative destination policy:

- absent destination → eligible for authorized copy
- existing destination + no overwrite → fail without mutation
- existing destination + overwrite → requires explicit authorization and remains subject to production protection
- post-copy checksum mismatch → transfer is not considered successful

Future resumable/rclone backends must preserve these semantics and add reconciliation before retrying a partially completed transfer.

## Resource discipline

The implementation uses bounded 1 MiB hashing chunks and does not load whole files into memory. Concurrency is intentionally absent until benchmarking establishes safe limits for the ~8 GiB host.

## Production boundary

The Phase 4 manager does **not** modify existing Telegram data, TelDrive, PostgreSQL, rclone configuration, Docker state, DNS, or mounts merely by being installed.

A future rclone/TelDrive adapter must pass the same policy boundary and must not infer authorization from a remote name such as `teldrive:` or `teldrive-crypt:`.

## Remaining Phase 4 integration work

The core transfer contract is now established. The remaining integration work is to add bounded queue integration, retry classification, network interruption handling, and approved rclone/TelDrive adapters only after their safety semantics are explicitly specified and tested.

## Exit criteria

Phase 4 is complete only when:

- upload/download jobs use the shared Transfer Manager rather than ad-hoc copy commands;
- bounded concurrency is benchmark-derived;
- transient/rate-limit/integrity failures map to Job Engine retry classes;
- interrupted transfers reconcile safely;
- approved rclone/TelDrive interfaces are wrapped without bypassing safety;
- successful transfer jobs require verification before completion.

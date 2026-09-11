# Phase 3 — Durable Job Engine

## Status

Implementation is in progress. Phase 3 now has a durable SQLite job store, lifecycle/audit support, and a worker coordination boundary. The worker does not execute storage operations itself and does not mutate TelDrive production.

## Contract

The Job Engine owns workflow state, not storage. A job records intent and execution state; a worker coordinates one claimed job and delegates actual side effects to a narrow executor boundary.

### Durable properties

- SQLite persistence under Lab-owned runtime state.
- Stable job IDs.
- Explicit job types and states.
- Worker leasing with expiration.
- Restart recovery for expired leases.
- Bounded retry attempts.
- Retry scheduling through `retry_at`.
- Cooperative cancellation state.
- Worker ownership checks on completion, retry, and lease renewal.
- Parent-job relationships for future workflows.
- Priority ordering without bypassing safety.
- Completion records 100% progress only after the worker explicitly completes the job.

## Worker boundary

`teldrive_lab/worker.py` provides:

- `JobExecutor` protocol as the only side-effect boundary.
- `ExecutionResult` and explicit execution statuses.
- `Worker.run_once()` for one durable claim/execute cycle.
- deterministic safety evaluation before executor invocation.
- worker lifecycle audit events.
- retryable, permanent, unsafe, and cancelled result handling.
- executor-exception recovery without stranded leases.

The worker deliberately never passes explicit authorization to the safety policy. Job existence, worker ownership, or a valid lease can never authorize a mutation.

For this phase, production transfer/mutation jobs are therefore blocked before the executor is called. Lab-only read/index fixtures may use the executor abstraction for testing.

## Current implementation excludes

- direct production file transfer execution
- automatic mutation of TelDrive paths
- automatic deletion or organization
- Telegram API calls
- background daemons
- hidden retries
- worker-generated authorization
- production-facing job execution

## Phase 3 sequence

1. Durable job store and state transitions. — complete
2. Lease/recovery and bounded retry tests. — complete
3. Audit integration and lifecycle tests. — complete
4. Idempotency/reconciliation contract. — complete
5. Worker abstraction with explicit safety checks. — implemented
6. Cooperative cancellation and pause/resume semantics.
7. Parent/child workflow orchestration.
8. Controlled host validation using only Lab-owned test fixtures.
9. Gate before any production-facing job execution.

## Safety invariant

A queued job is not authorization. A worker lease is not authorization. A successful job state is not proof of archival success. Production mutation remains governed by the existing `PLAN → DRY-RUN → EXPLICIT AUTHORIZATION → EXECUTE → VERIFY → AUDIT` lifecycle.

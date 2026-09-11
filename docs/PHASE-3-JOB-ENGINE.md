# Phase 3 — Durable Job Engine

## Status

Implementation started. The first Phase 3 slice adds a durable SQLite job store and focused tests. It does not execute transfers or mutate TelDrive production.

## Contract

The Job Engine owns workflow state, not storage. A job records intent and execution state; a worker remains responsible for the actual operation and must pass the existing safety boundary before any production-side effect.

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

## Current implementation

`teldrive_lab/jobs.py` provides `JobStore` plus typed `Job`, `JobState`, and `JobType` primitives.

The initial implementation deliberately excludes:

- direct file transfer execution
- automatic mutation of TelDrive paths
- automatic deletion or organization
- Telegram API calls
- background daemons
- hidden retries
- authorization decisions

## Phase 3 sequence

1. Durable job store and state transitions.
2. Lease/recovery and bounded retry tests.
3. Audit integration for every state transition.
4. Idempotency/reconciliation contract.
5. Worker abstraction with explicit safety checks.
6. Cooperative cancellation and pause/resume semantics.
7. Parent/child workflow orchestration.
8. Controlled host validation using only Lab-owned test fixtures.
9. Gate before any production-facing job execution.

## Safety invariant

A queued job is not authorization. A worker lease is not authorization. A successful job state is not proof of archival success. Production mutation remains governed by the existing `PLAN → DRY-RUN → EXPLICIT AUTHORIZATION → EXECUTE → VERIFY → AUDIT` lifecycle.

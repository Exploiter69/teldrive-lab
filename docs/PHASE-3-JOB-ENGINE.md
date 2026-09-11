# Phase 3 — Durable Job Engine

## Status

**Implementation complete.** Phase 3 now provides a durable SQLite job store, audited lifecycle controls, lease/recovery semantics, bounded retries, parent/child relationships, and a worker coordination boundary. The worker does not execute storage operations itself and does not mutate TelDrive production.

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
- Cooperative pause/resume with lease release and reacquisition.
- Worker ownership checks on completion, retry, pause, and lease renewal.
- Durable parent-job relationships and child enumeration.
- Durable child-state summaries for fan-out workflows.
- Terminal-parent protection against adding new children.
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
- control-race protection so a cooperative pause/cancel cannot be overwritten by a late executor result.

The worker deliberately never passes explicit authorization to the safety policy. Job existence, worker ownership, or a valid lease can never authorize a mutation.

For this phase, production transfer/mutation jobs are therefore blocked before the executor is called. Lab-only read/index fixtures may use the executor abstraction for testing.

## Parent/child orchestration

Parent/child support is intentionally a durable coordination primitive rather than an automatic mutation engine:

1. create a parent job;
2. enqueue bounded child jobs using `parent_job_id`;
3. query child state independently;
4. derive a durable `ChildSummary` (`queued`, `running`, `paused`, `verifying`, `completed`, `failed`, `cancelled`);
5. treat the parent as successful only when every child is independently completed by its own verified workflow.

The Job Engine does not silently mark a parent successful, retry a failed child, or grant authorization based on aggregate state. Higher-level orchestration must make those decisions explicitly.

## Pause/resume and cancellation

- `RUNNING → PAUSED` releases the worker lease.
- `PAUSED → QUEUED` makes work eligible for a new claim.
- pause may be scoped to the current worker when a worker identity is supplied.
- `QUEUED`, `RUNNING`, and `PAUSED` jobs may be cancelled.
- a running executor may observe a control request after it starts; the worker checks durable state before applying the executor result and will not overwrite a pause/cancel decision.
- executors remain responsible for idempotency/reconciliation if they already produced an external side effect before a control request was observed.

## Audit

The audited lifecycle facade records enqueue, claim, pause, resume, cancel, retry, lease recovery, completion, and other worker lifecycle events. Audit records are separate from the job store and contain no secrets.

## Controlled host gate

`scripts/phase3_host_gate.py` is the Phase 3 host validation fixture. It uses only a temporary directory, creates a real durable Lab job, executes a read-only index fixture, then submits a deliberately protected production-path mutation and verifies that the safety gate blocks it before the executor is called.

This is a validation fixture, not production execution and not a live TelDrive workflow.

## Phase 3 sequence

1. Durable job store and state transitions. — complete
2. Lease/recovery and bounded retry tests. — complete
3. Audit integration and lifecycle tests. — complete
4. Idempotency/reconciliation contract. — complete
5. Worker abstraction with explicit safety checks. — complete
6. Cooperative cancellation and pause/resume semantics. — complete
7. Parent/child workflow orchestration. — complete
8. Controlled host validation using only Lab-owned test fixtures. — implemented
9. Gate before any production-facing job execution. — complete

## Explicit Phase 3 boundary

Phase 3 does **not** provide production transfer execution, automatic organization, deletion, Telegram API calls, background daemons, or worker-generated authorization. Those belong to later phases and remain subject to the production boundary and safety contract.

## Safety invariant

A queued job is not authorization. A worker lease is not authorization. A successful job state is not proof of archival success. Production mutation remains governed by the existing `PLAN → DRY-RUN → EXPLICIT AUTHORIZATION → EXECUTE → VERIFY → AUDIT` lifecycle.

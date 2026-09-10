# TelDrive Lab — Safety Contract

**Status:** Mandatory  
**Version:** 1.0  
**Scope:** All Lab workflows, commands, workers, integrations, and future interfaces

This document is a hard safety contract. Implementation is considered incorrect if it violates these rules, even when the resulting operation appears technically successful.

## 1. Fundamental Rule

The Lab is a control plane around existing production storage. It must prefer stopping over making an unsafe assumption.

> **If an operation is potentially destructive or irreversible and its safety cannot be proven, stop.**

Human authorization is the final authority for protected and destructive operations.

## 2. Mandatory Execution Lifecycle

All operations that can mutate protected state follow:

`PLAN → DRY-RUN → EXPLICIT AUTHORIZATION → EXECUTE → VERIFY → AUDIT`

Read-only inspection may omit authorization and mutation stages when no state can be changed.

No implementation may silently collapse these stages for convenience.

## 3. Production Protection

The Lab must treat the existing TelDrive deployment and its storage as protected production infrastructure.

Protected areas include:

- `/home/thakuralok/TelegramRaw`
- `/home/thakuralok/TelegramDrive`
- `/home/thakuralok/teldrive`
- `/home/thakuralok/teldrive-project`
- production TelDrive containers;
- production PostgreSQL;
- rclone RAW and CRYPT mounts/remotes;
- Telegram-backed data;
- authentication/session state;
- DNS, nameservers, reverse-proxy and public routing.

The default behavior is inspection and controlled use, not modification.

## 4. Forbidden Default Operations

Without an explicit user request and the required safety lifecycle, the Lab must not:

- delete production files;
- move or rename production files;
- reorganize production storage;
- overwrite production data;
- migrate or re-upload the existing Telegram dataset;
- replace TelDrive;
- replace or migrate the production database;
- change production schemas automatically;
- rebuild or replace production containers;
- alter rclone mounts or remotes;
- change DNS or nameservers;
- change public routing or reverse-proxy configuration;
- modify authentication/session state;
- perform destructive deduplication.

A feature being technically capable of performing an operation does not constitute permission to perform it.

## 5. Destructive Operation Contract

Any operation that can delete, overwrite, move, rename, reorganize, replace, or otherwise make recovery harder must provide:

1. explicit intent;
2. a deterministic plan;
3. dry-run output;
4. affected-object count;
5. affected paths or a safely bounded representation;
6. reason for the operation;
7. policy and safety checks;
8. explicit authorization;
9. execution;
10. post-operation verification;
11. audit records.

If any required element is missing, execution must not proceed.

## 6. Dry-Run Is a Safety Boundary

Dry-run must describe what would happen without performing the mutation.

Where practical, a dry-run includes:

- operation type;
- source;
- destination;
- affected object count;
- estimated bytes;
- overwrite/delete/move implications;
- policy decision;
- verification plan;
- resource estimate;
- warnings.

Dry-run output must be deterministic enough for a human to understand and authorize the proposed action.

## 7. Explicit Authorization

Authorization must be a distinct event from planning.

A plan, AI recommendation, queued job, previous authorization, or successful dry-run is not itself authorization for a destructive operation.

Authorization must be bound to the planned operation so that materially changing the plan invalidates the authorization.

An authorization cannot silently expand from one object or scope to an unrelated scope.

## 8. Verification Is Mandatory

Execution success is not archival success.

A transfer command returning exit code zero does not by itself prove that the destination is complete or usable.

Required verification depends on the operation but may include:

- destination existence;
- size comparison;
- checksum comparison;
- readability;
- metadata consistency;
- expected object count;
- application-specific validation.

A job requiring verification must remain `VERIFYING` until verification succeeds.

Failed verification must never be converted into `COMPLETED` merely because the transfer command succeeded.

## 9. Duplicate Detection

Duplicate detection is informational by default.

A duplicate match must never automatically trigger deletion, replacement, merging, or source removal.

Initial duplicate identity is based on strong deterministic evidence such as SHA-256 plus size.

Ambiguous matches remain ambiguous and require human review.

## 10. Retry and Failure Safety

Retries must be bounded and classified.

Failure classes include:

- transient;
- rate-limited;
- permanent;
- integrity-related.

Retry behavior uses bounded exponential backoff with jitter and must respect upstream rate limits.

The system must never retry indefinitely, especially for operations with mutation side effects.

Before retrying a mutation, the worker must determine whether the previous attempt may already have succeeded. Idempotency or reconciliation must prevent duplicate execution where practical.

## 11. Protected Paths and Fail-Closed Policy

Protected paths must be centrally defined rather than duplicated across individual commands.

Path checks must use canonicalized/validated paths and reject traversal or ambiguous path forms.

If a source or destination cannot be confidently classified, the operation fails closed.

A worker must not infer that an unrecognized path is safe merely because it is outside a known path string.

## 12. Secrets and Sensitive State

Secrets must never be:

- committed to Git;
- written into logs;
- written into audit events;
- displayed in normal CLI output;
- embedded in plans;
- stored in job error messages;
- sent to AI providers;
- included in diagnostic bundles.

Examples include Telegram credentials, session material, tokens, passwords, private keys, and authentication cookies.

Configuration must separate secret references from ordinary policy/configuration.

## 13. AI Is Untrusted

AI output is advisory input, never authorization.

AI must not directly authorize or execute:

- deletion;
- destructive deduplication;
- production reorganization;
- database changes;
- storage migration;
- credential changes;
- DNS changes;
- security-policy changes.

AI-generated paths, commands, classifications, or plans must pass deterministic validation before they can influence execution.

The system must remain operational without AI.

## 14. Job Durability and Crash Recovery

A worker process may disappear at any time.

The durable Job Engine must ensure that a crash does not cause:

- data loss;
- false completion;
- silent skipped work;
- unbounded duplicate execution;
- permanent loss of audit history.

Intent and state must be persisted before relying on a long-running external operation.

Worker leases must allow abandoned jobs to be detected and recovered safely.

Recovery logic must reconcile uncertain external state before repeating a potentially mutating operation.

## 15. Network Loss

Network failure is expected behavior, not an exceptional reason to corrupt state.

When connectivity disappears:

- preserve durable job state;
- classify the failure appropriately;
- retry only within policy limits;
- do not mark the operation complete;
- do not lose the planned destination or verification requirements.

A recovered worker must not blindly repeat an operation whose prior outcome is uncertain.

## 16. Resource Safety

The Lab runs on a resource-constrained host and must remain bounded.

Operations must respect configured limits for:

- worker count;
- concurrent transfers;
- memory use;
- CPU-intensive work;
- disk/cache consumption;
- network activity;
- scan scope.

Resource exhaustion must degrade into controlled pause, retry, or failure rather than unsafe behavior.

Safety always takes precedence over throughput.

## 17. Telegram API Safety

Telegram-backed operations must remain conservative and rate-aware.

The Lab must not generate aggressive polling, uncontrolled concurrency, request storms, or unnecessary repeated scans.

Rate-limit responses must be classified and retried according to bounded backoff policy.

The Lab must not attempt to bypass Telegram limits.

## 18. Audit Requirements

Safety-relevant actions must be auditable.

At minimum, audit events should distinguish:

- requested;
- planned;
- dry-run;
- authorized;
- started;
- verifying;
- completed;
- failed;
- cancelled;
- rejected.

Audit records must identify the job, operation, scope, policy result, and verification result without exposing secrets.

## 19. Separation of Concerns

The following boundaries are mandatory:

- planner proposes; it does not mutate;
- policy decides whether an operation is permitted;
- authorization grants permission for the approved plan;
- executor performs the approved operation;
- verifier determines whether the required result exists;
- auditor records what happened;
- metadata index records informational state but is not storage authority.

No component may silently assume another component's authority.

## 20. No Hidden Side Effects

Commands presented as read-only must not mutate production state.

Inspection, search, indexing, status, and dry-run operations must not:

- delete data;
- reorganize files;
- rewrite metadata in production;
- alter mounts;
- restart production services without explicit policy and authorization.

Unexpected side effects are treated as safety defects.

## 21. Scope and Authorization Integrity

Authorization applies only to the exact approved scope.

If any of the following materially changes after authorization, the operation must require re-planning and re-authorization:

- source;
- destination;
- object set;
- operation type;
- deletion/overwrite behavior;
- verification requirements;
- relevant policy;
- resource impact.

A stale authorization must not remain valid indefinitely.

## 22. Cancellation

Cancellation must be cooperative and state-aware.

Cancelling a job must not silently report success.

If cancellation occurs during a transfer, the system must record the uncertain/partial state and determine whether cleanup, resume, or manual review is required.

Destructive cleanup after cancellation requires the same safety contract as any other destructive operation.

## 23. Recovery and Restore Safety

Restore operations are potentially destructive and therefore require explicit planning, dry-run, authorization, execution, verification, and audit.

The system must prefer restoring into a controlled destination before overwriting an existing object.

Any overwrite-capable restore must clearly identify the affected existing objects.

## 24. Testing Requirements

Every implementation affecting safety must have tests for both the happy path and failure path.

At minimum, tests should cover:

- protected-path rejection;
- missing authorization;
- stale authorization;
- dry-run non-mutation;
- verification failure;
- retry classification;
- retry exhaustion;
- worker crash/recovery;
- lease expiration;
- duplicate execution prevention;
- network loss;
- secret redaction;
- AI-generated unsafe input rejection;
- cancellation;
- malformed/ambiguous paths.

Safety tests are regression tests and must remain part of the project permanently.

## 25. Implementation Rule

Any new feature must answer these questions before implementation:

1. Can it mutate state?
2. Can it affect production?
3. Can it delete, overwrite, move, rename, or reorganize data?
4. What policy controls it?
5. What authorization does it require?
6. What does dry-run show?
7. How is success verified?
8. How does crash/network recovery behave?
9. What is logged?
10. How is the operation tested safely?

If these answers are not defined, the feature is not ready for implementation.

## Final Safety Principle

TelDrive Lab is intentionally conservative.

**Reliability, reversibility, verification, and human control are more important than automation speed.**

The safest automation is automation that knows when it must stop.

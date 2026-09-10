# TelDrive Lab — Architecture

**Status:** Architecture Baseline  
**Version:** 1.0  
**Scope:** Sidecar automation and control plane for an existing TelDrive deployment  
**Cost target:** ₹0 / $0

## 1. Purpose

TelDrive Lab is a conservative, removable sidecar system that adds reliability, automation, indexing, integrity verification, lifecycle workflows, monitoring, search, and optional intelligence around the existing TelDrive installation.

It does **not** replace TelDrive, Telegram storage, rclone, PostgreSQL, or the existing production deployment.

The Lab is an engineering control plane. Existing TelDrive-backed storage remains authoritative.

## 2. Core Architectural Principle

**The model is not the authority. Storage is not the job database. A transfer is not complete until verification succeeds.**

The system separates:

- deterministic policy from optional intelligence;
- durable job state from transient processes;
- metadata from authoritative storage;
- planning from mutation;
- authorization from execution;
- execution from verification;
- production infrastructure from Lab state.

The central workflow is:

`DISCOVER → PLAN → DRY-RUN → EXPLICIT AUTHORIZATION → EXECUTE → VERIFY → INDEX → AUDIT`

## 3. Architectural Boundary

### Production boundary

The following remain outside the Lab's ownership:

- `/home/thakuralok/TelegramRaw`
- `/home/thakuralok/TelegramDrive`
- `/home/thakuralok/teldrive`
- `/home/thakuralok/teldrive-project`
- TelDrive production containers
- PostgreSQL production database
- rclone RAW and CRYPT mounts/remotes
- Telegram-backed data
- authentication/session state
- DNS, nameservers, reverse-proxy/public routing

The Lab may inspect or use approved interfaces to these systems, but does not silently replace, migrate, reorganize, or delete them.

### Lab boundary

Lab source code and documentation live in this repository.

Runtime state is deliberately external to Git:

`~/.local/share/teldrive-lab/`

Cache and temporary data live under:

`~/.cache/teldrive-lab/`

The Lab must remain independently removable without damaging production data.

## 4. High-Level Component Architecture

```text
                         ┌─────────────────────────┐
                         │       Control Plane      │
                         │     CLI / future API    │
                         └────────────┬────────────┘
                                      │
                         ┌────────────▼────────────┐
                         │       Policy Engine     │
                         │ auth / boundaries /     │
                         │ safety / destinations   │
                         └───────┬────────┬────────┘
                                 │        │
                    ┌────────────▼──┐  ┌──▼─────────────┐
                    │   Job Engine  │  │ Metadata Index │
                    │ durable state │  │ SQLite catalog │
                    │ retries/lease │  │ rebuildable    │
                    └───────┬───────┘  └────────────────┘
                            │
                    ┌───────▼────────┐
                    │ Transfer       │
                    │ Manager        │
                    │ FS/rclone/     │
                    │ TelDrive       │
                    └───────┬────────┘
                            │
             ┌──────────────┼───────────────┐
             ▼              ▼               ▼
        Local FS        rclone/TelDrive   Approved
                                           integrations
             │              │               │
             └──────────────┼───────────────┘
                            ▼
                    ┌───────────────┐
                    │ Verification  │
                    │ + Audit Log   │
                    └───────────────┘
```

Optional modules such as media processing, OCR, semantic search, local AI, notifications, and external integrations attach to these shared deterministic services rather than creating independent mutation paths.

## 5. Control Plane

The initial interface is a CLI. Planned commands include:

- `td status`
- `td jobs`
- `td upload`
- `td download`
- `td archive`
- `td verify`
- `td search`
- `td duplicates`
- `td backup`
- `td snapshot`
- `td restore`
- `td cleanup`

Future interfaces may include an API, dashboard, PWA, or Telegram notifications.

All interfaces must call the same underlying policy, job, transfer, verification, and audit services. A new interface must never create a parallel safety model.

## 6. Policy Engine

The Policy Engine is deterministic and authoritative for allowed mutations.

It evaluates:

- authorization requirements;
- source and destination boundaries;
- RAW versus CRYPT policy;
- protected paths;
- retention rules;
- verification requirements;
- cleanup rules;
- immutable archive rules;
- priority limits;
- resource limits;
- network-dependent operations;
- destructive-operation requirements.

AI output, job priority, or user-interface convenience cannot bypass Policy Engine decisions.

If authorization, source, destination, verification, or policy is uncertain, the operation fails closed.

## 7. Job Engine

The Job Engine provides durable asynchronous execution.

Responsibilities:

- persistent job state;
- state transitions;
- bounded retries;
- failure classification;
- exponential backoff with jitter;
- worker leases;
- abandoned-job recovery;
- progress tracking;
- cooperative cancellation;
- idempotency;
- parent/child jobs;
- startup recovery;
- audit events.

The canonical successful path is:

`QUEUED → RUNNING → VERIFYING → COMPLETED`

Failures may return to `QUEUED` for retry or become `FAILED` when retry is unsafe or exhausted.

A job is never considered complete merely because an underlying command returned success.

## 8. Metadata Index

The Lab maintains a local SQLite catalog at:

`~/.local/share/teldrive-lab/catalog.db`

The catalog stores searchable metadata such as:

- path and name;
- parent path;
- size;
- MIME type and extension;
- timestamps;
- SHA-256 checksum;
- checksum state;
- source and destination identifiers;
- Telegram identifiers when available;
- encryption classification;
- verification state;
- tags;
- job relationships;
- first/last seen timestamps.

The catalog is **rebuildable** and is never the authoritative copy of user data.

Initial search/indexing uses ordinary SQLite indexes. Full-text search and richer indexes may be added later when justified.

## 9. Transfer Manager

The Transfer Manager is the single execution layer for data movement.

Supported backends initially include:

- local filesystem;
- rclone;
- existing TelDrive-supported paths/interfaces.

It provides:

- bounded concurrency;
- progress reporting;
- classified retries;
- backoff;
- rate-limit awareness;
- resumability where supported;
- integrity verification;
- recovery handling.

The Lab does **not** introduce a second authoritative storage backend.

Telegram API usage remains conservative and bounded.

## 10. Canonical Archive Flow

The canonical archive workflow is:

1. Discover the source object.
2. Collect metadata.
3. Compute a checksum when required.
4. Perform an informational duplicate check.
5. Evaluate policy.
6. Produce a dry-run plan.
7. Require explicit authorization for protected/destructive actions.
8. Queue a durable job.
9. Execute through the Transfer Manager.
10. Verify the destination.
11. Update the metadata index.
12. Record the complete audit trail.

Duplicate detection is informational by default. It never implies permission to delete either copy.

## 11. Deterministic Organization

Organization rules are deterministic and inspectable.

Examples include classification by:

- MIME type;
- extension;
- date;
- source;
- project;
- configured user tags.

Every organization operation supports dry-run before apply.

Production files are never silently renamed, moved, or deleted merely because an organization rule matches.

## 12. Archive Workflow

`td archive <file>` represents a controlled archival operation.

Archiving and local deletion are separate actions. Successful archival does not automatically authorize removal of the source.

If source removal is ever requested, it follows the destructive-operation contract independently:

`PLAN → DRY-RUN → EXPLICIT AUTHORIZATION → EXECUTE → VERIFY → AUDIT`

## 13. Integrity Architecture

SHA-256 is the initial checksum algorithm because it is widely available, deterministic, and sufficient for the first implementation.

BLAKE3 may be benchmarked as an optimization but does not become a dependency merely because it is faster.

Integrity states are explicit. A successful copy command is not equivalent to verified archival completion.

Verification may include:

- size comparison;
- checksum comparison where available;
- destination readability;
- source/destination metadata consistency;
- application-specific validation for future media/document modules.

## 14. Audit Architecture

Every meaningful job and mutation produces structured audit events.

Initial event classes include:

- `REQUESTED`
- `PLANNED`
- `DRY_RUN`
- `AUTHORIZED`
- `STARTED`
- `PROGRESS`
- `VERIFYING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`
- `REJECTED`

Audit records contain operational metadata but never secrets, authentication tokens, private credentials, or unnecessary sensitive content.

The audit trail must survive normal job failures and support reconstruction of what the Lab attempted and what it verified.

## 15. Monitoring Architecture

Monitoring observes both Lab and production dependencies without taking ownership of them.

Initial observability targets:

- TelDrive health;
- PostgreSQL health;
- rclone RAW mount;
- rclone CRYPT mount;
- Docker health;
- filesystem availability;
- disk capacity;
- network state;
- job queue;
- index health;
- verification failures;
- cache usage.

Remediation is conservative. Automatic remediation cannot cross the production safety boundary.

## 16. Resource-Aware Architecture

The host is resource-constrained, particularly in RAM. The Lab therefore prefers small, bounded, restartable processes.

Rules:

- bounded worker concurrency;
- bounded queues;
- incremental scans;
- resumable operations;
- controlled cache sizes;
- lightweight persistent services;
- scheduled heavy work;
- batch hashing where practical;
- optional AI rather than always-on AI;
- no unnecessary resident database/server stack beyond SQLite.

Heavy operations must be observable and cancellable.

## 17. Offline-First Behavior

Network-dependent jobs must survive temporary connectivity loss.

The system should:

- persist intent before network execution;
- distinguish offline failures from permanent failures;
- retry transient failures within bounded limits;
- avoid corrupting job state when connectivity disappears;
- never mark network-dependent work complete without verification.

Offline operation must not produce duplicate destructive execution after recovery.

## 18. AI Boundary

AI is optional and subordinate to deterministic infrastructure.

Potential AI uses include:

- search assistance;
- metadata classification suggestions;
- summaries;
- OCR interpretation;
- semantic retrieval;
- document/media analysis;
- natural-language query translation;
- operational recommendations.

AI must not independently authorize:

- deletion;
- production reorganization;
- database modification;
- storage migration;
- credential changes;
- DNS changes;
- security-policy bypasses.

AI output is untrusted input to deterministic policy and execution layers.

The system must remain fully useful without AI.

## 19. Technology Choices

The initial implementation should favor simple, free, locally available technologies:

- Python or Go for core services/CLI;
- SQLite for durable Lab metadata and job state;
- systemd for host scheduling where appropriate;
- rclone for supported transfer interfaces;
- existing TelDrive for Telegram-backed storage;
- Docker only where isolation is justified;
- standard Linux tooling for filesystem operations.

The architecture intentionally avoids paid APIs, paid infrastructure, mandatory hosted services, and unnecessary heavy orchestration.

## 20. Extensibility

Optional future modules can build on the core engines without weakening the production boundary.

Candidate extensions include:

- media indexing;
- OCR;
- transcripts;
- semantic search;
- image similarity;
- Jellyfin integration;
- WebDAV interoperability;
- notifications;
- storage intelligence;
- snapshot/time-machine workflows;
- VAJRA integration;
- Alok Engineering Lab integration;
- Mithila Heritage Archives integration.

These remain optional modules. Their failure must not compromise core storage safety.

## 21. Architectural Invariants

The following invariants are mandatory:

1. TelDrive-backed storage remains the storage authority.
2. Production paths and services are explicitly protected.
3. The Lab can be removed without damaging production data.
4. The metadata catalog is rebuildable.
5. Job state is durable across process restarts.
6. Mutations pass through deterministic policy.
7. Destructive actions require explicit authorization.
8. Dry-run precedes protected destructive execution.
9. Verification is part of successful completion.
10. Duplicate detection never implies deletion authority.
11. AI never has final mutation authority.
12. Secrets never enter source, logs, or audit records.
13. Telegram API usage remains conservative and rate-aware.
14. Resource usage remains bounded and observable.
15. The system remains functional without AI.
16. The architecture does not require migration or re-upload of existing TelDrive data.
17. A potentially destructive or irreversible operation that cannot be proven safe must stop.

## Architectural Decision

This baseline deliberately chooses a **sidecar control-plane architecture** rather than a TelDrive fork, storage migration, replacement backend, or AI-first automation system.

The first implementation priority is therefore not feature count. It is establishing a deterministic, durable, testable execution foundation that can safely support every later feature in the roadmap.

# TelDrive Lab — Architecture Decisions

**Status:** Living architectural record  
**Scope:** Decisions that constrain the design, implementation, safety, and evolution of TelDrive Lab

This document records decisions that should not be repeatedly reopened without new evidence. A later decision may supersede an earlier one, but it must explicitly state what changed, why, and what components are affected.

---

## ADR-001 — Build a Sidecar, Not a TelDrive Replacement

**Status:** Accepted

### Decision
TelDrive Lab is a sidecar control, automation, indexing, verification, and intelligence layer around the existing TelDrive deployment.

### Rationale
The existing TelDrive installation and Telegram-backed storage are already operational. Replacing the storage system would introduce unnecessary migration risk, data movement, compatibility risk, and a much larger failure surface.

### Consequences
- TelDrive remains operationally independent.
- Lab state is stored separately.
- Lab functionality must use supported interfaces or explicitly approved inspection paths.
- Existing production data is not migrated merely to support Lab features.

---

## ADR-002 — TelDrive and Telegram Remain Storage Authorities

**Status:** Accepted

### Decision
The existing TelDrive/Telegram stack remains authoritative for stored content. TelDrive Lab is never the canonical owner of the underlying stored bytes.

### Rationale
A metadata catalog, cache, index, or automation layer must not accidentally become a second storage system or create conflicting truths about content.

### Consequences
- The Lab catalog is rebuildable.
- Job state describes work, not storage ownership.
- Observations may become stale and must be reconciled.
- Lab deletion or database corruption must not constitute loss of the storage authority.

---

## ADR-003 — Keep TelDrive Lab in a Separate Repository

**Status:** Accepted

### Decision
TelDrive Lab lives in its own GitHub repository: `Exploiter69/teldrive-lab`.

### Rationale
The Lab has a different lifecycle and safety boundary from the TelDrive application source and production deployment. Mixing them would make accidental coupling and deployment confusion more likely.

### Consequences
- Lab source, architecture, scripts, tests, and documentation are versioned independently.
- The existing `teldrive-project` remains separate.
- Changes to the Lab do not imply changes to TelDrive.

---

## ADR-004 — Use a Local SQLite Catalog

**Status:** Accepted

### Decision
The initial metadata catalog uses SQLite in the Lab runtime data area.

### Rationale
SQLite provides durable local transactions, indexing, low operational overhead, and zero infrastructure cost. The host does not need another database service merely to index metadata.

### Consequences
- Initial catalog path: `~/.local/share/teldrive-lab/catalog.db`.
- No PostgreSQL/Redis service is introduced for Lab metadata.
- Schema versioning and migrations are required.
- Concurrency must remain bounded and SQLite-aware.

---

## ADR-005 — The Catalog Must Be Rebuildable

**Status:** Accepted

### Decision
The metadata catalog is an observation/index layer and must be rebuildable from supported storage interfaces and source observations.

### Rationale
Indexes inevitably become stale or can be corrupted. Making the catalog authoritative would turn an indexing failure into a storage failure.

### Consequences
- Catalog records must distinguish source facts from Lab observations.
- Reconciliation is a first-class operation.
- No storage operation may depend solely on an unverified catalog record.
- Catalog loss is recoverable through re-indexing.

---

## ADR-006 — Use a Durable Local Job Engine

**Status:** Accepted

### Decision
Long-running or asynchronous work is represented as durable jobs rather than process-local tasks.

### Rationale
A terminal can close, a worker can crash, the network can disappear, or the host can reboot. Work accepted by the system must remain explainable and recoverable.

### Consequences
- Jobs persist state.
- Workers use leases.
- Retries are bounded and classified.
- Recovery reconciles external state instead of blindly replaying operations.
- Verification is part of completion.

---

## ADR-007 — Deterministic Core Before Intelligence

**Status:** Accepted

### Decision
Deterministic discovery, policy, planning, transfer, verification, indexing, and audit mechanisms are implemented before advanced AI or semantic automation.

### Rationale
Automation is only trustworthy when its effects can be bounded and verified. AI should not compensate for missing deterministic control paths.

### Consequences
- Early phases prioritize contracts and tests.
- AI cannot become the hidden execution engine.
- Advanced intelligence is layered on stable primitives.

---

## ADR-008 — AI Is Advisory, Not Authoritative

**Status:** Accepted

### Decision
AI components may classify, summarize, suggest, rank, search, explain, or propose plans, but they do not receive independent authority to mutate production storage or bypass policy.

### Rationale
LLM output is probabilistic and may be incorrect. Deterministic policy and explicit authorization are required for consequential operations.

### Consequences
- AI output is treated as untrusted input.
- Destructive operations still require deterministic policy and explicit authorization.
- Secrets are excluded from AI context.
- AI may propose actions that the control plane rejects.

---

## ADR-009 — SHA-256 Is the Initial Canonical Content Hash

**Status:** Accepted

### Decision
SHA-256 is the initial canonical content identity/checksum algorithm.

### Rationale
It is widely available, deterministic, sufficiently strong for the initial integrity and duplicate-detection use cases, and avoids introducing an unnecessary dependency before the workload characteristics are measured.

### Consequences
- Hash state is explicitly tracked.
- Hashing can be deferred or scheduled according to resource constraints.
- BLAKE3 may be benchmarked later, but does not replace SHA-256 merely for theoretical performance.

---

## ADR-010 — Prefer One-Way Workflows Initially

**Status:** Accepted

### Decision
Initial automation emphasizes bounded, one-way operations such as discovery, indexing, verification, backup, and controlled transfer before introducing complex bidirectional synchronization.

### Rationale
Bidirectional synchronization creates conflict resolution, deletion propagation, rename reconciliation, and consistency problems that are unnecessary for the initial Lab mission.

### Consequences
- Initial workflows are easier to reason about.
- Synchronization is not assumed to be a default feature.
- Future sync designs require their own safety and conflict-resolution decision.

---

## ADR-011 — No Automatic Destructive Deduplication

**Status:** Accepted

### Decision
Duplicate detection is informational by default. The Lab does not automatically delete, merge, overwrite, or replace files merely because hashes match.

### Rationale
Identical content can have intentional duplicate paths, metadata significance, lifecycle significance, or different user intent. A matching hash proves content equivalence, not permission to remove an object.

### Consequences
- Duplicate reports may recommend candidates.
- Any destructive cleanup follows the Safety Contract.
- Duplicate decisions remain human-controlled until a stronger policy is explicitly designed.

---

## ADR-012 — Destructive Actions Require Explicit Authorization

**Status:** Accepted

### Decision
Any potentially destructive or irreversible action requires the lifecycle:

`PLAN → DRY-RUN → EXPLICIT AUTHORIZATION → EXECUTE → VERIFY → AUDIT`

### Rationale
Planning and authorization are different responsibilities. A generated plan must never silently become permission to execute it.

### Consequences
- Authorization is scope-bound.
- Dry-run output must expose affected scope sufficiently for review.
- Queued destructive jobs are not automatically authorized by their existence.
- Policy violations fail closed.

---

## ADR-013 — Verification Is Part of Completion

**Status:** Accepted

### Decision
A transfer or mutation requiring verification is not complete until verification succeeds.

### Rationale
A successful command exit code proves only that the executor reported success. It does not prove that the intended result exists, is complete, or is readable.

### Consequences
- Job state includes verification.
- Integrity mismatches cannot produce successful jobs.
- Recovery must account for operations interrupted between execution and verification.

---

## ADR-014 — Keep the Architecture Zero-Cost

**Status:** Accepted

### Decision
The Lab must be designed to operate without paid APIs, subscriptions, hosted infrastructure, or mandatory paid services.

### Rationale
The project's hard constraint is ₹0/$0 ongoing development and operation cost. The architecture must not rely on a future paid dependency to become useful.

### Consequences
- Prefer local software and existing host capabilities.
- Optional external free tiers may be adapters, never mandatory foundations.
- No pay-as-you-go service may be required for core operation.
- Architecture quality and safety must not be compromised merely to avoid cost.

---

## ADR-015 — Make Resource Awareness a First-Class Constraint

**Status:** Accepted

### Decision
Scheduling, indexing, hashing, transfers, media processing, and AI workloads must respect the host's limited CPU, RAM, disk, and network resources.

### Rationale
The Lab runs on a resource-constrained personal machine. Unbounded concurrency or always-on heavy processing can destabilize the host and harm the production environment indirectly.

### Consequences
- Concurrency is bounded.
- Expensive work is batchable or schedulable.
- Caches have explicit limits.
- AI workloads are optional and resource-aware.
- Backpressure is preferred over resource exhaustion.

---

## ADR-016 — Make the Production Boundary Explicit

**Status:** Accepted

### Decision
Protected production paths, services, databases, mounts, authentication/session state, DNS/network exposure, and existing TelDrive deployment assets are explicitly defined and tested as a boundary.

### Rationale
Safety rules that exist only as informal assumptions are easy to violate. A machine-readable/deterministic boundary is easier to enforce and test.

### Consequences
- Protected paths are centralized in policy.
- Lab runtime data is separate.
- Production modifications fail closed unless explicitly authorized.
- Boundary tests become part of implementation gates.

---

## ADR-017 — No Migration as a Prerequisite

**Status:** Accepted

### Decision
TelDrive Lab does not require migration, reuploading, storage reorganization, database replacement, or deployment reconstruction to become operational.

### Rationale
The existing storage system is valuable working infrastructure. A sidecar should add capabilities without forcing a risky transformation of the underlying system.

### Consequences
- Existing data stays where it is.
- New capabilities operate around the current system.
- Any future migration proposal must be treated as a separate project with its own authorization and rollback plan.

---

## ADR-018 — CLI Is the Initial Control Interface

**Status:** Accepted

### Decision
The first user-facing control plane is a local CLI exposing deterministic operations and job inspection.

### Rationale
A CLI is lightweight, scriptable, auditable, and does not require maintaining a web service or public control plane during the foundational phases.

### Consequences
Initial commands include concepts such as:

```text
`td status`
`td jobs`
`td upload`
`td download`
`td archive`
`td verify`
`td search`
`td duplicates`
`td backup`
`td snapshot`
`td restore`
`td cleanup`
```

Other interfaces may be added later as clients of the same internal control plane.

---

## ADR-019 — All Interfaces Share the Same Engines

**Status:** Accepted

### Decision
CLI, scheduler, future web UI, Telegram bot, API, MCP integration, or other interfaces must call the same policy, job, transfer, catalog, verification, and audit engines.

### Rationale
Duplicating business logic across interfaces creates inconsistent safety behavior and bypass paths.

### Consequences
- Interfaces are adapters, not independent execution systems.
- Safety rules are centralized.
- A future UI cannot silently implement a weaker authorization path than the CLI.

---

## ADR-020 — Architecture Evolves Through Recorded Decisions

**Status:** Accepted

### Decision
Material architectural changes are recorded in this document before or alongside implementation.

### Rationale
The project is intentionally being built in phases. Recording why decisions were made prevents context loss and reduces repeated architectural debates.

### Required format for superseding decisions

A later decision should identify:

- the decision being changed;
- the new decision;
- evidence or new requirements motivating the change;
- affected components;
- migration or compatibility implications;
- safety implications;
- whether the previous decision remains valid for existing deployments.

### Consequences
The architecture remains intentionally evolvable without becoming undocumented or inconsistent.

---

## Decision Review Rule

A decision may be revisited when there is **new evidence**, a **new hard requirement**, a **demonstrated implementation failure**, or a **material change in the production environment**.

A preference alone is not sufficient reason to overturn a safety or architectural invariant.

The governing principle is:

> **Change architecture deliberately, record the reason, preserve safety boundaries, and never let implementation convenience silently rewrite the system's authority model.**

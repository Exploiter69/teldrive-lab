# TelDrive Lab Roadmap

This is the canonical current roadmap. Historical implementation phases and reconciliation reports are no longer maintained as active documentation.

> **Product truth:** TelDrive remains the production storage authority. TelDrive Lab is the safe engineering control plane around it.

## Completion standard

```text
PRIMITIVE → IMPLEMENTED → INTEGRATED → OPERATIONAL → END-TO-END VERIFIED → DOCUMENTED → COMPLETE
```

## Current release state

**v1.0.0: COMPLETE and release-hardened through R0–R6.**

**Core control plane: COMPLETE and release-hardened through R0–R6.**

The v1.0.0 release tag points to the validated RC2 commit. Post-RC evidence is recorded separately on `main`; it does not mutate the release tag.

The core includes authoritative discovery/catalog, search, media/Jellyfin serving, durable execution, verification, audit, monitoring, and the read-only Control Center.

P12–P21 remain an extension layer. Only capabilities actually inside the current product contract are represented below. Optional AI-provider integrations are intentionally excluded.

## Baseline capability status

| Capability | Status | Boundary |
|---|---|---|
| Corpus discovery | COMPLETE | Bounded authoritative metadata discovery; derived local catalog |
| Unified search | COMPLETE | Filename/path/content search over supported local indexes |
| Media/Jellyfin | COMPLETE | Read-only protection with verified Lab-owned media workflow |
| Durable execution | COMPLETE | Durable jobs, leases, retries, recovery, verification, audit |
| Control Center | COMPLETE | Loopback-only, GET-only, read-only |
| Storage/cache intelligence | IMPLEMENTED | Deterministic classification, access frequency, planning; no automatic eviction |
| Read-only interoperability | IMPLEMENTED | Metadata/API surfaces; no TelDrive DB writes |
| Document intelligence | IMPLEMENTED | Fingerprints, PDF metadata/text extraction, OCR where locally available |
| Local embeddings/search | IMPLEMENTED | Deterministic local feature-hash embeddings; no remote AI service |
| Storage analytics | IMPLEMENTED | Forecasting, category analysis, transfer estimates; advisory only |
| Snapshots/recovery planning | IMPLEMENTED | Snapshot manifests, verification, restore planning; restore remains authorized/high-risk |
| Cross-project contracts | IMPLEMENTED | Explicit read/plan/export contracts; no implied production integration |
| CAS/dedup | EXPERIMENTAL | Lab-owned CAS and report-only dedup planning |

## v1.1 — Operational Control & Recovery

### Objective

Make the already-safe system easier to **operate, understand, recover, and trust** without weakening the production safety boundary or introducing paid/mandatory AI dependencies.

### Invariants for every v1.1 stage

1. TelDrive remains the production storage authority.
2. No direct TelDrive PostgreSQL writes.
3. No planner, UI, advisory layer, worker, or AI component can mint authorization.
4. Consequential production mutation remains behind the controlled executor boundary.
5. Verification follows consequential execution.
6. Evidence/audit remains durable and Lab-owned.
7. Destructive operations are never automatic.
8. No paid runtime service, paid API, mandatory cloud AI, or mandatory local LLM is introduced.
9. All discovery/indexing/search paths remain bounded.
10. Existing v1.0 behavior must remain regression-safe.
11. Optional downstream integrations cannot become hidden core dependencies.
12. Production data is never used as a disposable test fixture.

### Global v1.1 prerequisites

Before starting v1.1 implementation:

- [x] v1.0.0 release tag exists and remains immutable
- [x] v1.0.0 release checklist is closed
- [x] post-RC audit found no release blockers
- [x] local Jellyfin persistence has been operationally verified
- [x] preserved local stash remains untouched
- [ ] establish a v1.1 development baseline commit
- [ ] run the complete existing test/gate matrix before the first v1.1 code change
- [ ] record the baseline result before changing behavior

### Stage A — Control Center operational depth

**Goal:** turn the existing observer into a stronger operational read model without turning it into an unrestricted mutation console.

#### Scope

- catalog health and discovery freshness
- search/index health
- active, failed, recoverable, and stale jobs
- lease/recovery state
- verification state
- storage/cache statistics already available from deterministic Lab-owned data
- media/Jellyfin state
- recent audit evidence
- explicit safety-boundary/configuration state
- bounded pagination/limits for every new read surface
- deterministic JSON contracts suitable for CLI/UI consumption

#### Prerequisites

- existing R5 Control Center tests pass
- JobStore state model and recovery semantics remain unchanged unless a separately justified change is required
- catalog schema/index behavior is understood
- audit schema and event semantics are documented
- no production mutation is required to exercise the stage

#### Gate A1 — Read-model contract

- [ ] define versioned response schemas
- [ ] define bounded limits and deterministic ordering
- [ ] define freshness/unknown semantics; never fabricate health
- [ ] prove every value is derived from Lab-owned state or explicitly read-only source data

#### Gate A2 — Implementation

- [ ] implement the smallest required read-model changes
- [ ] add unit tests for normal, empty, stale, and failure states
- [ ] add HTTP contract tests
- [ ] preserve loopback-only and GET-only behavior
- [ ] ensure sensitive/local paths are not unnecessarily exposed

#### Gate A3 — Integration

- [ ] run existing R0–R6 and legacy extension tests
- [ ] run Control Center host gate
- [ ] verify no production TelDrive/rclone mutation
- [ ] verify bounded responses under larger synthetic datasets
- [ ] document the final contract

#### Completion

`IMPLEMENTED → INTEGRATED → OPERATIONAL → END-TO-END VERIFIED → DOCUMENTED → COMPLETE`

---

### Stage B — Recovery and restore workflows

**Goal:** make failures explainable and safe recovery actions explicit, reviewable, controlled, verifiable, and auditable.

#### Prerequisites

- Stage A complete
- JobStore lease/retry/recovery behavior remains green
- transfer/verification boundaries are identified
- restore planning semantics are deterministic
- disposable local fixtures exist for recovery tests
- protected production destinations remain blocked unless explicitly authorized by the existing boundary

#### Scope

```text
failure
  ↓
persist evidence
  ↓
classify failure
  ↓
show recovery options
  ↓
explicit authorization
  ↓
controlled executor
  ↓
verify
  ↓
audit
```

- failure classification/signatures
- recoverable vs non-recoverable state
- explicit retry/resume/restore plans
- stale-worker and lease-loss recovery visibility
- verification of restored outputs
- recovery evidence and audit linkage
- idempotency and duplicate-action protection

#### Safety requirements

- recovery suggestions are advisory until authorized
- workers cannot authorize themselves
- no automatic destructive purge
- no silent overwrite of protected production data
- failed recovery must remain auditable
- retries must remain bounded and fenced

#### Gates

- [ ] deterministic failure taxonomy
- [ ] recovery-plan digest/idempotency contract
- [ ] authorization boundary tests
- [ ] stale-worker fencing tests
- [ ] restore verification tests
- [ ] crash/process-boundary recovery test
- [ ] host gate with disposable fixtures
- [ ] production-boundary gate remains green

---

### Stage C — Observability and evidence

**Goal:** answer what is happening, what happened, why it happened, what is stuck, what is safely retryable, what requires authorization, what was verified, and what changed.

#### Prerequisites

- Stage B complete
- existing audit event schema reviewed
- JobStore and verification transitions mapped to observable lifecycle events
- no second competing logging/evidence system introduced without architectural justification

#### Scope

- lifecycle event coverage
- failure/retry/recovery visibility
- job duration and progress evidence
- verification outcomes
- discovery/index freshness indicators
- audit correlation across job/plan/execution/verification
- bounded operational reports
- deterministic export/report surfaces where useful

#### Gates

- [ ] every consequential lifecycle transition has sufficient evidence
- [ ] correlation IDs/job IDs remain stable and useful
- [ ] failure evidence survives process restart
- [ ] reports are bounded and deterministic
- [ ] no secrets or unnecessary credentials are exposed
- [ ] host and full regression gates pass

---

### Stage D — Storage intelligence integration

**Goal:** connect already-implemented deterministic storage intelligence and analytics to the operational control plane without converting advice into automatic mutation.

#### Prerequisites

- Stage C complete
- existing storage/cache intelligence and analytics implementation audited
- classification outputs have deterministic semantics
- planning output has stable identity/digest
- controlled executor and verification paths are identified for every consequential operation

#### Required flow

```text
storage intelligence
        ↓
advisory finding
        ↓
deterministic plan
        ↓
human review
        ↓
explicit authorization
        ↓
controlled executor
        ↓
verification
        ↓
audit
```

#### Scope

- operational presentation of storage findings
- deterministic plan generation
- stale/large/low-access indicators
- cache/storage forecasting
- transfer-cost/time estimates where deterministic
- archive/backup recommendations
- report-only cleanup candidates

#### Hard boundary

Never implement:

```text
finding → DELETE
```

Automatic production eviction, destructive cleanup, and automatic deduplication remain prohibited.

#### Gates

- [ ] deterministic finding tests
- [ ] deterministic plan digest tests
- [ ] authorization tests
- [ ] protected-root tests
- [ ] executor-boundary tests
- [ ] verification/audit tests
- [ ] host integration with disposable data
- [ ] zero-cost regression check

---

### Stage E — CAS and dedup safety investigation

**Goal:** determine whether experimental CAS/report-only dedup can become a trustworthy operational capability. This is an investigation first, not a promise of automatic deduplication.

#### Prerequisites

- Stages A–D complete
- complete provenance model documented
- content identity/hash guarantees reviewed
- collision handling defined
- rollback/recovery model defined
- cross-source identity semantics understood
- storage authority boundary unchanged

#### Investigation questions

- What constitutes a safe content identity?
- How are partial/failed hashes represented?
- How are source provenance and destination provenance retained?
- How are collisions detected and handled?
- How are hardlinks/references represented without mutating TelDrive authority?
- How is rollback proven?
- What happens when source and CAS state disagree?
- Can a report be produced without any destructive operation?

#### Default product boundary

CAS may remain report-only indefinitely. No automatic production deduplication is implied by this stage.

#### Gates

- [ ] identity/provenance specification
- [ ] collision tests
- [ ] incomplete-hash tests
- [ ] rollback/recovery proof
- [ ] report-only dedup gate
- [ ] protected-production gate
- [ ] independent review of destructive-risk assumptions

## v1.1 completion gate

v1.1 is complete only when **all selected stages** have reached:

```text
PRIMITIVE
  ↓
IMPLEMENTED
  ↓
INTEGRATED
  ↓
OPERATIONAL
  ↓
END-TO-END VERIFIED
  ↓
DOCUMENTED
  ↓
COMPLETE
```

And the final v1.1 release candidate must additionally satisfy:

- full regression suite passes
- complete release gate matrix passes
- clean-install validation passes
- production-boundary validation passes
- no unverified capability claims in release documentation
- zero-cost runtime contract remains intact
- no v1.0 release tag is moved
- no production data is mutated by validation

## Explicitly out of scope

The following are **not** part of the current TelDrive Lab product contract and must not be treated as missing release requirements:

- Whisper / speech-to-text
- Ollama or any local LLM runtime
- cloud AI APIs
- autonomous AI mutation or authorization
- automatic production eviction
- automatic production deduplication
- unbounded remote workers

The codebase must not require these components for its normal test or release path.

## Safety model

```text
Observe
  ↓
Understand
  ↓
Plan
  ↓
Authorize
  ↓
Controlled executor
  ↓
Verify
  ↓
Audit / evidence
```

No planner, advisory layer, UI, or future integration may bypass the controlled mutation boundary.

## Release policy

A release is valid only when:

1. the working tree is clean locally;
2. CI is green at the release head;
3. production-boundary tests pass;
4. no documentation claims capabilities that are not implemented and evidenced;
5. optional components do not become hidden hard dependencies;
6. the exact release commit and tag relationship are recorded;
7. validation does not mutate production data.

The current product deliberately favors a smaller deterministic control plane over an AI-heavy archive platform.

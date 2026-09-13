# Release checklist

This checklist is a release-control document. A checked reconciliation gate means the gate itself has current code/test/host evidence; it does **not** by itself authorize creation of a release tag. Final release/tag readiness also requires the clean-worktree, release-note, and target-host conditions below.

## Reconciliation gates

- [x] **R0 — Product truth:** roadmap, status, code, tests, host gates, CI, and release claims agree at repository/CI level
- [x] **R1 — Corpus discovery:** authoritative bounded incremental TelDrive ingestion is operational and end-to-end verified
- [x] **R2 — Unified TD Search:** `td search` searches the discovered corpus across applicable metadata/content layers
- [x] **R3 — Media / OTT:** TelDrive media discovery reaches a real media library and Jellyfin playback is verified with safe test media
- [x] **R4 — Durable execution:** JobStore, Worker, TransferManager, rclone, Archive, Organization, Backup, Lifecycle, Verification, and Audit share one durable execution model
- [x] **R5 — Control Center:** dashboard consumes live control-plane state rather than placeholder/default payloads
- [x] **R6 — Production hardening:** final R6 release-hardening gate passes for zero-cost runtime, least-privilege CI, production boundaries, unsafe shell execution, complete gate matrix, and evidence-controlled claims

## R0 evidence checklist

- [x] Evidence-driven completion standard is documented
- [x] Phases 12–22 are no longer advertised as complete merely from code/adapters/contracts
- [x] Phase 6 is no longer advertised as complete before its documented end-to-end workflow exists
- [x] R0→R6 reconciliation program is documented
- [x] Configurable protected roots/state are implemented additively
- [x] Lab runtime state/cache paths are rejected when they resolve inside protected production boundaries
- [x] CI declares least-privilege repository permissions
- [x] CI has a bounded job timeout
- [x] CI invokes pytest through the configured Python interpreter
- [x] CI enforces the applicable reconciliation gates before later phase gates
- [x] Transfer error classification has one canonical implementation (`retry.py`); compatibility code is a shim
- [x] `advanced.py` is canonical and `extended.py` is a compatibility facade, with regression coverage retained
- [x] Resource-sensitive canonical operations use bounded/streaming primitives, with regression coverage blocking known unbounded patterns
- [x] Read-only HTTP/control-center surfaces default to loopback-only binding; non-loopback exposure is not part of the release surface
- [ ] R0 target-host validation has been rerun on the final release commit and recorded

## Phase 12–21 evidence boundary

- [x] Phase 12–21 implementation status distinguishes implemented capability from universal E2E verification
- [x] Optional providers remain capability-gated
- [x] Advisory AI remains non-authoritative
- [x] Experimental/remote-worker workflows remain isolated until separately proven
- [x] High-risk restore remains explicitly authorized and is not represented as silently production-safe
- [x] Phase 20 contracts are not represented as independent production integrations

The project intentionally does **not** claim that every optional P12–P21 capability has independent real-world E2E evidence. A future concrete workflow may earn `COMPLETE` by adding its own applicable integration and E2E evidence without weakening the global completion standard.

## Safety invariants

A release must not introduce:

- direct TelDrive PostgreSQL writes
- autonomous destructive storage administration
- silent production mutation
- authorization minted by a worker, planner, scheduler, or UI
- paid runtime dependencies
- mandatory remote AI
- claims of unlimited or permanent Telegram storage

Production TelDrive/Telegram data remains outside Lab ownership. Every consequential mutation must remain inside the policy → authorization → controlled execution → verification → audit lifecycle.

## Release candidate

Before an RC or release tag:

- [x] all applicable R0–R6 gates are green
- [ ] the repository is clean and the release commit is identified
- [ ] clean-install validation passes
- [x] operator and safety gates pass at the current R6 evidence level
- [ ] release notes describe only verified capabilities and limitations
- [x] final production-boundary hardening gate is green
- [ ] final release/tag decision is explicitly recorded

**Current interpretation:** the **core control-plane product is complete and release-hardened through R6**. The repository is not yet represented as having every optional P12–P21 capability independently E2E-verified, and an RC/tag must wait for the remaining checklist conditions rather than weakening that distinction.

The repository's final release sequence is: clean the target worktree, rerun the target-host verification on the final commit, perform clean-install validation, record release notes and the final decision, and only then create the RC or release tag.

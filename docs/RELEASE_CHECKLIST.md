# Release checklist

This checklist is a release-control document, not evidence that the repository is already release-ready. A checked item must have current code/test/host evidence.

## Reconciliation gates

- [x] **R0 — Product truth:** roadmap, status, code, tests, host gates, CI, and release claims agree at repository/CI level
- [x] **R1 — Corpus discovery:** authoritative bounded incremental TelDrive ingestion is operational and end-to-end verified
- [x] **R2 — Unified TD Search:** `td search` searches the discovered corpus across applicable metadata/content layers
- [x] **R3 — Media / OTT:** TelDrive media discovery reaches a real media library and Jellyfin playback is verified with safe test media
- [x] **R4 — Durable execution:** JobStore, Worker, TransferManager, rclone, Archive, Organization, Backup, Lifecycle, Verification, and Audit share one durable execution model
- [x] **R5 — Control Center:** dashboard consumes live control-plane state rather than placeholder/default payloads
- [ ] **R6 — Production hardening & release:** final target-host validation, clean working tree, full CI, boundary audit, documentation, and release decision are complete

## R0 evidence checklist

- [x] Evidence-driven completion standard is documented
- [x] Phases 12–22 are no longer advertised as complete merely from code/adapters/contracts
- [x] Phase 6 is no longer advertised as complete before its documented end-to-end workflow exists
- [x] R0→R5 reconciliation program is documented
- [x] Configurable protected roots/state are implemented additively
- [x] Lab runtime state/cache paths are rejected when they resolve inside protected production boundaries
- [x] CI declares least-privilege repository permissions
- [x] CI has a bounded job timeout
- [x] CI invokes pytest through the configured Python interpreter
- [x] CI enforces R0, Phase 4, and Phase 5 gates before later phase gates
- [x] Transfer error classification has one canonical implementation (`retry.py`); compatibility code is a shim
- [x] `advanced.py` is canonical and `extended.py` is a compatibility facade, with regression coverage retained
- [x] Resource-sensitive canonical operations use bounded/streaming primitives, with regression coverage blocking known unbounded patterns
- [x] Read-only HTTP/control-center surfaces default to loopback-only binding; non-loopback exposure is not part of the release surface
- [ ] R0 target-host validation has been rerun on the final release commit and recorded

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

Before an RC:

- all applicable R0–R6 gates are green
- the repository is clean and the release commit is identified
- clean-install validation passes
- operator and safety gates pass
- release notes describe only verified capabilities and limitations
- final production-boundary audit is green

Only then may an RC or release tag be created.

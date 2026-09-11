# Release checklist

This checklist is the release path after completion of the product roadmap. It deliberately separates release hardening from future feature development.

## R1 — Safety audit

- [x] Production storage boundary audited
- [x] Protected roots/state cannot be weakened by configuration
- [x] Mutation authorization is scope-bound
- [x] No direct TelDrive PostgreSQL writes
- [x] No arbitrary shell execution boundary
- [x] Paid dependencies absent

## R2 — Clean installation / host validation

- [x] Fresh virtual environment
- [x] Package installs successfully
- [x] CLI works outside the source tree
- [x] Full test suite passes in the clean environment
- [x] Protected production mutation is denied

## R3 — Operator drill

- [x] Lab-owned state initialized in an isolated location
- [x] Durable job created and inspected
- [x] Worker lease exercised
- [x] Pause/resume/cancel exercised
- [x] Job-control actions appear in audit history

## R4 — CI hardening

- [x] CI uses least-privilege read-only repository permissions
- [x] CI has a bounded job timeout
- [x] CI invokes pytest through the configured Python interpreter
- [x] Full phase/stage gate chain remains enforced

## R5 — Documentation

- [x] Installation guide
- [x] Operator guide
- [x] Release safety contract
- [x] Product roadmap and non-goals
- [x] Repository README points to operational documentation
- [x] Release checklist

## R6 — Release candidate

- [ ] Freeze feature work
- [ ] Confirm release branch/commit is clean
- [ ] Re-run clean-install validation
- [ ] Re-run operator and safety gates
- [ ] Review version and release notes
- [ ] Perform final production-boundary audit
- [ ] Tag an RC only after all checks pass

## R7 — v1.0

- [ ] RC has no release-blocking findings
- [ ] Final test/gate suite is green
- [ ] Final production-boundary audit is green
- [ ] Release notes accurately describe implemented capabilities and limitations
- [ ] Publish the v1.0 tag

## Release invariants

A release must not introduce:

- direct TelDrive database writes
- autonomous destructive storage administration
- silent production mutation
- paid runtime dependencies
- mandatory remote AI
- claims of unlimited or permanent Telegram storage

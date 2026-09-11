# TelDrive Lab Release Checklist

## Release hardening sequence

- [x] R1 — repository safety audit and remediation
- [x] R2 — clean-install / clean-host validation
- [x] R3 — operator drill
- [x] R4 — CI hardening
- [x] R5 — release documentation
- [x] R6 — release candidate hardening
- [ ] R7 — v1.0 release

## R1 — Safety

- [x] Production storage boundary is fail-closed.
- [x] No direct TelDrive PostgreSQL writes.
- [x] Destructive operations require scoped authorization receipts.
- [x] Configurable protected roots/state are additive only.
- [x] CI includes the Stage 8 gate.

## R2 — Clean installation

- [x] Fresh virtual environment installs the package successfully.
- [x] Package imports outside the source tree.
- [x] CLI entrypoint works outside the source tree.
- [x] Full test suite passes in the clean environment.
- [x] Protected production DELETE is denied.

## R3 — Operator drill

- [x] Lab-owned runtime state initializes separately from production data.
- [x] Durable jobs can be created and inspected.
- [x] Jobs can be paused and resumed by explicit operator action.
- [x] Jobs can be cancelled by explicit operator action.
- [x] Job-control actions are visible in the audit log.

## R4 — CI

- [x] Workflow uses least-privilege repository permissions.
- [x] Workflow has a finite timeout.
- [x] Package is installed before tests.
- [x] Tests run through the workflow Python interpreter.
- [x] Phase and Stage gates remain in CI.

## R5 — Documentation

- [x] Installation guide is present and accurate.
- [x] Operator guide covers normal operation and troubleshooting.
- [x] Release safety contract documents production boundaries.
- [x] Product roadmap and non-goals remain explicit.
- [x] README points operators to the relevant documentation.
- [x] This release checklist records release state.

## R6 — Release Candidate

- [x] Freeze feature work.
- [x] Re-run clean-install validation from the release candidate commit.
- [x] Re-run operator and production-safety gates.
- [x] Review package version and release notes.
- [x] Perform final production-boundary audit.
- [x] Create an RC tag only after all release-blocking checks pass.

RC tag: `v1.0.0-rc1`

## R7 — v1.0

- [ ] RC has no release-blocking findings.
- [ ] Final test suite and gates are green.
- [ ] Final production-boundary audit is green.
- [ ] Release notes accurately describe supported behavior and limitations.
- [ ] Publish the v1.0 tag.

## Release invariants

A release must not introduce:

- direct TelDrive database mutation;
- autonomous destructive storage administration;
- silent production mutation;
- paid runtime dependencies;
- mandatory remote AI services;
- claims of unlimited or permanent Telegram storage.

Stage 8 is the final product-roadmap stage. R6 and R7 are release activities, not a new feature roadmap.
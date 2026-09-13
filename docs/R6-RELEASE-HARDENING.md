# R6 — Production Hardening & Release

**Status:** ACTIVE

R6 is the final hardening gate before any release tag. It does not add feature scope. It verifies that the reconciled control plane remains safe, reproducible, zero-cost, and honestly documented.

## Release principle

```text
AUDIT → TEST → SAFETY GATE → CLEAN INSTALL → FULL CI → DOCUMENT → RELEASE DECISION
```

A green R6 gate is necessary but is not, by itself, permission to create a release. The release checklist must also be satisfied.

## Required evidence

1. **Repository/runtime contract** — Python version and packaging are reproducible; runtime dependencies remain zero-cost and no paid service is mandatory.
2. **CI security** — GitHub Actions uses least-privilege repository permissions and a bounded job timeout.
3. **Safety boundary** — production TelDrive, PostgreSQL, Telegram-backed storage, rclone mounts/services, authentication state, DNS, and public routing remain outside default Lab ownership.
4. **Execution safety** — no uncontrolled shell execution patterns are introduced; consequential operations remain behind the Lab safety/authorization/execution/verification/audit model.
5. **Reconciliation matrix** — R0, R1, R2, R3, R4, R5 and the historical host gates remain present in CI.
6. **End-to-end evidence** — applicable host gates and disposable integrations use Lab-owned fixtures and do not mutate production.
7. **Documentation truth** — roadmap, architecture, safety contracts, R3/R4/R5 documents, and release checklist do not claim unsupported capabilities.
8. **Clean-install evidence** — CI installs the package from a clean checkout before executing tests and gates.
9. **Final production-boundary review** — no release step requires changing production TelDrive/rclone configuration, data, database state, DNS, or public exposure.

## Explicit non-goals

R6 does not authorize:

- production TelDrive database writes;
- production file deletion, movement, renaming, or migration;
- rclone mount/service reconfiguration;
- DNS or reverse-proxy changes;
- public exposure;
- mandatory remote AI;
- paid infrastructure or APIs.

## Release decision

Only after the release checklist is fully evidenced may a release candidate or release tag be created.

Until then, `main` is the verified engineering baseline, not a production-release claim.

# R6 Release Hardening

R6 is the final release-hardening boundary for the current TelDrive Lab core control plane.

## Purpose

R6 does not add a new product subsystem. It verifies that the already-completed R0–R5 control plane is safe to release under the current product contract.

## Release invariants

- TelDrive remains the production storage authority.
- Lab-owned state is derived, bounded, and auditable.
- Production mutation remains behind policy, explicit authorization, controlled execution, verification, and audit evidence.
- No direct TelDrive PostgreSQL writes are permitted.
- No autonomous planner, UI, worker, or AI provider can mint production authorization.
- CI uses least-privilege repository permissions and bounded execution time.
- The normal runtime path has no paid service, cloud AI, or mandatory local LLM dependency.
- Optional integrations remain optional and cannot silently become release prerequisites.
- Destructive storage actions remain explicitly authorized and are never automatic.

## Gate coverage

The R6 gate validates:

1. zero-cost dependency contract;
2. least-privilege CI and bounded CI execution;
3. production-boundary and safety-contract language;
4. unsafe shell-execution patterns are absent from Python sources;
5. the complete R0–R5 and legacy host-gate matrix remains wired into CI;
6. the active release checklist contains the final release sequence and release-tag boundary.

## Evidence boundary

R6 is repository/CI hardening only. It does not connect to or mutate the real TelDrive deployment. Live production validation must remain separately authorized and operationally controlled.

## Completion standard

`IMPLEMENTED → INTEGRATED → OPERATIONAL → END-TO-END VERIFIED → DOCUMENTED → COMPLETE`

R6 is complete only when its gate passes at the release candidate commit and the final release checklist conditions are satisfied.

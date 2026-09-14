# R1 — Corpus Discovery

## Purpose

R1 establishes the read-only discovery boundary between the real TelDrive/rclone corpus and the Lab-owned catalog. It discovers remote metadata without downloading file contents or performing storage mutation.

## Release contract

- TelDrive remains the storage authority.
- Discovery is read-only and uses the configured TelDrive rclone remote.
- Recursive listing is bounded by an explicit entry limit and timeout.
- Discovery records canonical Lab-owned catalog observations with stable TelDrive provenance.
- Reconciliation may report stale observations but does not delete remote or catalog data.
- Remote file contents are not downloaded or hashed during discovery (`sha256=None`).
- rclone commands are restricted to metadata listing; mutation/configuration commands are rejected by the R1 gate.
- The remote is configured explicitly through `TELDRIVE_LAB_TELDRIVE_RCLONE_REMOTE`.
- R1 tests and the R1 product gate must remain disposable and must not mutate production TelDrive data.

## Evidence

The R1 implementation is exercised by `tests/test_r1_corpus_discovery.py` and `scripts/r1_corpus_discovery_gate.py`. The gate verifies the required source, catalog, test, and documentation artifacts plus the read-only, bounded discovery contract.

## Safety boundary

R1 does not write directly to the TelDrive PostgreSQL database and does not authorize destructive storage operations. Catalog state is Lab-owned derived state. Any consequential operation remains subject to the later policy, authorization, durable execution, verification, and audit boundaries.

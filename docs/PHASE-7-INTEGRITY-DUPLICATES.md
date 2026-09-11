# Phase 7 — Integrity & Duplicate Intelligence

**Status:** complete
**Safety class:** read-only evidence and reporting
**Cost target:** ₹0 / $0

## Goal

Phase 7 establishes trustworthy checksum evidence, verification reports, stale-checksum detection, and duplicate intelligence without granting the system any destructive authority.

## Canonical invariants

```text
SHA-256 + size = duplicate identity
DUPLICATE FOUND != DELETE
verification failure != repair authorization
report != mutation
```

The Lab catalog remains derived state. The Phase 7 checksum evidence database is also Lab-owned derived state and can be rebuilt. Neither database is a storage authority.

## Components

### `teldrive_lab/integrity.py`

Provides:

- SHA-256 hashing using bounded streaming reads
- expected size + SHA-256 verification
- explicit states: `VERIFIED`, `MISSING`, `CHANGED`, `MISMATCH`, `UNVERIFIABLE`
- Lab-owned SQLite checksum evidence at `~/.local/share/teldrive-lab/integrity.db`
- duplicate groups by `(size, SHA-256)`
- missing verified-copy reporting
- stale checksum evidence detection using stored size + mtime
- optional BLAKE3 benchmark when the package is already installed
- no automatic dependency installation

### CLI

```text
td verify --source-type LOCAL --source-id <id>
td duplicates --source-type LOCAL --source-id <id>
```

Both commands are read-only. `duplicates` explicitly reports that destructive action is `NONE`.

### Transfer verification

Phase 4 already verifies local copies using source/destination SHA-256 before atomic publication. Phase 7 reuses that checksum contract for catalog-wide evidence and reporting rather than duplicating a second transfer implementation.

### Duplicate policy

Duplicate groups are informational. The planner reports:

- file count
- size
- SHA-256
- paths
- potential reclaimable bytes

No delete, merge, rename, overwrite, quarantine, or migration is performed.

## Stale checksum model

Checksum evidence records:

```text
path
size
sha256
modified_ns
computed_at
state
```

If current size or modification timestamp differs from the stored evidence, the checksum is stale and must be recomputed before treating the evidence as current.

A checksum mismatch is evidence of an integrity problem, not permission to replace the file.

## BLAKE3

SHA-256 remains canonical for Phase 7. The benchmark can compare BLAKE3 only when an already-installed `blake3` package exists. Phase 7 never installs a dependency and never changes the canonical algorithm automatically.

```bash
PYTHONPATH="$PWD" python scripts/phase7_benchmark.py <file>
```

## Safety boundary

All Phase 7 operations are observational. The host gate also checks that a production `DELETE` remains blocked even when explicit authorization is supplied.

No production TelDrive, Telegram data, rclone mount, PostgreSQL database, Docker service, DNS, or source repository is modified by Phase 7.

## Exit criteria

- SHA-256 checksum evidence is durable and Lab-owned
- verification detects missing, changed, and mismatched files
- duplicate groups are deterministic and informational
- missing verified copies are reportable
- stale checksum evidence is detectable
- transfer verification remains checksum-based
- optional BLAKE3 benchmark is non-authoritative
- CLI reports are read-only
- automated tests and the host gate pass
- destructive production operations remain fail-closed

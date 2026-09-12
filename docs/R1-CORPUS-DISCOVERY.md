# R1 — Automatic TelDrive Corpus Discovery

## Goal

Make the existing TelDrive corpus visible to TelDrive Lab without requiring the operator to add files manually.

TelDrive remains the source of truth. The Lab owns only a rebuildable derived catalog.

## Architecture

```text
Existing TelDrive
      │
      │ read-only rclone listing
      ▼
RcloneTelDriveSource
      │
      │ bounded metadata observations
      ▼
Lab Catalog (SQLite)
      ├── TD Search
      ├── duplicate detection
      ├── organization planning
      ├── archive planning
      └── future media metadata
```

The filesystem indexer remains useful for local/Lab-owned roots, but it is not the authority for TelDrive corpus discovery. R1 uses the existing TelDrive-facing rclone remote as the observation source.

## Safety contract

R1 is strictly read-only against TelDrive:

- only `rclone lsf --recursive --files-only` is used;
- no copy, move, delete, purge, sync, mount, or config command is invoked;
- file contents are not downloaded;
- SHA-256 is not calculated during discovery;
- catalog records are written only to the Lab-owned SQLite database;
- disappeared remote paths are reported as `stale_paths` and are **not deleted** from the catalog;
- every run is bounded by a maximum entry count and subprocess timeout.

The discovery adapter receives an explicit existing rclone remote. It never guesses credentials or modifies rclone configuration.

## Configuration

Set:

```bash
export TELDRIVE_LAB_TELDRIVE_RCLONE_REMOTE='teldrive:'
```

or pass `--remote` directly.

Optional remote subdirectory:

```bash
python scripts/discover_teldrive.py --remote 'teldrive:' --root 'Movies'
```

## Operation

```bash
cd ~/teldrive-lab
PYTHONPATH="$PWD" python scripts/discover_teldrive.py --remote 'teldrive:'
```

The result reports:

- discovered object count;
- skipped observations;
- whether the hard bound was reached;
- the stable catalog source identifier;
- stale paths from the previous observation;
- observation timestamp;
- `mutation: NONE`.

The catalog identity is:

```text
(source_type=TELDRIVE, source_identifier=rclone:teldrive:<remote>/<root>, path=<remote-relative-path>)
```

## Incremental behavior

R1 is safe to repeat. Existing observations are upserted and preserve their original `first_seen_at`. Each successful observation updates `last_seen_at`.

If a path disappears from the remote, R1 does not infer deletion authority. It reports the path as stale so a later reconciliation/integrity workflow can decide what it means.

## Completion standard

R1 is complete only when all of these are true:

- **Implemented:** TelDrive/rclone source adapter and catalog ingestion exist.
- **Integrated:** discovery writes through the canonical Lab catalog.
- **Operational:** an operator can run the discovery command against an existing rclone TelDrive remote.
- **End-to-end verified:** isolated fake-rclone tests prove ingestion, repeat/reconciliation, bounds, and failure behavior.
- **Documented:** this contract and safety boundary are documented.

R1 does not claim TD Search, Jellyfin, or control-center integration; those belong to R2, R3, and R5 respectively.

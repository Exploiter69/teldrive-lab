# Phase 11 — CLI & Operator Experience

## Goal

Provide one coherent, scriptable terminal interface for the TelDrive Lab sidecar without introducing a web UI or weakening the safety contract.

The CLI is an operator surface, not a second storage authority. TelDrive remains the production storage authority and Lab runtime state remains under `~/.local/share/teldrive-lab/`.

## Operator commands

### Status and health

```text
td status
td health
td init
```

These are read-only observations. `td init` only creates Lab-owned runtime directories.

### Catalog discovery

```text
td index <root> [--source-type ...] [--source-id ...]
td search <query> [--limit N]
```

`index` uses the existing bounded, read-only indexer. It records filesystem metadata only; it does not open file contents, follow symlinks, reorganize files, or delete stale records. `search` only queries the Lab catalog.

### Jobs

```text
td jobs [--state STATE] [--limit N]
td job <id>
td pause <id>
td resume <id>
td cancel <id>
```

Job inspection is read-only. Pause/resume/cancel are explicit Lab-owned queue controls and are audited. They do not authorize or perform a TelDrive production mutation.

### Audit

```text
td audit [--limit N] [--operation OPERATION]
```

Audit output is read-only and comes from the Lab-owned audit database.

### Monitoring

```text
td monitor run
td monitor health
td monitor jobs
td monitor alerts
td monitor alerts --all-alerts
td monitor storage --path <path>
```

Monitoring follows **Observe → Evaluate → Record → Notify**. It does not automatically repair production state.

### Existing safety-gated workflows

The Phase 4–10 control surfaces remain available:

```text
td organize ... --dry-run
td organize ... --apply
td archive ... --dry-run
td archive ... --apply
td verify ...
td duplicates ...
td lifecycle purge ...
td lifecycle restore ...
td backup plan ...
td backup apply ...
td backup verify ...
td backup restore ...
td backup-schedule ...
```

Mutating workflows continue to require explicit command intent and pass through their existing Policy/Authorization/Transfer/Verification boundaries.

## Output contract

All normal CLI output is JSON with stable field names, making the interface suitable for shell scripts and future systemd timers. Errors are emitted as JSON where practical and use non-zero exit codes.

Exit code convention:

- `0` — successful observation or completed operation
- `1` — operation completed but reported a failed verification/active monitoring condition
- `2` — invalid request, blocked plan, missing required explicit flag, or impossible job transition

## Safety properties

Phase 11 does **not**:

- modify TelDrive's PostgreSQL database
- modify Telegram storage
- alter rclone configuration or mounts
- modify Docker configuration
- change DNS or public exposure
- delete/reorganize production files automatically
- bypass the Policy Engine
- treat AI as authorization

The CLI can expose a production path as an argument only where an existing subsystem already defines a safe read-only or explicitly authorized boundary. It never creates a new production mutation path.

## Host gate

`scripts/phase11_host_gate.py` exercises the CLI using a temporary Lab-owned runtime:

1. initializes isolated runtime
2. indexes a synthetic directory
3. searches the catalog
4. creates and inspects a durable job
5. pauses/resumes/cancels the job
6. verifies audit visibility
7. observes isolated storage
8. confirms no production path is touched

The gate does not contact or mutate the live TelDrive installation.

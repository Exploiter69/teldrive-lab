# Phase 10 — Monitoring & Notifications

## Goal

Phase 10 adds a durable, local-only observability layer over the completed TelDrive Lab phases. The model is:

`OBSERVE → EVALUATE → RECORD → NOTIFY`

Monitoring is advisory and read-only with respect to the existing TelDrive installation.

## Monitored surfaces

- existing TelDrive/rclone/Docker health probes from the Phase 1 health layer
- filesystem capacity and free-space thresholds
- durable Lab job state, including stale running/verifying jobs and recorded workers
- backup schedule/verification status supplied to the evaluator
- integrity failures supplied to the evaluator
- deterministic alert state and local notification history

## Alert classes

- `DISK_SPACE_LOW`
- `DISK_SPACE_CRITICAL`
- `BACKUP_OVERDUE`
- `BACKUP_FAILED`
- `BACKUP_CORRUPT`
- `JOB_STUCK`
- `WORKER_UNAVAILABLE`
- `INTEGRITY_FAILURE`
- `TELDRIVE_UNHEALTHY`

Default disk thresholds are 15% free for warning and 5% for critical.

## Durable state

`MonitoringStore` owns a separate SQLite database under the Lab runtime. It stores alert fingerprints, severity, first/last seen timestamps, occurrence counts, active/resolved state, details, and local notification records. It never writes to TelDrive's database or Telegram storage.

Alert fingerprints make repeated observations deterministic. When a condition disappears, the previous alert is resolved instead of deleted, preserving history.

## Notifications

The first notification channel is `local`: a durable SQLite notification record suitable for CLI/systemd/journal presentation. No paid SaaS, cloud API, webhook provider, or subscription is required.

A future notification adapter may read these records and send through an explicitly configured local/free mechanism without changing the monitoring policy engine.

## CLI

```text
# one read-only monitoring pass
td monitor run

# individual read-only views
td monitor health
td monitor jobs
td monitor alerts
td monitor alerts --all-alerts
td monitor storage
```

The existing `td status` command remains available.

## Safety boundary

Phase 10 does **not**:

- change TelDrive
- change Telegram data
- mutate PostgreSQL
- remount or reconfigure rclone
- change Docker configuration
- delete, move, rename, overwrite, or reorganize production files
- purge backups automatically
- repair production systems automatically
- change DNS or public exposure

Health failures generate evidence and alerts only. Any future repair operation must pass through the existing Phase 1–9 safety/authorization lifecycle.

## Validation

Phase 10 includes unit tests and an isolated host gate. The host gate creates only temporary Lab-owned SQLite state, verifies durable alerts/notifications and resolution, and explicitly reports production mutation as `NONE`.

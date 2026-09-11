# TelDrive Lab operator guide

TelDrive Lab is a local-first, auditable sidecar around an existing TelDrive deployment. TelDrive remains the production storage authority. This guide describes the normal operator workflow without requiring knowledge of the implementation.

## 1. Install and initialize

Use Python 3.11 or newer:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
td init
```

Lab-owned runtime state defaults to `~/.local/share/teldrive-lab`; cache defaults alongside the Lab runtime unless `TELDRIVE_LAB_STATE` or `TELDRIVE_LAB_CACHE` is configured.

## 2. First checks

Run:

```bash
td health
td status
td jobs
```

These commands are observational. They do not modify TelDrive, Telegram storage, rclone configuration, or production data.

Health reports available host capabilities such as Docker, rclone, disk space, and protected storage paths. An unavailable optional provider is a degraded capability, not a reason to introduce a paid fallback.

## 3. Job operations

The Lab uses durable jobs so work can be inspected and controlled independently of a worker process.

Useful commands:

```bash
td jobs
td job <JOB_ID>
td pause <JOB_ID>
td resume <JOB_ID>
td cancel <JOB_ID>
td audit --operation JOB_CONTROL
```

Pause, resume, and cancel are explicit operator queue controls. They are audited. They do not by themselves authorize a TelDrive production mutation.

A normal operator lifecycle is:

```text
QUEUED → RUNNING → PAUSED → QUEUED
                         └→ CANCELLED
```

Workers use leases; the durable job record remains the source of truth for queue state.

## 4. Production safety boundary

Never treat the Lab as the owner of TelDrive production storage.

Protected production data includes the existing Telegram-backed storage roots and TelDrive production state. The Lab does not write directly to the TelDrive PostgreSQL database.

Mutation follows:

```text
Policy → Authorization → Execution → Verification → Audit
```

Mutation authorization is scope-bound. An authorization receipt must match the requested operation and normalized paths exactly and must be approved. A valid receipt cannot override the protected production boundary.

On a different host, additional protected roots/state may be configured with:

- `TELDRIVE_LAB_PROTECTED_ROOTS`
- `TELDRIVE_LAB_PROTECTED_STATE`

These settings are additive: configuration can strengthen protection but cannot remove the built-in protected paths.

## 5. Transfers and rclone

When byte movement is required, prefer the mature rclone boundary rather than rebuilding a transfer engine.

The Lab owns policy, authorization, durable job state, verification evidence, provenance, and audit. rclone provides transfer/protocol primitives.

Do not expose arbitrary shell commands through the Lab or treat rclone as an authorization mechanism.

## 6. Integrity, duplicates, and organization

Integrity verification produces evidence owned by the Lab. Duplicate detection is report-only by default and must never be interpreted as permission to delete an object.

Organization features should be evaluated as a plan/dry-run before any authorized mutation. Destructive cleanup, overwrite, retention changes, or moving the only verified copy are not autonomous operations.

## 7. Backups and recovery

Back up Lab-owned state and verify that restore procedures work before relying on mutation-capable workflows.

The Lab catalog and audit evidence are derived/control-plane state; loss of this state must not be confused with loss of the underlying stored objects. Keep exportable manifests and verified-copy evidence where supported.

A provider outage should result in a degraded/paused workflow, preservation of local metadata and cached material, and recovery or evacuation planning—not destructive cleanup.

## 8. Optional capabilities

rclone, Docker, FFmpeg, Tesseract, Whisper, Ollama, and other integrations are optional. Core operation must remain useful without an LLM or paid service.

AI, when enabled, is advisory. It cannot authorize deletion, overwrite data, change retention, restore over existing content, expose private data, or migrate the only verified copy.

## 9. Audit and troubleshooting

Use the audit log to answer what the Lab attempted, what authorization decision was made, and what result was recorded. Prefer audit evidence over assumptions from a worker's console output.

For a failed job:

1. inspect the job record;
2. inspect relevant audit events;
3. determine whether the failure is provider, policy, authorization, execution, or verification related;
4. retry only within the job's bounded retry semantics;
5. pause/cancel when continued execution is unsafe.

Do not repair production state by editing the TelDrive database directly.

## 10. Resource-conscious operation

The primary target is a modest local machine. Avoid unnecessary always-on services, mandatory search clusters, mandatory embeddings, or remote AI dependencies. Prefer SQLite/local processing and mature external tools where they already solve the problem.

## 11. What TelDrive Lab does not promise

TelDrive/Telegram is a supported storage substrate, not a promise of unlimited or permanent storage. Do not assume undocumented provider limits, guaranteed throughput, or a single Telegram account as the only verified copy.

The Lab is not a TelDrive replacement, rclone replacement, filesystem, media server, OTT service, or autonomous storage administrator.

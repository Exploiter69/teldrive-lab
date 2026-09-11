# TelDrive Lab Operations Guide

## Purpose

TelDrive Lab is a local-first, auditable storage control plane and archive layer around an existing TelDrive deployment and other storage providers. TelDrive remains the production storage authority.

The core safety flow is:

**Policy → Authorization → Execution → Verification → Audit**

The Lab must remain useful without an LLM, Ollama, paid API, or paid infrastructure.

## Installation and initialization

See [INSTALL.md](INSTALL.md) for prerequisites, virtual-environment setup, installation, runtime-state configuration, and optional integrations.

Initialize Lab-owned state with:

```bash
td init
```

By default runtime state is under `~/.local/share/teldrive-lab` and cache under `~/.cache/teldrive-lab`. Keep Lab state and cache separate from TelDrive production data.

## First checks

Use observational commands before operating on jobs or transfers:

```bash
td status
td health
td jobs
```

These commands inspect the environment and Lab-owned state. They do not authorize production mutation.

## Durable jobs

Jobs are stored durably in the Lab-owned queue. A job record is not permission to mutate production storage.

Inspect jobs with:

```bash
td jobs
td job <JOB_ID>
```

Operators may explicitly pause, resume, or cancel Lab-owned jobs. These controls are audited and do not bypass production policy.

```bash
td pause <JOB_ID>
td resume <JOB_ID>
td cancel <JOB_ID>
```

Inspect operator actions with:

```bash
td audit --operation JOB_CONTROL
```

## Production safety boundary

Do not point Lab state or cache at `~/TelegramRaw`, `~/TelegramDrive`, the TelDrive production database, or other production state.

Production paths are protected by the safety layer. Destructive operations must fail closed unless a valid, scope-bound authorization receipt exactly matches the requested operation and normalized paths.

The protected boundary is additive: `TELDRIVE_LAB_PROTECTED_ROOTS` and `TELDRIVE_LAB_PROTECTED_STATE` can add host-specific paths but cannot remove the built-in production protections.

There is no direct TelDrive PostgreSQL write path in the Lab.

## Transfers and rclone

Use the Lab's transfer boundary for supported transfers. rclone is an execution adapter, not the Lab's authority model. Non-dry-run transfer execution requires explicit scoped authorization and remains subject to verification and audit.

If a task is primarily about moving bytes between providers, prefer rclone rather than rebuilding a general transfer engine.

## Integrity, duplicates, and organization

Integrity operations are evidence-oriented. Lab-owned checksum evidence can be used to verify copies and detect missing verified copies.

Duplicate analysis is report-only. It must not silently delete, overwrite, evict, rename, or reorganize production storage.

Organization and lifecycle recommendations remain advisory until an explicitly authorized workflow is executed through the safety boundary.

## Backups and recovery

Use the Lab's backup and snapshot facilities for Lab-owned state and recovery drills. Establish and verify a recovery path before attempting any production-affecting workflow.

A successful backup or snapshot does not grant permission to mutate TelDrive storage.

## Optional capabilities

rclone, Docker, FFmpeg, Tesseract, Whisper, Ollama, and model providers are optional. Missing optional dependencies should produce unavailable capability behavior rather than an automatic paid fallback.

AI features are advisory. AI output never becomes authorization or production authority by itself.

## Audit and troubleshooting

Prefer read-only inspection first:

```bash
td health
td status
td jobs
td audit
```

For an unexpected denial, inspect the requested operation, normalized paths, and authorization receipt scope. Do not weaken the safety boundary to make an operation succeed.

For an unexpected job state, inspect the durable job record and audit history before retrying. Worker leases and queue state are Lab-owned coordination mechanisms.

## Resource-conscious operation

TelDrive Lab is designed for resource-constrained local operation. Avoid unnecessary whole-object reads, duplicate indexing work, and long-running local model processes when they are not required.

Do not introduce paid services merely to improve convenience or performance.

## What TelDrive Lab does not promise

TelDrive Lab is not:

- a replacement for TelDrive;
- a replacement for rclone;
- a filesystem or general-purpose automation platform;
- a media server or OTT service;
- an autonomous storage administrator;
- a mandatory AI system;
- a guarantee of unlimited or permanent Telegram storage.

Production storage remains under explicit human-controlled policy and authorization.
# TelDrive Lab

TelDrive Lab is a **local-first, auditable storage control plane and intelligent archive layer** around TelDrive and other storage providers.

It adds durable jobs, policy and authorization boundaries, verification evidence, metadata, organization, search, recovery, monitoring, and safe interoperability without taking ownership of TelDrive production storage.

## Safety first

- TelDrive remains the production storage authority.
- No direct TelDrive PostgreSQL writes.
- Existing Telegram-backed storage remains protected.
- Destructive production operations are never autonomous.
- Mutation follows **Policy → Authorization → Execution → Verification → Audit**.
- Duplicate detection is report-only; it never implies deletion.
- AI is optional and advisory, never an authorization authority.
- Optional providers fail explicitly; there is no paid fallback.
- ₹0 / $0 infrastructure is a hard constraint.

## Install

Requirements: Python 3.11+ and Git. The core package has no runtime dependencies.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
td init
td health
td status
```

Runtime state is Lab-owned and defaults to `~/.local/share/teldrive-lab`. Use `TELDRIVE_LAB_STATE` and `TELDRIVE_LAB_CACHE` to relocate Lab state/cache. Do not point them at TelDrive production data.

## Operator workflow

```bash
td jobs
td job <JOB_ID>
td pause <JOB_ID>
td resume <JOB_ID>
td cancel <JOB_ID>
td audit --operation JOB_CONTROL
```

Pause/resume/cancel are explicit queue controls and are audited. See the operator guide for the complete workflow and recovery model.

## Documentation

- [`docs/INSTALL.md`](docs/INSTALL.md) — installation and first checks
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — day-to-day operation, jobs, safety, transfers, integrity, backups, and recovery
- [`docs/RELEASE_HARDENING.md`](docs/RELEASE_HARDENING.md) — release safety contract
- [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md) — product identity, architecture, roadmap, and non-goals

## Architecture boundary

TelDrive Lab owns the control plane: policy, authorization, durable jobs, metadata, verification, audit, organization, search, recovery, and product-level health.

TelDrive/Telegram owns stored objects and provider state. rclone owns mature transfer/protocol primitives. Jellyfin owns media presentation and playback. External automation may consume safe events and APIs. AI may suggest or explain, but never self-authorize.

## Resource-conscious and provider-independent

The primary target is a modest local machine. Core functionality remains useful without an LLM. rclone, Docker, FFmpeg, Tesseract, Whisper, Ollama, and other integrations are optional.

Telegram is a supported provider/substrate, not a promise of unlimited or permanent storage. Keep independent verification and recovery evidence for important data.

## Development

```bash
python -m pip install -e .
python -m pytest
```

The repository CI runs the test suite plus the project phase/stage safety gates.

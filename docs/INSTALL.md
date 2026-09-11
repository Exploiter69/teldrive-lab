# TelDrive Lab installation

TelDrive Lab is a local sidecar. It does not replace or reconfigure an existing TelDrive deployment.

## Requirements

- Python 3.11+
- Git
- No paid service or API is required.
- Optional providers such as rclone, Docker, FFmpeg, Tesseract, Whisper, and Ollama are detected but are not required by the core.

## Install from a checkout

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

The package exposes the `td` command. The core package has no runtime dependencies.

## Initialize Lab-owned state

```bash
td init
```

By default state is under `~/.local/share/teldrive-lab`. Override it with `TELDRIVE_LAB_STATE`; cache may be overridden with `TELDRIVE_LAB_CACHE`.

## First checks

```bash
td health
td status
```

These are observational. They do not modify TelDrive, Telegram storage, rclone configuration, or production data.

## Optional capabilities

The productization layer detects optional local executables. Missing optional providers are reported as unavailable; the Lab must not silently substitute a paid or remote service.

## Safety boundary

Production storage remains outside the Lab's ownership boundary. Mutating workflows must continue through the existing policy, authorization, execution, verification, and audit path. Do not point Lab-owned state or cache at `~/TelegramRaw`, `~/TelegramDrive`, or TelDrive production databases.

## Recovery

Before using any mutation-capable Lab workflow, keep Lab state backed up using the existing backup/snapshot capabilities and perform a restore drill. A provider outage must not imply loss of Lab metadata or audit evidence.

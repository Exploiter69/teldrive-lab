# Changelog

## 1.0.0 — 2026-09-12

TelDrive Lab 1.0.0 is the first release-ready baseline of the local-first, auditable storage control plane and intelligent archive layer around an existing TelDrive deployment.

### Included

- Durable Lab-owned jobs, execution, verification, audit, lifecycle, backup, snapshot, indexing, search, and monitoring workflows.
- Deterministic production safety boundary with fail-closed protection for existing TelDrive/Telegram storage and state.
- Scope-bound authorization receipts for mutating operations.
- Local transfer verification with temporary-file commit and SHA-256 verification.
- Integrity evidence and report-only duplicate detection.
- Provider-independent transfer boundaries with optional rclone integration.
- Advisory intelligence and local AI experimentation without granting AI authorization authority.
- Stage 8 advanced experiments isolated from production mutation.
- Operator CLI and documented installation, operations, safety, and release procedures.

### Release invariants

- No direct TelDrive PostgreSQL writes.
- No autonomous destructive production storage administration.
- No silent production mutation.
- No paid runtime dependencies.
- No mandatory remote AI service.
- No claim of unlimited or permanent Telegram storage.

The `v1.0.0-rc1` candidate was frozen and validated before this final release preparation.

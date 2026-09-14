# TelDrive Lab v1.0.0-rc2

Release candidate for the R0–R6 hardened TelDrive Lab control plane.

## Verified capabilities

- Canonical, bounded, read-only TelDrive resource handling.
- Read-only TelDrive corpus discovery with canonical catalog ingestion and incremental reconciliation.
- Unified SQLite FTS5 search with bounded queries, filtering, pagination, and deterministic ordering.
- Media classification and controlled read-only media exposure.
- Real Jellyfin integration verification, including library indexing and real media streaming.
- Durable execution with worker fencing, persisted lifecycle state, lease recovery, cancellation/retry fencing, and audit evidence.
- Read-only loopback Control Center exposing live catalog, jobs/execution, transfers/workflow, search, media, health, audit, and configuration/safety state.
- Production-boundary controls keeping consequential mutation behind deterministic policy, authorization, executor, verification, and audit boundaries.
- Release hardening covering dependency, CI permission/timeout, safety-contract, and gate-matrix checks.
- Legacy P12–P21 extension surfaces remain governed by their actual implementation/evidence status and are not treated as unsupported provider commitments.

## Verification evidence

The release candidate is based on the R6-hardened mainline and has passed the repository gate matrix locally, including R0–R6 and Phase 4–11 plus Phase 12–22 host gates. The real Jellyfin host gate passed with a disposable container, read-only media mount, library scan/index, and real media stream. Clean-install import and the full pytest suite also passed from a fresh virtual environment.

GitHub Actions passed on commit `20b11c1bebb4ab6f6a7b36b03507384acfdfd18b` (`fix: tolerate transient Jellyfin startup resets`).

No production TelDrive/Telegram mutation was performed by these validations.

## Explicit non-goals

- No direct TelDrive PostgreSQL writes.
- No autonomous destructive storage administration.
- No worker, planner, UI, or AI authority to mint production authorization.
- No paid runtime dependency.
- No mandatory remote AI service.
- No claim of unlimited or permanent Telegram storage.
- Whisper/speech-to-text and Ollama/local-LLM runtime are outside this release scope.

## Candidate status

This document records only capabilities and validation evidence already established. The final RC tag must be created only after the exact candidate commit containing the final documentation is CI-green and the final local release checks have passed on that same commit.

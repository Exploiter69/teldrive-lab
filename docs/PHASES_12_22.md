# TelDrive Lab — Phases 12–22

## Completion policy

Phases 12–22 are implemented as a **safe extended capability layer** over the Phase 0–11 control plane. The implementation intentionally favors deterministic, local, zero-cost functionality over optional third-party services.

| Phase | Delivered capability |
|---|---|
| 12 | hot/warm/cold observation, cache pressure, eviction planning, RAM-aware concurrency |
| 13 | read-only catalog JSON export and validation |
| 14 | media discovery and sidecar library manifests |
| 15 | bounded local text extraction and document fingerprints |
| 16 | local content search over supported text files |
| 17 | advisory AI contract with deterministic fallback; policy/authorization/verification/audit remain authoritative |
| 18 | storage economics and growth forecasting |
| 19 | deterministic snapshot manifests and verification |
| 20 | explicit read-only integration contracts for other engineering projects |
| 21 | isolated experimental registry and safe experiment boundaries |
| 22 | framework-neutral control-center payload; UI is a client, never the authority |

## Safety invariants

The extended layer does **not**:

- write to TelDrive's production database;
- delete or reorganize production files;
- automatically evict cache or production data;
- rewrite rclone/Docker/systemd configuration;
- authorize destructive operations;
- give AI authority over policy or execution;
- expose a UI mutation path by default.

All future mutating workflows must continue through the existing Lab policy, authorization, execution, verification, and audit boundaries.

## What "complete" means here

Optional external ecosystems such as Jellyfin/Plex, OCR engines, speech-to-text models, embedding stores, local LLM runtimes, remote workers, and browser UI frameworks are represented by stable contracts or sidecar-ready primitives rather than being made mandatory dependencies. This preserves the zero-cost requirement and keeps the core deterministic and testable.

The complete implementation is in `teldrive_lab.extended` with regression coverage in `tests/test_phases12_22.py`.

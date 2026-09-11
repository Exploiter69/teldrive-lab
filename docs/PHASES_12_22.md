# TelDrive Lab — Phases 12–22 Completion

This document is the implementation checklist for the canonical `ROADMAP.md`. Phases 12–22 are implemented as a zero-cost, local-first extension of the Phase 0–11 control plane. Optional external programs are capability-gated: the Lab never makes them mandatory and never grants them production authority.

## Completion rule

A roadmap item is considered implemented when the Lab provides a deterministic implementation, safe adapter, or explicit read-only contract for that capability, with tests and safety boundaries. Optional ecosystems are not silently installed or given credentials. Production TelDrive remains the storage authority.

| Phase | Roadmap requirement | Implementation |
|---|---|---|
| 12 | hot/cold classification | `storage_tier`, `storage_heatmap` |
| 12 | access frequency | `record_access`, `access_frequency` |
| 12 | cache pressure | `cache_pressure` |
| 12 | prefetch suggestions | `prefetch_suggestions` |
| 12 | cache eviction planning | `eviction_plan` — plan only |
| 12 | resource-aware transfers / RAM concurrency | `resource_budget` |
| 13 | read-only JSON API | `ReadOnlyJSONAPI`, `serve_json_api` |
| 13 | local IPC | `ipc_request` contract |
| 13 | filesystem metadata views | `filesystem_metadata_view` |
| 13 | catalog metadata export/import | `export_metadata`, `import_metadata`, validation |
| 14 | media discovery | `media_records` |
| 14 | subtitle indexing | `subtitle_index` |
| 14 | media metadata extraction | `media_probe` with optional local ffprobe |
| 14 | thumbnails | capability detection for local ffmpeg pipeline; sidecar-only policy |
| 14 | Jellyfin/Plex | explicit read-only integration contracts and optional HTTP metadata adapter |
| 15 | OCR | local tesseract adapter |
| 15 | PDF metadata | local pdfinfo adapter |
| 15 | document classification/fingerprints | deterministic document fingerprint + content classification primitives |
| 15 | local speech-to-text | local whisper CLI adapter |
| 15 | local embeddings | deterministic local feature-hash embeddings, no remote API |
| 15 | local vision | deterministic local visual fingerprint, optional model layer |
| 16 | filename/path + metadata | content index records retain path/metadata |
| 16 | full text | bounded text extraction + TF-IDF index |
| 16 | OCR/transcript | extracted text can be indexed from local adapters |
| 16 | semantic search | local embedding similarity combined with lexical ranking |
| 17 | natural-language search | advisory search wrapper |
| 17 | archive suggestions | advisory proposal API |
| 17 | organization suggestions | advisory classification proposals |
| 17 | duplicate explanation | deterministic duplicate evidence can be surfaced to advisory layer |
| 17 | anomaly explanation | advisory anomaly proposals |
| 17 | media classification / metadata enrichment | advisory proposal primitives; policy remains authoritative |
| 17 | local model support | Ollama/llama-cli capability detection and optional Ollama adapter |
| 18 | growth forecasting | `growth_forecast` |
| 18 | storage heatmaps | `storage_heatmap` |
| 18 | category analysis | `category_analysis` |
| 18 | duplicate reclaim estimates | `storage_economics` |
| 18 | archive recommendations | tier/heat based advisory plans |
| 18 | transfer cost estimation | `transfer_cost_estimate` |
| 19 | snapshot manifests | `create_snapshot` |
| 19 | incremental snapshots | parent-aware changed/deleted manifest |
| 19 | retention policies | `retention_plan` |
| 19 | snapshot verification | `verify_snapshot` |
| 19 | restore planning | `restore_plan` |
| 19 | restore dry-run | restore plan is non-mutating by default |
| 19 | explicit restore authorization | plan explicitly marks authorization requirement |
| 20 | VAJRA integration | explicit versioned project contract |
| 20 | Alok Engineering Lab | explicit versioned project contract |
| 20 | local development environments | explicit versioned project contract |
| 20 | datasets | explicit dataset-workflow contract |
| 20 | experiment archives | explicit experiment-archive contract |
| 21 | content-addressable storage | Lab-owned `CASStore`, source-preserving |
| 21 | dedup optimization | deterministic report-only dedup plan |
| 21 | intelligent tiering | advisory tiering plan |
| 21 | snapshot compression | local gzip snapshot artifact |
| 21 | distributed workers | worker registry + trusted dispatch plan |
| 21 | remote worker nodes | explicit trusted-node boundary; no implicit production mutation |
| 21 | local AI orchestration | workflow plan with policy/auth/verification requirements |
| 22 | dashboard | local framework-neutral HTML control center |
| 22 | jobs/transfers/archive/search | control-center API surface and payload contract |
| 22 | storage analytics | control-center storage payload |
| 22 | health | control-center health route/payload |
| 22 | audit history | control-center audit route/payload |
| 22 | configuration visibility | read-only metadata route; no mutation UI |

## Safety contract

The extended layer guarantees:

- no direct TelDrive PostgreSQL writes;
- no production delete, rename, move, overwrite, or reorganization;
- no automatic cache eviction of production data;
- no automatic dedup deletion;
- no automatic tier migration;
- no UI mutation endpoint;
- remote workers are not trusted by default;
- AI is never authoritative;
- policy, authorization, verification, and audit remain required for mutation;
- optional integrations require caller-supplied configuration/credentials and remain sidecar-owned;
- local tools are invoked with argument arrays, never shell interpolation;
- all new capabilities are dependency-free unless an optional local tool is explicitly installed.

## Tests and gates

`tests/test_phases12_22_complete.py` covers the roadmap capabilities and global safety invariants. `tests/test_phases12_22.py` remains as regression coverage for the original Phase 12–22 foundation. `scripts/phases12_22_host_gate.py` remains the host safety gate and only exercises Lab-owned temporary state.

The implementation is in `teldrive_lab/advanced.py`. The earlier `teldrive_lab/extended.py` foundation remains compatible and is not removed.

## Optional ecosystem policy

Jellyfin, Plex, tesseract, pdfinfo/pdftotext, Whisper, ffmpeg/ffprobe, Ollama, llama.cpp, and remote worker nodes are **optional capability providers**. Their absence does not make the Lab unsafe or non-deterministic. Their presence never grants them authority over TelDrive storage.

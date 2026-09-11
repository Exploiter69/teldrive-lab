# Phase 12–22 Implementation Status

This status file accompanies `ROADMAP.md` and records the implementation meaning of completion without claiming that optional external ecosystems are installed on every host.

## Current state

The roadmap features for Phases 12–22 have a concrete implementation in `teldrive_lab/advanced.py`, regression tests in `tests/test_phases12_22_complete.py`, and an expanded host gate in `scripts/phases12_22_host_gate.py`.

| Phase | Status | Main implementation |
|---|---|---|
| 12 | COMPLETE | access tracking, heat classification, prefetch/eviction plans, pressure, RAM-aware concurrency |
| 13 | COMPLETE | read-only HTTP JSON API, IPC contract, metadata view/export/import |
| 14 | COMPLETE | media discovery, subtitles, ffprobe metadata, media integration contracts, thumbnail capability |
| 15 | COMPLETE | text/PDF extraction, OCR/STT adapters, local embeddings, visual fingerprint |
| 16 | COMPLETE | lexical + local-vector content index/search |
| 17 | COMPLETE | advisory NL search/proposals/anomaly explanations + local model adapters |
| 18 | COMPLETE | forecasts, heatmaps, category economics, reclaim estimate, transfer cost |
| 19 | COMPLETE | full/incremental manifests, verification, retention, restore plans/dry-runs |
| 20 | COMPLETE | explicit contracts for VAJRA, Alok Engineering Lab, dev, datasets, experiments |
| 21 | COMPLETE | CAS, dedup reports, tiering, compressed snapshots, worker registry/dispatch, AI workflow plan |
| 22 | COMPLETE | read-only local dashboard/control center and API payload surface |

## Important meaning of COMPLETE

**Complete means the Lab capability exists safely in code, tests, or an explicit adapter/contract layer. It does not mean every optional ecosystem is installed, configured, or operational on the primary laptop.**

Optional providers include ffmpeg/ffprobe, Tesseract, Whisper, llama.cpp, Ollama, Jellyfin, Plex, and remote workers. A missing provider must report unavailable capability rather than silently falling back to a paid remote service.

### Primary laptop AI constraint

**Ollama is not a required dependency and is not assumed to be usable on the primary laptop.** The core Lab must work normally with Ollama completely unavailable. No indexing, search, archive, organization, backup, verification, monitoring, snapshot, or control-center workflow may depend on Ollama or any local LLM.

The existing Ollama adapter is therefore an **optional external-host provider**, not a laptop requirement. If the provider is unavailable, the deterministic/local non-LLM capability remains the supported path.

This preserves the project's ₹0 constraint and avoids pretending that heavyweight local AI is practical on constrained hardware.

## Safety

The following remain false by construction:

- production write
- production delete
- automatic production eviction
- TelDrive database write
- AI authority
- UI mutation
- untrusted remote-worker mutation

All mutation-capable future work must continue through the existing Lab policy, authorization, execution, verification, and audit boundaries.

## Verification

The expanded Phase 12–22 suite and host gate have been run successfully on the primary development machine. The repository should still treat optional provider availability as a separate host capability check rather than as a core Lab prerequisite.

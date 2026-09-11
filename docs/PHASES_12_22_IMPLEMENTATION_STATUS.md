# Phase 12–22 Implementation Status

This status file accompanies `ROADMAP.md`; it does not replace or rewrite the canonical roadmap.

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

"Complete" means the roadmap capability exists without requiring a paid service and without violating the production boundary. Optional tools such as ffmpeg, tesseract, Whisper, Ollama, llama.cpp, Jellyfin, Plex, or remote workers are adapters/providers, not hidden mandatory dependencies.

A provider being absent means the corresponding optional operation reports unavailable capability; it does not silently substitute a remote paid API.

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

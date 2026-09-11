# Stage 5 — Media as Data, Not OTT

## Goal

Make media a first-class workload for TelDrive Lab while deliberately delegating playback and media-server responsibilities to mature software such as Jellyfin.

## Existing foundation reused

Phase 14 already provides media discovery, subtitle indexing, optional ffprobe metadata, thumbnail capability, and read-only media integration contracts. Stage 5 productizes those capabilities rather than creating a second media subsystem.

## Roadmap coverage

### MUST

- reliable media discovery — `discover_media()`
- technical metadata — existing `media_probe()`/ffprobe capability and media health
- subtitle indexing — discovery plus deterministic media-to-subtitle association
- stable library metadata exports — versioned JSON schema and catalog digest
- cache/materialization controls — bounded, report/plan-only materialization boundary
- health/latency visibility — media scan timing and provider latency normalization

### SHOULD

- Jellyfin integration/setup guide and safe setup plan
- media prefetch suggestions via existing storage heat intelligence
- direct-play-friendly organization guidance
- poster/thumbnail sidecar planning via optional local ffmpeg

## Ownership

**TelDrive Lab:** discovery, metadata, manifests, verification, organization, cache policy, health and audit.

**Jellyfin:** playback, watch history, profiles, clients, subtitles at playback time, and transcoding orchestration.

**FFmpeg/ffprobe:** media-processing and probing primitives only.

## Safety

- No production TelDrive mutation is performed by the Stage 5 gate.
- Materialization is a bounded plan; actual bytes must flow through existing authorized transfer machinery.
- Thumbnail generation is sidecar-only planning; it does not overwrite source media.
- Jellyfin setup is operator-confirmed and does not mutate Lab storage.
- No custom transcoding farm, OTT service, recommendation engine, or media-server implementation is introduced.
- Optional ffmpeg/ffprobe availability is reported rather than replaced by paid services.

## Zero-cost/resource model

All core functionality uses the standard library and existing local Lab capabilities. FFmpeg/ffprobe are optional local tools. No remote AI, paid API, hosted database, SaaS, or paid notification dependency is introduced.

## Verification

```bash
python -m pytest -q
PYTHONPATH="$PWD" python scripts/stage5_media_data_gate.py
```

Stage 5 is closed only after both commands pass locally.

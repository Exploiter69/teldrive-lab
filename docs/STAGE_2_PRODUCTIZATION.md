# Stage 2 — Productization Gate

> Implementation gate derived from `PRODUCT_ROADMAP.md`. This stage turns the audited Phase 0–22 foundation into an understandable, operable, recoverable product without changing the storage-safety model.

## Objective

A fresh TelDrive Lab installation should be understandable and operable without reading implementation source code, while loss of Lab-side catalog state must not imply loss of stored data.

## Scope

Stage 2 is productization, not a new storage engine. It must reuse the existing audited jobs, transfer boundary, metadata, integrity, backup, monitoring, CLI, API, and control-center foundations.

### MUST

1. One documented installation path.
2. First-run configuration and capability detection.
3. Clear separation of core capabilities and optional providers.
4. Health reporting with actionable failures.
5. Durable job visibility and retry controls.
6. Consistent CLI/API semantics.
7. Safe configuration validation.
8. Backup/restore drill documentation.
9. Provider availability and degraded-state reporting.
10. Honest Telegram capacity/risk messaging.
11. Complete operator documentation.

### SHOULD

1. Productized local control center.
2. Operation templates.
3. Lab metadata/manifest import and export.
4. Simple upgrade/migration procedure.
5. Event/audit timeline.

## Safety invariants

- TelDrive remains the production storage authority.
- No direct TelDrive PostgreSQL writes.
- No silent production delete, rename, move, overwrite, or reorganization.
- AI remains advisory and cannot self-authorize mutation.
- Optional providers fail explicitly; there is no paid fallback.
- Core functionality works without an LLM.
- Destructive operations retain the existing Policy → Authorization → Execution → Verification → Audit boundary.
- No production data mutation is introduced merely to productize the Lab.

## Gate order

### S2.1 — Installation and runtime contract

- document supported runtime/prerequisites
- provide one canonical local installation path
- validate required configuration before service startup
- report missing optional dependencies without silently substituting paid services

### S2.2 — Capability discovery

Expose a deterministic capability report covering:

- core Lab capabilities
- optional provider/tool availability
- unavailable optional dependencies
- runtime/resource constraints
- provider health/degraded state

### S2.3 — Operator experience

- make jobs discoverable through the existing CLI/control-plane surfaces
- expose actionable failure state
- preserve retry/pause/resume semantics already provided by durable jobs
- keep CLI/API terminology aligned with the underlying contracts

### S2.4 — Recovery and documentation

- document backup and restore drills
- document catalog/index rebuild expectations
- document provider degradation behavior
- document Telegram's non-guaranteed capacity model
- document upgrade/migration expectations

### S2.5 — Productization verification

Every S2 change must pass:

1. targeted unit tests
2. integration tests where applicable
3. safety tests
4. host gate
5. full regression suite
6. documentation consistency review
7. clean Git checkpoint

## Explicit non-goals

Stage 2 does **not** implement:

- provider abstraction (Stage 3)
- WebDAV server (Stage 4)
- OTT/player/transcoding
- autonomous AI mutation
- SMB/NFS
- replacement transfer engine
- generic workflow platform
- paid infrastructure

## Definition of done

Stage 2 is complete when a clean local installation can:

- explain what TelDrive Lab is and is not;
- validate its configuration safely;
- report available and unavailable capabilities clearly;
- expose durable job state and operator controls;
- explain degraded provider state;
- document backup/restore and recovery expectations;
- operate without optional AI providers;
- preserve all Phase 0–22 safety invariants;
- pass the Stage 2 host gate and full regression suite.

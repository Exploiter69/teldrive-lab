# Release Checklist

This document is the historical release-control record for **v1.0.0**. It is intentionally closed; future work belongs in the v1.1 roadmap and its own gates.

## v1.0.0 release identity

- **Release:** `v1.0.0`
- **Release candidate:** `v1.0.0-rc2`
- **Validated release commit:** `b3f879b5193bc4e2e8c091e87be49a3be1f5cc84`
- **Final tag:** `v1.0.0`
- **RC2 tag:** `v1.0.0-rc2`
- **Post-RC evidence commit:** `61d94f12e0b96fc86a85f21f148c331c6742dd91`
- **Post-RC audit:** `docs/POST-RC-VALIDATION.md`

The final `v1.0.0` tag intentionally points to the already validated RC2 commit. The post-RC documentation commit is on `main` and does not replace or mutate the release tag.

## Product scope

- [x] Core control plane release-hardened through R0–R6
- [x] TelDrive remains the production storage authority
- [x] Production mutation remains policy/authorization/executor/verification/audit controlled
- [x] Zero-cost runtime constraint preserved
- [x] No paid API or cloud AI dependency required
- [x] Whisper / speech-to-text excluded
- [x] Ollama / local LLM runtime excluded
- [x] Autonomous AI mutation excluded

## Core release gates

- [x] Authoritative bounded corpus discovery
- [x] Unified FTS5 search
- [x] Media/Jellyfin workflow
- [x] Durable execution and recovery
- [x] Verification and audit evidence
- [x] Read-only loopback Control Center
- [x] Production-boundary hardening
- [x] CI safety and least-privilege checks

## Extension boundary

P12–P21 capabilities are represented only according to their actual implementation/evidence status. They are not release blockers merely because optional or experimental capabilities are not production integrations.

Supported extension examples include deterministic storage/cache intelligence, read-only metadata surfaces, OCR/document processing where locally available, deterministic local feature-hash embeddings, content indexing/search, analytics, snapshots/recovery planning, explicit contracts, CAS, and report-only deduplication planning.

## Final release conditions — CLOSED

- [x] Target release worktree was clean apart from explicitly preserved local-only state
- [x] Exact release commit identified
- [x] CI green on the exact RC2 candidate (`34873474878`)
- [x] Clean-install import passed on the exact candidate
- [x] Full pytest passed on the exact candidate
- [x] R0–R6 and Phase 4–11 plus Phase 12–22 host gates passed
- [x] Final production-boundary validation passed without production mutation
- [x] Release notes contain only verified capabilities
- [x] Post-RC validation found no release blockers
- [x] `v1.0.0-rc2` tagged at the validated commit
- [x] `v1.0.0` promoted to the same validated commit

## Operational post-release evidence

The post-RC review recorded PASS for:

- discovery → catalog → search
- media discovery → safe exposure → Jellyfin → playback
- durable execution → VERIFYING → COMPLETED
- lease loss/recovery/stale-worker fencing
- verification and audit
- Control Center read-only behavior
- protected production-boundary behavior
- failure/recovery review

Local operational follow-up also verified persistent Jellyfin configuration with `restart=unless-stopped`, `init=true`, persistent `/config` and `/cache`, and a read-only `/media` mount. This is local operational evidence, not a change to the v1.0 release contract.

## Explicit non-goals

A v1.0 release must never imply or introduce:

- direct TelDrive PostgreSQL writes
- silent production mutation
- autonomous destructive storage administration
- authorization minted by a worker, planner, UI, or AI
- paid runtime dependencies
- mandatory remote AI
- unlimited or permanent Telegram storage
- automatic production eviction
- automatic production deduplication
- unbounded remote workers

## Release closure

**Status: COMPLETE.**

The v1.0 release-control record is closed. Do not reopen it for ordinary v1.1 development. Any new capability, gate, or behavioral change must be tracked under the v1.1 roadmap and must not move the `v1.0.0` tag.

# Release checklist

This is the active release-control document. Historical R0–R6 evidence reports are intentionally not maintained as separate active documents.

## Product scope

- [x] Core control plane is release-hardened through R0–R6
- [x] TelDrive remains the production storage authority
- [x] Production mutation remains policy/authorization/executor/verification/audit controlled
- [x] Zero-cost runtime remains the product constraint
- [x] No paid API or cloud AI dependency is required
- [x] Whisper / speech-to-text is out of scope
- [x] Ollama / local LLM runtime is out of scope
- [x] Autonomous AI mutation is out of scope

## Core release gates

- [x] authoritative corpus discovery
- [x] unified search
- [x] media/Jellyfin workflow
- [x] durable execution and recovery
- [x] verification and audit
- [x] read-only Control Center
- [x] production-boundary hardening
- [x] CI safety and least-privilege checks

## Extension boundary

P12–P21 capabilities are released only according to their actual implementation/evidence status. The strict gate must verify the current product contract, not unavailable or intentionally unsupported providers.

Legacy extension boundary markers: P12, P13, P15, P16, P17, P18, P19, P20, P21.

Supported extension examples include deterministic storage/cache intelligence, read-only metadata surfaces, OCR/document processing, local deterministic embeddings, content indexing/search, analytics, snapshots, contracts, CAS, and report-only deduplication.

## Final release conditions

- [ ] target worktree is clean
- [ ] final commit is identified
- [ ] CI is green on the final commit
- [ ] clean-install validation passes
- [ ] final production-boundary validation is green
- [ ] release notes describe only verified capabilities
- [ ] final release/tag decision is recorded

## Release-candidate evidence

The intended release candidate is **v1.0.0-rc2**. The release notes are recorded in `docs/RELEASE-NOTES-v1.0.0-rc2.md`.

Before tagging, the exact final documentation commit must be identified and independently validated. The final local worktree must be clean apart from explicitly preserved local-only state, and the complete CI gate matrix plus clean-install and production-boundary validation must pass on that exact commit. The preserved local stash `local-r0-gate-work-before-r3-sync` is intentionally unrelated to the release candidate and must not be popped, dropped, or committed.

Previously established evidence includes a clean-install import and full pytest pass on the R6-hardened code, R0–R6 and Phase 4–11 plus Phase 12–22 host gates passing, and real Jellyfin host verification with no production TelDrive/Telegram mutation. GitHub Actions was green on the pre-release-documentation commit `20b11c1bebb4ab6f6a7b36b03507384acfdfd18b`.

## Final release sequence

The repository's final release sequence is:

1. finish all code/documentation changes for the release candidate;
2. verify the target local worktree is clean, except for explicitly preserved local-only state such as a documented stash;
3. identify the exact release candidate commit;
4. run CI and require the full gate matrix to pass on that commit;
5. run clean-install and production-boundary validation without mutating production data;
6. record release notes containing only verified capabilities;
7. only then create the RC or release tag.

R6 hardening is a prerequisite for the release sequence, not permission for autonomous production mutation.

A release must never introduce:

- direct TelDrive PostgreSQL writes
- silent production mutation
- autonomous destructive storage administration
- authorization minted by a worker/planner/UI
- paid runtime dependencies
- mandatory remote AI
- claims of unlimited or permanent Telegram storage

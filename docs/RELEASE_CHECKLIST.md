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

Supported extension examples include deterministic storage/cache intelligence, read-only metadata surfaces, OCR/document processing, local deterministic embeddings, content indexing/search, analytics, snapshots, contracts, CAS, and report-only deduplication.

## Final release conditions

- [ ] target worktree is clean
- [ ] final commit is identified
- [ ] CI is green on the final commit
- [ ] clean-install validation passes
- [ ] final production-boundary validation is green
- [ ] release notes describe only verified capabilities
- [ ] final release/tag decision is recorded

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

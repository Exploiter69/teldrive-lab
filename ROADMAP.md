# TelDrive Lab Roadmap

This is the canonical current roadmap. Historical implementation phases and reconciliation reports are no longer maintained as active documentation.

> **Product truth:** TelDrive remains the production storage authority. TelDrive Lab is the safe engineering control plane around it.

## Completion standard

```text
PRIMITIVE → IMPLEMENTED → INTEGRATED → OPERATIONAL → END-TO-END VERIFIED → DOCUMENTED → COMPLETE
```

## Current release state

**Core control plane: COMPLETE and release-hardened through R0–R6.**

The core includes authoritative discovery/catalog, search, media/Jellyfin serving, durable execution, verification, audit, monitoring, and the read-only Control Center.

P12–P21 remain an extension layer. Only capabilities actually inside the current product contract are represented below. Optional AI-provider integrations are intentionally excluded.

| Capability | Status | Boundary |
|---|---|---|
| Corpus discovery | COMPLETE | Bounded authoritative metadata discovery; derived local catalog |
| Unified search | COMPLETE | Filename/path/content search over supported local indexes |
| Media/Jellyfin | COMPLETE | Read-only protection with verified Lab-owned media workflow |
| Durable execution | COMPLETE | Durable jobs, leases, retries, recovery, verification, audit |
| Control Center | COMPLETE | Loopback-only, GET-only, read-only |
| Storage/cache intelligence | IMPLEMENTED | Deterministic classification, access frequency, planning; no automatic eviction |
| Read-only interoperability | IMPLEMENTED | Metadata/API surfaces; no TelDrive DB writes |
| Document intelligence | IMPLEMENTED | Fingerprints, PDF metadata/text extraction, OCR where locally available |
| Local embeddings/search | IMPLEMENTED | Deterministic local feature-hash embeddings; no remote AI service |
| Storage analytics | IMPLEMENTED | Forecasting, category analysis, transfer estimates; advisory only |
| Snapshots/recovery planning | IMPLEMENTED | Snapshot manifests, verification, restore planning; restore remains authorized/high-risk |
| Cross-project contracts | IMPLEMENTED | Explicit read/plan/export contracts; no implied production integration |
| CAS/dedup | EXPERIMENTAL | Lab-owned CAS and report-only dedup planning |

## Explicitly out of scope

The following are **not** part of the current TelDrive Lab product contract and must not be treated as missing release requirements:

- Whisper / speech-to-text
- Ollama or any local LLM runtime
- cloud AI APIs
- autonomous AI mutation or authorization
- automatic production eviction
- automatic production deduplication
- unbounded remote workers

The codebase must not require these components for its normal test or release path.

## Safety model

```text
Observe
  ↓
Understand
  ↓
Plan
  ↓
Authorize
  ↓
Controlled executor
  ↓
Verify
  ↓
Audit / evidence
```

No planner, advisory layer, UI, or future integration may bypass the controlled mutation boundary.

## Release policy

A release is valid only when:

1. the working tree is clean locally;
2. CI is green at the release head;
3. production-boundary tests pass;
4. no documentation claims capabilities that are not implemented and evidenced;
5. optional components do not become hidden hard dependencies.

The current product deliberately favors a smaller deterministic control plane over an AI-heavy archive platform.

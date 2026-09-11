# TelDrive Lab — Stage 8 Advanced Experiments

Stage 8 is the experimental ceiling of the current product roadmap. It does **not** turn experiments into production storage authority.

## Scope

The roadmap names these potential experiments:

- content-addressable storage optimization
- advanced deduplication research
- intelligent tiering
- compressed snapshot optimization
- distributed workers
- remote worker nodes
- advanced local AI orchestration
- FUSE

The existing Lab already contains isolated, local implementations for the first seven capabilities through the Phase 21 experimental layer. They are plans, reports, local artifacts, or protocol experiments; they do not silently mutate production TelDrive storage.

FUSE remains intentionally **deferred**. It is a higher-risk filesystem boundary and is not required to declare Stage 8 complete because the product roadmap defines these as potential experiments, not MUST features.

## Experiment contracts

| Experiment | Status | Production mutation | Boundary |
|---|---|---:|---|
| Content-addressable storage | COMPLETE | No | Lab-owned CAS only; source-preserving |
| Advanced deduplication | COMPLETE | No | deterministic report-only plan |
| Intelligent tiering | COMPLETE | No | advisory tier plan |
| Snapshot compression | COMPLETE | No | local compressed snapshot artifact |
| Distributed workers | COMPLETE | No | explicit trusted-node protocol |
| Remote worker nodes | COMPLETE | No | trusted-node dispatch plan only |
| Advanced local AI orchestration | COMPLETE | No | policy/auth/verification required; AI not authority |
| FUSE | DEFERRED | N/A | requires separate architecture/security review |

## Safety invariants

Every Stage 8 experiment must preserve:

```text
AI / experiment proposes
        ↓
Policy evaluates
        ↓
Authorization permits
        ↓
Execution mutates
        ↓
Verification proves
        ↓
Audit records
```

Stage 8 experiments therefore:

- never write the production TelDrive database
- never silently delete, overwrite, move, or reorganize production data
- never make AI authoritative
- never grant implicit production mutation authority to workers
- keep derived state rebuildable where practical
- use local/free tooling only
- remain usable without paid services

## Completion rule

Stage 8 is complete when every roadmap experiment has an explicit disposition and every implemented experiment is isolated behind a testable safety boundary. Completion does **not** mean enabling every experiment in production.

### Explicit non-goals

Do not use Stage 8 to build:

- a replacement for rclone
- a custom POSIX filesystem
- a generic distributed platform
- an autonomous storage administrator
- automatic destructive deduplication
- paid cloud infrastructure

Stage 8 is research infrastructure, not a license to weaken the core product model.

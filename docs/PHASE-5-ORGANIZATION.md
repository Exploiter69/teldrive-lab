# Phase 5 — Deterministic Organization Engine

**Status:** implementation complete; controlled exit gate defined  
**Cost:** ₹0 / $0  
**Production execution:** intentionally not performed during implementation

## Goal

Make organization predictable, policy-driven, reviewable, and safe. Phase 5 decides where an observed file should be placed; it does not grant the planner storage authority.

The architecture is:

```text
catalog observation
      ↓
deterministic classification
      ↓
deterministic destination
      ↓
organization plan + digest
      ↓
dry-run / review
      ↓
explicit authorization
      ↓
Phase 4 TransferManager
      ↓
verification
      ↓
audit
```

## Implemented

### 1. Deterministic policy engine

`teldrive_lab/organization.py` provides `OrganizationPolicy` and ordered `OrganizationRule` evaluation.

Path rules have precedence over generic extension/MIME rules:

```text
projects/** → PROJECT → CRYPT
backups/**  → BACKUP  → CRYPT
movies/**   → MOVIE   → RAW
datasets/** → DATASET → RAW
```

Fallback classification uses known extensions and MIME types for:

- images
- video
- audio
- documents
- archives
- unknown/other data

Unknown metadata remains unknown. The engine does not invent content semantics.

### 2. Stable destination planning

Every item gets a deterministic destination:

```text
<storage-root>/<classification>/<basename>
```

The basename is sanitized to a single filename component, preventing `..` traversal from becoming an organization destination.

The planner sorts records deterministically and emits a SHA-256 plan digest over canonical JSON. The same observations and policy therefore produce the same plan digest.

### 3. Explicit plan actions

Each item is classified as exactly one of:

```text
COPY
NOOP
CONFLICT
BLOCKED
```

`CONFLICT` means the destination already exists and the planner will not overwrite it.

`BLOCKED` means the central safety policy refuses the proposed mutation, including protected production paths.

`NOOP` means source and deterministic destination are already identical.

### 4. No destructive organization primitive

Phase 5 deliberately uses the Phase 4 `COPY` boundary rather than introducing a new move/rename implementation. This means organization never silently deletes the source or bypasses transfer verification.

A future destructive move workflow, if ever justified, must receive its own safety contract and authorization path.

### 5. Phase 4 integration

`OrganizationExecutor` delegates every `COPY` to `TransferManager` and supplies a scope-bound `AuthorizationReceipt` created from the exact source and destination pair.

It refuses to apply plans containing conflicts or blocked items before starting any transfer.

The Phase 4 transfer layer remains responsible for:

- safety enforcement
- atomic publication
- SHA-256 verification
- progress
- bounded concurrency
- transfer failure classification

Phase 5 therefore does not duplicate transfer logic.

### 6. CLI control surface

The CLI now supports deterministic organization planning:

```text
td organize --source-type LOCAL --source-id host \
  --raw-root /path/raw --crypt-root /path/crypt --dry-run
```

An explicit Lab-only apply can be requested with `--apply` after reviewing the plan. Protected production paths remain hard-denied by the central safety layer even when apply is requested.

The CLI records plan/apply outcomes in the existing Lab audit database without recording secrets.

## Safety model

Classification is not authorization.

The organization engine cannot override the production boundary. In particular, it cannot mutate:

- `~/TelegramRaw`
- `~/TelegramDrive`
- `~/teldrive`
- `~/teldrive-project`
- protected production state

The planner may inspect protected sources for read-only planning, but a proposed mutation touching them is marked `BLOCKED`.

No AI or heuristic model is involved in authorization. Phase 5 policy is deterministic.

## Conflict model

The default is fail-closed:

```text
destination absent → COPY
same source/destination → NOOP
 destination exists → CONFLICT
protected/unsafe     → BLOCKED
```

There is no implicit overwrite, rename-on-conflict, duplicate deletion, or merge behavior.

## Controlled host gate

`scripts/phase5_host_gate.py` runs only in a temporary directory and validates:

- deterministic classification and rule precedence
- stable plan digest
- conflict-safe planning
- explicit authorization through Phase 4
- actual isolated transfer + verification
- protected production destination denial
- zero production mutation

No live TelDrive, Telegram, rclone mount, Docker configuration, or production database is touched by the gate.

## Exit gate

Phase 5 is implementation-complete when all of the following are true:

- [x] deterministic classification exists
- [x] explicit path policy precedence exists
- [x] extension/MIME fallback classification exists
- [x] deterministic destination generation exists
- [x] traversal-safe destination construction exists
- [x] stable plan digest exists
- [x] dry-run plan representation exists
- [x] conflict detection exists
- [x] protected-path blocking exists
- [x] explicit authorization is required for apply
- [x] organization execution delegates to Phase 4 TransferManager
- [x] SHA-256 transfer verification remains centralized in Phase 4
- [x] audit integration exists through the CLI
- [x] controlled host gate exists
- [x] tests cover deterministic policy, conflicts, safety, and apply
- [x] no live production organization was required

## What Phase 5 does not claim

Phase 5 does not automatically reorganize the existing Telegram/TelDrive corpus. It provides the deterministic policy and execution boundary required for later phases. Live production validation remains a separate final program after the planned implementation phases are complete.

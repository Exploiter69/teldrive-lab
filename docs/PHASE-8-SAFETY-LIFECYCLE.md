# Phase 8 — Safety & Lifecycle Management

**Status: COMPLETE**  
**Cost: ₹0 / $0**

Phase 8 makes cleanup possible without turning the Lab into an accidental deletion system.

## Safety model

```text
candidate
  ↓
PLAN
  ↓
DRY-RUN
  ↓
EXPLICIT AUTHORIZATION
  ↓
EXECUTE
  ↓
VERIFY
  ↓
AUDIT
```

Protected production paths remain fail-closed. Phase 8 does not mutate TelDrive, Telegram, rclone mounts, PostgreSQL, Docker, DNS, authentication/session state, or the TelDrive source tree.

## Quarantine

Quarantine is a **COPY**, never a move:

```text
Lab-owned source
      ↓
 SHA-256
      ↓
 explicit authorization
      ↓
 Lab quarantine
      ↓
 verification
```

The original source remains intact. A quarantine record is stored in the Lab-owned `lifecycle.db`.

The default quarantine destination must be Lab-owned and non-protected. Existing destinations cause a blocked plan; overwrite is never implicit.

## Safety window and retention

Every quarantine record has a durable `purge_after` timestamp. `RetentionPolicy` contains both a retention period and a safety window. Purge eligibility begins only after the **longer** of those two intervals has elapsed, so neither policy can silently shorten the other.

Lifecycle policy is represented explicitly by `RetentionPolicy`; deployments can select conservative retention/safety windows rather than relying on hidden timers.

## Immutable / locked archive mode

The Lab does not require privileged filesystem flags. Instead, lifecycle metadata can mark a record as `locked`.

A locked record produces:

```text
LOCKED
```

and cannot be purged through the lifecycle executor.

## Purge

Purge is deliberately narrow:

- only quarantine copies are eligible
- retention and safety windows must both have elapsed
- locked records are blocked
- protected production paths are blocked by the central safety policy
- explicit authorization is required
- no source deletion is performed
- the lifecycle action is audited

`DUPLICATE FOUND` never implies purge.

## Restore

Restore is a first-class operation:

```text
quarantine
    ↓
PLAN
    ↓
collision check
    ↓
explicit authorization
    ↓
COPY
    ↓
SHA-256 verification
```

Restore never overwrites an existing destination and retains the quarantine copy. The plan keeps the original quarantine source and requested restore destination separately, preventing source/destination confusion during recovery.

## Durable state

`LifecycleStore` owns only Lab metadata:

```text
~/.local/share/teldrive-lab/lifecycle.db
```

The database contains source/quarantine paths, size, SHA-256, quarantine time, purge deadline, and immutable lock state. It is rebuildable metadata and is not TelDrive state.

## Recovery / reconciliation

`LifecyclePlanner.reconcile()` is a **read-only** recovery view. For every durable lifecycle record it checks whether the quarantine copy exists and whether its size and SHA-256 still match the recorded evidence. It reports explicit states:

- `VERIFIED`
- `LOCKED_VERIFIED`
- `CORRUPT_QUARANTINE`
- `MISSING_QUARANTINE`

It never silently recreates, deletes, moves, or overwrites anything. Recovery therefore remains human-controlled: inconsistency becomes a visible state that can be replanned and explicitly authorized.

## Audit

Quarantine, restore, and purge executions write non-secret lifecycle events to the Lab-owned audit database through the shared audit layer. Authorization IDs and checksum evidence are recorded as metadata; secrets and credentials are never written.

## CLI / integration boundary

The Phase 8 engine is exposed through the shared Lab control plane and reuses the existing Phase 4 transfer and central safety layers. No lifecycle operation is allowed to bypass authorization.

## Host gate

`scripts/phase8_host_gate.py` proves, using isolated temporary files:

- deterministic quarantine planning
- SHA-256 evidence
- retention and safety-window enforcement
- verified quarantine copy
- original-source preservation
- read-only recovery reconciliation
- durable lifecycle metadata
- immutable lock enforcement
- verified non-overwriting restore
- explicit quarantine purge
- original-source preservation after purge
- lifecycle audit events
- protected production boundary blocking

The gate performs **zero production storage mutation**.

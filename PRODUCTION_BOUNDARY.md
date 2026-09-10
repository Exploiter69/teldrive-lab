# TelDrive Lab — Production Boundary

**Status:** Mandatory architectural contract  
**Scope:** TelDrive production deployment and all TelDrive Lab automation

## 1. Purpose

This document defines the hard boundary between the existing TelDrive installation and TelDrive Lab.

TelDrive Lab is a **sidecar control, automation, indexing, verification, and intelligence layer**. It is not a replacement for TelDrive, Telegram storage, the existing database, the existing mounts, or the existing deployment.

The production boundary is intentionally conservative: Lab may observe and operate through controlled, explicitly authorized interfaces, but it must never silently take ownership of production storage.

---

## 2. Protected Production Paths

The following paths are production-owned and must be treated as protected resources:

```text
/home/thakuralok/TelegramRaw
/home/thakuralok/TelegramDrive
/home/thakuralok/teldrive
/home/thakuralok/teldrive-project
```

The Lab repository is separate:

```text
/home/thakuralok/teldrive-lab
```

Runtime state for Lab belongs outside the repository, for example:

```text
~/.local/share/teldrive-lab/
~/.cache/teldrive-lab/
```

Deleting or rebuilding the Lab repository must not delete, move, rename, reorganize, migrate, or otherwise modify production data.

---

## 3. Protected Services and Systems

The following existing systems are production infrastructure:

- TelDrive container and application
- PostgreSQL / PGroonga database used by TelDrive
- `rclone-teldrive.service`
- `rclone-teldrive-raw.service`
- rclone remotes and mount configuration
- Docker runtime and existing TelDrive containers
- Telegram-backed storage and associated authentication/session state
- existing DNS, nameserver, reverse-proxy, and public-routing configuration

These systems remain outside the Lab's ownership boundary.

---

## 4. Storage Authority

TelDrive and its underlying Telegram-backed storage remain the authoritative storage system.

The Lab catalog is **derived and rebuildable**. It must never become the canonical owner of the actual file contents.

A Lab database failure must therefore result in loss of derived metadata or job state only, not loss of production files.

The Lab must not:

- migrate Telegram data to another storage backend;
- re-upload existing production content merely to integrate with Lab;
- replace TelDrive with a new storage implementation;
- rewrite the production storage layout as an integration strategy;
- treat the Lab catalog as more authoritative than the storage itself.

---

## 5. Database Boundary

The existing TelDrive PostgreSQL database is protected production state.

Lab automation must not automatically:

- drop the database;
- replace the database;
- migrate the database to another engine;
- rewrite or normalize the production schema;
- run uncontrolled schema modifications;
- delete production records;
- use the production database as Lab's internal job/catalog database.

TelDrive's database may be inspected through supported, read-only, controlled interfaces when required for diagnostics or metadata discovery.

Lab owns its own local SQLite state instead.

---

## 6. Authentication and Session State

Existing TelDrive authentication, Telegram session state, credentials, tokens, cookies, and other secrets are production-controlled.

Lab must not silently rotate, replace, invalidate, expose, copy, or relocate authentication state.

Secrets must never be committed to Git, emitted into normal logs, written into audit events, sent to external AI services, or included in generated diagnostics.

---

## 7. DNS, Networking, and Public Exposure

The existing DNS, nameservers, reverse proxy, public routing, and exposure model are outside the default Lab mutation scope.

Lab must not automatically:

- change DNS records;
- change nameservers;
- expose TelDrive publicly;
- open firewall ports;
- alter reverse-proxy routing;
- replace TLS configuration;
- make a production service internet-accessible.

Any such change requires a separate explicit user request and must pass the full safety lifecycle.

---

## 8. Source-Code Boundary

The existing TelDrive source repository at `/home/thakuralok/teldrive-project` is independent from TelDrive Lab.

Lab automation must not automatically:

- overwrite the existing repository;
- merge experimental Lab changes into production source;
- replace the existing TelDrive build;
- rebuild and redeploy production containers as a side effect of Lab development.

Source inspection is allowed when required for understanding supported behavior or compatibility.

Production deployment changes are a separate, explicitly authorized operation.

---

## 9. Allowed Default Operations

The following operations are allowed as non-destructive Lab capabilities, subject to normal safety checks:

- health inspection;
- service-status inspection;
- filesystem metadata inspection;
- supported TelDrive API/interface inspection;
- rclone listing and metadata discovery;
- read-only database inspection where justified;
- controlled file indexing;
- checksum calculation;
- verification of already-existing data;
- controlled transfer jobs with explicit source and destination;
- non-secret telemetry collection;
- job planning and dry-runs;
- audit generation;
- local catalog rebuilds;
- read-only integrations;
- resource and performance measurements.

Read-only does not mean uncontrolled: commands must still respect rate limits, resource limits, protected paths, and audit requirements.

---

## 10. Forbidden by Default

Without explicit authorization, Lab must not:

- delete production files;
- move production files;
- rename production files;
- reorganize production directories;
- overwrite existing production content;
- mass-edit production metadata;
- change rclone remotes;
- change mount configuration;
- stop or replace production services;
- rebuild or replace production containers;
- modify production database state;
- migrate storage;
- re-upload production content;
- alter DNS or public routing;
- expose private storage to the internet;
- perform destructive deduplication;
- automatically quarantine or purge content.

A feature that requires one of these actions must surface the operation explicitly rather than hiding it behind an apparently harmless command.

---

## 11. Destructive Operations

If a future Lab feature legitimately needs to mutate production state, the operation must follow:

```text
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

The authorization must be specific to the presented scope and must not be inferred from earlier unrelated approval.

The plan must identify, as applicable:

- exact operation;
- source;
- destination;
- affected paths or bounded selection;
- expected object count;
- expected size;
- reason;
- safety checks;
- rollback or recovery strategy;
- verification method.

If the scope changes materially, authorization must be obtained again.

---

## 12. No Hidden Production Side Effects

A Lab command advertised as `inspect`, `search`, `index`, `verify`, `status`, or `plan` must not silently perform destructive or mutating production operations.

In particular:

- indexing must not move files;
- duplicate detection must not delete files;
- verification must not repair by overwriting unless explicitly requested;
- search must not reorganize data;
- planning must not execute;
- dry-run must not mutate production state.

Side effects must be explicit in the command contract and audit trail.

---

## 13. Catalog Independence

The Lab catalog is a cache/index of observations about production storage.

Its failure must not affect production availability.

Its deletion must not affect production files.

Its rebuild must discover state again rather than assuming the old catalog is authoritative.

Where catalog information conflicts with direct storage observation, the system must surface the discrepancy rather than silently modifying either side.

---

## 14. Transfer Boundary

All production transfers must identify:

- source system;
- destination system;
- exact path or bounded selection;
- expected size where available;
- checksum strategy where applicable;
- retry policy;
- verification strategy;
- authorization state.

A successful transport command is not by itself proof that archival or backup objectives were achieved.

Completion requires the verification defined by the corresponding job type.

---

## 15. Telegram Safety

Telegram-backed operations must remain conservative and compatible with Telegram API limits.

Lab must not generate uncontrolled request bursts, unnecessary re-scans, infinite retry loops, or redundant uploads/downloads.

Rate limiting, bounded retries, backoff, idempotency, and reconciliation are mandatory for workflows that communicate with Telegram-backed services.

The objective is reliable automation, not maximum request volume.

---

## 16. Failure and Recovery Boundary

Production failures must fail closed rather than triggering increasingly invasive recovery actions.

Examples:

- uncertain destination → stop;
- uncertain authorization → stop;
- uncertain source identity → stop;
- verification failure → do not mark complete;
- unexpected path → stop;
- permission failure → report and stop rather than bypassing controls;
- database inconsistency → preserve evidence and stop rather than rewriting production state;
- network loss → persist job state and recover safely.

Recovery must not turn a transient failure into a destructive action.

---

## 17. Resource Boundary

The host is resource-constrained, particularly in RAM.

Lab workloads must therefore use bounded concurrency, bounded memory, bounded queues, and resumable work.

No feature may assume unlimited local cache, RAM, CPU, disk, or network bandwidth.

Large indexing, hashing, OCR, media analysis, and AI workloads should be scheduled or batched rather than made permanently resident without justification.

Resource pressure must never be solved by consuming protected production cache/storage indiscriminately.

---

## 18. AI Boundary

AI-generated plans, classifications, summaries, filenames, tags, search interpretations, or recommendations are untrusted outputs.

AI may advise Lab but cannot by itself:

- authorize a production mutation;
- delete files;
- change mounts;
- change DNS;
- modify production database state;
- replace TelDrive;
- migrate storage;
- expose services publicly.

Any AI-assisted action must pass through deterministic policy, explicit authorization where required, execution, verification, and audit.

---

## 19. Boundary Tests

The implementation must eventually include tests that prove:

1. protected paths are recognized;
2. protected services cannot be mutated by default;
3. destructive commands require authorization;
4. dry-runs do not mutate production;
5. Lab catalog deletion does not touch production data;
6. failed verification prevents completion;
7. unauthorized AI output cannot trigger production mutation;
8. unexpected paths fail closed;
9. network interruption preserves durable job state;
10. retries remain bounded;
11. secrets are excluded from logs and audit events;
12. DNS/network changes remain outside normal Lab execution scope.

These are architectural safety tests, not optional polish.

---

## 20. Operational Rule

The simplest rule for implementation and review is:

> **TelDrive production is protected infrastructure. TelDrive Lab may observe, index, verify, plan, and perform explicitly authorized controlled operations through defined interfaces. It must never silently become the owner or replacement of production storage.**

If an operation could cause irreversible production change and the system cannot prove that the scope, authorization, destination, and verification are correct, **stop**.

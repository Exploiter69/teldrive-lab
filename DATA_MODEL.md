# TelDrive Lab — Data Model

**Status:** Mandatory architectural contract  
**Scope:** Local metadata catalog, provenance, integrity, and derived state

## 1. Purpose

TelDrive Lab needs a local, queryable representation of files and related operational state without replacing or modifying TelDrive's storage authority.

The Data Model therefore defines a **local, rebuildable catalog**. It records observations, provenance, integrity state, and relationships needed by the Job Engine and higher-level features.

The catalog is not the storage itself and is never authoritative over production file contents.

---

## 2. Catalog Location

The initial catalog is SQLite and lives outside the Git repository:

```text
~/.local/share/teldrive-lab/catalog.db
```

The repository contains schema definitions, migrations, models, queries, and tests—not the runtime database.

The catalog must remain independently rebuildable from supported storage interfaces and metadata sources.

---

## 3. Authority Model

The authority hierarchy is:

```text
Actual storage/content
        ↓
Supported source interfaces
        ↓
Lab observations/catalog
        ↓
Search, planning, intelligence, and reports
```

A catalog record represents what Lab knows about an object at a point in time.

If the catalog conflicts with direct storage observation, Lab must surface the discrepancy and reconcile deliberately. It must not silently mutate production to make the catalog appear correct.

---

## 4. Canonical File Record

The canonical file record should support the following fields.

| Field | Purpose |
|---|---|
| `id` | Stable Lab-local record identifier |
| `path` | Full logical or observed path |
| `name` | Base filename |
| `parent_path` | Parent directory/path |
| `size` | Observed byte size, nullable when unknown |
| `mime_type` | Detected or reported MIME type |
| `extension` | Normalized extension |
| `created_at` | Source creation time when available |
| `modified_at` | Source modification time when available |
| `sha256` | SHA-256 content checksum when computed |
| `hash_state` | Lifecycle state of checksum computation |
| `source_type` | Origin/storage class |
| `source_identifier` | Stable identifier for the source |
| `destination_type` | Destination/storage class when applicable |
| `destination_identifier` | Stable identifier for the destination |
| `telegram_file_id` | Telegram file identifier when available |
| `telegram_message_id` | Telegram message identifier when available |
| `telegram_channel_id` | Telegram channel identifier when available |
| `encryption_class` | RAW, CRYPT, or UNKNOWN metadata |
| `verification_state` | Integrity/transfer verification state |
| `tags` | Lab-managed informational classification |
| `job_id` | Related current/creating job when applicable |
| `first_seen_at` | First Lab observation |
| `last_seen_at` | Most recent Lab observation |

Fields may be split into normalized relational tables where implementation quality requires it, but the logical model above remains canonical.

---

## 5. Source Types

`source_type` uses a controlled vocabulary:

```text
LOCAL
TELDRIVE
RCLONE
TELEGRAM
ARCHIVE
BACKUP
UNKNOWN
```

Source type describes where an observation or object originates. It does not grant permission to mutate that source.

For example, a `TELDRIVE` record remains production-protected under the Production Boundary contract.

---

## 6. Destination Types

`destination_type` uses a controlled vocabulary:

```text
LOCAL
RAW
CRYPT
TELDRIVE
BACKUP
QUARANTINE
UNKNOWN
```

A destination classification is descriptive unless a job has explicitly authorized an operation involving that destination.

`RAW` and `CRYPT` describe the existing rclone-backed storage classes. The Lab catalog does not perform encryption merely because a record has `encryption_class=CRYPT`.

---

## 7. Encryption Classification

`encryption_class` is policy metadata:

```text
RAW
CRYPT
UNKNOWN
```

This field describes the expected storage class of an object. It must never be interpreted as proof that Lab itself encrypted the content.

Encryption state should remain separate from content identity and checksum identity.

---

## 8. Hash Model

The initial canonical content hash is **SHA-256**.

```text
hash_state:
  UNKNOWN
  PENDING
  COMPUTED
  VERIFIED
  FAILED
  STALE
```

Meaning:

- `UNKNOWN` — no usable hash exists;
- `PENDING` — hashing has been scheduled or is in progress;
- `COMPUTED` — a checksum was calculated from observed content;
- `VERIFIED` — checksum has been independently confirmed where the workflow requires it;
- `FAILED` — hashing could not be completed reliably;
- `STALE` — the object changed or the observation can no longer be trusted.

BLAKE3 may be benchmarked later for performance, but it does not replace SHA-256 as the initial canonical identity without a recorded architectural decision.

---

## 9. Duplicate Identity

Initial duplicate candidates are identified using:

```text
SHA-256 + size
```

This is an **informational identity signal**, not an automatic deletion rule.

Duplicate detection must:

- group candidates;
- show evidence;
- distinguish exact hashes from partial/unknown hashes;
- preserve provenance;
- avoid claiming certainty when hashing is incomplete;
- never delete or merge production objects automatically.

A future stronger identity model may include additional evidence, but such changes must be recorded as architectural decisions.

---

## 10. Verification State

`verification_state` uses:

```text
UNVERIFIED
PENDING
VERIFIED
FAILED
STALE
```

Meaning:

- `UNVERIFIED` — no required verification has completed;
- `PENDING` — verification is scheduled or running;
- `VERIFIED` — required verification succeeded;
- `FAILED` — required verification failed;
- `STALE` — an earlier verification no longer applies because relevant content/state changed.

Verification state is distinct from transfer state and hash state.

A file can be transferred successfully while still being `UNVERIFIED`.

---

## 11. Provenance

Every meaningful observation should preserve enough provenance to answer:

- where was this object observed?
- when was it observed?
- through which source/interface?
- what identifiers did the source provide?
- what job produced or changed the observation?
- which checksum and verification evidence exists?

At minimum, `source_type`, `source_identifier`, `first_seen_at`, `last_seen_at`, and relevant Telegram identifiers should be retained when available.

Provenance is essential for reconciliation and safe automation.

---

## 12. Telegram Identifiers

When available, the model may retain:

```text
telegram_file_id
telegram_message_id
telegram_channel_id
```

These identifiers are references, not permission grants.

They must not be exposed unnecessarily in logs or public interfaces, and secrets/session credentials must never be stored in the catalog.

Telegram identifiers should be treated as potentially useful for reconciliation, diagnostics, and source correlation.

---

## 13. Tags and Classification

Tags are Lab-level metadata and may be used for:

- search;
- organization planning;
- workflow selection;
- media/document classification;
- user-facing filters;
- reporting.

Tags must not silently cause production mutations.

AI-generated tags are advisory until accepted through the normal policy and authorization boundary where an associated operation would be mutating.

---

## 14. Job Relationship

A file record may reference a related `job_id` when its state was created, changed, indexed, transferred, verified, or otherwise processed by a durable Lab job.

The Job Model remains authoritative for job lifecycle state.

The Data Model records the resulting file observation and relationship; it must not duplicate the entire Job Engine state machine.

Parent/child job relationships are represented by the Job Model, not encoded into arbitrary file paths or filenames.

---

## 15. Time Semantics

The model distinguishes source timestamps from Lab observation timestamps.

Source timestamps:

```text
created_at
modified_at
```

Lab observation timestamps:

```text
first_seen_at
last_seen_at
```

These must not be conflated.

A file observed today may have been created years ago. Conversely, a source may not provide a trustworthy creation timestamp, in which case the field remains nullable/unknown rather than being fabricated.

All persisted Lab timestamps should use a consistent timezone-safe representation, preferably UTC.

---

## 16. Nullability and Unknown Values

Unknown information must remain unknown.

The implementation must not substitute fake values such as zero, empty strings, current time, or guessed MIME types when the source does not provide reliable information.

This is particularly important for:

- size;
- creation time;
- modification time;
- MIME type;
- checksums;
- Telegram identifiers;
- verification state.

Unknown state is preferable to false certainty.

---

## 17. Indexing Strategy

The initial SQLite implementation should provide indexes for common operations involving:

- path;
- name;
- parent path;
- SHA-256;
- MIME type;
- size;
- creation/modification timestamps;
- source type and source identifier;
- destination type and destination identifier;
- verification state;
- job identifier.

Full-text search (FTS) can be added later for filename, path, tags, descriptions, OCR text, and other textual metadata.

Search indexes are derived state and may be rebuilt.

---

## 18. Catalog Rebuildability

The catalog must be rebuildable without modifying production content.

A rebuild may:

1. inspect supported sources;
2. discover objects;
3. normalize metadata;
4. calculate required checksums;
5. populate the local catalog;
6. record provenance;
7. report objects that could not be observed.

A rebuild must not:

- delete production files;
- reorganize production paths;
- overwrite production metadata;
- migrate content;
- assume an old catalog is authoritative.

---

## 19. Snapshot and Observation History

The initial model may maintain current-state records while retaining enough timestamps and job/audit relationships to understand observation history.

Future snapshot/time-machine functionality can introduce explicit historical versions rather than corrupting current-state semantics.

Historical state must be additive and reconstructable where practical.

A future snapshot system must not require rewriting existing production storage merely to represent history.

---

## 20. Schema Versioning

Schema changes must be versioned.

Every migration should have:

- a unique version;
- deterministic application order;
- tests;
- rollback/recovery consideration where practical;
- documentation of affected fields and indexes;
- compatibility expectations.

Schema evolution must not silently alter the meaning of existing records.

If a change materially alters identity, provenance, verification, or safety semantics, it requires an architectural decision in `DECISIONS.md`.

---

## 21. Runtime Separation

The data model has three distinct locations/concepts:

```text
Git repository
  → schema definitions, migrations, models, queries, tests

Lab runtime
  → ~/.local/share/teldrive-lab/catalog.db
  → ~/.cache/teldrive-lab/

Production
  → TelDrive/Telegram storage and existing production database
```

These boundaries must remain explicit.

The Lab repository must never contain a production database dump or Telegram storage contents.

---

## 22. Integrity Invariants

The implementation must preserve these invariants:

1. Catalog records are derived observations.
2. Production storage remains authoritative for actual content.
3. Unknown information remains unknown.
4. SHA-256 is the initial canonical content checksum.
5. Duplicate detection is informational only.
6. Verification state is distinct from transfer/job state.
7. Provenance is preserved for meaningful observations.
8. Lab state can be deleted and rebuilt without deleting production files.
9. Schema changes are versioned.
10. Secrets never enter the catalog.
11. AI output cannot directly mutate catalog or production state outside deterministic policy.
12. A stale or inconsistent catalog must trigger reconciliation rather than silent destructive correction.

---

## 23. Minimum Initial Implementation

The first implementation should prioritize a small, reliable core:

- SQLite database;
- schema version table;
- canonical file record;
- controlled source/destination enums;
- hash state;
- verification state;
- provenance fields;
- timestamps;
- essential indexes;
- deterministic upsert/reconciliation behavior;
- rebuild support;
- migration tests;
- catalog integrity tests.

FTS, semantic embeddings, OCR text, media fingerprints, knowledge graphs, and advanced similarity indexes are later extensions—not prerequisites for the foundational catalog.

---

## 24. Operational Principle

> **The Data Model describes what TelDrive Lab knows about storage; it does not become the storage.**

The catalog must optimize for correctness, provenance, rebuildability, and safe automation rather than pretending derived metadata is more authoritative than the underlying content.

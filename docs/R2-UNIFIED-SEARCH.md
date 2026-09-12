# R2 — Unified TD Search

R2 replaces the old path/name-only `Catalog.search()` surface with one read-only
operator search contract over the canonical Lab catalog.

## Authority

TelDrive remains the production source of truth. R1 discovers existing TelDrive
metadata into the Lab-owned SQLite catalog. R2 searches that derived catalog only;
it never contacts Telegram/TelDrive to mutate data and never downloads remote files.

## Search surface

`td search QUERY` is the operator entry point. It is routed through the R2 search
engine while every other Phase 11 CLI command remains unchanged.

Free-text terms use SQLite FTS5 with AND semantics across indexed metadata:

- path
- name
- parent path
- extension
- MIME type
- source identifier
- tags

Structured filters may be combined with free text:

- `source:TELDRIVE`
- `source_id:rclone:teldrive:teldrive`
- `ext:mp4`
- `mime:video/mp4`
- `path:Movies`
- `tag:favorite`
- `min_size:1gb`
- `max_size:5gb`
- `after:2026-01-01T00:00:00Z`
- `before:2026-12-31T23:59:59Z`
- `sort:path|name|size|modified|created|source`
- `order:asc|desc`
- `limit:N`
- `offset:N`

CLI flags provide the same structured controls for scripting.

## Consistency

The FTS index is disposable derived state. Before a search, R2 compares a catalog
fingerprint (row count plus latest observation/modified timestamps) and rebuilds
the index automatically when it is stale. A standalone `UnifiedSearch.rebuild()`
operation is also available for explicit maintenance.

## Safety and bounds

- Read-only: search issues SELECT/FTS operations only.
- No rclone commands are executed by R2.
- Maximum page size is 500 records.
- Query length is bounded to 512 characters.
- Offset must be non-negative.
- Search filters are parameterized SQL values.
- FTS input is tokenized and quoted; arbitrary FTS operators are not accepted.
- Results have deterministic tie-breaking by path.
- The index is stored in the existing Lab catalog DB and contains no production files.

## Completion evidence

R2 is complete only when all of the following are green:

1. FTS5 index is available and automatically synchronized from the catalog.
2. `td search` uses the R2 engine.
3. Free-text, source, path, tag, size, date, sort, and pagination behavior is tested.
4. Invalid/bounded queries are tested.
5. Search does not mutate catalog records.
6. R2 gate and full CI pass.

R3 remains blocked until this evidence is green.

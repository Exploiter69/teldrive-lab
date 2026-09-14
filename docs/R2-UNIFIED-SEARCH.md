# R2 — Unified Search

## Purpose

R2 provides a single Lab-owned, bounded, deterministic search surface over the canonical catalog. It is an index/query capability, not a storage authority.

## Contract

- SQLite FTS5 is the canonical derived search index.
- Search covers catalog identity and metadata, including path, filename, parent path, extension, MIME type, source identity, tags, and optional bounded content.
- Structured filters are supported for source type, path prefix, size, and modification time.
- Result ordering is deterministic and pagination is hard-bounded.
- Content indexing is optional and bounded by the configured content-size/character limits.
- Search is read-only with respect to TelDrive and production storage.
- The search layer never performs rclone copy, move, delete, or filesystem deletion operations.

## CLI

`td search` routes through the R2 search implementation and reports the operation as non-mutating.

## Verification

The R2 gate checks the canonical search module, FTS5 index, bounded query/content behavior, supported filters, deterministic pagination, CLI routing, read-only contract, tests, and this documentation. The isolated R2 test suite is executed as part of the gate.

## Production boundary

R2 does not write to TelDrive PostgreSQL and does not mutate the production rclone remote. Index state is Lab-owned derived state and can be rebuilt from the canonical catalog.

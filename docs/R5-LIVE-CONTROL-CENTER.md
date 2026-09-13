# R5 — Live Control Center

## Purpose

R5 reconciles the historical Phase 22 control-center shell into a real operational observer over the already-proven TelDrive Lab control plane.

The Control Center is **not** a storage authority and does not execute jobs. TelDrive remains the production storage authority. The UI/API reads only Lab-owned derived state.

## Live surfaces

| Surface | Live source | Mutation |
|---|---|---|
| Dashboard | combined live provider | none |
| Catalog | Lab `Catalog` SQLite | none |
| Jobs | durable `JobStore` SQLite | none |
| Transfers | durable jobs filtered by workflow type | none |
| Media | canonical catalog media records | none |
| Search | canonical catalog search | none |
| Health | Lab runtime + store readiness + host disk state | none |
| Audit | Lab-owned `audit.db` | none |
| Configuration | runtime paths and safety invariants | none |

## HTTP contract

The local server binds to loopback by default (`127.0.0.1`). Existing loopback validation remains the binding boundary.

GET routes:

- `/`
- `/api/dashboard`
- `/api/catalog`
- `/api/jobs`
- `/api/transfers`
- `/api/media`
- `/api/search?q=<query>`
- `/api/health`
- `/api/audit`
- `/api/config`

POST, PUT, PATCH, and DELETE are rejected with HTTP 405.

## Safety contract

- no direct TelDrive PostgreSQL access;
- no production storage mutation;
- no UI-created authorization receipts;
- no worker/planner/scheduler authority;
- runtime state is subject to the existing protected-boundary checks;
- state returned to the UI is derived from Lab-owned stores;
- ₹0/$0 runtime dependencies;
- bounded API result sets prevent unbounded dashboard payloads.

## Operator entry point

```bash
PYTHONPATH="$PWD" python scripts/control_center.py
```

For disposable state or a specific Lab-owned state directory:

```bash
PYTHONPATH="$PWD" python scripts/control_center.py --state-root /path/to/lab-state
```

The state root must remain outside protected production boundaries.

## Evidence

R5 completion requires:

1. unit/integration tests for live catalog/jobs/search/media/health/audit reads;
2. HTTP read-only method enforcement;
3. disposable host gate using Lab-owned temporary state only;
4. CI invocation of the R5 host gate;
5. documentation of the live-state contract and safety boundary;
6. a clean Git checkpoint before merge.

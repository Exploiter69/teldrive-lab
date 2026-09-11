"""Safe, deterministic terminal control surface for TelDrive Lab.

Phase 11 is an operator interface, not a second authority. Commands that can
mutate Lab-owned state are explicit and audited; production storage/configuration
remains behind the existing safety boundaries.
"""
from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import asdict

from .archive import ArchiveExecutor, ArchivePlanner
from .audit import open_audit, record_event
from .backups import BackupExecutor, BackupPlanner, BackupScheduler, BackupStore
from .catalog import open_default_catalog
from .health import health_dict
from .integrity import duplicate_groups, duplicate_payload, missing_verified_copies, verify_records
from .jobs import JobState, JobStore
from .lifecycle import LifecycleExecutor, LifecyclePlanner
from .models import SourceType
from .monitoring import MonitoringStore, collect, job_snapshot, payload, storage_snapshot
from .organization import OrganizationExecutor, OrganizationPlanner
from .runtime import ensure_runtime
from .indexer import Indexer


def _json(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, default=str))


def _job_payload(job) -> dict[str, object]:
    data = asdict(job)
    data["type"] = job.type.value
    data["state"] = job.state.value
    return data


def _audit(conn, *, operation: str, decision: str, result: str, job_id: str | None = None, details: dict | None = None) -> None:
    record_event(conn, event_id=uuid.uuid4().hex, operation=operation, decision=decision, result=result, job_id=job_id, details=details or {})


def _add_organization_parser(sub):
    p = sub.add_parser("organize", help="plan or explicitly apply deterministic organization")
    p.add_argument("--source-type", choices=[x.value for x in SourceType], required=True); p.add_argument("--source-id", required=True)
    p.add_argument("--raw-root", required=True); p.add_argument("--crypt-root", required=True)
    mode = p.add_mutually_exclusive_group(); mode.add_argument("--dry-run", action="store_true"); mode.add_argument("--apply", action="store_true")


def _add_archive_parser(sub):
    p = sub.add_parser("archive", help="plan or explicitly apply a one-way archive workflow")
    p.add_argument("--source-type", choices=[x.value for x in SourceType], required=True); p.add_argument("--source-id", required=True); p.add_argument("--archive-root", required=True)
    mode = p.add_mutually_exclusive_group(); mode.add_argument("--dry-run", action="store_true"); mode.add_argument("--apply", action="store_true")


def _add_integrity_parser(sub):
    p = sub.add_parser("verify", help="read-only SHA-256 verification report"); p.add_argument("--source-type", choices=[x.value for x in SourceType], required=True); p.add_argument("--source-id", required=True)


def _add_duplicate_parser(sub):
    p = sub.add_parser("duplicates", help="read-only duplicate groups by size + SHA-256"); p.add_argument("--source-type", choices=[x.value for x in SourceType], required=True); p.add_argument("--source-id", required=True)


def _add_lifecycle_parser(sub):
    p = sub.add_parser("lifecycle", help="plan or explicitly apply Lab-owned lifecycle actions"); p.add_argument("action", choices=["purge", "restore"]); p.add_argument("--root", required=True); p.add_argument("--apply", action="store_true")


def _add_backup_parser(sub):
    p = sub.add_parser("backup", help="plan, apply, verify, or restore a Lab-owned backup"); p.add_argument("action", choices=["plan", "apply", "verify", "restore"]); p.add_argument("sources", nargs="+"); p.add_argument("--root", required=True); p.add_argument("--restore-root"); p.add_argument("--apply", action="store_true")


def _add_backup_schedule_parser(sub):
    p = sub.add_parser("backup-schedule", help="create or run durable Lab-owned backup schedules"); p.add_argument("action", choices=["add", "run-due"]); p.add_argument("sources", nargs="*"); p.add_argument("--root"); p.add_argument("--interval", type=int, default=86400)


def _add_monitoring_parser(sub):
    p = sub.add_parser("monitor", help="read-only health, storage, jobs, and alert observation"); p.add_argument("action", choices=["run", "health", "jobs", "alerts", "storage"]); p.add_argument("--path", action="append", dest="paths"); p.add_argument("--all-alerts", action="store_true")


def _add_job_parser(sub):
    p = sub.add_parser("jobs", help="inspect the durable Lab job queue"); p.add_argument("--state", choices=[x.value for x in JobState]); p.add_argument("--limit", type=int, default=100)
    p = sub.add_parser("job", help="inspect one durable job"); p.add_argument("job_id")
    for command, help_text in (("pause", "pause a running Lab job"), ("resume", "resume a paused Lab job"), ("cancel", "cancel a queued/running/paused Lab job")):
        p = sub.add_parser(command, help=help_text); p.add_argument("job_id")


def _add_search_parser(sub):
    p = sub.add_parser("search", help="read-only search of indexed catalog metadata"); p.add_argument("query"); p.add_argument("--limit", type=int, default=50)


def _add_index_parser(sub):
    p = sub.add_parser("index", help="bounded read-only filesystem metadata indexing"); p.add_argument("root"); p.add_argument("--source-type", choices=[x.value for x in SourceType], default=SourceType.LOCAL.value); p.add_argument("--source-id")


def _add_health_parser(sub):
    sub.add_parser("health", help="read-only system health report")


def _add_status_parser(sub):
    sub.add_parser("status", help="compact operator status report")


def _add_audit_parser(sub):
    p = sub.add_parser("audit", help="read-only audit event history"); p.add_argument("--limit", type=int, default=50); p.add_argument("--operation")


def _archive_payload(plan):
    return {"digest": plan.digest, "total": plan.total, "copy": plan.copy_count, "duplicate": plan.duplicate_count, "conflict": plan.conflict_count, "blocked": plan.blocked_count, "items": [{"source": i.candidate.source, "destination": i.candidate.destination, "size": i.candidate.size, "sha256": i.candidate.sha256, "source_type": i.candidate.source_type.value, "duplicate_of": i.candidate.duplicate_of, "action": i.action.value, "reason": i.reason} for i in plan.items]}


def _verification_payload(report):
    return {"total": len(report.results), "verified": report.verified, "missing": report.missing, "changed": report.changed, "mismatched": report.mismatched, "unverifiable": report.unverifiable, "items": [{"path": i.path, "expected_sha256": i.expected_sha256, "actual_sha256": i.actual_sha256, "expected_size": i.expected_size, "actual_size": i.actual_size, "state": i.state.value} for i in report.results]}


def _run_job_control(command: str, job_id: str, store: JobStore, audit) -> int:
    try:
        if command == "pause": job = store.pause(job_id)
        elif command == "resume": job = store.resume(job_id)
        else: job = store.cancel(job_id)
    except (KeyError, ValueError) as exc:
        _json({"success": False, "error": str(exc)}); return 2
    _audit(audit, operation="JOB_CONTROL", decision="EXPLICIT_OPERATOR_ACTION", result=job.state.value, job_id=job_id, details={"action": command})
    _json({"success": True, "action": command, "job": _job_payload(job)}); return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="td", description="TelDrive Lab safe operator CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_status_parser(sub); _add_health_parser(sub); sub.add_parser("init", help="initialize and print the Lab runtime path")
    _add_search_parser(sub); _add_index_parser(sub); _add_job_parser(sub); _add_audit_parser(sub)
    _add_organization_parser(sub); _add_archive_parser(sub); _add_integrity_parser(sub); _add_duplicate_parser(sub); _add_lifecycle_parser(sub); _add_backup_parser(sub); _add_backup_schedule_parser(sub); _add_monitoring_parser(sub)
    args = parser.parse_args(); paths = ensure_runtime(); audit = open_audit(paths.state / "audit.db")
    try:
        if args.command == "init": _json({"runtime": str(paths.root), "state": str(paths.state), "cache": str(paths.cache)}); return 0
        if args.command in {"status", "health"}:
            _json(health_dict()); return 0
        if args.command == "search":
            catalog = open_default_catalog(); results = catalog.search(args.query, limit=args.limit); _json({"query": args.query, "count": len(results), "items": [asdict(r) for r in results]}); return 0
        if args.command == "index":
            catalog = open_default_catalog(); result = Indexer(catalog).scan(args.root, source_type=SourceType(args.source_type), source_identifier=args.source_id); _audit(audit, operation="INDEX", decision="ALLOWED_READ_ONLY", result="COMPLETED", details={"root": result.root, "indexed": result.indexed, "bounded": result.bounded}); _json(asdict(result)); return 0
        if args.command == "jobs":
            store = JobStore(paths.state / "jobs.db"); state = JobState(args.state) if args.state else None; _json({"count": len(store.list_jobs(state=state, limit=args.limit)), "items": [_job_payload(j) for j in store.list_jobs(state=state, limit=args.limit)]}); return 0
        if args.command == "job":
            try: job = JobStore(paths.state / "jobs.db").get(args.job_id)
            except KeyError: _json({"success": False, "error": "job not found", "job_id": args.job_id}); return 2
            _json(_job_payload(job)); return 0
        if args.command in {"pause", "resume", "cancel"}: return _run_job_control(args.command, args.job_id, JobStore(paths.state / "jobs.db"), audit)
        if args.command == "audit":
            if args.limit < 1 or args.limit > 1000: _json({"success": False, "error": "limit must be between 1 and 1000"}); return 2
            sql = "SELECT event_id,timestamp,operation,job_id,source,destination,decision,result,checksum,error_code,details_json FROM events"; params = []
            if args.operation: sql += " WHERE operation=?"; params.append(args.operation)
            sql += " ORDER BY id DESC LIMIT ?"; params.append(args.limit)
            rows = audit.execute(sql, params).fetchall(); _json([dict(r) for r in rows]); return 0
        if args.command == "monitor":
            store = MonitoringStore(paths.state / "monitor.db")
            if args.action == "health": _json(health_dict()); return 0
            if args.action == "storage": _json([asdict(storage_snapshot(p)) for p in (args.paths or [paths.root])]); return 0
            if args.action == "jobs": _json(asdict(job_snapshot(paths.state / "jobs.db"))); return 0
            if args.action == "alerts": _json([asdict(a) for a in store.alerts(active_only=not args.all_alerts)]); return 0
            snapshot = collect(store=store, audit_path=paths.state / "audit.db", job_db=paths.state / "jobs.db", storage_paths=args.paths or [paths.root]); _json(payload(snapshot)); return 0 if not snapshot.alerts else 1
        if args.command == "organize":
            catalog = open_default_catalog(); plan = OrganizationPlanner().plan(catalog.list_source(SourceType(args.source_type), args.source_id), raw_root=args.raw_root, crypt_root=args.crypt_root); data = {"digest": plan.digest, "total": plan.total, "copy": plan.copy_count, "noop": plan.noop_count, "conflict": plan.conflict_count, "blocked": plan.blocked_count, "items": [asdict(i) for i in plan.items]}
            if not args.apply: _json(data); return 0
            if plan.blocked_count or plan.conflict_count: _json(data); return 2
            result = OrganizationExecutor().apply(plan, authorization_id=f"cli:{uuid.uuid4()}"); data.update(applied=len(result.results), success=result.success); _json(data); return 0 if result.success else 1
        if args.command == "archive":
            catalog = open_default_catalog(); plan = ArchivePlanner().plan(catalog.list_source(SourceType(args.source_type), args.source_id), archive_root=args.archive_root); data = _archive_payload(plan)
            if not args.apply: _json(data); return 0
            if plan.blocked_count or plan.conflict_count or plan.duplicate_count: _json(data); return 2
            result = ArchiveExecutor().apply(plan, authorization_id=f"cli:{uuid.uuid4()}"); data.update(applied=len(result.results), success=result.success); _json(data); return 0 if result.success else 1
        if args.command == "verify":
            catalog = open_default_catalog(); report = verify_records(catalog.list_source(SourceType(args.source_type), args.source_id)); _json(_verification_payload(report)); return 0 if report.missing == report.changed == report.mismatched == report.unverifiable == 0 else 1
        if args.command == "duplicates":
            catalog = open_default_catalog(); records = catalog.list_source(SourceType(args.source_type), args.source_id); groups = duplicate_groups(records); missing = missing_verified_copies(records); _json({"groups": duplicate_payload(groups), "group_count": len(groups), "potential_reclaimable_bytes": sum(g.reclaimable_bytes for g in groups), "missing_verified_copies": list(missing), "destructive_action": "NONE"}); return 0
        if args.command == "lifecycle":
            planner = LifecyclePlanner(); plan = planner.purge_plan() if args.action == "purge" else planner.restore_plan(destination_root=args.root); data = {"action": args.action, "digest": plan.digest, "total": len(plan.items), "blocked": plan.blocked_count, "items": [{"source": i.source, "destination": i.destination or i.quarantine, "action": i.action.value, "reason": i.reason, "size": i.size, "sha256": i.sha256, "purge_after": i.purge_after} for i in plan.items]}
            if not args.apply: _json(data); return 0
            if plan.blocked_count: _json(data); return 2
            executor = LifecycleExecutor(); success, changed = executor.purge(plan, authorization_id=f"cli:{uuid.uuid4()}") if args.action == "purge" else executor.restore(plan, authorization_id=f"cli:{uuid.uuid4()}"); data.update(changed=list(changed), success=success); _json(data); return 0 if success else 1
        if args.command == "backup":
            planner = BackupPlanner(); store = BackupStore(); executor = BackupExecutor(store); plan = planner.plan(args.sources, backup_root=args.root)
            if args.action == "plan": _json({"digest": plan.digest, "manifest": plan.manifest_path, "items": [asdict(i) for i in plan.items]}); return 0
            if args.action == "apply":
                if not args.apply: _json({"success": False, "error": "backup mutation requires --apply"}); return 2
                success, changed = executor.apply(plan, authorization_id=f"cli:{uuid.uuid4()}"); _json({"success": success, "changed": list(changed), "digest": plan.digest}); return 0 if success else 1
            if args.action == "verify":
                results = executor.verify(plan); _json([asdict(r) for r in results]); return 0 if all(r.state == "VERIFIED" for r in results) else 1
            if not args.restore_root or not args.apply: _json({"success": False, "error": "restore requires --restore-root and --apply"}); return 2
            success, changed = executor.restore(plan, restore_root=args.restore_root, authorization_id=f"cli:{uuid.uuid4()}"); _json({"success": success, "restored": list(changed), "digest": plan.digest}); return 0 if success else 1
        if args.command == "backup-schedule":
            scheduler = BackupScheduler()
            if args.action == "add":
                if not args.sources or not args.root: _json({"success": False, "error": "add requires sources and --root"}); return 2
                _json(asdict(scheduler.add(args.sources, args.root, interval_seconds=args.interval))); return 0
            _json({"created_jobs": list(scheduler.run_due())}); return 0
        return 2
    finally:
        audit.close()

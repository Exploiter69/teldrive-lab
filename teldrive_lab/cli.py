from __future__ import annotations

import argparse
import json
import uuid

from .archive import ArchiveExecutor, ArchivePlanner
from .audit import open_audit, record_event
from .backups import BackupExecutor, BackupPlanner, BackupStore, BackupScheduler
from .catalog import open_default_catalog
from .health import health_dict
from .integrity import duplicate_groups, duplicate_payload, missing_verified_copies, verify_records
from .lifecycle import LifecycleExecutor, LifecyclePlanner
from .models import SourceType
from .organization import OrganizationExecutor, OrganizationPlanner
from .runtime import ensure_runtime


def _add_organization_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("organize", help="plan or explicitly apply deterministic organization")
    parser.add_argument("--source-type", choices=[item.value for item in SourceType], required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--crypt-root", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")


def _add_archive_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("archive", help="plan or explicitly apply a one-way archive workflow")
    parser.add_argument("--source-type", choices=[item.value for item in SourceType], required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--archive-root", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")


def _add_integrity_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("verify", help="read-only SHA-256 verification report")
    parser.add_argument("--source-type", choices=[item.value for item in SourceType], required=True)
    parser.add_argument("--source-id", required=True)


def _add_duplicate_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("duplicates", help="read-only duplicate groups by size + SHA-256")
    parser.add_argument("--source-type", choices=[item.value for item in SourceType], required=True)
    parser.add_argument("--source-id", required=True)


def _add_lifecycle_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("lifecycle", help="plan or explicitly apply Lab-owned lifecycle actions")
    parser.add_argument("action", choices=["purge", "restore"])
    parser.add_argument("--root", required=True)
    parser.add_argument("--apply", action="store_true")


def _add_backup_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("backup", help="plan, apply, verify, or restore a Lab-owned backup")
    parser.add_argument("action", choices=["plan", "apply", "verify", "restore"])
    parser.add_argument("sources", nargs="+", help="Lab-owned source files")
    parser.add_argument("--root", required=True, help="backup destination root")
    parser.add_argument("--restore-root", help="restore destination root")
    parser.add_argument("--apply", action="store_true", help="explicitly authorize the requested mutation")


def _add_backup_schedule_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("backup-schedule", help="create or run durable Lab-owned backup schedules")
    parser.add_argument("action", choices=["add", "run-due"])
    parser.add_argument("sources", nargs="*", help="source files for add")
    parser.add_argument("--root", help="backup destination root")
    parser.add_argument("--interval", type=int, default=86400)


def _archive_payload(plan) -> dict:
    return {"digest": plan.digest, "total": plan.total, "copy": plan.copy_count, "duplicate": plan.duplicate_count,
            "conflict": plan.conflict_count, "blocked": plan.blocked_count,
            "items": [{"source": item.candidate.source, "destination": item.candidate.destination,
                       "size": item.candidate.size, "sha256": item.candidate.sha256,
                       "source_type": item.candidate.source_type.value, "duplicate_of": item.candidate.duplicate_of,
                       "action": item.action.value, "reason": item.reason} for item in plan.items]}


def _verification_payload(report) -> dict:
    return {"total": len(report.results), "verified": report.verified, "missing": report.missing,
            "changed": report.changed, "mismatched": report.mismatched, "unverifiable": report.unverifiable,
            "items": [{"path": item.path, "expected_sha256": item.expected_sha256, "actual_sha256": item.actual_sha256,
                       "expected_size": item.expected_size, "actual_size": item.actual_size, "state": item.state.value}
                      for item in report.results]}


def main() -> int:
    parser = argparse.ArgumentParser(prog="td")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="run read-only system health checks")
    sub.add_parser("init", help="initialize Lab-owned runtime directories")
    _add_organization_parser(sub); _add_archive_parser(sub); _add_integrity_parser(sub)
    _add_duplicate_parser(sub); _add_lifecycle_parser(sub); _add_backup_parser(sub); _add_backup_schedule_parser(sub)
    args = parser.parse_args()
    paths = ensure_runtime()
    audit = open_audit(paths.state / "audit.db")
    try:
        if args.command == "init":
            record_event(audit, event_id=str(uuid.uuid4()), operation="init", decision="allowed", result="completed")
            print(paths.root); return 0
        if args.command == "status":
            result = health_dict()
            record_event(audit, event_id=str(uuid.uuid4()), operation="health", decision="allowed", result="completed",
                         details={"checks": len(result), "failed": sum(not x["ok"] for x in result)})
            print(json.dumps(result, indent=2)); return 0 if all(x["ok"] for x in result) else 1
        if args.command == "organize":
            catalog = open_default_catalog(); records = catalog.list_source(SourceType(args.source_type), args.source_id)
            plan = OrganizationPlanner().plan(records, raw_root=args.raw_root, crypt_root=args.crypt_root)
            payload = {"digest": plan.digest, "total": plan.total, "copy": plan.copy_count, "noop": plan.noop_count,
                       "conflict": plan.conflict_count, "blocked": plan.blocked_count,
                       "items": [{"source": i.source, "destination": i.destination, "class": i.file_class.value,
                                  "storage": i.storage_class.value, "rule": i.rule_id, "action": i.action.value, "reason": i.reason}
                                 for i in plan.items]}
            if not args.apply:
                record_event(audit, event_id=str(uuid.uuid4()), operation="organize-plan", decision="allowed", result="dry-run", details={"digest": plan.digest})
                print(json.dumps(payload, indent=2)); return 0
            if plan.blocked_count or plan.conflict_count:
                print(json.dumps(payload, indent=2)); return 2
            result = OrganizationExecutor().apply(plan, authorization_id=f"cli:{uuid.uuid4()}")
            payload.update(applied=len(result.results), success=result.success); print(json.dumps(payload, indent=2)); return 0 if result.success else 1
        if args.command == "archive":
            catalog = open_default_catalog(); records = catalog.list_source(SourceType(args.source_type), args.source_id)
            plan = ArchivePlanner().plan(records, archive_root=args.archive_root); payload = _archive_payload(plan)
            if not args.apply:
                print(json.dumps(payload, indent=2)); return 0
            if plan.blocked_count or plan.conflict_count or plan.duplicate_count:
                print(json.dumps(payload, indent=2)); return 2
            result = ArchiveExecutor().apply(plan, authorization_id=f"cli:{uuid.uuid4()}")
            payload.update(applied=len(result.results), success=result.success); print(json.dumps(payload, indent=2)); return 0 if result.success else 1
        if args.command == "verify":
            catalog = open_default_catalog(); report = verify_records(catalog.list_source(SourceType(args.source_type), args.source_id))
            print(json.dumps(_verification_payload(report), indent=2)); return 0 if report.missing == report.changed == report.mismatched == report.unverifiable == 0 else 1
        if args.command == "duplicates":
            catalog = open_default_catalog(); records = catalog.list_source(SourceType(args.source_type), args.source_id)
            groups = duplicate_groups(records); missing = missing_verified_copies(records)
            print(json.dumps({"groups": duplicate_payload(groups), "group_count": len(groups),
                              "potential_reclaimable_bytes": sum(g.reclaimable_bytes for g in groups),
                              "missing_verified_copies": list(missing), "destructive_action": "NONE"}, indent=2)); return 0
        if args.command == "lifecycle":
            planner = LifecyclePlanner(); plan = planner.purge_plan() if args.action == "purge" else planner.restore_plan(destination_root=args.root)
            payload = {"action": args.action, "digest": plan.digest, "total": len(plan.items), "blocked": plan.blocked_count,
                       "items": [{"source": i.source, "destination": i.destination or i.quarantine, "action": i.action.value,
                                  "reason": i.reason, "size": i.size, "sha256": i.sha256, "purge_after": i.purge_after} for i in plan.items]}
            if not args.apply:
                print(json.dumps(payload, indent=2)); return 0
            if plan.blocked_count:
                print(json.dumps(payload, indent=2)); return 2
            executor = LifecycleExecutor()
            success, changed = (executor.purge(plan, authorization_id=f"cli:{uuid.uuid4()}") if args.action == "purge"
                                else executor.restore(plan, authorization_id=f"cli:{uuid.uuid4()}"))
            payload.update(changed=list(changed), success=success); print(json.dumps(payload, indent=2)); return 0 if success else 1
        if args.command == "backup":
            planner = BackupPlanner(); store = BackupStore(); executor = BackupExecutor(store)
            plan = planner.plan(args.sources, backup_root=args.root)
            if args.action == "plan":
                print(json.dumps({"digest": plan.digest, "manifest": plan.manifest_path, "items": [i.__dict__ for i in plan.items]}, indent=2)); return 0
            if args.action == "apply":
                if not args.apply: print("refusing backup mutation without --apply"); return 2
                success, changed = executor.apply(plan, authorization_id=f"cli:{uuid.uuid4()}")
                print(json.dumps({"success": success, "changed": list(changed), "digest": plan.digest}, indent=2)); return 0 if success else 1
            if args.action == "verify":
                results = executor.verify(plan); print(json.dumps([r.__dict__ for r in results], indent=2)); return 0 if all(r.state == "VERIFIED" for r in results) else 1
            if not args.restore_root: print("--restore-root is required for restore"); return 2
            if not args.apply: print("refusing restore mutation without --apply"); return 2
            success, changed = executor.restore(plan, restore_root=args.restore_root, authorization_id=f"cli:{uuid.uuid4()}")
            print(json.dumps({"success": success, "restored": list(changed), "digest": plan.digest}, indent=2)); return 0 if success else 1
        if args.command == "backup-schedule":
            scheduler = BackupScheduler()
            if args.action == "add":
                if not args.sources or not args.root: print("add requires sources and --root"); return 2
                schedule = scheduler.add(args.sources, args.root, interval_seconds=args.interval)
                print(json.dumps(schedule.__dict__, indent=2)); return 0
            ids = scheduler.run_due(); print(json.dumps({"created_jobs": list(ids)}, indent=2)); return 0
    finally:
        audit.close()
    return 2

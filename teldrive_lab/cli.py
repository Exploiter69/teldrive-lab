from __future__ import annotations

import argparse
import json
import uuid

from .archive import ArchiveExecutor, ArchivePlanner
from .audit import open_audit, record_event
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
    parser.add_argument("--source-id", required=True, help="catalog source identifier")
    parser.add_argument("--raw-root", required=True, help="organization destination root for RAW files")
    parser.add_argument("--crypt-root", required=True, help="organization destination root for CRYPT files")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="show the deterministic plan without mutation")
    mode.add_argument("--apply", action="store_true", help="explicitly authorize and apply a safe Lab-only plan")


def _add_archive_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("archive", help="plan or explicitly apply a one-way archive workflow")
    parser.add_argument("--source-type", choices=[item.value for item in SourceType], required=True)
    parser.add_argument("--source-id", required=True, help="catalog source identifier")
    parser.add_argument("--archive-root", required=True, help="archive destination root")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="show the archive plan without mutation")
    mode.add_argument("--apply", action="store_true", help="explicitly authorize and apply a safe Lab-only plan")


def _add_integrity_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("verify", help="read-only SHA-256 verification report")
    parser.add_argument("--source-type", choices=[item.value for item in SourceType], required=True)
    parser.add_argument("--source-id", required=True, help="catalog source identifier")


def _add_duplicate_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("duplicates", help="read-only duplicate groups by size + SHA-256")
    parser.add_argument("--source-type", choices=[item.value for item in SourceType], required=True)
    parser.add_argument("--source-id", required=True, help="catalog source identifier")


def _add_lifecycle_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("lifecycle", help="plan or explicitly apply Lab-owned lifecycle actions")
    parser.add_argument("action", choices=["purge", "restore"], help="lifecycle operation")
    parser.add_argument("--root", required=True, help="Lab-owned quarantine root for purge or restore destination root")
    parser.add_argument("--apply", action="store_true", help="explicitly authorize the planned lifecycle action")


def _archive_payload(plan) -> dict:
    return {
        "digest": plan.digest,
        "total": plan.total,
        "copy": plan.copy_count,
        "duplicate": plan.duplicate_count,
        "conflict": plan.conflict_count,
        "blocked": plan.blocked_count,
        "items": [
            {
                "source": item.candidate.source,
                "destination": item.candidate.destination,
                "size": item.candidate.size,
                "sha256": item.candidate.sha256,
                "source_type": item.candidate.source_type.value,
                "duplicate_of": item.candidate.duplicate_of,
                "action": item.action.value,
                "reason": item.reason,
            }
            for item in plan.items
        ],
    }


def _verification_payload(report) -> dict:
    return {
        "total": len(report.results),
        "verified": report.verified,
        "missing": report.missing,
        "changed": report.changed,
        "mismatched": report.mismatched,
        "unverifiable": report.unverifiable,
        "items": [
            {
                "path": item.path,
                "expected_sha256": item.expected_sha256,
                "actual_sha256": item.actual_sha256,
                "expected_size": item.expected_size,
                "actual_size": item.actual_size,
                "state": item.state.value,
            }
            for item in report.results
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="td")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="run read-only system health checks")
    sub.add_parser("init", help="initialize Lab-owned runtime directories")
    _add_organization_parser(sub)
    _add_archive_parser(sub)
    _add_integrity_parser(sub)
    _add_duplicate_parser(sub)
    _add_lifecycle_parser(sub)
    args = parser.parse_args()

    paths = ensure_runtime()
    audit = open_audit(paths.state / "audit.db")
    try:
        if args.command == "init":
            record_event(audit, event_id=str(uuid.uuid4()), operation="init",
                         decision="allowed", result="completed")
            print(paths.root)
            return 0
        if args.command == "status":
            result = health_dict()
            record_event(audit, event_id=str(uuid.uuid4()), operation="health",
                         decision="allowed", result="completed",
                         details={"checks": len(result), "failed": sum(not x["ok"] for x in result)})
            print(json.dumps(result, indent=2))
            return 0 if all(x["ok"] for x in result) else 1
        if args.command == "organize":
            catalog = open_default_catalog()
            records = catalog.list_source(SourceType(args.source_type), args.source_id)
            plan = OrganizationPlanner().plan(records, raw_root=args.raw_root, crypt_root=args.crypt_root)
            payload = {
                "digest": plan.digest, "total": plan.total, "copy": plan.copy_count,
                "noop": plan.noop_count, "conflict": plan.conflict_count, "blocked": plan.blocked_count,
                "items": [
                    {"source": item.source, "destination": item.destination, "class": item.file_class.value,
                     "storage": item.storage_class.value, "rule": item.rule_id,
                     "action": item.action.value, "reason": item.reason}
                    for item in plan.items
                ],
            }
            if not args.apply:
                record_event(audit, event_id=str(uuid.uuid4()), operation="organize-plan",
                             decision="allowed", result="dry-run", details={"digest": plan.digest})
                print(json.dumps(payload, indent=2))
                return 0
            if plan.blocked_count or plan.conflict_count:
                record_event(audit, event_id=str(uuid.uuid4()), operation="organize-apply",
                             decision="denied", result="blocked",
                             details={"digest": plan.digest, "blocked": plan.blocked_count, "conflict": plan.conflict_count})
                print(json.dumps(payload, indent=2))
                return 2
            result = OrganizationExecutor().apply(plan, authorization_id=f"cli:{uuid.uuid4()}")
            record_event(audit, event_id=str(uuid.uuid4()), operation="organize-apply",
                         decision="allowed", result="completed" if result.success else "failed",
                         details={"digest": plan.digest, "transfers": len(result.results)})
            payload["applied"] = len(result.results)
            payload["success"] = result.success
            print(json.dumps(payload, indent=2))
            return 0 if result.success else 1
        if args.command == "archive":
            catalog = open_default_catalog()
            records = catalog.list_source(SourceType(args.source_type), args.source_id)
            plan = ArchivePlanner().plan(records, archive_root=args.archive_root)
            payload = _archive_payload(plan)
            if not args.apply:
                record_event(audit, event_id=str(uuid.uuid4()), operation="archive-plan",
                             decision="allowed", result="dry-run", details={"digest": plan.digest})
                print(json.dumps(payload, indent=2))
                return 0
            if plan.blocked_count or plan.conflict_count or plan.duplicate_count:
                record_event(audit, event_id=str(uuid.uuid4()), operation="archive-apply",
                             decision="denied", result="blocked",
                             details={"digest": plan.digest, "blocked": plan.blocked_count,
                                      "conflict": plan.conflict_count, "duplicate": plan.duplicate_count})
                print(json.dumps(payload, indent=2))
                return 2
            result = ArchiveExecutor().apply(plan, authorization_id=f"cli:{uuid.uuid4()}")
            record_event(audit, event_id=str(uuid.uuid4()), operation="archive-apply",
                         decision="allowed", result="completed" if result.success else "failed",
                         details={"digest": plan.digest, "transfers": len(result.results)})
            payload["applied"] = len(result.results)
            payload["success"] = result.success
            print(json.dumps(payload, indent=2))
            return 0 if result.success else 1
        if args.command == "verify":
            catalog = open_default_catalog()
            records = catalog.list_source(SourceType(args.source_type), args.source_id)
            report = verify_records(records)
            payload = _verification_payload(report)
            record_event(audit, event_id=str(uuid.uuid4()), operation="verify",
                         decision="allowed", result="completed",
                         details={"total": len(report.results), "verified": report.verified,
                                  "missing": report.missing, "mismatched": report.mismatched})
            print(json.dumps(payload, indent=2))
            return 0 if report.missing == report.changed == report.mismatched == report.unverifiable == 0 else 1
        if args.command == "duplicates":
            catalog = open_default_catalog()
            records = catalog.list_source(SourceType(args.source_type), args.source_id)
            groups = duplicate_groups(records)
            missing = missing_verified_copies(records)
            payload = {"groups": duplicate_payload(groups), "group_count": len(groups),
                       "potential_reclaimable_bytes": sum(group.reclaimable_bytes for group in groups),
                       "missing_verified_copies": list(missing),
                       "destructive_action": "NONE"}
            record_event(audit, event_id=str(uuid.uuid4()), operation="duplicates",
                         decision="allowed", result="report",
                         details={"groups": len(groups), "missing_verified_copies": len(missing)})
            print(json.dumps(payload, indent=2))
            return 0
        if args.command == "lifecycle":
            planner = LifecyclePlanner()
            if args.action == "purge":
                plan = planner.purge_plan()
            else:
                plan = planner.restore_plan(destination_root=args.root)
            payload = {
                "action": args.action,
                "digest": plan.digest,
                "total": len(plan.items),
                "blocked": plan.blocked_count,
                "items": [
                    {"source": item.source, "destination": item.quarantine,
                     "action": item.action.value, "reason": item.reason,
                     "size": item.size, "sha256": item.sha256, "purge_after": item.purge_after}
                    for item in plan.items
                ],
            }
            if not args.apply:
                record_event(audit, event_id=str(uuid.uuid4()), operation=f"lifecycle-{args.action}-plan",
                             decision="allowed", result="dry-run", details={"digest": plan.digest})
                print(json.dumps(payload, indent=2))
                return 0
            if plan.blocked_count:
                record_event(audit, event_id=str(uuid.uuid4()), operation=f"lifecycle-{args.action}-apply",
                             decision="denied", result="blocked", details={"digest": plan.digest})
                print(json.dumps(payload, indent=2))
                return 2
            executor = LifecycleExecutor()
            if args.action == "purge":
                success, changed = executor.purge(plan, authorization_id=f"cli:{uuid.uuid4()}")
            else:
                success, changed = executor.restore(plan, authorization_id=f"cli:{uuid.uuid4()}")
            payload["changed"] = list(changed)
            payload["success"] = success
            record_event(audit, event_id=str(uuid.uuid4()), operation=f"lifecycle-{args.action}-apply",
                         decision="allowed", result="completed" if success else "failed",
                         details={"digest": plan.digest, "changed": len(changed)})
            print(json.dumps(payload, indent=2))
            return 0 if success else 1
    finally:
        audit.close()
    return 2

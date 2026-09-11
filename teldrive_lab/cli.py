from __future__ import annotations

import argparse
import json
import uuid

from .audit import open_audit, record_event
from .health import health_dict
from .models import SourceType
from .organization import OrganizationExecutor, OrganizationPlanner
from .catalog import open_default_catalog
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


def main() -> int:
    parser = argparse.ArgumentParser(prog="td")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="run read-only system health checks")
    sub.add_parser("init", help="initialize Lab-owned runtime directories")
    _add_organization_parser(sub)
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
            plan = OrganizationPlanner().plan(
                records, raw_root=args.raw_root, crypt_root=args.crypt_root
            )
            payload = {
                "digest": plan.digest,
                "total": plan.total,
                "copy": plan.copy_count,
                "noop": plan.noop_count,
                "conflict": plan.conflict_count,
                "blocked": plan.blocked_count,
                "items": [
                    {
                        "source": item.source,
                        "destination": item.destination,
                        "class": item.file_class.value,
                        "storage": item.storage_class.value,
                        "rule": item.rule_id,
                        "action": item.action.value,
                        "reason": item.reason,
                    }
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
                             details={"digest": plan.digest, "blocked": plan.blocked_count,
                                      "conflict": plan.conflict_count})
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
    finally:
        audit.close()
    return 2

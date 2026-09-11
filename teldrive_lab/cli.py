from __future__ import annotations

import argparse
import json
import uuid

from .audit import open_audit, record_event
from .health import health_dict
from .runtime import ensure_runtime


def main() -> int:
    parser = argparse.ArgumentParser(prog="td")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="run read-only system health checks")
    sub.add_parser("init", help="initialize Lab-owned runtime directories")
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
    finally:
        audit.close()
    return 2

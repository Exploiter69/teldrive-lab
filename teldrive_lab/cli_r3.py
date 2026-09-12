"""R3 CLI: operational media discovery and Jellyfin verification."""
from __future__ import annotations
import argparse, json
from dataclasses import asdict
from pathlib import Path
from .catalog import open_default_catalog
from .media_jellyfin import discover_media, discover_filesystem, jellyfin_status, status_payload

def main() -> int:
    import sys
    if len(sys.argv) < 2 or sys.argv[1] != "media":
        from .cli_r2 import main as legacy
        return legacy()
    p = argparse.ArgumentParser(prog="td media")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    scan = sub.add_parser("scan")
    scan.add_argument("--root")
    scan.add_argument("--source-id")
    scan.add_argument("--limit", type=int, default=5000)
    verify = sub.add_parser("verify")
    verify.add_argument("--base-url", default="http://127.0.0.1:8096")
    args = p.parse_args(sys.argv[2:])
    if args.action == "status":
        print(json.dumps(status_payload(), indent=2, sort_keys=True)); return 0
    if args.action == "scan":
        if args.root:
            items = discover_filesystem(Path(args.root), source=args.source_id or "LOCAL")[:args.limit]
        else:
            items = discover_media(open_default_catalog().list_source(__import__('teldrive_lab.models', fromlist=['SourceType']).SourceType.TELDRIVE, args.source_id or "teldrive"))[:args.limit]
        counts = {}
        for item in items: counts[item.media_type] = counts.get(item.media_type, 0) + 1
        print(json.dumps({"discovered":len(items),"by_type":counts,"items":[asdict(x) for x in items],"mutation":"NONE"}, indent=2, default=str)); return 0
    status = jellyfin_status(args.base_url)
    print(json.dumps(asdict(status), indent=2, sort_keys=True))
    return 0 if status.reachable else 1

if __name__ == "__main__": raise SystemExit(main())

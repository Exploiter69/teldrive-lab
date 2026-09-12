"""R2 CLI compatibility wrapper.

Only the existing ``td search`` command is upgraded here. Every other command
continues through the established Phase 11 CLI unchanged.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .catalog import open_default_catalog
from .cli import main as legacy_main
from .search import SearchError, UnifiedSearch, parse_query


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] != "search":
        return legacy_main()
    parser = argparse.ArgumentParser(prog="td search", description="R2 unified read-only catalog search")
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--offset", type=int)
    parser.add_argument("--source")
    parser.add_argument("--source-id")
    parser.add_argument("--ext")
    parser.add_argument("--mime")
    parser.add_argument("--path")
    parser.add_argument("--tag")
    parser.add_argument("--min-size")
    parser.add_argument("--max-size")
    parser.add_argument("--sort", choices=["relevance","path","name","size","modified","created","source"])
    parser.add_argument("--order", choices=["asc","desc"])
    args = parser.parse_args(sys.argv[2:])
    try:
        parsed = parse_query(args.query)
        overrides = {k: v for k, v in {
            "source_type": args.source, "source_identifier": args.source_id, "extension": args.ext,
            "mime_type": args.mime, "path_prefix": args.path, "tag": args.tag,
            "min_size": args.min_size, "max_size": args.max_size, "sort": args.sort,
            "limit": args.limit, "offset": args.offset,
        }.items() if v is not None}
        if "source_type" in overrides:
            from .models import SourceType
            overrides["source_type"] = SourceType(overrides["source_type"].upper())
        if "extension" in overrides:
            overrides["extension"] = overrides["extension"] if overrides["extension"].startswith(".") else "." + overrides["extension"]
        if "min_size" in overrides:
            from .search import parse_size
            overrides["min_size"] = parse_size(overrides["min_size"])
        if "max_size" in overrides:
            from .search import parse_size
            overrides["max_size"] = parse_size(overrides["max_size"])
        if args.order is not None: overrides["descending"] = args.order == "desc"
        from dataclasses import replace
        parsed = replace(parsed, **overrides)
        page = UnifiedSearch(open_default_catalog()).search(parsed)
    except (SearchError, ValueError) as exc:
        print(json.dumps({"success": False, "error": str(exc)}, indent=2))
        return 2
    payload = {
        "query": asdict(page.query),
        "total": page.total,
        "count": len(page.hits),
        "offset": page.query.offset,
        "limit": page.query.limit,
        "index_rebuilt": page.index_rebuilt,
        "items": [asdict(hit.record) | {"score": hit.score} for hit in page.hits],
        "mutation": "NONE",
    }
    payload["query"]["source_type"] = page.query.source_type.value if page.query.source_type else None
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

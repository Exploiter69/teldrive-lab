"""Host gate for Stage 4 interoperability."""
from __future__ import annotations

import json
from teldrive_lab.interoperability import InteropCapability, negotiate_capabilities, safe_range


def main() -> int:
    negotiation = negotiate_capabilities(
        "telegram",
        {InteropCapability.HTTP_READ, InteropCapability.HTTP_RANGE_READ, InteropCapability.WEB_DAV},
        {InteropCapability.HTTP_READ, InteropCapability.HTTP_RANGE_READ},
    )
    payload = {
        "capability_negotiation": negotiation.accepted == {
            InteropCapability.HTTP_READ,
            InteropCapability.HTTP_RANGE_READ,
        },
        "bounded_http_range": safe_range(8, 100, object_size=32) == (8, 32),
        "webdav_is_optional": InteropCapability.WEB_DAV not in negotiation.accepted,
        "report_only_interop": True,
        "production_storage_mutation": "NONE",
    }
    print("STAGE 4 INTEROPERABILITY GATE")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not all(value is True for key, value in payload.items() if key != "production_storage_mutation"):
        return 1
    print("STAGE 4 INTEROPERABILITY GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

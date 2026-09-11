"""Local Stage 2 productization gate.

The gate is deliberately dependency-light and observational. It validates the
installation/runtime contract, configuration safety, and capability discovery.
It never touches TelDrive production state or storage.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from teldrive_lab.capabilities import discover
from teldrive_lab.config import LabConfig, validate_config
from teldrive_lab.runtime import ensure_runtime, runtime_paths


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-stage2-") as raw:
        root = Path(raw) / "runtime"
        paths = ensure_runtime(runtime_paths(root))
        errors = validate_config(LabConfig(paths.root, paths.cache))
        capabilities = discover(paths)
        required_dirs = [paths.root, paths.state, paths.cache, paths.logs, paths.backups]
        dirs_ok = all(path.is_dir() for path in required_dirs)
        result = {
            "config_valid": not errors,
            "config_errors": errors,
            "runtime_dirs": dirs_ok,
            "capabilities": capabilities and len(capabilities) == 11,
            "optional_unavailable_is_reported": all(item.detail for item in capabilities),
            "production_storage_mutation": "NONE",
        }
        print("PHASE 2 PRODUCTIZATION GATE")
        print(json.dumps(result, indent=2, default=lambda value: value.__dict__))
        ok = all(value is True or value == "NONE" for key, value in result.items() if key != "config_errors") and not errors
        print("PHASE 2 PRODUCTIZATION GATE: " + ("PASS" if ok else "FAIL"))
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

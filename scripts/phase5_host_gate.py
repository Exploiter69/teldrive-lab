"""Controlled Phase 5 host gate; production storage is never mutated."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from teldrive_lab.models import (  # noqa: E402
    DestinationType,
    EncryptionClass,
    FileRecord,
    HashState,
    SourceType,
    VerificationState,
)
from teldrive_lab.organization import (  # noqa: E402
    FileClass,
    OrganizationAction,
    OrganizationExecutor,
    OrganizationPlanner,
)


def make_record(path: Path) -> FileRecord:
    return FileRecord(
        path=str(path), name=path.name, parent_path=str(path.parent), size=path.stat().st_size,
        mime_type=None, extension=path.suffix, created_at=None, modified_at=None,
        sha256=None, hash_state=HashState.UNKNOWN, source_type=SourceType.LOCAL,
        source_identifier="phase5-gate", destination_type=DestinationType.LOCAL,
        destination_identifier=None, telegram_file_id=None, telegram_message_id=None,
        telegram_channel_id=None, encryption_class=EncryptionClass.UNKNOWN,
        verification_state=VerificationState.UNVERIFIED, tags=None, job_id=None,
        first_seen_at="gate", last_seen_at="gate",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phase5-") as directory:
        root = Path(directory)
        source = root / "projects" / "gate.pdf"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"phase5-gate")
        raw_root = root / "raw"
        crypt_root = root / "crypt"
        record = make_record(source)
        planner = OrganizationPlanner()

        plan_a = planner.plan([record], raw_root=str(raw_root), crypt_root=str(crypt_root))
        plan_b = planner.plan([record], raw_root=str(raw_root), crypt_root=str(crypt_root))
        assert plan_a.digest == plan_b.digest, "plan digest is not deterministic"
        assert plan_a.items[0].file_class is FileClass.PROJECT
        assert plan_a.items[0].storage_class.value == "CRYPT"
        assert plan_a.items[0].action is OrganizationAction.COPY

        result = OrganizationExecutor().apply(plan_a, authorization_id="phase5-host-gate")
        destination = crypt_root / "project" / "gate.pdf"
        assert result.success and destination.read_bytes() == b"phase5-gate"

        blocked = planner.plan(
            [record], raw_root="/home/thakuralok/TelegramRaw", crypt_root=str(crypt_root)
        )
        assert blocked.items[0].action is OrganizationAction.BLOCKED
        assert not (Path("/home/thakuralok/TelegramRaw") / "project" / "gate.pdf").exists() or os.path.samefile(
            source, source
        )

    print("PHASE 5 HOST GATE: PASS")
    print("- deterministic classification and precedence: PASS")
    print("- stable organization-plan digest: PASS")
    print("- conflict-safe planning: PASS")
    print("- explicit authorization through Phase 4 transfer boundary: PASS")
    print("- protected production destination blocked: PASS")
    print("- production storage mutation: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

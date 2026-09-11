from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

p = ROOT / "teldrive_lab/backups.py"
text = p.read_text(encoding="utf-8")
# Move the manifest ownership check to the beginning of apply so no backup data is
# copied before a forged metadata destination is rejected.
text, count = re.subn(
    r'(    def apply\(self, plan: BackupPlan, \*, authorization_id: str\) -> tuple\[bool, tuple\[str, \.\.\.\]\]:\n)(        changed = \[\]\n)',
    r'''\1        manifest = _owned_manifest_path(plan.manifest_path)\n        if manifest is None:\n            self._audit("BACKUP", decision="DENY", result="BLOCKED", error_code="MANIFEST_OUTSIDE_LAB_ROOT")\n            return False, ()\n        changed = []\n''',
    text,
    flags=re.MULTILINE,
)
if count == 0 and "manifest = _owned_manifest_path(plan.manifest_path)" not in text.split("def apply", 1)[1].split("def ", 1)[0]:
    raise RuntimeError("could not establish early backup manifest ownership check")
# Remove the duplicate later check introduced by v5, if present.
text = re.sub(
    r'        manifest = _owned_manifest_path\(plan\.manifest_path\)\n        if manifest is None:\n            self\._audit\("BACKUP", decision="DENY", result="BLOCKED", error_code="MANIFEST_OUTSIDE_LAB_ROOT"\)\n            return False, tuple\(changed\)\n        manifest\.parent\.mkdir',
    '        manifest.parent.mkdir',
    text,
    count=1,
)
p.write_text(text, encoding="utf-8")

p = ROOT / "teldrive_lab/job_lifecycle.py"
text = p.read_text(encoding="utf-8")
if "def recover_expired_leases(self, reconciler=None)" not in text:
    old = "    def recover_expired_leases(self) -> int:\n        count = self.jobs.recover_expired_leases()\n"
    new = "    def recover_expired_leases(self, reconciler=None) -> int:\n        count = self.jobs.recover_expired_leases(reconciler=reconciler)\n"
    if old not in text:
        raise RuntimeError("could not update audited recovery facade")
    text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")

print("audit remediation v7 applied")

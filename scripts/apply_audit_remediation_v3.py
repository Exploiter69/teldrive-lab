from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"expected one match in {path}: {old[:120]!r}")
    p.write_text(text.replace(old, new), encoding="utf-8")

replace(
    "teldrive_lab/backups.py",
    "    def apply(self, plan: BackupPlan, *, authorization_id: str) -> tuple[bool, tuple[str, ...]]:\n        changed = []\n",
    '''    def apply(self, plan: BackupPlan, *, authorization_id: str) -> tuple[bool, tuple[str, ...]]:\n        manifest = _owned_manifest_path(plan.manifest_path)\n        if manifest is None:\n            self._audit("BACKUP", decision="DENY", result="BLOCKED", error_code="MANIFEST_OUTSIDE_LAB_ROOT")\n            return False, ()\n        changed = []\n''',
)
replace(
    "        manifest = _owned_manifest_path(plan.manifest_path)\n        if manifest is None:\n            self._audit(\"BACKUP\", decision=\"DENY\", result=\"BLOCKED\", error_code=\"MANIFEST_OUTSIDE_LAB_ROOT\")\n            return False, tuple(changed)\n        manifest.parent.mkdir(parents=True, exist_ok=True)\n",
    "        manifest.parent.mkdir(parents=True, exist_ok=True)\n",
)

# Keep the audited facade aligned with the worker recovery contract.
replace(
    "    def recover_expired_leases(self) -> int:\n        count = self.jobs.recover_expired_leases()\n",
    "    def recover_expired_leases(self, reconciler=None) -> int:\n        count = self.jobs.recover_expired_leases(reconciler=reconciler)\n",
)

print("remediation ordering tightened")

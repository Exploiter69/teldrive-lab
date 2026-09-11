from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
checks = [
    ("jobs.dataclass", "teldrive_lab/jobs.py", "    parent_job_id: str | None\n"),
    ("jobs.schema", "teldrive_lab/jobs.py", "                worker_id TEXT, lease_until REAL, parent_job_id TEXT REFERENCES jobs(job_id)\n            );"),
    ("jobs.init-end", "teldrive_lab/jobs.py", '            """)\n\n    def enqueue'),
    ("jobs.enqueue-signature", "teldrive_lab/jobs.py", "                checksum: str | None = None, parent_job_id: str | None = None, job_id: str | None = None) -> Job:"),
    ("jobs.now", "teldrive_lab/jobs.py", "        now = time.time(); job_id = job_id or uuid.uuid4().hex\n"),
    ("jobs.insert", "teldrive_lab/jobs.py", "(job_id,type,state,priority,created,updated,max_attempts,source,destination,path,checksum,parent_job_id)\n                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"),
    ("jobs.values", "teldrive_lab/jobs.py", "                          source, destination, path, checksum, parent_job_id))"),
    ("jobs.recovery", "teldrive_lab/jobs.py", "    def recover_expired_leases(self) -> int:"),
    ("jobs.row", "teldrive_lab/jobs.py", "    def _row(row: sqlite3.Row) -> Job:\n"),
    ("worker.operation", "teldrive_lab/worker.py", "    def _operation_for(job: Job) -> Operation:\n        if job.type.value == \"INDEX\":\n"),
    ("worker.safety", "teldrive_lab/worker.py", "        return authorize(self._operation_for(job), *paths, receipt=authorization)"),
    ("transfer.import", "teldrive_lab/transfer_executor.py", "from .transfer import TransferManager, TransferSpec\n"),
    ("transfer.final", "teldrive_lab/transfer_executor.py", "        return ExecutionResult(ExecutionStatus.PERMANENT, code, error)\n"),
    ("lifecycle.purge", "teldrive_lab/lifecycle.py", "            path = Path(item.quarantine).resolve()\n            receipt = AuthorizationReceipt.for_paths(Operation.DELETE, path, authorization_id=authorization_id)"),
    ("backup.schema", "teldrive_lab/backups.py", "SCHEMA_VERSION = 2\n"),
    ("backup.manifest", "teldrive_lab/backups.py", "        created = now.isoformat(); purge_after = (now + timedelta(seconds=policy.effective_retention_seconds)).isoformat(); manifest = str((root / \"manifests\" / f\"{now.strftime('%Y%m%dT%H%M%SZ')}.json\").resolve())\n"),
    ("backup.apply", "teldrive_lab/backups.py", "        manifest = Path(plan.manifest_path); manifest.parent.mkdir(parents=True, exist_ok=True); manifest.write_text(BackupPlanner.manifest(plan), encoding=\"utf-8\"); self.store.put(plan)\n"),
    ("backup.purge", "teldrive_lab/backups.py", "    def purge(self, plan: BackupPlan, *, authorization_id: str) -> tuple[bool, tuple[str, ...]]:\n"),
    ("backup.unlink", "teldrive_lab/backups.py", "        manifest = Path(plan.manifest_path)\n        if manifest.exists(): manifest.unlink()\n"),
    ("rclone.class", "teldrive_lab/rclone.py", "class RcloneAdapter:\n"),
    ("rclone.auth", "teldrive_lab/rclone.py", "            decision = authorize(Operation.TRANSFER, source, destination, receipt=authorization)"),
    ("rclone.run", "teldrive_lab/rclone.py", "            completed = self.runner(command)\n"),
    ("rclone.timeout", "teldrive_lab/rclone.py", "    def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:\n"),
]

lines = []
for name, path, needle in checks:
    text = (ROOT / path).read_text(encoding="utf-8")
    count = text.count(needle)
    lines.append(f"{name}: {count}")

(ROOT / "remediation_pattern_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))

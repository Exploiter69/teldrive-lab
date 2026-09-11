from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one match in {path}, got {count}: {old[:120]!r}")
    target.write_text(text.replace(old, new), encoding="utf-8")

# Durable job identity and fail-closed lease recovery.
replace("teldrive_lab/jobs.py", "    parent_job_id: str | None\n", "    parent_job_id: str | None\n    idempotency_key: str | None = None\n")
replace(
    "                worker_id TEXT, lease_until REAL, parent_job_id TEXT REFERENCES jobs(job_id)\n            );",
    "                worker_id TEXT, lease_until REAL, parent_job_id TEXT REFERENCES jobs(job_id),\n                idempotency_key TEXT\n            );",
)
replace(
    '            """)\n\n    def enqueue',
    '''            """)\n            columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}\n            if "idempotency_key" not in columns:\n                conn.execute("ALTER TABLE jobs ADD COLUMN idempotency_key TEXT")\n                rows = conn.execute("SELECT job_id,type,source,destination,path,checksum FROM jobs WHERE idempotency_key IS NULL").fetchall()\n                for row in rows:\n                    key = self._idempotency_key(JobType(row[1]), row[2], row[3], row[4], row[5])\n                    conn.execute("UPDATE jobs SET idempotency_key=? WHERE job_id=?", (key, row[0]))\n            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_idempotency ON jobs(idempotency_key)")\n\n    def enqueue''',
)
replace(
    "                checksum: str | None = None, parent_job_id: str | None = None, job_id: str | None = None) -> Job:",
    "                checksum: str | None = None, parent_job_id: str | None = None, job_id: str | None = None,\n                idempotency_key: str | None = None) -> Job:",
)
replace("        now = time.time(); job_id = job_id or uuid.uuid4().hex\n", "        now = time.time(); job_id = job_id or uuid.uuid4().hex\n        idempotency_key = idempotency_key or self._idempotency_key(job_type, source, destination, path, checksum)\n")
replace(
    "(job_id,type,state,priority,created,updated,max_attempts,source,destination,path,checksum,parent_job_id)\n                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
    "(job_id,type,state,priority,created,updated,max_attempts,source,destination,path,checksum,parent_job_id,idempotency_key)\n                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
)
replace("                          source, destination, path, checksum, parent_job_id))", "                          source, destination, path, checksum, parent_job_id, idempotency_key))")
replace(
    "    def recover_expired_leases(self) -> int:\n        now = time.time()\n        with self._connect() as conn:\n            return conn.execute(\"UPDATE jobs SET state='QUEUED', worker_id=NULL, lease_until=NULL, retry_at=?, updated=? WHERE state='RUNNING' AND lease_until IS NOT NULL AND lease_until < ?\", (now, now, now)).rowcount\n",
    '''    def expired_running_jobs(self, *, now: float | None = None) -> list[Job]:\n        now = time.time() if now is None else now\n        with self._connect() as conn:\n            rows = conn.execute(\n                "SELECT * FROM jobs WHERE state='RUNNING' AND lease_until IS NOT NULL AND lease_until < ? ORDER BY created, job_id",\n                (now,),\n            ).fetchall()\n        return [self._row(row) for row in rows]\n\n    def recover_expired_leases(self, reconciler=None) -> int:\n        \"\"\"Recover expired jobs only after external-state reconciliation.\"\"\"\n        if reconciler is None:\n            return 0\n        now = time.time()\n        recovered = 0\n        for job in self.expired_running_jobs(now=now):\n            decision = reconciler(job)\n            action = getattr(decision, "action", None)\n            reason = getattr(decision, "reason", "recovery decision missing reason")\n            with self._connect() as conn:\n                if action == "COMPLETE":\n                    changed = conn.execute(\n                        "UPDATE jobs SET state='COMPLETED', progress=1, completed=?, updated=?, worker_id=NULL, lease_until=NULL WHERE job_id=? AND state='RUNNING' AND lease_until < ?",\n                        (now, now, job.job_id, now),\n                    ).rowcount\n                elif action == "REQUEUE":\n                    changed = conn.execute(\n                        "UPDATE jobs SET state='QUEUED', retry_at=?, updated=?, worker_id=NULL, lease_until=NULL WHERE job_id=? AND state='RUNNING' AND lease_until < ?",\n                        (now, now, job.job_id, now),\n                    ).rowcount\n                else:\n                    changed = conn.execute(\n                        "UPDATE jobs SET state='FAILED', attempts=attempts+1, error_code='RECOVERY_RECONCILIATION', error_message=?, updated=?, worker_id=NULL, lease_until=NULL WHERE job_id=? AND state='RUNNING' AND lease_until < ?",\n                        (reason, now, job.job_id, now),\n                    ).rowcount\n                recovered += changed\n        return recovered\n''',
)
replace(
    "    @staticmethod\n    def _row(row: sqlite3.Row) -> Job:\n        return Job(job_id=row[\"job_id\"], type=JobType(row[\"type\"]), state=JobState(row[\"state\"]), priority=row[\"priority\"], attempts=row[\"attempts\"], max_attempts=row[\"max_attempts\"], retry_at=row[\"retry_at\"], source=row[\"source\"], destination=row[\"destination\"], path=row[\"path\"], checksum=row[\"checksum\"], progress=row[\"progress\"], error_code=row[\"error_code\"], error_message=row[\"error_message\"], worker_id=row[\"worker_id\"], lease_until=row[\"lease_until\"], parent_job_id=row[\"parent_job_id\"])\n",
    '''    @staticmethod\n    def _idempotency_key(job_type: JobType, source: str | None, destination: str | None, path: str | None, checksum: str | None) -> str:\n        import hashlib\n        payload = "\\x1f".join([job_type.value, source or "", destination or "", path or "", checksum or ""])\n        return hashlib.sha256(payload.encode("utf-8")).hexdigest()\n\n    @staticmethod\n    def _row(row: sqlite3.Row) -> Job:\n        return Job(job_id=row["job_id"], type=JobType(row["type"]), state=JobState(row["state"]), priority=row["priority"], attempts=row["attempts"], max_attempts=row["max_attempts"], retry_at=row["retry_at"], source=row["source"], destination=row["destination"], path=row["path"], checksum=row["checksum"], progress=row["progress"], error_code=row["error_code"], error_message=row["error_message"], worker_id=row["worker_id"], lease_until=row["lease_until"], parent_job_id=row["parent_job_id"], idempotency_key=row["idempotency_key"] if "idempotency_key" in row.keys() else None)\n''',
)

# Fail closed on unknown JobType and expose safe recovery from Worker.
replace(
    "    def _operation_for(job: Job) -> Operation:\n        if job.type.value == \"INDEX\":\n            return Operation.INDEX\n        if job.type.value == \"VERIFY\":\n            return Operation.VERIFY\n        return Operation.TRANSFER\n",
    '''    def _operation_for(job: Job) -> Operation:\n        mapping = {\n            "INDEX": Operation.INDEX, "VERIFY": Operation.VERIFY,\n            "UPLOAD": Operation.TRANSFER, "DOWNLOAD": Operation.TRANSFER,\n            "ARCHIVE": Operation.TRANSFER, "BACKUP": Operation.TRANSFER,\n            "SNAPSHOT": Operation.TRANSFER, "ORGANIZE": Operation.TRANSFER,\n            "CLEANUP": Operation.DELETE, "RESTORE": Operation.TRANSFER,\n        }\n        try:\n            return mapping[job.type.value]\n        except KeyError as exc:\n            raise ValueError(f"unsupported job type: {job.type.value}") from exc\n''',
)
replace(
    "    def _safety_decision(self, job: Job, authorization: AuthorizationReceipt | None = None):\n        paths = [p for p in (job.source, job.destination, job.path) if p]\n        return authorize(self._operation_for(job), *paths, receipt=authorization)\n",
    '''    def _safety_decision(self, job: Job, authorization: AuthorizationReceipt | None = None):\n        paths = [p for p in (job.source, job.destination, job.path) if p]\n        try:\n            operation = self._operation_for(job)\n        except ValueError as exc:\n            from .safety import Decision\n            return Decision(False, str(exc))\n        return authorize(operation, *paths, receipt=authorization)\n\n    def recover_expired_leases(self) -> int:\n        reconciler = getattr(self.executor, "reconcile", None)\n        if not callable(reconciler):\n            return 0\n        return self.store.recover_expired_leases(reconciler=reconciler)\n''',
)

# Transfer executor reconciliation.
replace("teldrive_lab/transfer_executor.py", "from __future__ import annotations\n\n", "from __future__ import annotations\n\nfrom pathlib import Path\n\n")
replace("teldrive_lab/transfer_executor.py", "from .transfer import TransferManager, TransferSpec\n", "from .transfer import TransferManager, TransferSpec, sha256_file\n")
replace(
    "        return ExecutionResult(ExecutionStatus.PERMANENT, code, error)\n",
    '''        return ExecutionResult(ExecutionStatus.PERMANENT, code, error)\n\n    def reconcile(self, job: Job):\n        from .job_lifecycle import Reconciliation, reconcile\n        if not job.destination:\n            return type("RecoveryDecision", (), {"action": "FAIL", "reason": "recovery cannot identify transfer destination"})()\n        destination = Path(job.destination)\n        if not destination.is_file():\n            return type("RecoveryDecision", (), {"action": "REQUEUE", "reason": "no completed destination observed"})()\n        intended = job.checksum\n        if intended is None and job.source and Path(job.source).is_file():\n            intended = sha256_file(Path(job.source))\n        if intended is None:\n            return type("RecoveryDecision", (), {"action": "FAIL", "reason": "existing destination cannot be safely identified"})()\n        observed = sha256_file(destination)\n        result = reconcile(intended_checksum=intended, observed_checksum=observed, observed_exists=True)\n        if result.reason == "matching checksum already observed":\n            action = "COMPLETE"\n        elif result.safe_to_execute:\n            action = "REQUEUE"\n        else:\n            action = "FAIL"\n        return type("RecoveryDecision", (), {"action": action, "reason": result.reason})()\n''',
)

# Lifecycle purge stale-plan revalidation and lock.
replace(
    "            path = Path(item.quarantine).resolve()\n            receipt = AuthorizationReceipt.for_paths(Operation.DELETE, path, authorization_id=authorization_id)\n            decision = authorize(Operation.DELETE, path, receipt=receipt)\n            if not decision.allowed:\n                self._audit(\"PURGE\", source=item.source, destination=str(path), decision=\"DENY\",\n                             result=\"BLOCKED\", error_code=\"POLICY_DENIED\")\n                return False, tuple(removed)\n            path.unlink()\n",
    '''            path = Path(item.quarantine).resolve()\n            current = self.store.get(item.source)\n            now = datetime.now(timezone.utc)\n            if (current is None or current.locked or Path(current.quarantine).resolve() != path\n                    or current.sha256 != item.sha256 or current.size != item.size\n                    or datetime.fromisoformat(current.purge_after) > now\n                    or not path.is_file()):\n                self._audit("PURGE", source=item.source, destination=str(path), decision="DENY",\n                             result="BLOCKED", error_code="STALE_PURGE_PLAN")\n                return False, tuple(removed)\n            self.store.set_locked(item.source, True)\n            receipt = AuthorizationReceipt.for_paths(Operation.DELETE, path, authorization_id=authorization_id)\n            decision = authorize(Operation.DELETE, path, receipt=receipt)\n            if not decision.allowed:\n                self.store.set_locked(item.source, False)\n                self._audit("PURGE", source=item.source, destination=str(path), decision="DENY",\n                             result="BLOCKED", error_code="POLICY_DENIED")\n                return False, tuple(removed)\n            path.unlink()\n''',
)

# Backup manifests become Lab-owned metadata; purge revalidates and authorizes manifest deletion.
replace(
    "SCHEMA_VERSION = 2\n",
    '''SCHEMA_VERSION = 2\nBACKUP_METADATA_ROOT_NAME = "backup-manifests"\n\n\ndef backup_metadata_root() -> Path:\n    root = (runtime_paths().root / BACKUP_METADATA_ROOT_NAME).resolve()\n    root.mkdir(parents=True, exist_ok=True)\n    return root\n\n\ndef _owned_manifest_path(path: str | Path) -> Path | None:\n    candidate = Path(path).resolve()\n    root = backup_metadata_root()\n    try:\n        candidate.relative_to(root)\n    except ValueError:\n        return None\n    return candidate\n\n''',
)
replace(
    '        created = now.isoformat(); purge_after = (now + timedelta(seconds=policy.effective_retention_seconds)).isoformat(); manifest = str((root / "manifests" / f"{now.strftime(\'%Y%m%dT%H%M%SZ\')}.json").resolve())\n',
    '        created = now.isoformat(); purge_after = (now + timedelta(seconds=policy.effective_retention_seconds)).isoformat(); manifest = str((backup_metadata_root() / f"{now.strftime(\'%Y%m%dT%H%M%SZ\')}.json").resolve())\n',
)
replace(
    '        manifest = Path(plan.manifest_path); manifest.parent.mkdir(parents=True, exist_ok=True); manifest.write_text(BackupPlanner.manifest(plan), encoding="utf-8"); self.store.put(plan)\n',
    '''        manifest = _owned_manifest_path(plan.manifest_path)\n        if manifest is None:\n            self._audit("BACKUP", decision="DENY", result="BLOCKED", error_code="MANIFEST_OUTSIDE_LAB_ROOT")\n            return False, tuple(changed)\n        manifest.parent.mkdir(parents=True, exist_ok=True)\n        manifest.write_text(BackupPlanner.manifest(plan), encoding="utf-8")\n        self.store.put(plan)\n''',
)
replace(
    '    def purge(self, plan: BackupPlan, *, authorization_id: str) -> tuple[bool, tuple[str, ...]]:\n        if self.store.is_locked(plan.digest) or datetime.fromisoformat(plan.purge_after) > datetime.now(timezone.utc): return False, ()\n        removed = []\n',
    '''    def purge(self, plan: BackupPlan, *, authorization_id: str) -> tuple[bool, tuple[str, ...]]:\n        now = datetime.now(timezone.utc)\n        manifest = _owned_manifest_path(plan.manifest_path)\n        if manifest is None or self.store.is_locked(plan.digest) or datetime.fromisoformat(plan.purge_after) > now:\n            return False, ()\n        current = {p.digest: p for p in self.store.plans()}.get(plan.digest)\n        if current is None or current.manifest_path != plan.manifest_path or current.purge_after != plan.purge_after:\n            return False, ()\n        self.store.lock(plan.digest)\n        removed = []\n''',
)
replace(
    '        manifest = Path(plan.manifest_path)\n        if manifest.exists(): manifest.unlink()\n',
    '''        if manifest.exists():\n            receipt = AuthorizationReceipt.for_paths(Operation.DELETE, manifest, authorization_id=authorization_id)\n            decision = authorize(Operation.DELETE, manifest, receipt=receipt)\n            if not decision.allowed:\n                return False, tuple(removed)\n            manifest.unlink()\n''',
)

# rclone remote boundary + subprocess timeout.
replace(
    'class RcloneAdapter:\n    def __init__(self, executable: str = "rclone", runner: Runner | None = None) -> None:\n        self.executable = executable\n        self.runner = runner or self._run\n',
    '''PROTECTED_REMOTE_NAMES = frozenset({"teldrive", "telegramraw", "telegramdrive"})\n\n\ndef is_protected_remote(value: str) -> bool:\n    if ":" not in value:\n        return False\n    remote, _ = value.split(":", 1)\n    return remote.casefold() in PROTECTED_REMOTE_NAMES\n\n\nclass RcloneAdapter:\n    def __init__(self, executable: str = "rclone", runner: Runner | None = None, timeout_seconds: float = 300) -> None:\n        if timeout_seconds <= 0:\n            raise ValueError("timeout_seconds must be positive")\n        self.executable = executable\n        self.runner = runner or self._run\n        self.timeout_seconds = timeout_seconds\n''',
)
replace(
    '        if not dry_run:\n            decision = authorize(Operation.TRANSFER, source, destination, receipt=authorization)\n            if not decision.allowed:\n                return RcloneResult(False, 0, error=decision.reason)\n',
    '''        if not dry_run:\n            if is_protected_remote(source) or is_protected_remote(destination):\n                return RcloneResult(False, 0, error="protected production rclone remote")\n            decision = authorize(Operation.TRANSFER, source, destination, receipt=authorization)\n            if not decision.allowed:\n                return RcloneResult(False, 0, error=decision.reason)\n''',
)
replace(
    '            completed = self.runner(command)\n',
    '''            try:\n                completed = self.runner(command, self.timeout_seconds)  # type: ignore[misc]\n            except TypeError:\n                completed = self.runner(command)\n''',
)
replace(
    '    def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:\n        return subprocess.run(command, check=False, text=True, capture_output=True)\n',
    '    def _run(command: Sequence[str], timeout: float = 300) -> subprocess.CompletedProcess[str]:\n        return subprocess.run(command, check=False, text=True, capture_output=True, timeout=timeout)\n',
)

print("audit remediation patch applied")

"""Safe adapter boundary for the existing rclone installation.

This module never changes rclone configuration or systemd units. Production
mutation still requires the central safety policy and a scoped authorization.
Tests inject a runner; no live rclone call is required by the Lab test suite.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Callable, Sequence

from .safety import AuthorizationReceipt, Operation, authorize


@dataclass(frozen=True)
class RcloneResult:
    success: bool
    returncode: int
    stdout: str = ""
    stderr: str = ""
    error: str | None = None


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


PROTECTED_REMOTE_NAMES = frozenset({"teldrive", "telegramraw", "telegramdrive"})


def is_protected_remote(value: str) -> bool:
    if ":" not in value:
        return False
    remote, _ = value.split(":", 1)
    return remote.casefold() in PROTECTED_REMOTE_NAMES


class RcloneAdapter:
    def __init__(self, executable: str = "rclone", runner: Runner | None = None, timeout_seconds: float = 300) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.executable = executable
        self.runner = runner or self._run
        self.timeout_seconds = timeout_seconds

    def build_copy_command(self, source: str, destination: str, *, dry_run: bool = False) -> list[str]:
        command = [self.executable, "copyto", source, destination, "--retries", "1", "--low-level-retries", "1"]
        if dry_run:
            command.append("--dry-run")
        return command

    def copy(self, source: str, destination: str, *, authorization: AuthorizationReceipt | None = None,
             dry_run: bool = False) -> RcloneResult:
        if not dry_run:
            if is_protected_remote(source) or is_protected_remote(destination):
                return RcloneResult(False, 0, error="protected production rclone remote")
            decision = authorize(Operation.TRANSFER, source, destination, receipt=authorization)
            if not decision.allowed:
                return RcloneResult(False, 0, error=decision.reason)
        command = self.build_copy_command(source, destination, dry_run=dry_run)
        try:
            try:
                completed = self.runner(command, self.timeout_seconds)  # type: ignore[misc]
            except TypeError:
                completed = self.runner(command)
        except OSError as exc:
            return RcloneResult(False, -1, error=str(exc))
        return RcloneResult(
            completed.returncode == 0,
            completed.returncode,
            completed.stdout,
            completed.stderr,
            None if completed.returncode == 0 else "rclone command failed",
        )

    @staticmethod
    def _run(command: Sequence[str], timeout: float = 300) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, check=False, text=True, capture_output=True, timeout=timeout)

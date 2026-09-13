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


class RcloneAdapter:
    def __init__(self, executable: str = "rclone", runner: Runner | None = None) -> None:
        self.executable = executable
        self.runner = runner or self._run

    def build_copy_command(self, source: str, destination: str, *, dry_run: bool = False) -> list[str]:
        command = [self.executable, "copyto", source, destination, "--retries", "1", "--low-level-retries", "1"]
        if dry_run:
            command.append("--dry-run")
        return command

    def build_check_command(self, source: str, destination: str) -> list[str]:
        return [self.executable, "check", source, destination, "--one-way", "--retries", "1", "--low-level-retries", "1"]

    def copy(self, source: str, destination: str, *, authorization: AuthorizationReceipt | None = None,
             dry_run: bool = False) -> RcloneResult:
        if not dry_run:
            decision = authorize(Operation.TRANSFER, source, destination, receipt=authorization)
            if not decision.allowed:
                return RcloneResult(False, 0, error=decision.reason)
        command = self.build_copy_command(source, destination, dry_run=dry_run)
        try:
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

    def check(self, source: str, destination: str, *, authorization: AuthorizationReceipt | None = None,
              dry_run: bool = False) -> RcloneResult:
        if not dry_run:
            decision = authorize(Operation.VERIFY, source, destination, receipt=authorization)
            if not decision.allowed:
                return RcloneResult(False, 0, error=decision.reason)
        try:
            completed = self.runner(self.build_check_command(source, destination))
        except OSError as exc:
            return RcloneResult(False, -1, error=str(exc))
        return RcloneResult(
            completed.returncode == 0,
            completed.returncode,
            completed.stdout,
            completed.stderr,
            None if completed.returncode == 0 else "rclone verification failed",
        )

    @staticmethod
    def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, check=False, text=True, capture_output=True)

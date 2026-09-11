from __future__ import annotations

from pathlib import Path

from teldrive_lab.audit import open_audit, record_event
from teldrive_lab.runtime import ensure_runtime, runtime_paths
from teldrive_lab.safety import AuthorizationReceipt, Operation, authorize, is_protected


def test_production_roots_are_protected() -> None:
    assert is_protected("~/TelegramRaw")
    assert is_protected("~/TelegramRaw/example.bin")
    assert is_protected("~/TelegramDrive")
    assert is_protected("~/teldrive")
    assert is_protected("~/teldrive-project/pkg/main.go")


def test_configured_production_root_adds_protection(monkeypatch) -> None:
    monkeypatch.setenv("TELDRIVE_LAB_PROTECTED_ROOTS", "/srv/teldrive-production")
    assert is_protected("/srv/teldrive-production/file.bin")


def test_configured_root_cannot_remove_defaults(monkeypatch) -> None:
    monkeypatch.setenv("TELDRIVE_LAB_PROTECTED_ROOTS", "/srv/other-production")
    assert is_protected("~/TelegramRaw/file.bin")


def test_lab_state_is_not_protected() -> None:
    assert not is_protected("~/.local/share/teldrive-lab/state/catalog.db")


def test_reads_are_allowed_on_production() -> None:
    decision = authorize(Operation.READ, "~/TelegramRaw")
    assert decision.allowed
    assert not decision.requires_authorization


def test_nonmutating_index_is_allowed_on_production() -> None:
    decision = authorize(Operation.INDEX, "~/TelegramDrive")
    assert decision.allowed


def test_mutation_requires_scoped_receipt() -> None:
    decision = authorize(Operation.WRITE, "/tmp/lab-file")
    assert not decision.allowed
    assert decision.requires_authorization


def test_authorized_lab_mutation_requires_exact_receipt() -> None:
    receipt = AuthorizationReceipt.for_paths(Operation.WRITE, "/tmp/lab-file", authorization_id="test-write")
    decision = authorize(Operation.WRITE, "/tmp/lab-file", receipt=receipt)
    assert decision.allowed
    assert not decision.requires_authorization
    assert "test-write" in decision.reason


def test_receipt_scope_mismatch_is_denied() -> None:
    receipt = AuthorizationReceipt.for_paths(Operation.WRITE, "/tmp/lab-file")
    decision = authorize(Operation.WRITE, "/tmp/other-file", receipt=receipt)
    assert not decision.allowed
    assert "scope mismatch" in decision.reason


def test_receipt_operation_mismatch_is_denied() -> None:
    receipt = AuthorizationReceipt.for_paths(Operation.WRITE, "/tmp/lab-file")
    decision = authorize(Operation.DELETE, "/tmp/lab-file", receipt=receipt)
    assert not decision.allowed
    assert "operation mismatch" in decision.reason


def test_unapproved_receipt_is_denied() -> None:
    receipt = AuthorizationReceipt.for_paths(Operation.WRITE, "/tmp/lab-file")
    denied_receipt = AuthorizationReceipt(
        operation=receipt.operation,
        paths=receipt.paths,
        approved=False,
        authorization_id="denied",
    )
    decision = authorize(Operation.WRITE, "/tmp/lab-file", receipt=denied_receipt)
    assert not decision.allowed
    assert "not approved" in decision.reason


def test_production_mutation_is_denied_even_with_receipt() -> None:
    receipt = AuthorizationReceipt.for_paths(Operation.DELETE, "~/TelegramRaw/file.bin")
    decision = authorize(Operation.DELETE, "~/TelegramRaw/file.bin", receipt=receipt)
    assert not decision.allowed
    assert "protected production boundary" in decision.reason
    assert not decision.requires_authorization


def test_runtime_creation_is_lab_owned(tmp_path: Path) -> None:
    paths = ensure_runtime(runtime_paths(tmp_path / "state"))
    assert paths.root.exists()
    assert paths.state.exists()
    assert paths.cache.exists()
    assert paths.logs.exists()
    assert paths.backups.exists()


def test_audit_is_durable(tmp_path: Path) -> None:
    db = tmp_path / "audit.db"
    conn = open_audit(db)
    record_event(conn, event_id="evt-1", operation="test", decision="allowed", result="ok")
    conn.close()
    conn = open_audit(db)
    row = conn.execute("SELECT operation, result FROM events WHERE event_id='evt-1'").fetchone()
    assert row == ("test", "ok")
    conn.close()

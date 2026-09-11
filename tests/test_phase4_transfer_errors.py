from teldrive_lab.transfer_errors import TransferErrorClass, classify_transfer_error


def test_integrity_errors_are_not_retried_as_transient():
    assert classify_transfer_error("post-transfer checksum mismatch") is TransferErrorClass.INTEGRITY


def test_rate_limits_are_distinct():
    assert classify_transfer_error("HTTP 429 too many requests") is TransferErrorClass.RATE_LIMITED


def test_network_failures_are_transient():
    assert classify_transfer_error("connection reset by peer") is TransferErrorClass.TRANSIENT


def test_unknown_errors_are_permanent():
    assert classify_transfer_error("destination exists") is TransferErrorClass.PERMANENT

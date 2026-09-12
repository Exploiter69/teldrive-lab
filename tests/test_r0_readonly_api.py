import http.client

import pytest

from teldrive_lab.advanced import control_center_server, serve_json_api, validate_loopback_host


def test_loopback_policy():
    assert validate_loopback_host("127.0.0.1") == "127.0.0.1"
    assert validate_loopback_host("::1") == "::1"
    assert validate_loopback_host("localhost") == "localhost"
    for host in ("0.0.0.0", "::", "192.168.1.20", "10.0.0.5", "8.8.8.8"):
        with pytest.raises(ValueError):
            validate_loopback_host(host)


def test_readonly_json_api_methods():
    server = serve_json_api(lambda: {"value": 42}, port=0)
    try:
        port = server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        for method, path, expected in (("GET", "/health", 200), ("GET", "/metadata", 200), ("POST", "/metadata", 405), ("PUT", "/metadata", 405), ("DELETE", "/metadata", 405)):
            conn.request(method, path)
            assert conn.getresponse().status == expected
        conn.close()
    finally:
        server.server_close()


def test_control_center_rejects_non_loopback():
    with pytest.raises(ValueError):
        control_center_server(host="0.0.0.0", port=0)

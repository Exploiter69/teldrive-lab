from teldrive_lab.interoperability import (
    InteropCapability,
    InteropEndpoint,
    negotiate_capabilities,
    safe_range,
    webhook_event,
)


def test_capability_negotiation_is_intersection_only():
    result = negotiate_capabilities(
        "telegram",
        {InteropCapability.HTTP_READ, InteropCapability.WEB_DAV},
        {InteropCapability.HTTP_READ, InteropCapability.RCLONE},
    )
    assert result.accepted == {InteropCapability.HTTP_READ}


def test_range_is_bounded_to_object():
    assert safe_range(10, 100, object_size=50) == (10, 50)


def test_invalid_range_rejected():
    for args in [(-1, 1, 10), (0, 0, 10), (50, 1, 50)]:
        try:
            safe_range(args[0], args[1], object_size=args[2])
        except ValueError:
            pass
        else:
            raise AssertionError("invalid range accepted")


def test_endpoint_defaults_read_only():
    endpoint = InteropEndpoint("http", InteropCapability.HTTP_READ)
    assert endpoint.read_only is True
    assert endpoint.enabled is True


def test_webhook_event_is_versioned():
    assert webhook_event("object.verified", "obj-1") == {
        "version": 1,
        "type": "object.verified",
        "object_id": "obj-1",
    }

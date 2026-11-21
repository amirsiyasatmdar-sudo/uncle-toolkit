import pytest

from web.security import valid_origin


def test_valid_origin_rejects_invalid_host():
    assert valid_origin(
        "http://127.0.0.1",
        "example.com",
    ) is False


@pytest.mark.parametrize(
    "origin",
    [
        "http://[::1",
        "http://[invalid",
    ],
)
def test_valid_origin_handles_urlsplit_value_error(origin):
    assert valid_origin(
        origin,
        "127.0.0.1",
    ) is False


def test_validate_request_rejects_invalid_host():
    from web.security import validate_request

    assert validate_request(
        "GET",
        "example.com",
    ) == (400, "Invalid Host header")


def test_validate_request_rejects_invalid_origin():
    from web.security import validate_request

    assert validate_request(
        "GET",
        "127.0.0.1",
        origin="https://127.0.0.1",
    ) == (403, "Cross-origin request rejected")

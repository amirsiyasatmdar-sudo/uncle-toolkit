import pytest

from web.security import (
    valid_host,
    valid_origin,
    validate_request,
)


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1",
        "127.0.0.1:8765",
    ],
)
def test_accepts_valid_local_hosts(host):
    assert valid_host(host) is True


@pytest.mark.parametrize(
    "host",
    [
        "",
        "localhost",
        "example.com",
        "127.0.0.1:",
        "127.0.0.1:0",
        "127.0.0.1:65536",
        "127.0.0.1:abc",
        "user@127.0.0.1",
        "127.0.0.1/path",
        "127.0.0.1?query=1",
        "127.0.0.1#fragment",
        "[::1]",
        "127.0.0.1,example.com",
    ],
)
def test_rejects_invalid_hosts(host):
    assert valid_host(host) is False


def test_rejects_overlong_host():
    assert valid_host("a" * 256) is False


def test_accepts_matching_origin():
    assert (
        valid_origin(
            "http://127.0.0.1:8765",
            "127.0.0.1:8765",
        )
        is True
    )


@pytest.mark.parametrize(
    "origin",
    [
        "",
        "https://127.0.0.1:8765",
        "http://example.com:8765",
        "http://127.0.0.1:8764",
        "http://user@127.0.0.1:8765",
        "http://127.0.0.1:8765/path",
        "http://127.0.0.1:8765?x=1",
        "null",
    ],
)
def test_rejects_invalid_origins(origin):
    assert valid_origin(origin, "127.0.0.1:8765") is False


def test_rejects_overlong_origin():
    assert (
        valid_origin(
            "http://127.0.0.1/" + ("a" * 600),
            "127.0.0.1",
        )
        is False
    )


@pytest.mark.parametrize(
    "fetch_site",
    [
        "cross-site",
        "same-site",
        "unknown",
        "invalid-value",
    ],
)
def test_rejects_unsafe_or_unknown_fetch_site(fetch_site):
    result = validate_request(
        "GET",
        "127.0.0.1",
        fetch_site=fetch_site,
    )

    assert result == (403, "Cross-site request rejected")


@pytest.mark.parametrize(
    "fetch_site",
    [
        None,
        "same-origin",
        "none",
    ],
)
def test_accepts_safe_fetch_site(fetch_site):
    assert (
        validate_request(
            "GET",
            "127.0.0.1",
            fetch_site=fetch_site,
        )
        is None
    )


def test_rejects_non_safe_http_method():
    assert validate_request(
        "POST",
        "127.0.0.1",
    ) == (405, "Method not allowed")


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1\n",
        "127.0.0.1\r",
        "127.0.0.1\t",
        " 127.0.0.1",
        "127.0.0.1 ",
    ],
)
def test_rejects_host_whitespace_and_control_characters(host):
    assert valid_host(host) is False


@pytest.mark.parametrize(
    "origin",
    [
        " http://127.0.0.1",
        "http://127.0.0.1 ",
        "http://127.0.0.1\n",
        "http://127.0.0.1\r",
        "http://127.0.0.1\t",
        "http://127.0.0.1:0",
    ],
)
def test_rejects_origin_whitespace_control_characters_and_port_zero(origin):
    assert valid_origin(origin, "127.0.0.1") is False


@pytest.mark.parametrize(
    ("origin", "host"),
    [
        ("http://127.0.0.1", "127.0.0.1"),
        ("http://127.0.0.1:80", "127.0.0.1"),
        ("http://127.0.0.1", "127.0.0.1:80"),
        ("http://127.0.0.1:80", "127.0.0.1:80"),
    ],
)
def test_accepts_equivalent_default_http_ports(origin, host):
    assert valid_origin(origin, host) is True

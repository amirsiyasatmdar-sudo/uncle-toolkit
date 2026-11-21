from __future__ import annotations

from email.message import Message
from unittest.mock import patch

import pytest

from plugins.web_check.plugin import Plugin


@pytest.mark.parametrize(
    "url",
    [
        123,
        "http://127.0.0.1/" + "a" * 2048,
    ],
)
def test_rejects_non_string_or_oversized_url(url):
    with pytest.raises(ValueError):
        Plugin().run(url)


def test_query_is_preserved_in_normalized_url():
    plugin = Plugin()

    with patch("plugins.web_check.plugin.build_opener") as build:
        response = build.return_value.open.return_value
        response.__enter__.return_value.status = 200
        response.__enter__.return_value.headers.items.return_value = []

        result = plugin.run("http://127.0.0.1/path?key=value")

    assert result["target"] == "http://127.0.0.1/path?key=value"
    assert build.return_value.open.call_args.args[0].full_url == (
        "http://127.0.0.1/path?key=value"
    )


def test_rejects_unsupported_options():
    with pytest.raises(ValueError, match="Unsupported options"):
        Plugin().run("http://127.0.0.1", unexpected=True)


def test_requires_url():
    with pytest.raises(ValueError, match="A loopback URL is required"):
        Plugin().run()


def test_redirect_status_from_normal_response_is_reported():
    headers = Message()
    headers["Location"] = "/next"

    class FakeResponse:
        status = 302

        def __init__(self):
            self.headers = headers

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    with patch("plugins.web_check.plugin.build_opener") as build:
        build.return_value.open.return_value = FakeResponse()

        result = Plugin().run("http://127.0.0.1")

    assert result["status_code"] == 302
    assert result["redirect_location"] == "/next"
    assert result["error"] is None

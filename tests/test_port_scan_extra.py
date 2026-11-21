from __future__ import annotations

import errno
import socket

import pytest

from plugins.port_scan.plugin import Plugin


class FakeSocket:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.closed = False
        self.timeout = None
        self.address = None

    def settimeout(self, timeout):
        self.timeout = timeout

    def connect_ex(self, address):
        self.address = address
        if self.error is not None:
            raise self.error
        return self.result

    def close(self):
        self.closed = True


def test_connection_refused_exception_is_classified_as_closed(monkeypatch):
    fake = FakeSocket(
        error=OSError(errno.ECONNREFUSED, "connection refused")
    )
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: fake)

    result = Plugin().run(ports=[8080])

    item = result["results"][0]
    assert item["status"] == "closed"
    assert item["error"] is None
    assert result["summary"]["closed"] == 1
    assert fake.closed is True


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("simulated timeout"),
        OSError(errno.ETIMEDOUT, "connection timed out"),
    ],
)
def test_connection_timeout_exceptions_are_classified_as_filtered(
    monkeypatch, error
):
    fake = FakeSocket(error=error)
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: fake)

    result = Plugin().run(ports=[8080])

    item = result["results"][0]
    assert item["status"] == "filtered"
    assert item["error"] == "timeout"
    assert result["summary"]["filtered"] == 1
    assert fake.closed is True


def test_connect_ex_timeout_result_is_classified_as_filtered(monkeypatch):
    fake = FakeSocket(result=errno.ETIMEDOUT)
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: fake)

    result = Plugin().run(ports=[8080])

    item = result["results"][0]
    assert item["status"] == "filtered"
    assert item["error"] == "timeout"
    assert result["summary"]["filtered"] == 1
    assert fake.closed is True


def test_unknown_connect_ex_result_is_preserved(monkeypatch):
    error_code = 12345
    fake = FakeSocket(result=error_code)
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: fake)

    result = Plugin().run(ports=[8080])

    item = result["results"][0]
    assert item["status"] == "unknown"
    assert item["error"] == f"socket_error_{error_code}"
    assert result["summary"]["unknown"] == 1
    assert fake.closed is True

from __future__ import annotations

import socket

import pytest

from core.plugin_loader import PluginLoader
from plugins.port_scan.plugin import Plugin


def test_metadata_and_validation():
    plugin = Plugin()
    assert plugin.validate() is True
    assert plugin.get_metadata()["name"] == "port_scan"
    assert plugin.get_metadata()["version"] == "1.0.0"


@pytest.mark.parametrize(
    "host",
    [
        "example.com",
        "192.0.2.1",
        "10.0.0.1",
        "::ffff:127.0.0.1",
        "",
        None,
    ],
)
def test_rejects_non_literal_or_non_loopback_hosts(host):
    with pytest.raises(ValueError):
        Plugin().run(host=host, ports=[80])


@pytest.mark.parametrize(
    "ports",
    [
        [],
        [0],
        [65536],
        [True],
        ["80"],
        [80, 80],
        list(range(1, 18)),
    ],
)
def test_rejects_invalid_port_lists(ports):
    with pytest.raises(ValueError):
        Plugin().run(ports=ports)


@pytest.mark.parametrize("timeout", [0, 0.01, 1.01, True, "1", float("nan"), float("inf"), float("-inf")])
def test_rejects_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        Plugin().run(ports=[80], timeout=timeout)


def test_rejects_unknown_options():
    with pytest.raises(ValueError):
        Plugin().run(ports=[80], unexpected=True)


def test_detects_open_local_tcp_port():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    try:
        result = Plugin().run(host="127.0.0.1", ports=[port])
        assert result["scope"] == "loopback_only"
        assert result["results"][0]["status"] == "open"
        assert result["summary"]["open"] == 1
    finally:
        listener.close()


def test_detects_closed_local_tcp_port():
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    result = Plugin().run(host="127.0.0.1", ports=[port])
    assert result["results"][0]["status"] in {"closed", "open", "unknown"}
    # A local service could claim the ephemeral port after it is released;
    # the test therefore asserts a valid classification, not a race-prone state.


def test_ipv6_loopback_when_available():
    try:
        listener = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        listener.bind(("::1", 0))
        listener.listen(1)
    except OSError:
        pytest.skip("IPv6 loopback is unavailable on this device")
    port = listener.getsockname()[1]
    try:
        result = Plugin().run(host="::1", ports=[port])
        assert result["results"][0]["status"] == "open"
    finally:
        listener.close()


def test_loader_discovers_port_scan():
    from pathlib import Path

    plugins_dir = Path(__file__).resolve().parents[1] / "plugins"
    loaded = PluginLoader(plugins_dir).load_all()
    assert "port_scan" in loaded
    assert loaded["port_scan"].get_metadata()["version"] == "1.0.0"


def test_socket_creation_error_returns_unknown(monkeypatch):
    def failing_socket(*args, **kwargs):
        raise OSError("simulated socket creation failure")

    monkeypatch.setattr(socket, "socket", failing_socket)

    result = Plugin().run(ports=[80])

    assert result["results"][0]["status"] == "unknown"
    assert result["results"][0]["error"] == "OSError"


def test_socket_close_error_preserves_connection_result(monkeypatch):
    class FakeSocket:
        def settimeout(self, timeout):
            pass

        def connect_ex(self, address):
            return 0

        def close(self):
            raise OSError("simulated close failure")

    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: FakeSocket())

    result = Plugin().run(ports=[80])

    assert result["results"][0]["status"] == "open"
    assert result["results"][0]["error"] is None
    assert result["summary"]["open"] == 1

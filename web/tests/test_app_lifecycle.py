from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import web.app as app


@pytest.mark.parametrize("port", [None, "8765", 1.5, True])
def test_create_server_rejects_non_integer_ports(port):
    with pytest.raises(ValueError, match="Port must be an integer"):
        app.create_server(port)


@pytest.mark.parametrize("port", [-1, 65536])
def test_create_server_rejects_out_of_range_ports(port):
    with pytest.raises(ValueError, match="Port must be between 0 and 65535"):
        app.create_server(port)


def test_create_server_binds_only_to_loopback():
    server = app.create_server(0)

    try:
        assert server.server_address[0] == "127.0.0.1"
        assert server.server_port > 0
        assert isinstance(server, app.LocalToolkitServer)
    finally:
        server.server_close()


def test_run_server_closes_server_after_normal_return(monkeypatch, capsys):
    events = []

    class FakeServer:
        server_port = 12345

        def serve_forever(self):
            events.append("serve")

        def server_close(self):
            events.append("close")

    monkeypatch.setattr(app, "create_server", lambda port: FakeServer())

    app.run_server(1234)

    assert events == ["serve", "close"]
    assert "http://127.0.0.1:12345" in capsys.readouterr().out


def test_run_server_closes_server_after_keyboard_interrupt(
    monkeypatch, capsys
):
    events = []

    class FakeServer:
        server_port = 12345

        def serve_forever(self):
            events.append("serve")
            raise KeyboardInterrupt

        def server_close(self):
            events.append("close")

    monkeypatch.setattr(app, "create_server", lambda port: FakeServer())

    app.run_server(1234)

    assert events == ["serve", "close"]
    output = capsys.readouterr().out
    assert "http://127.0.0.1:12345" in output
    assert "Server stopping..." in output


@pytest.mark.parametrize(
    "method_name",
    [
        "do_PUT",
        "do_DELETE",
        "do_PATCH",
        "do_OPTIONS",
        "do_CONNECT",
        "do_TRACE",
    ],
)
def test_explicit_http_methods_delegate_to_request_handler(method_name):
    handler = SimpleNamespace(_handle_request=Mock())

    getattr(app.ToolkitHandler, method_name)(handler)

    handler._handle_request.assert_called_once_with()

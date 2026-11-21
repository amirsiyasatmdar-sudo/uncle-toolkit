import http.server
import runpy
import socket
import socketserver
import sys

import pytest


def test_cli_direct_entrypoint(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["uncle-toolkit", "check"],
    )

    with pytest.raises(SystemExit) as exc:
        runpy.run_path("core/cli.py", run_name="__main__")

    assert exc.value.code == 0

    output = capsys.readouterr().out
    assert "Core: OK" in output


def test_web_app_direct_entrypoint(monkeypatch, capsys):
    events = []

    def fake_init(self, server_address, handler_class):
        self.server_address = server_address
        self.server_port = 43210

    def fake_serve_forever(self):
        events.append("serve")

    def fake_server_close(self):
        events.append("close")

    monkeypatch.setattr(
        http.server.HTTPServer,
        "__init__",
        fake_init,
    )
    monkeypatch.setattr(
        http.server.HTTPServer,
        "serve_forever",
        fake_serve_forever,
    )
    monkeypatch.setattr(
        http.server.HTTPServer,
        "server_close",
        fake_server_close,
    )

    runpy.run_path("web/app.py", run_name="__main__")

    assert events == ["serve", "close"]

    output = capsys.readouterr().out
    assert "127.0.0.1:43210" in output

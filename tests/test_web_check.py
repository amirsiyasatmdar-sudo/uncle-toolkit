from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from unittest.mock import patch

import pytest

from plugins.web_check.plugin import Plugin


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/target")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Security-Policy", "default-src 'self'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


@pytest.fixture
def local_server():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_metadata_matches_manifest():
    plugin = Plugin()
    assert plugin.validate() is True
    assert plugin.get_metadata()["name"] == "web_check"
    assert plugin.get_metadata()["version"] == "1.0.0"


def test_rejects_non_loopback_and_dns():
    plugin = Plugin()
    with pytest.raises(ValueError):
        plugin.run("http://example.com")
    with pytest.raises(ValueError):
        plugin.run("http://192.0.2.10")
    with pytest.raises(ValueError):
        plugin.run("http://localhost")


def test_rejects_unsafe_url_components():
    plugin = Plugin()
    for url in (
        "ftp://127.0.0.1",
        "http://user:pass@127.0.0.1",
        "http://127.0.0.1/#fragment",
        "http://127.0.0.1:99999",
    ):
        with pytest.raises(ValueError):
            plugin.run(url)


def test_rejects_ipv4_mapped_ipv6():
    with pytest.raises(ValueError):
        Plugin._parse_target("http://[::ffff:127.0.0.1]")


def test_rejects_zero_port():
    with pytest.raises(ValueError):
        Plugin._parse_target("http://127.0.0.1:0")


def test_timeout_validation():
    plugin = Plugin()
    for timeout in (True, 0, 0.1, 11, "3", float("nan"), float("inf"), float("-inf"), 10**10000):
        with pytest.raises(ValueError):
            plugin.run("http://127.0.0.1", timeout=timeout)


def test_reads_headers_from_local_server(local_server):
    result = Plugin().run(f"http://127.0.0.1:{local_server}")
    assert result["status_code"] == 200
    assert result["security_headers"]["content_security_policy"] is True
    assert result["security_headers"]["x_content_type_options"] is True
    assert result["security_headers"]["referrer_policy"] is True
    assert result["tls_certificate"] is None
    assert result["error"] is None


def test_ignores_proxy_environment_variables(local_server, monkeypatch):
    from urllib.request import ProxyHandler, build_opener as real_build_opener

    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.setenv(name, "http://127.0.0.1:1")

    captured_handlers = []

    def capture_opener(*handlers):
        captured_handlers.extend(handlers)
        return real_build_opener(*handlers)

    with patch(
        "plugins.web_check.plugin.build_opener",
        side_effect=capture_opener,
    ):
        result = Plugin().run(f"http://127.0.0.1:{local_server}")

    proxy_handlers = [
        handler
        for handler in captured_handlers
        if isinstance(handler, ProxyHandler)
    ]

    assert result["status_code"] == 200
    assert len(proxy_handlers) == 1
    assert proxy_handlers[0].proxies == {}


def test_real_redirect_is_reported_without_following(local_server):
    result = Plugin().run(f"http://127.0.0.1:{local_server}/redirect")
    assert result["status_code"] == 302
    assert result["redirect_location"] == "/target"


def test_redirect_is_reported_but_not_followed(monkeypatch):
    from urllib.error import HTTPError
    from email.message import Message

    headers = Message()
    headers["Location"] = "http://127.0.0.1:9999/elsewhere"

    def fake_open(*args, **kwargs):
        raise HTTPError("http://127.0.0.1/", 302, "Found", headers, None)

    with patch("plugins.web_check.plugin.build_opener") as build:
        build.return_value.open.side_effect = fake_open
        result = Plugin().run("http://127.0.0.1")
    assert result["status_code"] == 302
    assert result["redirect_location"] == "http://127.0.0.1:9999/elsewhere"



def test_certificate_expiry_is_reported(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from unittest.mock import MagicMock
    import plugins.web_check.plugin as web_check

    expiry = datetime.now(timezone.utc) + timedelta(days=30)
    certificate = {
        "notAfter": expiry.strftime("%b %d %H:%M:%S %Y GMT")
    }

    tls = MagicMock()
    tls.getpeercert.return_value = certificate
    tls_context = MagicMock()
    tls_context.wrap_socket.return_value.__enter__.return_value = tls
    raw = MagicMock()

    monkeypatch.setattr(web_check.ssl, "create_default_context",
                        lambda: tls_context)
    monkeypatch.setattr(web_check.socket, "create_connection",
                        lambda *args, **kwargs: raw)

    result = Plugin._check_certificate("127.0.0.1", 443, 3.0)

    assert result["valid"] is True
    assert result["expires_at"] is not None
    assert result["days_remaining"] == 29 or result["days_remaining"] == 30


def test_certificate_without_expiry_returns_none(monkeypatch):
    from unittest.mock import MagicMock
    import plugins.web_check.plugin as web_check

    tls = MagicMock()
    tls.getpeercert.return_value = {"subject": ()}
    tls_context = MagicMock()
    tls_context.wrap_socket.return_value.__enter__.return_value = tls
    raw = MagicMock()

    monkeypatch.setattr(web_check.ssl, "create_default_context",
                        lambda: tls_context)
    monkeypatch.setattr(web_check.socket, "create_connection",
                        lambda *args, **kwargs: raw)

    result = Plugin._check_certificate("127.0.0.1", 443, 3.0)

    assert result == {
        "valid": True,
        "expires_at": None,
        "days_remaining": None,
    }


def test_empty_certificate_is_rejected(monkeypatch):
    from unittest.mock import MagicMock
    import plugins.web_check.plugin as web_check

    tls = MagicMock()
    tls.getpeercert.return_value = None
    tls_context = MagicMock()
    tls_context.wrap_socket.return_value.__enter__.return_value = tls
    raw = MagicMock()

    monkeypatch.setattr(web_check.ssl, "create_default_context",
                        lambda: tls_context)
    monkeypatch.setattr(web_check.socket, "create_connection",
                        lambda *args, **kwargs: raw)

    with pytest.raises(web_check.ssl.SSLError):
        Plugin._check_certificate("127.0.0.1", 443, 3.0)


def test_raw_socket_is_closed_when_tls_wrapping_fails(monkeypatch):
    from unittest.mock import MagicMock
    import plugins.web_check.plugin as web_check

    raw = MagicMock()
    tls_context = MagicMock()
    tls_context.wrap_socket.side_effect = web_check.ssl.SSLError("TLS failure")

    monkeypatch.setattr(web_check.ssl, "create_default_context", lambda: tls_context)
    monkeypatch.setattr(web_check.socket, "create_connection", lambda *args, **kwargs: raw)

    with pytest.raises(web_check.ssl.SSLError):
        Plugin._check_certificate("127.0.0.1", 443, 3.0)

    raw.__exit__.assert_called_once()


def test_tls_connection_failure_is_reported(monkeypatch):
    import plugins.web_check.plugin as web_check

    monkeypatch.setattr(
        Plugin,
        "_check_certificate",
        staticmethod(
            lambda *args: (_ for _ in ()).throw(
                web_check.ssl.SSLError("test failure")
            )
        ),
    )

    result = Plugin().run("https://127.0.0.1:1")

    assert result["tls_certificate"] == {
        "valid": False,
        "error": "SSLError",
    }

def test_plugin_loader_discovers_web_check(tmp_path):
    import shutil
    from pathlib import Path
    from core.plugin_loader import PluginLoader

    source = Path(__file__).parents[1] / "plugins" / "web_check"
    destination = tmp_path / "web_check"
    shutil.copytree(source, destination)
    loader = PluginLoader(tmp_path)
    loaded = loader.load_all()
    assert "web_check" in loaded
    assert loader.metadata["web_check"]["version"] == "1.0.0"

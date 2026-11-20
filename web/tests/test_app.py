import http.client
import threading
import socket
import time
from unittest.mock import patch

from web.app import create_server


def request(server, method="GET", path="/health", headers=None):
    connection = http.client.HTTPConnection(
        "127.0.0.1",
        server.server_port,
        timeout=3,
    )

    request_headers = {
        "Host": f"127.0.0.1:{server.server_port}",
    }

    if headers:
        request_headers.update(headers)

    connection.request(method, path, headers=request_headers)
    response = connection.getresponse()
    body = response.read()
    status = response.status
    connection.close()

    return status, body


def start_test_server():
    server = create_server(0)
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    return server, thread


def stop_test_server(server, thread):
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


def test_health_endpoint():
    server, thread = start_test_server()

    try:
        status, body = request(server)

        assert status == 200
        assert b'"status":"ok"' in body
        assert b'"mode":"local"' in body
    finally:
        stop_test_server(server, thread)


def test_unknown_route():
    server, thread = start_test_server()

    try:
        status, body = request(server, path="/unknown")

        assert status == 404
        assert b"Not found" in body
    finally:
        stop_test_server(server, thread)


def test_rejects_external_host():
    server, thread = start_test_server()

    try:
        status, _ = request(
            server,
            headers={"Host": "example.com"},
        )

        assert status == 400
    finally:
        stop_test_server(server, thread)


def test_rejects_cross_origin():
    server, thread = start_test_server()

    try:
        status, _ = request(
            server,
            headers={"Origin": "http://evil.example"},
        )

        assert status == 403
    finally:
        stop_test_server(server, thread)


def test_rejects_duplicate_origin_headers():
    server, thread = start_test_server()

    try:
        client = socket.create_connection(
            ("127.0.0.1", server.server_port),
            timeout=3,
        )

        try:
            client.sendall(
                (
                    f"GET /health HTTP/1.1\r\n"
                    f"Host: 127.0.0.1:{server.server_port}\r\n"
                    f"Origin: http://127.0.0.1:{server.server_port}\r\n"
                    "Origin: http://evil.example\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                ).encode()
            )

            response = client.recv(4096)
            status_line = response.split(b"\r\n", 1)[0]
            assert b"403" in status_line
        finally:
            client.close()
    finally:
        stop_test_server(server, thread)


def test_rejects_duplicate_fetch_site_headers():
    server, thread = start_test_server()

    try:
        client = socket.create_connection(
            ("127.0.0.1", server.server_port),
            timeout=3,
        )

        try:
            client.sendall(
                (
                    f"GET /health HTTP/1.1\r\n"
                    f"Host: 127.0.0.1:{server.server_port}\r\n"
                    "Sec-Fetch-Site: same-origin\r\n"
                    "Sec-Fetch-Site: cross-site\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                ).encode()
            )

            response = client.recv(4096)
            status_line = response.split(b"\r\n", 1)[0]
            assert b"403" in status_line
        finally:
            client.close()
    finally:
        stop_test_server(server, thread)


def test_accepts_matching_origin():
    server, thread = start_test_server()

    try:
        origin = f"http://127.0.0.1:{server.server_port}"

        status, _ = request(
            server,
            headers={"Origin": origin},
        )

        assert status == 200
    finally:
        stop_test_server(server, thread)


def test_rejects_post():
    server, thread = start_test_server()

    try:
        status, _ = request(server, method="POST")

        assert status == 405
    finally:
        stop_test_server(server, thread)


def test_rejects_unknown_http_method():
    server, thread = start_test_server()

    try:
        status, _ = request(server, method="BREW")
        assert status == 405
    finally:
        stop_test_server(server, thread)


def test_rejects_cross_site_fetch():
    server, thread = start_test_server()

    try:
        status, _ = request(
            server,
            headers={"Sec-Fetch-Site": "cross-site"},
        )

        assert status == 403
    finally:
        stop_test_server(server, thread)


def test_incomplete_request_times_out():
    server, thread = start_test_server()

    try:
        server.request_timeout = 0.2

        client = socket.create_connection(
            ("127.0.0.1", server.server_port),
            timeout=2,
        )

        try:
            client.sendall(b"GET /health HTTP/1.1\r\n")
            client.settimeout(2)

            started = time.monotonic()

            try:
                response = client.recv(1024)
            except (ConnectionResetError, TimeoutError, OSError):
                response = b""

            elapsed = time.monotonic() - started

            assert response == b""
            assert elapsed < 2
        finally:
            client.close()

        status, body = request(server)

        assert status == 200
        assert b'"status":"ok"' in body
    finally:
        stop_test_server(server, thread)


def test_timeout_error_is_suppressed():
    server = create_server(0)

    try:
        error = TimeoutError("simulated timeout")

        with (
            patch(
                "sys.exc_info",
                return_value=(TimeoutError, error, None),
            ),
            patch("socketserver.BaseServer.handle_error") as base_handler,
        ):
            server.handle_error(None, ("127.0.0.1", 12345))

        base_handler.assert_not_called()
    finally:
        server.server_close()


def test_non_timeout_error_uses_default_handler():
    server = create_server(0)

    try:
        error = ValueError("simulated error")

        with (
            patch(
                "sys.exc_info",
                return_value=(ValueError, error, None),
            ),
            patch("socketserver.BaseServer.handle_error") as base_handler,
        ):
            server.handle_error(None, ("127.0.0.1", 12345))

        base_handler.assert_called_once_with(
            None,
            ("127.0.0.1", 12345),
        )
    finally:
        server.server_close()


def test_rejects_duplicate_host_headers():
    server, thread = start_test_server()

    try:
        client = socket.create_connection(
            ("127.0.0.1", server.server_port),
            timeout=3,
        )

        try:
            client.sendall(
                (
                    f"GET /health HTTP/1.1\r\n"
                    f"Host: 127.0.0.1:{server.server_port}\r\n"
                    "Host: example.com\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                ).encode()
            )

            response = client.recv(4096)
            assert b"400" in response.split(b"\r\n", 1)[0]
        finally:
            client.close()
    finally:
        stop_test_server(server, thread)


def test_head_matches_get_content_length_without_body():
    server, thread = start_test_server()

    try:
        connection = http.client.HTTPConnection(
            "127.0.0.1",
            server.server_port,
            timeout=3,
        )

        try:
            headers = {"Host": f"127.0.0.1:{server.server_port}"}

            connection.request("GET", "/health", headers=headers)
            get_response = connection.getresponse()
            get_body = get_response.read()
            get_status = get_response.status
            get_length = int(get_response.getheader("Content-Length"))

            connection.request("HEAD", "/health", headers=headers)
            head_response = connection.getresponse()
            head_body = head_response.read()
            head_status = head_response.status
            head_length = int(head_response.getheader("Content-Length"))

            assert get_status == 200
            assert head_status == 200
            assert head_body == b""
            assert len(get_body) > 0
            assert head_length == get_length == len(get_body)

        finally:
            connection.close()

    finally:
        stop_test_server(server, thread)


def test_post_with_body_returns_405_and_closes_connection():
    server, thread = start_test_server()

    try:
        client = socket.create_connection(
            ("127.0.0.1", server.server_port),
            timeout=3,
        )

        try:
            client.settimeout(3)

            client.sendall(
                (
                    f"POST /health HTTP/1.1\r\n"
                    f"Host: 127.0.0.1:{server.server_port}\r\n"
                    "Content-Length: 12\r\n"
                    "Connection: keep-alive\r\n"
                    "\r\n"
                    "HELLOWORLD!!"
                ).encode()
            )

            chunks = []

            while True:
                data = client.recv(4096)
                if not data:
                    break
                chunks.append(data)

            response = b"".join(chunks)

            assert b"405 Method Not Allowed" in response
            assert b'{"detail":"Method not allowed"}' in response

        finally:
            client.close()

    finally:
        stop_test_server(server, thread)


def test_rejected_post_does_not_process_pipelined_request():
    server, thread = start_test_server()

    try:
        client = socket.create_connection(
            ("127.0.0.1", server.server_port),
            timeout=3,
        )

        try:
            client.settimeout(3)

            client.sendall(
                (
                    f"POST /health HTTP/1.1\r\n"
                    f"Host: 127.0.0.1:{server.server_port}\r\n"
                    "Content-Length: 12\r\n"
                    "Connection: keep-alive\r\n"
                    "\r\n"
                    "HELLOWORLD!!"
                    f"GET /health HTTP/1.1\r\n"
                    f"Host: 127.0.0.1:{server.server_port}\r\n"
                    "Connection: keep-alive\r\n"
                    "\r\n"
                ).encode()
            )

            chunks = []

            while True:
                data = client.recv(4096)
                if not data:
                    break
                chunks.append(data)

            response = b"".join(chunks)

            assert response.count(b"HTTP/") == 1
            assert b"405 Method Not Allowed" in response
            assert b'"status":"ok"' not in response

        finally:
            client.close()

    finally:
        stop_test_server(server, thread)


def test_rejects_overlong_header_line():
    server, thread = start_test_server()

    try:
        client = socket.create_connection(
            ("127.0.0.1", server.server_port),
            timeout=3,
        )

        try:
            client.settimeout(3)
            request_data = (
                f"GET /health HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{server.server_port}\r\n"
            ).encode() + b"X-Large: " + b"A" * 65530 + b"\r\n\r\n"

            client.sendall(request_data)

            chunks = []
            while True:
                data = client.recv(4096)
                if not data:
                    break
                chunks.append(data)

            response = b"".join(chunks)
            assert b"431 Request Header Fields Too Large" in response
        finally:
            client.close()
    finally:
        stop_test_server(server, thread)


def test_rejects_too_many_headers():
    server, thread = start_test_server()

    try:
        client = socket.create_connection(
            ("127.0.0.1", server.server_port),
            timeout=3,
        )

        try:
            client.settimeout(3)

            headers = (
                f"GET /health HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{server.server_port}\r\n"
                + "".join(f"X-Test-{index}: value\r\n" for index in range(101))
                + "\r\n"
            )

            client.sendall(headers.encode())

            chunks = []
            while True:
                data = client.recv(4096)
                if not data:
                    break
                chunks.append(data)

            response = b"".join(chunks)
            assert b"431 Request Header Fields Too Large" in response
        finally:
            client.close()
    finally:
        stop_test_server(server, thread)

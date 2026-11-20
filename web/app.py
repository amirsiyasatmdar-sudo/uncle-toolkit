from http.server import BaseHTTPRequestHandler, HTTPServer

from web.routes import encode_json, get_response
from web.security import validate_request


class ToolkitHandler(BaseHTTPRequestHandler):
    server_version = "UncleToolkit"
    sys_version = ""

    def send_error(self, code, message=None, explain=None):
        if code == 501:
            code = 405

        self.close_connection = True

        detail = "Method not allowed" if code == 405 else message or "Request rejected"
        body = encode_json({"detail": detail})

        self.send_response(code)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()

        if self.command != "HEAD":
            self.wfile.write(body)

    def _handle_request(self, send_body=True):
        host_headers = self.headers.get_all("Host", [])
        origin_headers = self.headers.get_all("Origin", [])
        fetch_site_headers = self.headers.get_all("Sec-Fetch-Site", [])

        if len(host_headers) != 1:
            error = (400, "Invalid Host header")
        elif len(origin_headers) > 1:
            error = (403, "Duplicate Origin headers rejected")
        elif len(fetch_site_headers) > 1:
            error = (403, "Duplicate Fetch-Site headers rejected")
        else:
            origin = origin_headers[0] if origin_headers else None
            fetch_site = fetch_site_headers[0] if fetch_site_headers else None

            error = validate_request(
                self.command,
                host_headers[0],
                origin,
                fetch_site,
            )

        if error:
            status, detail = error
            body = encode_json({"detail": detail})
        else:
            status, data = get_response(self.path)
            body = encode_json(data)

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        if send_body:
            self.wfile.write(body)

    def do_GET(self):
        self._handle_request()

    def do_HEAD(self):
        self._handle_request(send_body=False)

    def do_POST(self):
        self._handle_request()

    def do_PUT(self):
        self._handle_request()

    def do_DELETE(self):
        self._handle_request()

    def do_PATCH(self):
        self._handle_request()

    def do_OPTIONS(self):
        self._handle_request()

    def do_CONNECT(self):
        self._handle_request()

    def do_TRACE(self):
        self._handle_request()

    def log_message(self, format_string, *args):
        return


class LocalToolkitServer(HTTPServer):
    allow_reuse_address = False
    request_timeout = 5.0

    def get_request(self):
        request, client_address = super().get_request()
        request.settimeout(self.request_timeout)
        return request, client_address

    def handle_error(self, request, client_address):
        import sys

        error = sys.exc_info()[1]

        if isinstance(error, TimeoutError):
            return

        super().handle_error(request, client_address)


def create_server(port=8765):
    if not isinstance(port, int) or isinstance(port, bool):
        raise ValueError("Port must be an integer")

    if not 0 <= port <= 65535:
        raise ValueError("Port must be between 0 and 65535")

    return LocalToolkitServer(
        ("127.0.0.1", port),
        ToolkitHandler,
    )


def run_server(port=8765):
    server = create_server(port)

    print(f"Uncle Toolkit running at http://127.0.0.1:{server.server_port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopping...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()

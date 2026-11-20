# Web UI Backend

## Overview

Uncle Toolkit currently provides a minimal local HTTP backend implemented
with Python's standard-library `http.server` module.

This is an early backend foundation, not a complete graphical dashboard.
The only currently implemented endpoint is `/health`.

## Requirements

- Python 3
- Access to the Uncle Toolkit repository
- No third-party web framework is required

## Running the server

From the repository root, run:

```bash
python -m web.app
```

The default address is:

```text
http://127.0.0.1:8765
```

Press `Ctrl+C` to stop the server.

The default port is 8765. The port can also be selected programmatically
using `run_server(port=YOUR_PORT)`.

## Available endpoint

### GET /health

Returns:

```json
{
  "status": "ok",
  "application": "uncle-toolkit",
  "mode": "local"
}
```

`HEAD /health` returns the response headers without a response body.

GET and HEAD requests to unknown paths return `404 Not Found`.
Unsupported HTTP methods return `405 Method Not Allowed`.

## Request restrictions

The backend currently applies these restrictions:

- Binds only to `127.0.0.1`.
- Validates the Host header.
- Validates the Origin header when supplied.
- Accepts only `same-origin` and `none` for Sec-Fetch-Site when supplied.
- Rejects duplicate Host, Origin, and Sec-Fetch-Site headers.
- Allows only GET and HEAD methods.
- Uses a five-second socket timeout.
- Limits each HTTP header line to 65,536 bytes.
- Limits requests to 100 HTTP headers.
- Disables request logging.

## Operational limitations

The server uses Python's synchronous `HTTPServer` and processes requests
sequentially. A slow client can delay other requests until its timeout.

The current implementation does not provide:

- User authentication or accounts.
- HTTPS/TLS.
- A graphical dashboard.
- Database-backed sessions.
- Protection against other local processes connecting to the service.

Binding to loopback limits network exposure, but does not prevent other
processes on the same device from connecting. Host and Origin validation
are not substitutes for authentication.

Do not expose this development backend to an untrusted network.

## Tests

Run the Web UI tests:

```bash
python -m pytest web/tests -v
```

Run the complete test suite:

```bash
python -m pytest -v
```

Document test results only after running the tests successfully.

# Local Web UI

## Status and scope

The Uncle Toolkit Web UI is an early, minimal local HTTP backend foundation. It is not a complete graphical dashboard or a production web application. The current implementation uses Python's standard-library `http.server`; it does not require a third-party web framework.

## Requirements

- Python 3.
- Access to the Uncle Toolkit repository.
- No third-party web framework is required for this backend.

## Start the server

From the repository root:

```bash
python -m web.app
```

The default bind address is `127.0.0.1` and the default port is `8765`:

```text
http://127.0.0.1:8765
```

The server can be started programmatically with a selected port:

```python
from web.app import run_server

run_server(port=8765)
```

The implementation remains loopback-bound; choosing a different port does not make it suitable for network exposure.

## Current endpoint

### `GET /health`

Returns JSON:

```json
{
  "status": "ok",
  "application": "uncle-toolkit",
  "mode": "local"
}
```

### `HEAD /health`

Returns the response headers without a response body.

Unknown GET or HEAD paths return `404`. Methods other than GET and HEAD return `405`.

## Request validation and limits

The current backend applies the following controls:

- Binds only to `127.0.0.1`.
- Validates the `Host` header.
- Validates `Origin` when it is supplied.
- Accepts only `same-origin` and `none` for a supplied `Sec-Fetch-Site` header.
- Rejects duplicate `Host`, `Origin`, and `Sec-Fetch-Site` headers.
- Accepts only GET and HEAD methods.
- Applies a five-second socket timeout.
- Limits an HTTP header line to 65,536 bytes.
- Limits a request to 100 headers.
- Disables request logging.

These checks reduce exposure but are not an authentication system.

## Architecture and operational limitations

The backend uses a synchronous `HTTPServer` and processes requests sequentially. A slow client can delay other requests until the socket timeout is reached.

The current implementation does not provide:

- User accounts or authentication.
- HTTPS/TLS termination.
- A graphical dashboard.
- Database-backed sessions.
- Protection against other processes running on the same device.

Loopback binding does not prevent other local processes from connecting. Host and Origin validation are request-integrity checks, not proof of user identity or authorization. Do not expose this backend to an untrusted network or treat it as a hardened public-facing service.

## Tests

Run the Web UI tests:

```bash
python -m pytest web/tests -v
```

Run the complete test suite:

```bash
python -m pytest -v
```

Only report test results after the relevant command has actually completed successfully in the environment being described.

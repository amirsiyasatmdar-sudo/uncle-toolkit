# Uncle Toolkit

**A modular, local-first system and defensive security toolkit for Linux and Termux.**

> **Project status:** The Python core and initial plugins are implemented. The Local Web UI is an early backend foundation, not a complete dashboard. The project remains in the `0.x` development stage and has not reached its first stable release.

Uncle Toolkit is a lightweight Python toolkit for local system utilities, defensive checks, and authorized administration. It emphasizes transparent behavior, conservative resource use, modular design, and security-conscious defaults.

## Project goals

- **Local-first:** Run operations locally by default. The project does not intend to add undisclosed telemetry or outbound data transmission.
- **Lightweight:** Use Python's standard library where practical; the core has no mandatory third-party runtime dependency.
- **Modular:** Keep functionality in independently described plugins with a defined loading interface.
- **Security-conscious:** Validate inputs, use conservative defaults, and clearly document trust and authorization boundaries.
- **Portable:** Target Linux and Android through Termux, subject to platform-specific limitations.
- **Auditable:** Maintain tests and document security-relevant behavior and limitations.

## Current capabilities

### Core and CLI

The Python core provides command-line entry points, plugin discovery/loading, resource-management facilities, and shared input/security validation.

Typical commands, run from the repository root:

```bash
python -m core.cli --help
python -m core.cli check
python -m core.cli --version
python -m core.cli plugins --directory plugins
```

The ResourceManager includes resource profiles and, where its controls are used, concurrency and per-key rate limiting. In the documented low profile, the concurrency limit is one operation. The 50 MiB memory threshold is advisory; it is not an operating-system-enforced memory limit.

The helper `target_is_in_scope()` is available to callers. It requires both ownership verification and explicit authorization for non-loopback targets when used. It is not centrally enforced across every current Core, CLI, or plugin execution path. A DNS TXT proof is an ownership signal, not legal permission.

### Initial plugins

#### File Audit

File Audit performs read-only filesystem metadata and permission inspection. It does not read file contents, modify files, or delete files. It does not follow symbolic links. Recursive traversal uses directory file descriptors and no-follow operations; platforms that cannot provide the required safe operations should reject the unsafe scan rather than silently fall back.

The default scan is non-recursive and traversal is bounded by an entry limit. Findings such as world-writable entries or sensitive-looking files with world-readable permissions are indicators for manual review, not proof of compromise. Verify ownership and permissions before taking action.

Example:

```python
from core.plugin_loader import PluginLoader

plugins = PluginLoader("plugins").load_all()
report = plugins["file_audit"].run(".", recursive=False)
print(report)
```

Plugin loading executes Python code. Load only plugins whose source and behavior you trust.

#### Port Scan

Port Scan is a deliberately narrow TCP connectivity check. It accepts literal IPv4/IPv6 loopback addresses only (`127.0.0.1` and `::1`), limits each call to at most 16 ports, and bounds connection timeouts to 0.1–1.0 seconds. It does not resolve DNS names, scan remote systems, perform service detection, or send application-level requests.

The initial plugin manifest identifies `port_scan` version `1.0.0`.

#### Web Check

Web Check is a bounded HTTP/TLS inspection helper restricted to literal loopback addresses (`127.0.0.1` and `::1`). It does not accept DNS names or public addresses, use proxy environment variables, or automatically follow redirects. It makes a bounded GET request; a redirect response is reported through its `Location` header rather than followed.

For HTTPS, certificate inspection uses a separate TLS connection before the HTTP GET. The TLS and HTTP operations have separate timeout budgets, so total execution time may exceed either individual timeout. The configured timeout is bounded to 0.2–10 seconds per connection.

Web Check does not execute JavaScript, submit forms, modify remote data, send telemetry, crawl sites, or establish that a service is vulnerability-free. External-domain support is deferred pending a separate design and security review.

## Local Web UI

The Local Web UI is a minimal backend built with Python's standard-library `http.server`; it is not a graphical dashboard.

Run it from the repository root:

```bash
python -m web.app
```

The default address is `http://127.0.0.1:8765`. The current API surface is limited to `GET /health` and `HEAD /health`. The server can also be started programmatically with `run_server(port=YOUR_PORT)`.

The server is synchronous and handles requests sequentially. It validates Host, validates Origin when supplied, restricts supplied `Sec-Fetch-Site` values to `same-origin` or `none`, rejects duplicate Host/Origin/Sec-Fetch-Site headers, accepts only GET and HEAD, applies a five-second socket timeout, and bounds header lines and header count. Request logging is disabled. Unknown GET/HEAD paths return 404; unsupported methods return 405.

The backend has no authentication, accounts, HTTPS/TLS, graphical dashboard, or database-backed sessions. Loopback binding and Host/Origin checks are not authentication and do not prevent other local processes from connecting. Do not expose this backend to an untrusted network. See [`docs/WEB_UI.md`](docs/WEB_UI.md) for the full behavior and limitations.

## Installation

Clone the repository and enter its directory:

```bash
git clone https://github.com/amirsiyasatmdar-sudo/uncle-toolkit.git
cd uncle-toolkit
```

The core has no mandatory third-party runtime dependencies. To install the project in editable mode together with its test dependency:

```bash
python -m pip install -e ".[test]"
```

Run the complete test suite using the same test paths as the CI workflow:

```bash
python -m pytest tests web/tests -q
```

Additional local checks include:

```bash
python -m compileall -q core plugins web
python -m core.cli check
python -m core.cli plugins --directory plugins
```

These commands are instructions for contributors; their presence here does not by itself claim that they passed on every supported platform.

## Platform support

Linux and Android through Termux are target platforms. The package metadata specifies Python 3.10 or newer. Compatibility is verified incrementally and can vary with Android version, kernel, Python build, permissions, and installed system utilities. Unsupported operations should fail clearly; the project does not intend to silently escalate privileges or require root.

The latest recorded Termux validation snapshot used Android/aarch64 with Python 3.13.13: 301 tests passed and reported coverage was 99%. This is a result from that tested environment, not a guarantee for every Termux device or Linux distribution. Linux validation remains outstanding. See [`docs/PLATFORM_SUPPORT.md`](docs/PLATFORM_SUPPORT.md) for platform constraints and the validation record.

## Security and acceptable use

Use Uncle Toolkit only for local administration and defensive testing of systems and services that you own or are explicitly authorized to assess. You are responsible for obtaining permission and complying with applicable laws, contracts, platform terms, and organizational policies.

Do not use the project to access, scan, disrupt, or test systems without authorization; bypass authentication or safeguards; collect data unlawfully; or invade another person's privacy. Tool output is not a guarantee that a system is secure.

Python plugins are executable code. Loading one can execute arbitrary Python with the permissions of the toolkit process. Review plugin source before loading it, and keep private plugins, credentials, and local data out of public repositories.

Security helpers are not a substitute for explicit authorization. In particular, the availability of `target_is_in_scope()` does not mean every current call path enforces it centrally. The current Port Scan and Web Check plugins remain restricted to literal loopback targets.

See [`SECURITY.md`](SECURITY.md) for additional security boundaries and vulnerability-reporting guidance.

## Project layout

```text
uncle-toolkit/
├── .github/
│   └── workflows/
│       └── ci.yml
├── core/
├── plugins/
│   ├── file_audit/
│   ├── port_scan/
│   └── web_check/
├── web/
│   └── tests/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PLATFORM_SUPPORT.md
│   └── WEB_UI.md
├── tests/
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── SECURITY.md
├── pyproject.toml
├── pytest.ini
└── requirements.txt
```

This is a high-level view; implementation and test files may evolve.

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) before submitting changes. Contributions should preserve local-first behavior, safe defaults, Linux/Termux compatibility, and clear documentation of limitations.

## License

Uncle Toolkit is distributed under the MIT License. See [`LICENSE`](LICENSE).

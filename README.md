# Uncle Toolkit

**A modular, local-first system and defensive security toolkit for Linux and Termux.**

> **Project status:** The Python core and initial plugins are implemented. The local Web UI is an early backend foundation, not a complete dashboard. The project is under active development and has not reached its first stable release.

Uncle Toolkit is a lightweight, modular Python toolkit for local system utilities, defensive checks, and authorized administration. It emphasizes local execution, transparent behavior, conservative resource usage, and security-conscious defaults.

## Project goals

- **Local-first:** Process data on the user's device. No telemetry or external data transmission is intended by default.
- **Lightweight:** Use Python's standard library where practical and keep third-party dependencies optional.
- **Modular:** Organize functionality into independent plugins with a documented interface.
- **Security-conscious:** Validate inputs, avoid unsafe shell command construction, and require authorization for non-local security checks.
- **Portable:** Target Linux and Termux while documenting platform-specific limitations.
- **Auditable:** Maintain tests, code-quality checks, and clear project documentation.

## Current features

### Core

- Command-line interface.
- Plugin discovery and loading.
- Resource management with configurable resource profiles.
- Input and security validation.
- Concurrency controls and per-key rate limiting.

### Initial plugins

- **File Audit:** Read-only file and permission auditing.
- **Port Scan:** Conservative network and port checks within the tool's authorization rules.
- **Web Check:** HTTP response-header and TLS configuration checks for permitted targets.

### Local Web UI

- Minimal HTTP backend using Python's standard library.
- Loopback-only binding by default (`127.0.0.1`).
- Basic request validation and security checks.
- Health endpoint.

The Web UI is an early backend foundation. It is not a complete dashboard or user-management system. The server is synchronous and intended for local use; loopback binding does not authenticate other local processes.

## Project roadmap

Development is organized into six phases:

| Phase | Description | Status |
|---|---|---|
| 1 | Repository setup and governance | Completed |
| 2 | Python core and resource management | Completed |
| 3 | Initial audit plugins | Completed |
| 4 | Local Web UI backend foundation | Implemented; limited functionality |
| 5 | Security review, quality checks, and documentation | In progress |
| 6 | Linux and Termux verification and `v1.0.0` release | Planned |

A completed implementation phase does not mean that the project has reached a stable release.

For implementation history, see [CHANGELOG.md](CHANGELOG.md). For Web UI details and limitations, see [docs/WEB_UI.md](docs/WEB_UI.md).

## Project structure

The main project components are organized as follows:

```text
uncle-toolkit/
├── core/
├── plugins/
├── web/
├── docs/
├── tests/
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── LICENSE
├── README.md
└── requirements.txt
```

The project structure may evolve as implementation and review continue.

## Installation and basic checks

Clone the repository:

```bash
git clone https://github.com/amirsiyasatmdar-sudo/uncle-toolkit.git
cd uncle-toolkit
```

Install the development test dependency and run the test suite:

```bash
python -m pip install pytest
python -m pytest -q
```

Run the CLI help:

```bash
python -m core.cli --help
```

The core runtime uses the Python standard library. Optional dependencies are documented in `requirements.txt`.

## Security design

The project aims to follow these practices:

- Use subprocess argument lists with `shell=False`; avoid `os.system`, `eval`, and shell-command construction.
- Validate untrusted input.
- Keep secrets out of source control.
- Bind the local Web UI to `127.0.0.1` by default.
- Restrict security checks to targets for which the user has authorization.
- Apply conservative resource limits and rate limiting.
- Keep optional or heavyweight dependencies out of the mandatory runtime dependency set where practical.
- Test security-sensitive behavior and document platform limitations.

The resource manager's memory threshold is advisory; it is not an operating-system-enforced memory limit. If optional process-monitoring support is unavailable, memory measurements may be unavailable.

Plugin loading executes Python code. Only load plugins from sources you trust. No software can guarantee complete security, and this project's checks are not a substitute for a professional security assessment.

## Acceptable use

Uncle Toolkit is intended for education, defensive security, and authorized administration of systems and accounts that you own or are explicitly permitted to assess.

Do not use this project to access, scan, disrupt, or test systems or accounts without permission. Do not use it to bypass access controls, authentication, rate limits, or other safeguards, or to invade another person's privacy.

You are responsible for complying with applicable laws, contracts, platform terms, and organizational policies. A DNS TXT record, where used for ownership verification, is only an ownership signal; it is not legal authorization.

## Platform support

Linux and Termux are target platforms. Compatibility is verified incrementally. Some checks may be unavailable or behave differently depending on Android, the kernel, permissions, and installed system utilities. Unsupported operations should be reported clearly rather than silently escalating privileges.

## Development and documentation

The core, initial plugins, and local Web UI backend are under active development.

Before contributing, read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). See the [Web UI documentation](docs/WEB_UI.md) for current backend instructions and limitations.

English is the primary project documentation language. Persian (`fa`) localization is planned. User-facing strings may use locale JSON files as the project matures.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

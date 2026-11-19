Uncle Toolkit

A modular, local-first system and security toolkit for Linux and Termux.

Uncle Toolkit is a lightweight, modular Python toolkit designed for local system utilities, defensive security checks, and authorized administration.

The project emphasizes local execution, transparent behavior, conservative resource usage, and security-conscious defaults.

«Project status: The Python core and initial plugins are implemented. The local Web UI currently provides an early backend foundation and is not a complete dashboard. The project is still under development and has not reached its first stable release.»

---

Project Goals

- Local-first: Keep processing on the user's device. No telemetry or external data transmission is intended by default.
- Lightweight: Use Python's standard library wherever practical and keep third-party dependencies optional.
- Modular: Organize functionality into independent plugins with a documented interface.
- Security-conscious: Validate inputs, avoid unsafe shell command construction, and require authorization for non-local security checks.
- Portable: Target Linux and Termux while documenting platform-specific limitations.
- Auditable: Maintain tests, code-quality checks, and clear project documentation.

---

Current Features

The following components have been implemented:

Core

- Command-line interface.
- Plugin discovery and loading.
- Resource management.
- Input and security validation.
- Configurable resource profiles.
- Concurrency and rate-limit controls.

Initial Plugins

- File Audit: Read-only file and permission auditing.
- Port Scan: Conservative network and port checks within the tool's authorization rules.
- Web Check: HTTP response-header and TLS configuration checks for permitted targets.

Local Web UI

- Minimal HTTP backend using Python's standard library.
- Loopback-only binding by default ("127.0.0.1").
- Basic request validation and security checks.
- Health endpoint.

The Web UI is an early backend foundation. It does not currently represent a complete web dashboard or user-management system.

---

Project Roadmap

Development is organized into six phases:

Phase| Description| Status
1| Repository setup and governance| Completed
2| Python core and resource management| Completed
3| Initial audit plugins| Completed
4| Local Web UI backend foundation| Implemented; limited functionality
5| Security review, quality checks, and documentation| In progress
6| Linux and Termux verification and "v1.0.0" release| Planned

A completed implementation phase does not mean that the project has reached a stable release.

For implementation history, see "CHANGELOG.md" (CHANGELOG.md).

For Web UI details and limitations, see "docs/WEB_UI.md" (docs/WEB_UI.md).

---

Project Structure

The main project components are organized as follows:

uncle-toolkit/
├── core/
│   ├── __init__.py
│   ├── cli.py
│   ├── plugin_loader.py
│   ├── resource_manager.py
│   └── security.py
├── plugins/
│   ├── file_audit/
│   ├── port_scan/
│   └── web_check/
├── web/
│   ├── app.py
│   └── security.py
├── docs/
│   └── WEB_UI.md
├── tests/
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── LICENSE
├── requirements.txt
└── pytest.ini

The structure may evolve as the project develops.

Plugins are loaded as Python code. Only use plugins from sources you trust. Private local plugins and local data should not be committed to the public repository.

---

Installation

Clone the repository:

git clone https://github.com/amirsiyasatmdar-sudo/uncle-toolkit.git
cd uncle-toolkit

The core is designed to use Python's standard library and does not require mandatory third-party runtime packages.

To run the test suite, install the development dependency if it is not already available:

python -m pip install pytest

Run the tests:

python -m pytest -q

See the phase-specific installation guides for additional setup and usage instructions:

- "Phase 2 — Core Installation" (PHASE2_INSTALL.md)
- "Phase 3 — File Audit Installation" (PHASE3_FILE_AUDIT_INSTALL.md)
- "Phase 3 — Port Scan Installation" (PHASE3_PORT_SCAN_INSTALL.md)
- "Phase 3 — Web Check Installation" (PHASE3_WEB_CHECK_INSTALL.md)

---

Security Design

Uncle Toolkit follows these security principles:

- Use subprocess argument lists and avoid shell command construction.
- Do not use unsafe execution patterns such as "os.system", "eval", or "shell=True".
- Validate untrusted input before processing it.
- Keep secrets and private configuration out of source control.
- Bind the local Web UI to "127.0.0.1" by default.
- Apply conservative resource limits and rate limiting.
- Keep optional dependencies out of the mandatory runtime dependency set where practical.
- Test security-sensitive behavior and document known limitations.
- Require appropriate authorization before assessing non-local systems.

DNS TXT verification, when used, can provide evidence of domain control. It does not establish legal authorization to test a system and is not a complete security assessment.

Important Plugin Warning

Python plugins execute code within the permissions of the process that loads them. A plugin should therefore be treated as executable software, not as harmless configuration.

Only install and load plugins from trusted sources.

Web UI Limitations

The local Web UI is not an authentication boundary. Binding to loopback and validating request headers do not prevent every other local process from connecting to the service.

The current backend is minimal and should not be exposed to public networks.

No security mechanism should be considered a guarantee that a system is completely secure.

---

Acceptable Use

Uncle Toolkit is intended for:

- Educational use.
- Defensive security activities.
- Local system administration.
- Testing systems and accounts that you own or are explicitly authorized to assess.

You must not use this project to:

1. Access, scan, disrupt, or test systems without permission.
2. Bypass authentication, access controls, rate limits, or security safeguards.
3. Collect data unlawfully or invade another person's privacy.
4. Develop or contribute features intended to facilitate unauthorized access.
5. Misrepresent tool output or claim that a successful check guarantees security.

Users are responsible for complying with applicable laws, contracts, platform terms, and organizational policies.

---

Platform Support

The project targets:

- Linux
- Android through Termux

Compatibility is verified incrementally. Behavior may vary depending on the Android version, Linux distribution, kernel, permissions, Python version, and installed system utilities.

Unsupported operations should be reported clearly. The project does not intend to silently escalate privileges.

---

Development and Contributions

Contributions, bug reports, documentation improvements, and security reviews are welcome.

Before contributing:

1. Read "CONTRIBUTING.md" (CONTRIBUTING.md).
2. Read "CODE_OF_CONDUCT.md" (CODE_OF_CONDUCT.md).
3. Review the existing project structure and security principles.
4. Run the relevant tests before submitting changes.

Contributions should preserve the project's local-first design and security-conscious defaults.

---

Documentation Language

English is the primary language of the project documentation.

Persian ("fa") localization is planned for future development. User-facing localization may be introduced through language-specific JSON files as the project evolves.

---

License

Uncle Toolkit is distributed under the MIT License.

See the "LICENSE" (LICENSE) file for the complete license text.

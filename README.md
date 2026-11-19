# Uncle Toolkit

**A modular, local-first system and security toolkit for Linux and Termux.**

> **Project status:** Initial repository setup. The application core and plugins are not implemented yet.

Uncle Toolkit is planned as a lightweight, extensible toolkit that runs on the user's own device. Its design prioritizes local processing, transparent behavior, conservative resource usage, and security-conscious defaults.

## Project goals

- **Local-first:** Process data on the user's device. No telemetry or external data transmission is intended by default.
- **Lightweight:** Keep the Python core small and make optional dependencies optional.
- **Modular:** Discover and run plugins through a documented plugin contract.
- **Security-conscious:** Validate inputs, avoid shell command construction, and require authorization before testing non-local targets.
- **Portable:** Support Linux and Termux, subject to documented platform limitations.
- **Auditable:** Provide automated quality, security, and test checks for contributions.

## Planned capabilities

The roadmap currently includes:

- Telegram account/channel security checks for resources controlled by the user.
- Local system and file-permission audits.
- Conservative network diagnostics and authorized port checks.
- Web response-header and TLS configuration checks for authorized targets.
- A loopback-only local web interface.

These are planned capabilities, not claims that the features are already available.

## Project status and roadmap

Development is planned in six gated phases:

1. Repository setup and governance.
2. Python core: CLI, resource manager, security validation, and plugin loader.
3. Initial plugins: port scan, file audit, and web check.
4. Local web interface using FastAPI.
5. Multi-layer review automation and complete contributor documentation.
6. Linux and Termux verification, followed by the `v1.0.0` release.

Each phase will be tested and reviewed before the next phase begins. See [CHANGELOG.md](CHANGELOG.md) for released changes.

## Intended architecture

```text
uncle-toolkit/
├── core/
│   ├── cli.py
│   ├── plugin_loader.py
│   ├── resource_manager.py
│   └── security.py
├── plugins/
│   ├── telegram_audit/
│   ├── port_scan/
│   ├── web_check/
│   └── file_audit/
├── web_ui/
│   ├── backend/
│   ├── templates/
│   └── static/
├── docs/
├── tests/
└── .github/
    └── workflows/
```

The final structure may evolve through reviewed design decisions. Third-party plugins will use a documented `BasePlugin` contract and a `plugin.json` manifest. Private local plugins will be excluded from version control.

## Security design commitments

The implementation is expected to follow these rules:

- Use `subprocess.run` with argument lists and `shell=False`; do not use `os.system` or `eval`.
- Validate untrusted input on the server side.
- Keep secrets out of source control; use environment-based configuration for any future secrets.
- Bind the local web server to `127.0.0.1` by default.
- Restrict network checks to localhost until target ownership or authorization has been verified. DNS TXT verification may be used as one ownership-verification mechanism.
- Apply resource limits and rate limiting, including a constrained low-resource mode for Termux.
- Keep optional or heavyweight dependencies out of the mandatory dependency set where practical.
- Test security-sensitive behavior and document platform limitations.

A DNS TXT record is an ownership signal, not a substitute for legal authorization or a complete security assessment.

## Legal disclaimer

Uncle Toolkit is intended for education, defensive security, and authorized administration of systems and accounts that you own or are explicitly permitted to assess.

You are responsible for complying with applicable laws, contracts, platform terms, and organizational policies. Do not use this project to access, scan, disrupt, or test systems or accounts without permission. The maintainers do not authorize misuse and are not responsible for damage, loss, or legal consequences arising from use of the software.

The software is provided **"AS IS"**, without warranty of any kind, to the maximum extent permitted by applicable law. See [LICENSE](LICENSE).

## Acceptable Use Policy

By using or contributing to this project, you agree that you will not:

1. Use it against systems, networks, services, or accounts without clear authorization.
2. Attempt to bypass access controls, authentication, rate limits, or security safeguards.
3. Use it to disrupt availability, collect data unlawfully, or invade another person's privacy.
4. Add features designed to facilitate unauthorized access or conceal abusive activity.
5. Misrepresent scan results or claim that a check guarantees a system is secure.

Maintainers may reject contributions that conflict with this policy. This policy does not replace applicable law or grant permission to test any target.

## Platform support

Linux and Termux are target platforms. Compatibility will be verified incrementally. Some checks may be unavailable or behave differently depending on Android, kernel, permissions, and installed system utilities. The project must report unsupported operations clearly rather than silently escalating privileges.

## Development

The repository is currently in its setup phase. Installation instructions and runnable commands will be added when the core and dependency policy are established. Do not assume the planned CLI or web interface exists yet.

Before contributing, read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Language and documentation

English is the primary project documentation language. Persian (`fa`) localization is planned. User-facing strings are intended to use locale JSON files as the project matures.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

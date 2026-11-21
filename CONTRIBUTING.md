# Contributing to Uncle Toolkit

Thank you for your interest in contributing to Uncle Toolkit.

This project values focused changes, clear documentation, security-conscious development, and safe defaults. Contributions should remain maintainable, testable, and compatible with the project's local-first design.

## Before You Start

1. Read the [README](README.md), especially the Security and Acceptable Use section.
2. Read the [Code of Conduct](CODE_OF_CONDUCT.md) and [Security Policy](SECURITY.md).
3. Review existing Issues and Pull Requests to avoid duplicate work.
4. For substantial changes, open an Issue before implementation to discuss scope and design.
5. Never include credentials, personal data, private plugin files, or information collected from systems without authorization.

## Contribution Requirements

- Keep changes focused and explain the problem they solve.
- Use clear names, appropriate type hints, and docstrings for public modules and APIs.
- Preserve Linux and Termux compatibility, or document any platform limitations.
- Add or update tests for changed behavior.
- Update relevant documentation and `CHANGELOG.md` when appropriate.
- Do not introduce mandatory dependencies without explaining their purpose, maintenance status, size, and security implications.
- Obtain maintainer approval before adding a new mandatory runtime dependency.
- Do not introduce telemetry or undisclosed outbound data transmission.
- Document and narrowly scope any proposed network behavior.
- Do not weaken authorization checks, resource limits, or existing security protections.

## Security Requirements

- Never construct shell command strings using untrusted input.
- If subprocess execution is necessary, use argument lists, `shell=False`, validated arguments, and bounded timeouts.
- Do not use `os.system` or `eval`.
- Validate untrusted input on the server side.
- Keep secrets in local environment configuration. Never commit `.env` files, credentials, or private keys.
- Keep the Web UI bound to `127.0.0.1` by default.
- Preserve the current Port Scan and Web Check loopback-only restrictions. Any proposal to support non-loopback targets requires a separate design and security review; ownership proof alone is not authorization.
- Do not automatically run the application with root privileges.
- Avoid collecting, storing, or logging sensitive information.
- Treat third-party plugins as trusted code only after reviewing their source and behavior.

## Tests and CI

Install the project and its test dependency in editable mode:

```bash
python -m pip install -e ".[test]"
```

Run the complete test suite:

```bash
python -m pytest tests web/tests -q
```

The current `.github/workflows/ci.yml` workflow runs on Ubuntu with Python 3.10–3.13. It installs the project with the `test` extra, runs `tests` and `web/tests`, and checks the CLI version and help output. Contributors should not describe a remote CI run as successful unless its result is visible and successful in GitHub Actions.

## Pull Request Process

1. Create a focused branch from the latest `main`.
2. Implement the change and add or update relevant tests.
3. Run applicable tests and quality checks locally.
4. Update documentation and changelog entries where necessary.
5. Open a Pull Request describing:
   - The problem and proposed solution.
   - The changes introduced.
   - Tests and checks performed.
   - Platform compatibility impact.
   - Security implications.
6. Address review feedback and update the Pull Request as needed.

The maintainer reviews contributions and retains final merge approval. Contributors must not claim that a test, security check, or quality check passed unless it was actually executed successfully.

## Review Expectations

The following checks are part of the current CI workflow:

- **Python test matrix:** pytest on Python 3.10, 3.11, 3.12, and 3.13 on Ubuntu.
- **CLI smoke checks:** version and help commands.

The following are useful additional review layers but are **not currently enforced by the CI workflow**:

- **Python static/security checks:** Ruff, Bandit, and coverage thresholds.
- **Web checks:** ESLint, HTMLHint, Prettier, and checks for unexpected external data transmission.
- **Shell/Linux checks:** ShellCheck and checks for unsafe commands or automatic root execution.
- **Supply chain:** Dependency auditing and review of dependency changes.

Do not describe a planned or optional check as an active CI requirement until the workflow is updated and the change is verified.

## Reporting Vulnerabilities

Please do not publish exploitable vulnerability details in a public Issue.

Use GitHub's private vulnerability reporting feature if it is enabled for this repository. If unavailable, contact the repository owner privately through GitHub before public disclosure.

Include the affected components, impact, affected versions or commits, and safe reproduction information.

## License

By submitting a contribution, you agree that it may be distributed under the project's MIT License.

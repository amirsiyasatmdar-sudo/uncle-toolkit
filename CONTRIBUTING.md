# Contributing to Uncle Toolkit

Thank you for your interest in contributing to Uncle Toolkit.

This project values focused changes, clear documentation, security-conscious development, and safe defaults. Contributions should remain maintainable, testable, and compatible with the project's local-first design.

## Before You Start

1. Read the [README](README.md), including the Legal Disclaimer and Acceptable Use Policy.
2. Review existing Issues and Pull Requests to avoid duplicate work.
3. For substantial changes, open an Issue before implementation to discuss scope and design.
4. Never include credentials, personal data, private plugin files, or information collected from systems without authorization.

## Contribution Requirements

- Keep changes focused and explain the problem they solve.
- Use clear names, appropriate type hints, and docstrings for public modules and APIs.
- Preserve Linux and Termux compatibility, or document any platform limitations.
- Add or update tests for changed behavior.
- Update relevant documentation and `CHANGELOG.md` when appropriate.
- Do not introduce mandatory dependencies without explaining their purpose, maintenance status, size, and security implications.
- Obtain maintainer approval before adding a new runtime dependency.
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
- Restrict network testing to localhost unless target ownership or explicit authorization has been established.
- Do not automatically run the application with root privileges.
- Avoid collecting, storing, or logging sensitive information.
- Treat third-party plugins as trusted code only after reviewing their source and behavior.

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

Changes must pass the repository's required checks and receive maintainer approval before merging. The project owner retains final merge approval.

Contributors must not claim that a test, security check, or quality check passed unless it was actually executed successfully.

## Review Expectations

The planned CI review layers include:

- **Python:** Ruff, Bandit, pytest, coverage, and resource-manager integration checks.
- **Web:** ESLint, HTMLHint, Prettier, and checks for unexpected external data transmission.
- **Shell/Linux:** ShellCheck and checks for unsafe commands or automatic root execution.
- **Supply chain:** Dependency auditing and review of dependency changes.

These checks are planned review layers. Their exact commands and enforcement requirements will be documented when the corresponding CI workflows are introduced.

## Reporting Vulnerabilities

Please do not publish exploitable vulnerability details in a public Issue.

Use GitHub's private vulnerability reporting feature if it is enabled for this repository. If unavailable, contact the repository owner privately through GitHub before public disclosure.

Include the affected components, impact, affected versions or commits, and safe reproduction information.

## License

By submitting a contribution, you agree that it may be distributed under the project's MIT License.

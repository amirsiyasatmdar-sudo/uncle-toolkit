# Contributing to Uncle Toolkit

Thank you for considering a contribution. This project values small, reviewable changes, clear documentation, and safe defaults.

## Before you start

1. Read the project [README](README.md), including its Legal Disclaimer and Acceptable Use Policy.
2. Check existing Issues and Pull Requests to avoid duplicate work.
3. For substantial changes, open an Issue first to discuss scope and design.
4. Never include secrets, personal data, private plugin files, or data collected from systems without permission.

## Contribution requirements

- Keep changes focused and explain the problem they solve.
- Use clear names, type hints where useful, and docstrings for public modules and APIs.
- Preserve Linux and Termux compatibility or document any limitation.
- Add or update tests for behavior you change.
- Update documentation and `CHANGELOG.md` when appropriate.
- Do not add a mandatory dependency without explaining its need, maintenance status, size, and security implications.
- Obtain maintainer approval before introducing a new runtime dependency.
- Do not add telemetry or outbound data transmission. Any proposed network behavior must be explicitly documented, narrowly scoped, and reviewed.
- Do not weaken authorization checks, resource limits, or safe defaults.

## Security requirements

- Never construct shell command strings from user input.
- If a subprocess is necessary, use an argument list and `shell=False`, with validated arguments and bounded timeouts.
- Do not use `os.system` or `eval`.
- Validate untrusted input on the server side.
- Keep secrets in local environment configuration; never commit `.env` files or credentials.
- Keep the web interface bound to loopback (`127.0.0.1`) by default.
- Network testing must be limited to localhost until target ownership or explicit authorization is verified.
- Do not run the application automatically with root privileges.
- Avoid collecting, storing, or logging sensitive data.

## Pull request process

1. Create a focused branch from `main`.
2. Make your changes and add tests.
3. Run the relevant tests and quality/security checks locally.
4. Update docs and changelog entries.
5. Open a Pull Request using the repository template, describing the change, test evidence, platform impact, and security implications.
6. Respond to review feedback and keep the PR up to date.

No Pull Request may be merged until required automated checks pass and a maintainer has reviewed and approved it. The project owner retains final merge approval. Contributors should provide tests for the area they modify.

## Review expectations

The planned CI review layers include:

- Python: Ruff, Bandit, pytest, coverage, and checks for resource-manager integration.
- Web: ESLint, HTMLHint, Prettier, and checks against unexpected external data transmission.
- Shell/Linux: ShellCheck and checks against unsafe commands or automatic root execution.
- Supply chain: dependency auditing and review of dependency changes.

The exact commands will be documented when the CI workflow is introduced. Do not claim a check has passed unless it has actually been run.

## Reporting vulnerabilities

Please do not publish exploitable vulnerability details in a public Issue. Use GitHub's private vulnerability reporting feature if it is enabled for this repository. If it is unavailable, contact the repository owner privately through GitHub before disclosing details publicly. Include impact, affected versions/commits, and safe reproduction information.

## License

By submitting a contribution, you agree that it may be distributed under the project's MIT License.

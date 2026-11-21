# Security Policy

Uncle Toolkit is a local-first system utility and defensive security project for Linux
and Termux. Security reports are welcome. This document explains the supported
reporting process, the project's security boundaries, and the expectations for
safe use.

## Supported versions

The project is under active development and has not declared a stable `v1.0.0`
release. Security fixes are therefore evaluated against the current `main` branch.
When a stable release is published, this section should be updated with an explicit
support window.

## Reporting a vulnerability

Please do not publish an unpatched vulnerability, proof-of-concept exploit, private
data, or access credentials in a public issue.

1. Check whether the behavior is already documented as an intentional limitation.
2. If GitHub private vulnerability reporting is enabled for this repository, use
   its **Report a vulnerability** flow.
3. Otherwise, contact the repository maintainer privately through a verified
   contact method listed on the maintainer's GitHub profile. Do not assume that a
   public issue is a private channel.
4. Include the affected commit or version, platform and Python version, a concise
   impact description, reproducible steps that do not affect third-party systems,
   and any relevant logs with secrets and personal data removed.

Please allow the maintainer reasonable time to investigate and prepare a fix before
disclosing technical details publicly. There is currently no guaranteed response
or remediation SLA.

## Scope and security boundaries

The following areas are especially relevant to security review:

- **Plugin loading:** loading a plugin executes Python code. The loader's path,
  symlink, file-type, and size checks reduce specific filesystem risks; they do
  not create a sandbox. Only load plugins from sources you trust.
- **File Audit:** intended to inspect files and permissions without modifying
  audited content. Findings depend on operating-system permissions and the
  filesystem view available to the process.
- **Port Scan:** intentionally constrained to loopback targets. It is not a
  general-purpose remote scanner.
- **Web Check:** accepts literal loopback IP targets and performs bounded HTTP/TLS
  checks. DNS names, redirects, and environment proxies are intentionally not
  used by this plugin.
- **Local Web UI:** the development backend binds to `127.0.0.1`. Loopback binding,
  Host validation, and Origin validation are not authentication and do not prevent
  other local processes from connecting.
- **Resource management:** configured memory thresholds are advisory, not
  operating-system-enforced limits. Concurrency and rate controls are application
  safeguards, not isolation boundaries.

A DNS TXT ownership check, where used, is only an ownership signal. It is not legal
authorization to test a system, account, service, or network.

## Safe testing expectations

- Test only on systems and accounts you own or have explicit permission to assess.
- Prefer isolated temporary directories, loopback services, and test fixtures.
- Do not use production data or third-party targets when preparing a report.
- Do not attempt privilege escalation, persistence, destructive actions, denial of
  service, or access to data outside the test scope.
- Remove credentials, tokens, private addresses, and personal data from reports.

## Security-related changes

Security-sensitive changes should include focused regression tests where practical.
Reviewers should consider path traversal, symlink and race conditions, resource
exhaustion, input validation, error handling, platform capability differences,
and accidental disclosure through logs or error messages.

## Disclaimer

Uncle Toolkit is provided on an "as is" basis under its project license. Its
defensive checks do not replace a professional security assessment, operating
system protections, or an organization's security policies.

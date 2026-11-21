# Platform Support

## 1. Supported targets

Uncle Toolkit targets:

- **Linux:** primary desktop/server operating-system family.
- **Termux on Android:** mobile terminal environment with Android-specific
  filesystem, permission, and kernel constraints.

Compatibility is verified incrementally. A successful run on one device or
distribution does not guarantee identical behavior on another.

## 2. Python version

The project configuration in this bundle declares Python `>=3.10`. The automated
GitHub Actions workflow tests the supported Python versions on Ubuntu. This CI
matrix is a Linux reference environment; it does not replace testing on a user's
actual distribution or Android device.

If a platform packages an older Python interpreter, use a compatible project
revision rather than bypassing the declared minimum version.

## 3. Linux

Linux is a target platform, but release readiness requires an actual validation
run on a representative Linux environment. The following should be checked:

- Python version and standard-library availability.
- Plugin discovery and loading, including filesystem capability checks.
- File Audit behavior under ordinary user permissions.
- Resource manager concurrency, timeout, and rate-limit behavior.
- CLI version, help, environment checks, and plugin listing.
- Web UI loopback binding and request validation.
- Full automated test suite.

Do not mark Linux as verified solely because an Ubuntu CI job passes. CI validates
the tested workflow and Python matrix, not every distribution, filesystem, or
security policy.

## 4. Termux on Android

Termux is supported as a target, subject to Android restrictions:

- Shared-storage access may require Android storage permission and may still be
  restricted by scoped-storage behavior.
- Filesystem semantics and available `open` flags can vary with the Android
  version, kernel, and Termux environment.
- Some directories are inaccessible to an unprivileged Termux process.
- Optional native or process-inspection dependencies may be unavailable or
  behave differently across device architectures.
- Network access can be affected by Android battery controls, VPN configuration,
  carrier routing, and local firewall policy.

Run the toolkit as a normal Termux user. Do not assume root access, and do not
attempt to bypass Android permission boundaries. A feature that lacks a required
filesystem capability should report the limitation rather than silently weakening
its safety checks.

## 5. Filesystem capability requirements

Some security-sensitive filesystem operations rely on platform support for
directory-relative file access and flags such as `O_NOFOLLOW` and `O_DIRECTORY`.
Availability is not identical across all Python builds and operating systems.

The plugin loader and File Audit use capability checks around sensitive traversal
operations. If required capabilities are absent, the safe behavior is to reject
or skip the affected operation with a clear error. Do not remove these checks just
to make an unsupported environment appear compatible.

Filesystem behavior should be tested on the actual filesystem in use, including
shared storage where applicable. Symlink and race-condition tests in a temporary
directory are useful but cannot represent every filesystem implementation.

## 6. Network behavior

The current network-oriented plugins are intentionally constrained:

- Port Scan is limited to loopback targets.
- Web Check accepts literal loopback IP addresses and does not resolve DNS names,
  use environment proxies, or follow redirects.
- The local Web UI binds to `127.0.0.1` by default.

These restrictions are design boundaries, not temporary suggestions to work
around when a platform behaves differently.

## 7. Validation checklist

For each platform release candidate, record:

| Check | Result to record |
| --- | --- |
| OS/distribution and version | Exact device or distribution details |
| CPU architecture | For example, `aarch64` or `x86_64` |
| Python version | Exact `python --version` output |
| Installation | Commands used and whether they completed |
| CLI smoke tests | Version, help, environment check, plugin listing |
| Test suite | Exact command, pass/fail count, and duration |
| Filesystem tests | File Audit and plugin-loader security tests |
| Web UI | Bind address, health endpoint, shutdown behavior |
| Known limitations | Permissions, optional dependencies, unsupported flags |

Keep raw logs free of credentials, tokens, and personal data.

## 8. Current verification status

The project history supplied for this documentation bundle records a successful
Termux test run with Python 3.13.13 on Android/aarch64: 301 tests passed, and the
reported combined coverage was 99%. Treat these as a historical validation
snapshot, not a guarantee about the current checkout or every Termux device.
Re-run the suite after applying this bundle.

Linux validation has not yet been confirmed in the project workflow described
here. The Ubuntu CI workflow added in this bundle is an automated check, but the
project should not claim full Linux platform validation until a real Linux
validation run has been reviewed and recorded.

## 9. Reporting platform issues

A useful report includes the exact OS and version, device architecture, Python
version, filesystem location involved, command executed, full error class and
message, and a minimal reproduction. Remove secrets and personal data before
sharing logs.

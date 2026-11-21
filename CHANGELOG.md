# Changelog

All notable changes to Uncle Toolkit are documented here.

The project follows Semantic Versioning. Before the first stable release, it remains in the `0.x` development stage and interfaces may change.

## [Unreleased]

### Added
- Modular Python core and command-line foundation.
- Plugin discovery and loading with manifest validation and bounded plugin-file reads.
- Resource-management facilities, including configurable concurrency and per-key rate limiting where integrated.
- Shared input and security validation utilities.
- File Audit plugin for read-only filesystem metadata and permission inspection.
- Port Scan plugin for bounded TCP connectivity checks restricted to literal loopback addresses.
- Web Check plugin for bounded loopback HTTP requests and separate HTTPS/TLS inspection.
- Local Web UI backend using Python's standard-library HTTP server.
- Python package metadata and editable-install configuration through `pyproject.toml`.
- GitHub Actions CI workflow covering Python 3.10–3.13, the complete test suite, and CLI smoke checks.
- Architecture, platform-support, and security documentation.
- Automated tests for core components, plugins, and Web UI security behavior.

### Security
- Added strict validation for plugin metadata, names, ports, and network targets.
- Added bounded reads for plugin source and manifest files.
- Added file-descriptor-based protections and no-follow handling in relevant plugin and filesystem operations.
- Added symlink and atomic-replacement handling in relevant loading paths.
- Restricted Port Scan and Web Check to literal loopback targets.
- Disabled proxy-environment use and automatic redirect following in Web Check.
- Added Host, Origin, and Fetch-Site validation for the local Web UI.
- Documented trusted-plugin requirements, authorization boundaries, and acceptable-use limits.

### Changed
- Replaced the planned FastAPI approach with a standard-library HTTP server for the initial Web UI backend.
- Improved ResourceManager timeout validation and rate-limit cleanup.
- Clarified that the 50 MiB memory threshold is advisory, not an OS-enforced limit.
- Clarified that `target_is_in_scope()` is available to callers but is not centrally enforced across all current Core, CLI, and plugin paths.
- Updated installation and test instructions to use the package's `.[test]` extra and the same test paths as CI.
- Consolidated phase-specific implementation and installation guidance into the main project documentation.

### Testing and validation record
- The latest recorded Termux test run used Android/aarch64 with Python 3.13.13: 301 tests passed.
- The corresponding coverage run reported 99% total coverage, with zero missed statements.
- A wheel for `uncle-toolkit 0.1.0` was built and installed locally; CLI version, core check, and plugin listing commands were also run successfully.
- The GitHub Actions workflow is configured for Python 3.10, 3.11, 3.12, and 3.13 on Ubuntu. A configured workflow is not evidence that a remote GitHub Actions run has completed successfully.

These records describe checks performed in the stated development environment. They do not establish Linux compatibility across distributions or guarantee results on every Termux device.

## Development status

Phase 5 — Review & Documentation is complete. Phase 6 — Validation & Release is in progress. The recorded Termux test and packaging checks have completed, while final Linux validation and release preparation remain outstanding. The Local Web UI remains an early backend foundation, not a complete dashboard. The project has not reached stable `v1.0.0`.

## Planned
- Complete Linux validation on a supported environment.
- Finish final cross-platform validation and release review.
- Complete release preparation.
- Prepare the first stable release after validation.

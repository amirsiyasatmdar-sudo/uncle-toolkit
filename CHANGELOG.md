# Changelog

All notable changes to Uncle Toolkit will be documented in this file.

The project follows Semantic Versioning (SemVer). Until the first stable release, the project remains in the `0.x` development stage, and interfaces may change.

## [Unreleased]

### Added
- Modular Python core and command-line foundation.
- Plugin discovery and loading system.
- Resource management with concurrency limits and rate limiting.
- Security validation utilities.
- File Audit plugin for read-only file permission auditing.
- Port Scan plugin for conservative, scope-aware network checks.
- Web Check plugin for HTTP header and TLS checks.
- Local Web UI backend with loopback-only binding.
- Automated tests for core components, plugins, and web security.
- Documentation for the Web UI backend and its limitations.

### Security
- Added strict port validation.
- Added file-descriptor-based plugin loading protections.
- Added symlink and atomic replacement handling in plugin loading.
- Added Host, Origin, and Fetch-Site validation for the local Web UI.
- Documented trusted-plugin requirements and acceptable-use boundaries.

### Changed
- Replaced the planned FastAPI-based Web UI approach with a standard-library HTTP server.
- Improved resource manager timeout validation and rate-limit cleanup.
- Updated project documentation to reflect implemented functionality.

### Testing and Quality
- Test suite: 76 tests passing.
- Ruff lint checks passing.
- Python compile checks passing.

## [Planned]

- Complete remaining documentation reviews.
- Perform final release preparation.
- Prepare the first stable release (`v1.0.0`).

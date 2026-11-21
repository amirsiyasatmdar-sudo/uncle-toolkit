# Architecture

## 1. Purpose and design principles

Uncle Toolkit is a modular, local-first Python toolkit for system inspection and
defensive checks on Linux and Termux. Its architecture favors:

- **Local execution:** operations are performed on the user's device by default.
- **Small runtime footprint:** the core uses the Python standard library.
- **Explicit boundaries:** plugins own focused capabilities and expose a common
  interface.
- **Conservative behavior:** inputs, resource use, filesystem access, and network
  targets are constrained.
- **Testability:** core logic and plugins are exercised through automated tests.

The project is still under active development. This document describes the current
implemented structure, not a promise that every planned feature exists.

## 2. Component map

```text
uncle-toolkit/
├── core/
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
│   ├── routes.py
│   └── security.py
├── docs/
└── tests/
    └── web/tests/
```

The tree is representative; tests and documentation may be reorganized as the
project evolves.

## 3. Core responsibilities

### CLI (`core/cli.py`)

The command-line interface is the user-facing entry point for version information,
environment checks, and plugin operations. It delegates plugin discovery and
execution to the core rather than implementing plugin-specific behavior itself.

### Plugin loader (`core/plugin_loader.py`)

The loader discovers plugin directories, reads their manifests, validates plugin
identity and version metadata, and loads the Python source. The implementation
uses bounded file reads and filesystem operations designed to reject symlinked
plugin paths and non-regular files where supported.

**Important:** loading a plugin executes its Python code. The loader is not a
sandbox, and a plugin can exercise the permissions of the Python process. Install
and load only trusted plugins.

### Resource manager (`core/resource_manager.py`)

The resource manager provides named resource profiles, bounded concurrent
operations, per-key rate limiting, and optional process-memory reporting. Memory
measurements depend on optional process-inspection support. A memory budget check
is advisory; it does not impose a kernel-level memory limit.

### Security helpers (`core/security.py`)

The security module centralizes reusable validation, including safe names, domain
and port parsing, loopback checks, scope helpers, and optional DNS TXT ownership
verification. A helper returning a positive ownership signal does not establish
legal authorization. Callers remain responsible for enforcing the correct scope
for each operation.

## 4. Plugin model

Each plugin is maintained in its own directory and includes Python implementation
and manifest metadata. Plugins implement the base interface defined by the core.
The loader validates metadata before instantiating the plugin.

### File Audit

File Audit performs read-only inspection of filesystem entries and permission
conditions. Its traversal uses defensive directory handling and reports skipped
symlinks, truncation, and encountered errors rather than intentionally modifying
audited files.

### Port Scan

Port Scan is deliberately limited to literal loopback targets and a conservative
set of ports and timeouts. It does not resolve arbitrary hostnames or provide
remote network scanning functionality.

### Web Check

Web Check accepts literal loopback IP addresses. It checks HTTP response metadata
and, for HTTPS, certificate information. It intentionally avoids DNS resolution,
environment proxies, and redirect following. Timeout values are validated and
bounded.

## 5. Local Web UI

The `web/` package is an early local HTTP backend built with Python's standard
library. It is not a complete graphical dashboard or account system. The current
health endpoint is `/health`; the default server address is
`http://127.0.0.1:8765`.

The server validates selected request headers and accepts only the implemented
read-only methods. It is synchronous and processes requests sequentially. It has
no user authentication, TLS, database-backed sessions, or isolation from other
local processes. See [WEB_UI.md](WEB_UI.md) for operational details.

## 6. Typical request flow

1. The user invokes a CLI command or starts the local Web UI.
2. The entry point validates command-level arguments and selects a core operation.
3. The plugin loader discovers and validates plugin metadata when a plugin is
   requested.
4. The selected plugin validates its own inputs and applies its capability-specific
   restrictions.
5. Resource controls are applied where the operation uses them.
6. The plugin returns structured results; the caller presents them to the user.

Not every component is involved in every request. The Web UI currently exposes
only its health endpoint and is not a general plugin execution gateway.

## 7. Dependency strategy

The core runtime is designed around the Python standard library. Optional
capabilities may use:

- `psutil` for process RSS measurements.
- `dnspython` for DNS TXT ownership verification.

`pytest` is a development/test dependency, not a runtime requirement. Optional
dependencies should fail gracefully when their feature is not available.

## 8. Testing and quality boundaries

The repository contains core, plugin, and Web UI tests. Run the full suite from
the repository root:

```bash
python -m pytest tests web/tests -q
```

A passing test suite demonstrates behavior covered by those tests on the
environment where they ran. It does not prove compatibility with every Linux
distribution, Android device, filesystem, kernel, or Python implementation.
Linux and Termux validation status is tracked separately in
[PLATFORM_SUPPORT.md](PLATFORM_SUPPORT.md).

## 9. Extension guidelines

When adding a plugin or core capability:

1. Keep the feature focused and expose a narrow interface.
2. Validate all external inputs at the boundary.
3. Bound file sizes, timeouts, concurrency, and iteration where applicable.
4. Avoid shell-string execution; use argument arrays with `shell=False` if a
   subprocess is genuinely required.
5. Fail closed when required platform capabilities are unavailable.
6. Keep optional dependencies optional and document degraded behavior.
7. Add tests for normal behavior, invalid inputs, error paths, and security
   boundaries.
8. Update user and developer documentation in the same change.

Do not describe a feature as implemented until its code and tests are present.

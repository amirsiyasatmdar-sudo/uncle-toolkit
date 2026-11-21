# Phase 2 Core Files

Extract this archive into the root of the cloned repository, preserving folders.
It adds `core/`, `tests/`, `requirements.txt`, and `pytest.ini`.

Run tests:

```bash
python -m pytest -q
```

Run the CLI:

```bash
python -m core.cli --help
python -m core.cli check
python -m core.cli --version
```

Security notes:
- The ResourceManager low profile configures a one-operation concurrency limit
  and a per-key rate limit when its controls are used.
- The 50 MiB memory threshold is advisory, not an OS-enforced hard limit.
- The `target_is_in_scope()` helper accepts non-loopback targets only when both
  ownership verification and explicit authorization are confirmed. This helper
  is available to callers; current Core, CLI, and plugin paths do not enforce
  this check centrally. DNS proof alone is not legal authorization.
- Loading plugins executes Python code; only load trusted local plugins.
- No mandatory third-party runtime dependencies are required.

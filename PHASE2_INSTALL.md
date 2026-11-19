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
- Low mode limits concurrent operations to one and applies a per-key rate limit.
- The 50 MiB memory threshold is advisory, not an OS-enforced hard limit.
- Non-loopback targets require both DNS ownership verification and explicit
  authorization. DNS proof alone is not legal authorization.
- Loading plugins executes Python code; only load trusted local plugins.
- No mandatory third-party runtime dependencies are required.

# Phase 3 — File Audit Plugin

This package adds the first Phase 3 plugin, `file_audit`, to an existing
`uncle-toolkit` repository. Extract the archive into the repository root.

## Files

- `plugins/file_audit/plugin.py` — read-only permission audit.
- `plugins/file_audit/plugin.json` — plugin name and SemVer metadata.
- `tests/test_file_audit.py` — plugin and loader tests.

## Run

```bash
python -m pytest -q
python -m core.cli plugins --directory plugins
```

The plugin inspects filesystem metadata only. It does not read file contents,
modify or delete files, or follow symbolic links. Recursive traversal uses
directory file descriptors and no-follow opens to resist directory-to-symlink
replacement during traversal; platforms without the required safe operations are
rejected rather than scanned unsafely. It defaults to a non-recursive scan, has
a maximum entry limit, and reports potentially world-writable entries
and sensitive-looking files that are world-readable. Findings are indicators,
not proof of compromise. Review permissions and ownership before taking action.

Run it through the Python API:

```python
from core.plugin_loader import PluginLoader

plugins = PluginLoader("plugins").load_all()
report = plugins["file_audit"].run(".", recursive=False)
print(report)
```

Only load trusted local plugins: importing a plugin executes its Python code.

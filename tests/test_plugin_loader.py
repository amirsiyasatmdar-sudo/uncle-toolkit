import os
import json
import pytest
from core.plugin_loader import BasePlugin, PluginLoader


def make_plugin(root, name="sample"):
    folder = root / name
    folder.mkdir()
    (folder / "plugin.json").write_text(json.dumps({"name": name, "version": "1.2.3"}))
    (folder / "plugin.py").write_text(
        "from core.plugin_loader import BasePlugin\n"
        "class Plugin(BasePlugin):\n"
        " def run(self, *args, **kwargs): return 'ok'\n"
        f" def get_metadata(self): return {{'name': '{name}'}}\n"
    )
    return folder


def test_discover_and_load(tmp_path):
    make_plugin(tmp_path)
    loader = PluginLoader(tmp_path)
    assert len(loader.discover()) == 1
    plugins = loader.load_all()
    assert isinstance(plugins["sample"], BasePlugin)
    assert plugins["sample"].run() == "ok"


def test_private_folder_skipped(tmp_path):
    make_plugin(tmp_path, "_private")
    assert PluginLoader(tmp_path).discover() == []


def test_external_plugin_path_rejected(tmp_path):
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    outside = make_plugin(tmp_path, "outside")
    with pytest.raises(ValueError):
        PluginLoader(plugins).load(outside)


def test_bad_manifest_version_rejected(tmp_path):
    folder = make_plugin(tmp_path)
    (folder / "plugin.json").write_text('{"name":"sample","version":"latest"}')
    with pytest.raises(ValueError):
        PluginLoader(tmp_path).load(folder)


def test_manifest_version_is_preserved_in_loader_metadata(tmp_path):
    make_plugin(tmp_path)
    loader = PluginLoader(tmp_path)
    loader.load_all()
    assert loader.metadata["sample"]["version"] == "1.2.3"


def test_cli_displays_manifest_version(tmp_path, capsys):
    from core.cli import main

    make_plugin(tmp_path)
    assert main(["plugins", "--directory", str(tmp_path)]) == 0
    assert "sample 1.2.3" in capsys.readouterr().out


def test_duplicate_manifest_names_rejected(tmp_path):
    make_plugin(tmp_path, "first")
    make_plugin(tmp_path, "second")
    (tmp_path / "second" / "plugin.json").write_text(
        json.dumps({"name": "first", "version": "1.2.3"})
    )
    with pytest.raises(ValueError, match="Duplicate plugin name: first"):
        PluginLoader(tmp_path).load_all()


def test_plugin_metadata_must_match_manifest(tmp_path):
    folder = make_plugin(tmp_path)
    (folder / "plugin.py").write_text(
        "from core.plugin_loader import BasePlugin\n"
        "class Plugin(BasePlugin):\n"
        " def run(self, *args, **kwargs): return 'ok'\n"
        " def get_metadata(self): return {'name': 'other', 'version': '1.2.3'}\n"
    )
    with pytest.raises(ValueError, match="does not match manifest"):
        PluginLoader(tmp_path).load(folder)


def test_discover_skips_symlinked_plugin_file(tmp_path):
    plugin_dir = tmp_path / "sample"
    plugin_dir.mkdir()

    outside = tmp_path / "outside.py"
    outside.write_text("# external plugin\\n", encoding="utf-8")
    (plugin_dir / "plugin.py").symlink_to(outside)

    assert PluginLoader(tmp_path).discover() == []


def test_load_rejects_symlinked_plugin_file(tmp_path):
    plugin_dir = tmp_path / "sample"
    plugin_dir.mkdir()

    outside = tmp_path / "outside.py"
    outside.write_text("# external plugin\\n", encoding="utf-8")
    (plugin_dir / "plugin.py").symlink_to(outside)

    with pytest.raises(ValueError):
        PluginLoader(tmp_path).load(plugin_dir)


def test_discover_skips_symlinked_plugin_directory(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "plugin.py").write_text(
        "# external plugin\\n",
        encoding="utf-8",
    )

    linked = tmp_path / "linked"
    linked.symlink_to(outside, target_is_directory=True)

    assert linked not in PluginLoader(tmp_path).discover()

def test_load_rejects_symlinked_plugin_directory(tmp_path):
    plugins = tmp_path / "plugins"
    plugins.mkdir()

    real_plugin = make_plugin(plugins, "real")
    linked_plugin = plugins / "linked"
    linked_plugin.symlink_to(real_plugin, target_is_directory=True)

    with pytest.raises(ValueError, match="Symlinked plugin directories"):
        PluginLoader(plugins).load(linked_plugin)

def test_failed_plugin_execution_cleans_sys_modules(tmp_path):
    import sys

    folder = make_plugin(tmp_path)
    (folder / "plugin.py").write_text(
        "raise RuntimeError('plugin startup failed')\n",
        encoding="utf-8",
    )

    module_name = f"_uncle_toolkit_plugin_{folder.name}"

    with pytest.raises(RuntimeError, match="plugin startup failed"):
        PluginLoader(tmp_path).load(folder)

    assert module_name not in sys.modules


def test_duplicate_manifest_name_does_not_execute_second_plugin(tmp_path):
    import sys

    make_plugin(tmp_path, "first")
    second = make_plugin(tmp_path, "second")

    (second / "plugin.json").write_text(
        json.dumps({"name": "first", "version": "1.2.3"}),
        encoding="utf-8",
    )
    (second / "plugin.py").write_text(
        "raise RuntimeError('second plugin must not execute')\n",
        encoding="utf-8",
    )

    module_name = f"_uncle_toolkit_plugin_{second.name}"

    with pytest.raises(ValueError, match="Duplicate plugin name: first"):
        PluginLoader(tmp_path).load_all()

    assert module_name not in sys.modules

def test_load_rejects_symlinked_manifest(tmp_path):
    folder = make_plugin(tmp_path)

    outside_manifest = tmp_path / "outside.json"
    outside_manifest.write_text(
        json.dumps({"name": "sample", "version": "1.2.3"}),
        encoding="utf-8",
    )

    manifest = folder / "plugin.json"
    manifest.unlink()
    manifest.symlink_to(outside_manifest)

    with pytest.raises(
        ValueError,
        match="Symlinked plugin manifests",
    ):
        PluginLoader(tmp_path).load(folder)

def test_loader_rejects_plugin_replaced_by_symlink(tmp_path, monkeypatch):
    folder = make_plugin(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_text(
        "raise RuntimeError('outside plugin executed')\\n",
        encoding="utf-8",
    )

    import os
    original_open = os.open
    replaced = False

    def replacing_open(file, flags, *args, **kwargs):
        nonlocal replaced

        if file == "plugin.py" and kwargs.get("dir_fd") is not None:
            plugin_file = folder / "plugin.py"
            plugin_file.unlink()
            plugin_file.symlink_to(outside)
            replaced = True

        return original_open(file, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", replacing_open)

    with pytest.raises((OSError, ValueError)):
        PluginLoader(tmp_path).load(folder)

    assert replaced


def test_loader_uses_open_file_after_atomic_replacement(tmp_path, monkeypatch):
    import os

    folder = make_plugin(tmp_path)
    plugin_file = folder / "plugin.py"

    replacement = tmp_path / "replacement.py"
    replacement.write_text(
        "raise RuntimeError('replacement plugin executed')\n",
        encoding="utf-8",
    )

    original_open = os.open
    replaced = False

    def replacing_open(file, flags, *args, **kwargs):
        nonlocal replaced

        fd = original_open(file, flags, *args, **kwargs)

        if (
            file == "plugin.py"
            and kwargs.get("dir_fd") is not None
            and not replaced
        ):
            os.replace(replacement, plugin_file)
            replaced = True

        return fd

    monkeypatch.setattr(os, "open", replacing_open)

    plugin = PluginLoader(tmp_path).load(folder)

    assert replaced
    assert plugin.run() == "ok"


def test_manifest_size_limit_rejects_oversized_file(tmp_path):
    from core.plugin_loader import MAX_MANIFEST_SIZE

    folder = make_plugin(tmp_path)
    manifest = folder / "plugin.json"
    manifest.write_bytes(b" " * (MAX_MANIFEST_SIZE + 1))

    with pytest.raises(ValueError, match="exceeds maximum size"):
        PluginLoader(tmp_path).load(folder)


def test_manifest_size_limit_accepts_exact_limit(tmp_path):
    from core.plugin_loader import MAX_MANIFEST_SIZE

    folder = make_plugin(tmp_path)
    manifest = folder / "plugin.json"
    valid_manifest = json.dumps(
        {"name": "sample", "version": "1.2.3"}
    ).encode("utf-8")
    manifest.write_bytes(
        valid_manifest + b" " * (MAX_MANIFEST_SIZE - len(valid_manifest))
    )

    plugin = PluginLoader(tmp_path).load(folder)
    assert plugin.run() == "ok"


def test_plugin_source_size_limit_rejects_oversized_file(tmp_path):
    from core.plugin_loader import MAX_PLUGIN_SOURCE_SIZE

    folder = make_plugin(tmp_path)
    source = folder / "plugin.py"
    source.write_bytes(b"#" * (MAX_PLUGIN_SOURCE_SIZE + 1))

    with pytest.raises(ValueError, match="exceeds maximum size"):
        PluginLoader(tmp_path).load(folder)


def test_plugin_source_size_limit_accepts_exact_limit(tmp_path):
    from core.plugin_loader import MAX_PLUGIN_SOURCE_SIZE

    folder = make_plugin(tmp_path)
    source = folder / "plugin.py"
    valid_source = source.read_bytes()
    source.write_bytes(
        valid_source
        + b"\n# padding"
        + b" " * (
            MAX_PLUGIN_SOURCE_SIZE - len(valid_source) - len(b"\n# padding")
        )
    )

    plugin = PluginLoader(tmp_path).load(folder)
    assert plugin.run() == "ok"


def test_close_fds_continues_after_close_error(monkeypatch):
    closed = []

    def fake_close(fd):
        closed.append(fd)
        if fd == 10:
            raise OSError("simulated close failure")

    monkeypatch.setattr(os, "close", fake_close)

    PluginLoader._close_fds(10, 11, None, 12)

    assert closed == [10, 11, 12]


@pytest.mark.parametrize(
    "manifest_content",
    [
        b'{"name":',
        b'\xff\xfe\xfa',
    ],
)
def test_invalid_manifest_encoding_or_json_rejected(
    tmp_path, manifest_content
):
    folder = make_plugin(tmp_path)
    (folder / "plugin.json").write_bytes(manifest_content)

    with pytest.raises(ValueError, match="Invalid manifest"):
        PluginLoader(tmp_path).load(folder)


@pytest.mark.parametrize(
    "manifest_content",
    [
        b'[]',
        b'"plugin"',
        b'null',
    ],
)
def test_non_object_manifest_rejected(tmp_path, manifest_content):
    folder = make_plugin(tmp_path)
    (folder / "plugin.json").write_bytes(manifest_content)

    with pytest.raises(ValueError, match="JSON object"):
        PluginLoader(tmp_path).load(folder)


def test_invalid_manifest_name_rejected(tmp_path):
    folder = make_plugin(tmp_path)
    (folder / "plugin.json").write_text(
        json.dumps({"name": "../invalid", "version": "1.2.3"})
    )

    with pytest.raises(ValueError, match="Invalid plugin name"):
        PluginLoader(tmp_path).load(folder)


def test_loader_rejects_missing_required_open_flag(tmp_path, monkeypatch):
    from core import plugin_loader

    monkeypatch.delattr(os, "O_NOFOLLOW")

    loader = PluginLoader(tmp_path)
    with pytest.raises(RuntimeError, match="required filesystem capabilities"):
        loader._check_platform_support()


def test_loader_rejects_missing_dir_fd_support(tmp_path, monkeypatch):
    from core import plugin_loader

    supported = set(os.supports_dir_fd)
    supported.discard(os.open)
    monkeypatch.setattr(os, "supports_dir_fd", supported)

    loader = PluginLoader(tmp_path)
    with pytest.raises(RuntimeError, match="required filesystem capabilities"):
        loader._check_platform_support()

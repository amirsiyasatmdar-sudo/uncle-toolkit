import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

import core.plugin_loader as pl
from core.plugin_loader import BasePlugin, PluginLoader


def make_plugin(root, name="sample", source=None):
    folder = root / name
    folder.mkdir()
    (folder / "plugin.json").write_text(
        json.dumps({"name": name, "version": "1.2.3"})
    )
    (folder / "plugin.py").write_text(
        source
        or (
            "from core.plugin_loader import BasePlugin\n"
            "class Plugin(BasePlugin):\n"
            " def run(self, *args, **kwargs): return 'ok'\n"
            f" def get_metadata(self): return {{'name': '{name}'}}\n"
        )
    )
    return folder


@pytest.mark.parametrize(
    "name",
    [None, 1, "", "Upper", "1start", "_private", "a" * 33, "bad.name"],
)
def test_register_command_rejects_invalid_names(name):
    with pytest.raises(ValueError, match="Invalid command name"):
        pl.register_command(name)


def test_register_command_registers_and_returns_function():
    name = "extra_test_command"

    def callback():
        return "ok"

    try:
        decorator = pl.register_command(name)
        assert decorator(callback) is callback
        assert pl._COMMANDS[name] is callback

        with pytest.raises(ValueError, match="already registered"):
            pl.register_command(name)(callback)
    finally:
        pl._COMMANDS.pop(name, None)


def test_base_plugin_abstract_methods_raise_not_implemented():
    with pytest.raises(NotImplementedError):
        BasePlugin.run(None)

    with pytest.raises(NotImplementedError):
        BasePlugin.get_metadata(None)


def test_discover_returns_empty_for_missing_directory(tmp_path):
    loader = PluginLoader(tmp_path / "missing")
    assert loader.discover() == []


def test_discover_rejects_non_directory_path(tmp_path):
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("file")

    with pytest.raises(ValueError, match="not a directory"):
        PluginLoader(file_path).discover()


def test_open_regular_file_rejects_directory_and_closes_fd(tmp_path):
    folder = tmp_path / "plugin"
    folder.mkdir()
    (folder / "plugin.py").mkdir()

    loader = PluginLoader(tmp_path)
    directory_fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)

    try:
        with pytest.raises(ValueError, match="not regular"):
            loader._open_regular_file("plugin.py", directory_fd)
    finally:
        os.close(directory_fd)


def test_open_root_rejects_non_directory_fstat_result(tmp_path, monkeypatch):
    loader = PluginLoader(tmp_path)
    real_fstat = os.fstat
    opened_fd = []

    def fake_fstat(fd):
        if opened_fd and fd == opened_fd[0]:
            return SimpleNamespace(st_mode=stat.S_IFREG)
        return real_fstat(fd)

    real_open = os.open

    def tracking_open(*args, **kwargs):
        fd = real_open(*args, **kwargs)
        if not opened_fd:
            opened_fd.append(fd)
        return fd

    monkeypatch.setattr(pl.os, "open", tracking_open)
    monkeypatch.setattr(pl.os, "fstat", fake_fstat)

    with pytest.raises(ValueError, match="not a directory"):
        loader._open_root()

    with pytest.raises(OSError):
        real_fstat(opened_fd[0])


def test_read_manifest_fd_propagates_non_symlink_oserror(tmp_path, monkeypatch):
    loader = PluginLoader(tmp_path)

    def fail_open(name, directory_fd):
        raise PermissionError("manifest access denied")

    monkeypatch.setattr(loader, "_open_regular_file", fail_open)

    with pytest.raises(PermissionError, match="manifest access denied"):
        loader._read_manifest_fd(123, "sample")


def test_load_all_rejects_duplicate_loaded_metadata_names(tmp_path, monkeypatch):
    make_plugin(tmp_path, "first")
    make_plugin(tmp_path, "second")

    loader = PluginLoader(tmp_path)

    class DummyPlugin:
        pass

    def fake_load(plugin_dir):
        loader.metadata[plugin_dir.name] = {
            "name": "first",
            "version": "1.2.3",
        }
        return DummyPlugin()

    monkeypatch.setattr(loader, "load", fake_load)

    with pytest.raises(ValueError, match="Duplicate plugin name: first"):
        loader.load_all()


@pytest.mark.parametrize(
    "source",
    [
        "class Plugin:\n    pass\n",
        "Plugin = 123\n",
    ],
)
def test_load_rejects_invalid_plugin_class(tmp_path, source):
    folder = make_plugin(tmp_path, source=source)

    with pytest.raises(TypeError, match="must define Plugin"):
        PluginLoader(tmp_path).load(folder)


@pytest.mark.parametrize(
    "source",
    [
        (
            "from core.plugin_loader import BasePlugin\n"
            "class Plugin(BasePlugin):\n"
            " def run(self, *args, **kwargs): return None\n"
            " def get_metadata(self): return []\n"
        ),
        (
            "from core.plugin_loader import BasePlugin\n"
            "class Plugin(BasePlugin):\n"
            " def run(self, *args, **kwargs): return None\n"
            " def get_metadata(self): return {'name': 'sample'}\n"
            " def validate(self): return False\n"
        ),
    ],
)
def test_load_rejects_plugin_validation_failure(tmp_path, source):
    folder = make_plugin(tmp_path, source=source)

    with pytest.raises(ValueError, match="Plugin validation failed"):
        PluginLoader(tmp_path).load(folder)


def test_load_propagates_non_symlink_source_open_error(
    tmp_path, monkeypatch
):
    folder = make_plugin(tmp_path)
    loader = PluginLoader(tmp_path)
    original_open = loader._open_regular_file

    def fail_source_open(name, directory_fd):
        if name == "plugin.py":
            raise PermissionError("source access denied")
        return original_open(name, directory_fd)

    monkeypatch.setattr(loader, "_open_regular_file", fail_source_open)

    with pytest.raises(PermissionError, match="source access denied"):
        loader.load(folder)


def test_load_rejects_non_directory_plugin_fd(tmp_path, monkeypatch):
    folder = make_plugin(tmp_path)
    loader = PluginLoader(tmp_path)
    real_fstat = os.fstat
    plugin_fd = []

    original_open = os.open

    def tracking_open(*args, **kwargs):
        fd = original_open(*args, **kwargs)
        if kwargs.get("dir_fd") is not None and not plugin_fd:
            plugin_fd.append(fd)
        return fd

    def fake_fstat(fd):
        if plugin_fd and fd == plugin_fd[0]:
            return SimpleNamespace(st_mode=stat.S_IFREG)
        return real_fstat(fd)

    monkeypatch.setattr(pl.os, "open", tracking_open)
    monkeypatch.setattr(pl.os, "fstat", fake_fstat)

    with pytest.raises(ValueError, match="Plugin path is not a directory"):
        loader.load(folder)

    with pytest.raises(OSError):
        real_fstat(plugin_fd[0])

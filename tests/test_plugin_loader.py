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
        f" def get_metadata(self): return {{'name': '{name}'}}\n")
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

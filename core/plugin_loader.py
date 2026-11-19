"""Discovery and loading of trusted local Python plugins.

Loading a plugin executes Python code. Only load plugins from trusted sources.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable

_COMMANDS: dict[str, Callable[..., Any]] = {}

def register_command(name: str):
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", name):
        raise ValueError("Invalid command name")
    def decorator(func: Callable[..., Any]):
        if name in _COMMANDS:
            raise ValueError(f"Command already registered: {name}")
        _COMMANDS[name] = func
        return func
    return decorator

class BasePlugin(ABC):
    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError
    def validate(self) -> bool:
        return True
    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        raise NotImplementedError

class PluginLoader:
    def __init__(self, plugins_dir: str | Path) -> None:
        self.plugins_dir = Path(plugins_dir).expanduser().resolve()
        self.loaded: dict[str, BasePlugin] = {}
        self.metadata: dict[str, dict[str, Any]] = {}

    def discover(self) -> list[Path]:
        if not self.plugins_dir.exists():
            return []
        if not self.plugins_dir.is_dir():
            raise ValueError("Plugins path is not a directory")
        return sorted(p for p in self.plugins_dir.iterdir()
                      if p.is_dir() and not p.name.startswith("_")
                      and (p / "plugin.py").is_file())

    @staticmethod
    def _read_manifest(plugin_dir: Path) -> dict[str, Any]:
        manifest_path = plugin_dir / "plugin.json"
        if not manifest_path.exists():
            return {"name": plugin_dir.name, "version": "0.0.0"}
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid manifest for {plugin_dir.name}") from exc
        if not isinstance(data, dict):
            raise ValueError("Plugin manifest must be a JSON object")
        name, version = data.get("name", plugin_dir.name), data.get("version", "0.0.0")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name):
            raise ValueError("Invalid plugin name")
        if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
            raise ValueError("Plugin version must use MAJOR.MINOR.PATCH")
        return data

    def load_all(self) -> dict[str, BasePlugin]:
        for plugin_dir in self.discover():
            manifest = self._read_manifest(plugin_dir)
            declared_name = manifest.get("name", plugin_dir.name)
            if declared_name in self.loaded:
                raise ValueError(f"Duplicate plugin name: {declared_name}")
            plugin = self.load(plugin_dir)
            metadata = self.metadata[plugin_dir.name]
            name = metadata["name"]
            if name in self.loaded:
                raise ValueError(f"Duplicate plugin name: {name}")
            self.loaded[name] = plugin
            self.metadata[name] = metadata
        return dict(self.loaded)

    def load(self, plugin_dir: str | Path) -> BasePlugin:
        path = Path(plugin_dir).resolve()
        if path.parent != self.plugins_dir or not (path / "plugin.py").is_file():
            raise ValueError("Plugin must be a direct child of plugins directory")
        manifest = self._read_manifest(path)
        module_name = f"_uncle_toolkit_plugin_{path.name}"
        spec = importlib.util.spec_from_file_location(module_name, path / "plugin.py")
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin: {path.name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            cls = getattr(module, "Plugin", None)
            if not isinstance(cls, type) or not issubclass(cls, BasePlugin):
                raise TypeError(f"{path.name}/plugin.py must define Plugin(BasePlugin)")
            plugin = cls()
            raw_metadata = plugin.get_metadata()
            if not isinstance(raw_metadata, dict) or not plugin.validate():
                raise ValueError(f"Plugin validation failed: {path.name}")
            metadata = dict(raw_metadata)
            manifest_name = manifest.get("name", path.name)
            manifest_version = manifest.get("version", "0.0.0")
            plugin_name = metadata.get("name", manifest_name)
            plugin_version = metadata.get("version", manifest_version)
            if plugin_name != manifest_name or plugin_version != manifest_version:
                raise ValueError(f"Plugin metadata does not match manifest: {path.name}")
            metadata["name"] = manifest_name
            metadata["version"] = manifest_version
            self.metadata[path.name] = metadata
            return plugin
        except Exception:
            sys.modules.pop(module_name, None)
            raise

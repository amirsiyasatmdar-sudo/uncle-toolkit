"""Discovery and loading of trusted local Python plugins.

Loading a plugin executes Python code. Only load plugins from trusted sources.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import errno
import importlib.machinery
import json
import os
from pathlib import Path
import re
import stat
import sys
from types import ModuleType
from typing import Any, Callable


_COMMANDS: dict[str, Callable[..., Any]] = {}

MAX_PLUGIN_SOURCE_SIZE = 1024 * 1024
MAX_MANIFEST_SIZE = 64 * 1024

# Capture the original platform capability before tests or callers
# temporarily replace os.open.
_ORIGINAL_OS_OPEN = os.open


def register_command(name: str):
    if not isinstance(name, str) or not re.fullmatch(
        r"[a-z][a-z0-9_-]{0,31}", name
    ):
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

    @staticmethod
    def _read_fd(fd: int, max_bytes: int) -> bytes:
        chunks = []
        total = 0

        while True:
            remaining = max_bytes - total
            chunk = os.read(fd, min(65536, remaining + 1))

            if not chunk:
                break

            total += len(chunk)
            if total > max_bytes:
                raise ValueError(
                    f"Plugin file exceeds maximum size of {max_bytes} bytes"
                )

            chunks.append(chunk)

        return b"".join(chunks)

    @staticmethod
    def _close_fds(*fds: int | None) -> None:
        for fd in fds:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass

    @staticmethod
    def _check_platform_support() -> None:
        required_flags = (
            "O_RDONLY",
            "O_CLOEXEC",
            "O_NOFOLLOW",
            "O_DIRECTORY",
            "O_NONBLOCK",
        )
        if any(not hasattr(os, flag) for flag in required_flags):
            raise RuntimeError(
                "This platform lacks required filesystem capabilities"
            )

        if _ORIGINAL_OS_OPEN not in getattr(os, "supports_dir_fd", set()):
            raise RuntimeError(
                "This platform lacks required filesystem capabilities"
            )

    @staticmethod
    def _open_flags() -> int:
        PluginLoader._check_platform_support()
        return os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW

    def _open_regular_file(self, name: str, directory_fd: int) -> int:
        fd = os.open(
            name,
            self._open_flags() | os.O_NONBLOCK,
            dir_fd=directory_fd,
        )
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError(f"Plugin file is not regular: {name}")
            return fd
        except Exception:
            os.close(fd)
            raise

    def _open_root(self) -> int:
        fd = os.open(
            self.plugins_dir,
            self._open_flags() | os.O_DIRECTORY,
        )
        if not stat.S_ISDIR(os.fstat(fd).st_mode):
            os.close(fd)
            raise ValueError("Plugins path is not a directory")
        return fd

    def discover(self) -> list[Path]:
        self._check_platform_support()
        if not self.plugins_dir.exists():
            return []
        if not self.plugins_dir.is_dir():
            raise ValueError("Plugins path is not a directory")

        results = []
        root_fd = self._open_root()
        try:
            for name in sorted(os.listdir(root_fd)):
                if name.startswith("_"):
                    continue
                try:
                    plugin_fd = os.open(
                        name,
                        self._open_flags() | os.O_DIRECTORY,
                        dir_fd=root_fd,
                    )
                except OSError:
                    continue

                try:
                    try:
                        file_fd = self._open_regular_file(
                            "plugin.py", plugin_fd
                        )
                    except (OSError, ValueError):
                        continue
                    else:
                        os.close(file_fd)
                        results.append(self.plugins_dir / name)
                finally:
                    os.close(plugin_fd)
        finally:
            os.close(root_fd)

        return results

    @staticmethod
    def _parse_manifest(data: bytes, plugin_name: str) -> dict[str, Any]:
        try:
            result = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Invalid manifest for {plugin_name}"
            ) from exc

        if not isinstance(result, dict):
            raise ValueError("Plugin manifest must be a JSON object")

        name = result.get("name", plugin_name)
        version = result.get("version", "0.0.0")

        if not isinstance(name, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,64}", name
        ):
            raise ValueError("Invalid plugin name")

        if not isinstance(version, str) or not re.fullmatch(
            r"\d+\.\d+\.\d+", version
        ):
            raise ValueError("Plugin version must use MAJOR.MINOR.PATCH")

        return result

    def _read_manifest_fd(
        self, plugin_fd: int, plugin_name: str
    ) -> dict[str, Any]:
        try:
            fd = self._open_regular_file("plugin.json", plugin_fd)
        except FileNotFoundError:
            return {"name": plugin_name, "version": "0.0.0"}
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise ValueError(
                    "Symlinked plugin manifests are not allowed"
                ) from exc
            raise

        try:
            data = self._read_fd(fd, MAX_MANIFEST_SIZE)
        finally:
            os.close(fd)

        return self._parse_manifest(data, plugin_name)

    @staticmethod
    def _read_manifest(plugin_dir: Path) -> dict[str, Any]:
        loader = PluginLoader(plugin_dir.parent)
        loader._check_platform_support()
        directory_fd = os.open(
            plugin_dir,
            loader._open_flags() | os.O_DIRECTORY,
        )
        try:
            return loader._read_manifest_fd(
                directory_fd, plugin_dir.name
            )
        finally:
            os.close(directory_fd)

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
        self._check_platform_support()
        raw_path = Path(plugin_dir).expanduser()

        if raw_path.is_symlink():
            raise ValueError("Symlinked plugin directories are not allowed")

        if raw_path.parent.resolve() != self.plugins_dir:
            raise ValueError(
                "Plugin must be a direct child of plugins directory"
            )

        root_fd = self._open_root()
        plugin_fd = None
        source_fd = None
        module_name = f"_uncle_toolkit_plugin_{raw_path.name}"

        try:
            plugin_fd = os.open(
                raw_path.name,
                self._open_flags() | os.O_DIRECTORY,
                dir_fd=root_fd,
            )

            if not stat.S_ISDIR(os.fstat(plugin_fd).st_mode):
                raise ValueError("Plugin path is not a directory")

            manifest = self._read_manifest_fd(
                plugin_fd, raw_path.name
            )

            try:
                source_fd = self._open_regular_file(
                    "plugin.py", plugin_fd
                )
            except OSError as exc:
                if exc.errno == errno.ELOOP:
                    raise ValueError(
                        "Symlinked plugin files are not allowed"
                    ) from exc
                raise

            source = self._read_fd(source_fd, MAX_PLUGIN_SOURCE_SIZE).decode("utf-8")

            module = ModuleType(module_name)
            module.__file__ = str(
                self.plugins_dir / raw_path.name / "plugin.py"
            )
            module.__package__ = ""
            module.__loader__ = None
            module.__spec__ = importlib.machinery.ModuleSpec(
                module_name, loader=None, origin=module.__file__
            )

            sys.modules[module_name] = module

            code = compile(source, module.__file__, "exec")
            exec(code, module.__dict__)

            cls = getattr(module, "Plugin", None)
            if not isinstance(cls, type) or not issubclass(
                cls, BasePlugin
            ):
                raise TypeError(
                    f"{raw_path.name}/plugin.py must define Plugin(BasePlugin)"
                )

            plugin = cls()
            raw_metadata = plugin.get_metadata()

            if not isinstance(raw_metadata, dict) or not plugin.validate():
                raise ValueError(
                    f"Plugin validation failed: {raw_path.name}"
                )

            metadata = dict(raw_metadata)
            manifest_name = manifest.get("name", raw_path.name)
            manifest_version = manifest.get("version", "0.0.0")
            plugin_name = metadata.get("name", manifest_name)
            plugin_version = metadata.get("version", manifest_version)

            if (
                plugin_name != manifest_name
                or plugin_version != manifest_version
            ):
                raise ValueError(
                    f"Plugin metadata does not match manifest: {raw_path.name}"
                )

            metadata["name"] = manifest_name
            metadata["version"] = manifest_version
            self.metadata[raw_path.name] = metadata
            return plugin

        except Exception:
            sys.modules.pop(module_name, None)
            raise
        finally:
            self._close_fds(source_fd, plugin_fd, root_fd)

import os
import stat

import pytest

import plugins.file_audit.plugin as audit_module
from core.plugin_loader import PluginLoader


@pytest.fixture
def plugin():
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    return PluginLoader(root / "plugins").load_all()["file_audit"]


def test_rejects_invalid_target_types(plugin, tmp_path):
    for target in (None, 123, [], ""):
        with pytest.raises(ValueError):
            plugin.run(target)


@pytest.mark.parametrize("value", [True, "10", 1.5, None])
def test_rejects_non_integer_max_entries(plugin, tmp_path, value):
    with pytest.raises(ValueError, match="max_entries must be an integer"):
        plugin.run(tmp_path, max_entries=value)


@pytest.mark.parametrize("value", [True, "2", 1.5, None])
def test_rejects_non_integer_max_depth(plugin, tmp_path, value):
    with pytest.raises(ValueError, match="max_depth must be an integer"):
        plugin.run(tmp_path, max_depth=value)


def test_rejects_existing_file_as_target(plugin, tmp_path):
    target = tmp_path / "regular-file"
    target.write_text("data")

    with pytest.raises(ValueError, match="existing directory"):
        plugin.run(target)


def test_rejects_platform_without_required_directory_flag(
    plugin, tmp_path, monkeypatch
):
    monkeypatch.delattr(audit_module.os, "O_NOFOLLOW")

    with pytest.raises(RuntimeError, match="safe directory-relative"):
        plugin.run(tmp_path)


@pytest.mark.parametrize(
    "flag_name",
    ["_SUPPORTS_OPEN_DIR_FD", "_SUPPORTS_STAT_DIR_FD"],
)
def test_rejects_platform_without_dir_fd_operation(
    plugin, tmp_path, monkeypatch, flag_name
):
    monkeypatch.setitem(plugin.run.__globals__, flag_name, False)

    with pytest.raises(RuntimeError, match="safe directory-relative"):
        plugin.run(tmp_path)


def test_root_open_error_becomes_value_error(plugin, tmp_path, monkeypatch):
    real_open = os.open

    def failing_open(path, flags, *args, **kwargs):
        if str(path) == str(tmp_path):
            raise PermissionError("root access denied")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(audit_module.os, "open", failing_open)

    with pytest.raises(ValueError, match="accessed safely"):
        plugin.run(tmp_path)


def test_entry_stat_error_is_counted(plugin, tmp_path, monkeypatch):
    (tmp_path / "item.txt").write_text("data")
    real_stat = os.stat

    def failing_stat(path, *args, **kwargs):
        if path == "item.txt" and kwargs.get("dir_fd") is not None:
            raise PermissionError("entry stat denied")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(audit_module.os, "stat", failing_stat)

    report = plugin.run(tmp_path)

    assert report["scanned_entries"] == 1
    assert report["errors"] == 1
    assert report["findings_count"] == 0


def test_ignores_non_regular_non_directory_entries(plugin, tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO creation is unavailable")

    fifo = tmp_path / "pipe"
    try:
        os.mkfifo(fifo)
    except (OSError, NotImplementedError):
        pytest.skip("FIFO creation is unavailable on this platform")

    report = plugin.run(tmp_path)

    assert report["scanned_entries"] == 1
    assert report["findings_count"] == 0
    assert report["errors"] == 0


def test_child_open_error_counts_as_error(plugin, tmp_path, monkeypatch):
    root = tmp_path / "root"
    (root / "child").mkdir(parents=True)

    real_open = os.open

    def failing_child_open(path, flags, *args, **kwargs):
        if path == "child" and kwargs.get("dir_fd") is not None:
            raise PermissionError("child open denied")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(audit_module.os, "open", failing_child_open)

    report = plugin.run(root, recursive=True)

    assert report["errors"] == 1
    assert report["scanned_entries"] == 1


def test_child_open_error_followed_by_stat_error(plugin, tmp_path, monkeypatch):
    root = tmp_path / "root"
    (root / "child").mkdir(parents=True)

    real_open = os.open
    real_stat = os.stat
    child_stat_calls = 0

    def failing_child_open(path, flags, *args, **kwargs):
        if path == "child" and kwargs.get("dir_fd") is not None:
            raise PermissionError("child open denied")
        return real_open(path, flags, *args, **kwargs)

    def failing_latest_stat(path, *args, **kwargs):
        nonlocal child_stat_calls
        if path == "child" and kwargs.get("dir_fd") is not None:
            child_stat_calls += 1
            if child_stat_calls == 2:
                raise PermissionError("latest stat denied")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(audit_module.os, "open", failing_child_open)
    monkeypatch.setattr(audit_module.os, "stat", failing_latest_stat)

    report = plugin.run(root, recursive=True)

    assert child_stat_calls == 2
    assert report["errors"] == 1


def test_child_descriptor_closed_when_fstat_fails(
    plugin, tmp_path, monkeypatch
):
    root = tmp_path / "root"
    (root / "child").mkdir(parents=True)

    real_open = os.open
    real_fstat = os.fstat
    child_fds = []

    def tracking_open(path, flags, *args, **kwargs):
        fd = real_open(path, flags, *args, **kwargs)
        if path == "child" and kwargs.get("dir_fd") is not None:
            child_fds.append(fd)
        return fd

    def failing_child_fstat(fd):
        if fd in child_fds:
            raise OSError("simulated fstat failure")
        return real_fstat(fd)

    monkeypatch.setattr(audit_module.os, "open", tracking_open)
    monkeypatch.setattr(audit_module.os, "fstat", failing_child_fstat)

    report = plugin.run(root, recursive=True)

    assert len(child_fds) == 1
    assert report["errors"] == 1

    with pytest.raises(OSError):
        real_fstat(child_fds[0])

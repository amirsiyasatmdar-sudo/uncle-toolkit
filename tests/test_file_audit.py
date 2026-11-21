from __future__ import annotations

import json
import os
from pathlib import Path
import pytest

from core.plugin_loader import PluginLoader


@pytest.fixture()
def plugin(tmp_path: Path):
    source_root = Path(__file__).resolve().parents[1]
    plugins_dir = source_root / "plugins"
    loaded = PluginLoader(plugins_dir).load_all()
    return loaded["file_audit"]


def test_manifest_and_loader_contract(plugin):
    metadata = plugin.get_metadata()
    assert metadata["name"] == "file_audit"
    assert metadata["version"] == "1.0.0"
    assert plugin.validate() is True


def test_reports_world_writable_file_and_sensitive_readable_file(plugin, tmp_path):
    public_write = tmp_path / "shared.txt"
    public_write.write_text("not read by the plugin", encoding="utf-8")
    public_write.chmod(0o666)

    secret = tmp_path / ".env"
    secret.write_text("SECRET=do-not-read", encoding="utf-8")
    secret.chmod(0o644)

    report = plugin.run(tmp_path)
    codes = {item["code"] for item in report["findings"]}

    assert report["read_only"] is True
    assert report["scanned_entries"] == 2
    assert report["findings_count"] == 2
    assert codes == {"world_writable", "sensitive_world_readable"}
    assert "SECRET=do-not-read" not in json.dumps(report)


def test_does_not_follow_symlinks(plugin, tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    secret = outside / ".env"
    secret.write_text("PRIVATE", encoding="utf-8")
    secret.chmod(0o644)
    link = tmp_path / "outside-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symbolic links are unavailable on this platform")

    report = plugin.run(tmp_path, recursive=True)
    assert report["skipped_symlinks"] == 1
    assert report["findings_count"] == 0
    assert str(secret) not in json.dumps(report)


def test_rejects_invalid_targets_and_limits(plugin, tmp_path):
    with pytest.raises(ValueError):
        plugin.run(tmp_path / "missing")
    with pytest.raises(ValueError):
        plugin.run(tmp_path, max_entries=0)
    with pytest.raises(ValueError):
        plugin.run(tmp_path, max_depth=9)
    with pytest.raises(ValueError):
        plugin.run(tmp_path, recursive="yes")


def test_entry_limit_marks_report_truncated(plugin, tmp_path):
    for index in range(5):
        (tmp_path / f"file-{index}.txt").write_text("x", encoding="utf-8")

    report = plugin.run(tmp_path, max_entries=2)
    assert report["scanned_entries"] == 2
    assert report["truncated"] is True


def test_rejects_symlink_as_scan_root(plugin, tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(real_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symbolic links are unavailable on this platform")
    with pytest.raises(ValueError):
        plugin.run(link)


def test_rejects_directory_replaced_by_symlink_during_traversal(
    plugin, tmp_path, monkeypatch
):
    import plugins.file_audit.plugin as file_audit_module

    root = tmp_path / "root"
    child = root / "child"
    outside = tmp_path / "outside"
    child.mkdir(parents=True)
    outside.mkdir()
    secret = outside / ".env"
    secret.write_text("OUTSIDE_SECRET", encoding="utf-8")
    secret.chmod(0o644)

    real_open = os.open
    replaced = False

    def swap_then_open(path, flags, *args, **kwargs):
        nonlocal replaced
        if path == "child" and kwargs.get("dir_fd") is not None and not replaced:
            replaced = True
            child.rename(root / "child-original")
            child.symlink_to(outside, target_is_directory=True)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(file_audit_module.os, "open", swap_then_open)
    report = plugin.run(root, recursive=True)

    assert replaced is True
    assert report["skipped_symlinks"] == 1
    assert report["findings_count"] == 0
    assert "OUTSIDE_SECRET" not in json.dumps(report)


def test_closes_queued_directory_descriptors_when_scan_is_truncated(
    plugin, tmp_path, monkeypatch
):
    import plugins.file_audit.plugin as file_audit_module

    root = tmp_path / "root"
    root.mkdir()

    for name in ("child-a", "child-b", "child-c"):
        (root / name).mkdir()

    real_open = os.open
    child_fds = []

    def tracking_open(path, flags, *args, **kwargs):
        fd = real_open(path, flags, *args, **kwargs)
        if kwargs.get("dir_fd") is not None:
            child_fds.append(fd)
        return fd

    monkeypatch.setattr(file_audit_module.os, "open", tracking_open)

    report = plugin.run(root, recursive=True, max_entries=2)

    assert report["truncated"] is True
    assert report["scanned_entries"] == 2
    assert len(child_fds) == 2

    for fd in child_fds:
        with pytest.raises(OSError):
            os.fstat(fd)


def test_closes_child_descriptor_when_directory_scan_fails(
    plugin, tmp_path, monkeypatch
):
    import plugins.file_audit.plugin as file_audit_module

    root = tmp_path / "root"
    child = root / "child"
    child.mkdir(parents=True)

    real_scandir = os.scandir
    real_open = os.open
    child_fds = []

    def tracking_open(path, flags, *args, **kwargs):
        fd = real_open(path, flags, *args, **kwargs)
        if kwargs.get("dir_fd") is not None:
            child_fds.append(fd)
        return fd

    def failing_scandir(path):
        if isinstance(path, int) and path in child_fds:
            raise OSError("simulated directory scan failure")
        return real_scandir(path)

    monkeypatch.setattr(file_audit_module.os, "open", tracking_open)
    monkeypatch.setattr(file_audit_module.os, "scandir", failing_scandir)

    report = plugin.run(root, recursive=True)

    assert len(child_fds) == 1
    assert report["errors"] >= 1

    with pytest.raises(OSError):
        os.fstat(child_fds[0])


def test_closes_remaining_descriptors_when_close_reports_error(
    plugin, tmp_path, monkeypatch
):
    import plugins.file_audit.plugin as file_audit_module

    root = tmp_path / "root"
    root.mkdir()

    for name in ("child-a", "child-b"):
        (root / name).mkdir()

    real_open = os.open
    real_close = os.close
    real_scandir = os.scandir
    real_fstat = os.fstat

    child_fds = []
    root_fds = []
    failed_once = False

    def tracking_open(path, flags, *args, **kwargs):
        fd = real_open(path, flags, *args, **kwargs)
        if kwargs.get("dir_fd") is not None:
            child_fds.append(fd)
        else:
            root_fds.append(fd)
        return fd

    def failing_scandir(path):
        if isinstance(path, int) and path in child_fds:
            raise OSError("simulated scandir failure")
        return real_scandir(path)

    def close_then_raise(fd):
        nonlocal failed_once
        real_close(fd)

        if fd in child_fds and not failed_once:
            failed_once = True
            raise OSError("simulated close error")

    monkeypatch.setattr(file_audit_module.os, "open", tracking_open)
    monkeypatch.setattr(file_audit_module.os, "scandir", failing_scandir)
    monkeypatch.setattr(file_audit_module.os, "close", close_then_raise)

    report = plugin.run(root, recursive=True)

    assert failed_once is True
    assert len(child_fds) == 2
    assert report["errors"] >= 1

    for fd in root_fds + child_fds:
        with pytest.raises(OSError):
            real_fstat(fd)


def test_inode_mismatch_and_close_error_count_as_two_independent_errors(
    plugin, tmp_path, monkeypatch
):
    import plugins.file_audit.plugin as file_audit_module

    root = tmp_path / "root"
    (root / "child").mkdir(parents=True)

    real_open = os.open
    real_close = os.close
    real_fstat = os.fstat
    child_fds = []

    def tracking_open(path, flags, *args, **kwargs):
        fd = real_open(path, flags, *args, **kwargs)
        if kwargs.get("dir_fd") is not None:
            child_fds.append(fd)
        return fd

    def mismatching_fstat(fd):
        result = real_fstat(fd)
        if fd in child_fds:
            values = list(result)
            values[1] += 1
            return os.stat_result(values)
        return result

    failed_close = False

    def close_then_raise(fd):
        nonlocal failed_close
        real_close(fd)
        if fd in child_fds and not failed_close:
            failed_close = True
            raise OSError("simulated close error")

    monkeypatch.setattr(file_audit_module.os, "open", tracking_open)
    monkeypatch.setattr(file_audit_module.os, "fstat", mismatching_fstat)
    monkeypatch.setattr(file_audit_module.os, "close", close_then_raise)

    report = plugin.run(root, recursive=True)

    assert len(child_fds) == 1
    assert failed_close is True
    assert report["errors"] == 2

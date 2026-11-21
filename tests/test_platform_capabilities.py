import errno
import os
import stat

import pytest


def test_required_os_flags_exist():
    assert hasattr(os, "O_NOFOLLOW")
    assert hasattr(os, "O_DIRECTORY")
    assert hasattr(os, "O_CLOEXEC")


def test_dir_fd_support():
    assert os.open in os.supports_dir_fd
    assert os.stat in os.supports_dir_fd


def test_open_file_using_dir_fd(tmp_path):
    (tmp_path / "sample.txt").write_text(
        "uncle-toolkit", encoding="utf-8"
    )

    directory_fd = os.open(
        tmp_path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )

    try:
        file_fd = os.open(
            "sample.txt",
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=directory_fd,
        )

        try:
            assert stat.S_ISREG(os.fstat(file_fd).st_mode)
        finally:
            os.close(file_fd)
    finally:
        os.close(directory_fd)


def test_o_nofollow_rejects_symlink(tmp_path):
    target = tmp_path / "target.txt"
    link = tmp_path / "link.txt"

    target.write_text("test", encoding="utf-8")
    link.symlink_to(target)

    directory_fd = os.open(
        tmp_path,
        os.O_RDONLY | os.O_DIRECTORY,
    )

    try:
        with pytest.raises(OSError) as exc:
            os.open(
                "link.txt",
                os.O_RDONLY | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )

        assert exc.value.errno in (errno.ELOOP, errno.EMLINK)
    finally:
        os.close(directory_fd)


def test_o_directory_accepts_directory(tmp_path):
    directory_fd = os.open(
        tmp_path,
        os.O_RDONLY | os.O_DIRECTORY,
    )

    try:
        assert stat.S_ISDIR(os.fstat(directory_fd).st_mode)
    finally:
        os.close(directory_fd)


def test_stat_without_following_symlink(tmp_path):
    target = tmp_path / "target.txt"
    link = tmp_path / "link.txt"

    target.write_text("test", encoding="utf-8")
    link.symlink_to(target)

    directory_fd = os.open(
        tmp_path,
        os.O_RDONLY | os.O_DIRECTORY,
    )

    try:
        info = os.stat(
            "link.txt",
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
        assert stat.S_ISLNK(info.st_mode)
    finally:
        os.close(directory_fd)

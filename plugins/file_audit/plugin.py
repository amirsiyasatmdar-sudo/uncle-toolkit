"""Read-only audit of local filesystem permissions.

The plugin inspects metadata only. It never reads, changes, creates, or deletes
user files, and it does not follow symbolic links.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

from core.plugin_loader import BasePlugin

_SENSITIVE_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "credentials",
    "credentials.json",
    "secrets.json",
    "token",
    "tokens.json",
}
_SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
_SUPPORTS_OPEN_DIR_FD = os.open in os.supports_dir_fd
_SUPPORTS_STAT_DIR_FD = os.stat in os.supports_dir_fd


class Plugin(BasePlugin):
    """Inspect a directory and report potentially unsafe permission bits."""

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": "file_audit",
            "version": "1.0.0",
            "description": "Read-only audit of local file and directory permissions",
        }

    def validate(self) -> bool:
        return True

    def run(
        self,
        target: str | Path,
        *,
        recursive: bool = False,
        max_entries: int = 1000,
        max_depth: int = 8,
    ) -> dict[str, Any]:
        """Audit a local directory without following symlinks or reading contents.

        Args:
            target: Existing local directory to inspect.
            recursive: Whether to inspect child directories.
            max_entries: Maximum filesystem entries inspected (1..10000).
            max_depth: Maximum recursion depth when recursive is enabled (0..8).

        Returns:
            A JSON-serializable report containing findings and scan counters.
        """
        if not isinstance(target, (str, Path)) or not str(target).strip():
            raise ValueError("target must be a non-empty local directory path")
        if not isinstance(recursive, bool):
            raise ValueError("recursive must be a boolean")
        if isinstance(max_entries, bool) or not isinstance(max_entries, int):
            raise ValueError("max_entries must be an integer")
        if not 1 <= max_entries <= 10000:
            raise ValueError("max_entries must be between 1 and 10000")
        if isinstance(max_depth, bool) or not isinstance(max_depth, int):
            raise ValueError("max_depth must be an integer")
        if not 0 <= max_depth <= 8:
            raise ValueError("max_depth must be between 0 and 8")

        supplied_path = Path(target).expanduser()
        if supplied_path.is_symlink():
            raise ValueError("target directory must not be a symbolic link")
        try:
            root = supplied_path.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ValueError("target directory cannot be accessed") from exc
        if not root.is_dir():
            raise ValueError("target must be an existing directory")

        # Traverse using directory file descriptors. Every child is opened
        # relative to its already-open parent with O_NOFOLLOW, so replacing a
        # directory entry with a symlink between enumeration and descent does
        # not redirect the scan outside the selected tree.
        required_flags = ("O_DIRECTORY", "O_NOFOLLOW")
        if any(not hasattr(os, flag) for flag in required_flags) or not hasattr(
            os, "supports_dir_fd"
        ):
            raise RuntimeError(
                "This platform lacks safe directory-relative file operations"
            )
        if not (_SUPPORTS_OPEN_DIR_FD and _SUPPORTS_STAT_DIR_FD):
            raise RuntimeError(
                "This platform lacks safe directory-relative file operations"
            )

        findings: list[dict[str, str]] = []
        scanned_entries = 0
        skipped_symlinks = 0
        errors = 0
        truncated = False
        # (directory fd, display path, depth); each fd is owned by this scan.
        pending: list[tuple[int, Path, int]] = []
        root_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        try:
            root_fd = os.open(root, root_flags)
        except OSError as exc:
            raise ValueError("target directory cannot be accessed safely") from exc
        pending.append((root_fd, root, 0))

        def close_directory_fd(fd):
            nonlocal errors
            try:
                os.close(fd)
            except OSError:
                # Do not retry: the descriptor state may be ambiguous.
                errors += 1

        try:
            while pending:
                current_fd, current_path, depth = pending.pop()
                try:
                    with os.scandir(current_fd) as entries:
                        for entry in entries:
                            if scanned_entries >= max_entries:
                                truncated = True
                                break
                            scanned_entries += 1
                            name = entry.name
                            display_path = current_path / name

                            try:
                                info = os.stat(
                                    name, dir_fd=current_fd, follow_symlinks=False
                                )
                            except OSError:
                                errors += 1
                                continue

                            mode = info.st_mode
                            if stat.S_ISLNK(mode):
                                skipped_symlinks += 1
                                continue
                            is_directory = stat.S_ISDIR(mode)
                            is_regular_file = stat.S_ISREG(mode)
                            if not (is_directory or is_regular_file):
                                continue

                            permissions = stat.S_IMODE(mode)
                            name_lower = name.lower()
                            sensitive = (
                                name_lower in _SENSITIVE_NAMES
                                or Path(name_lower).suffix in _SENSITIVE_SUFFIXES
                            )

                            if permissions & stat.S_IWOTH:
                                if not (is_directory and permissions & stat.S_ISVTX):
                                    findings.append(
                                        {
                                            "code": "world_writable",
                                            "severity": "high",
                                            "path": str(display_path),
                                            "permissions": format(permissions, "04o"),
                                            "message": "Entry is writable by all local users.",
                                        }
                                    )

                            if (
                                is_regular_file
                                and sensitive
                                and permissions & stat.S_IROTH
                            ):
                                findings.append(
                                    {
                                        "code": "sensitive_world_readable",
                                        "severity": "high",
                                        "path": str(display_path),
                                        "permissions": format(permissions, "04o"),
                                        "message": "Potentially sensitive file is readable by all local users.",
                                    }
                                )

                            if recursive and is_directory and depth < max_depth:
                                child_fd = None
                                try:
                                    child_flags = (
                                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                                    )
                                    child_fd = os.open(
                                        name, child_flags, dir_fd=current_fd
                                    )
                                    child_info = os.fstat(child_fd)
                                    # Confirm the opened object is the same directory
                                    # observed by the no-follow stat above.
                                    if (child_info.st_dev, child_info.st_ino) != (
                                        info.st_dev,
                                        info.st_ino,
                                    ):
                                        close_directory_fd(child_fd)
                                        child_fd = None
                                        errors += 1
                                        continue
                                    pending.append((child_fd, display_path, depth + 1))
                                except OSError:
                                    if child_fd is not None:
                                        close_directory_fd(child_fd)
                                    # A replacement symlink is safely rejected by
                                    # O_NOFOLLOW; count it as skipped when detectable.
                                    try:
                                        latest = os.stat(
                                            name,
                                            dir_fd=current_fd,
                                            follow_symlinks=False,
                                        )
                                        if stat.S_ISLNK(latest.st_mode):
                                            skipped_symlinks += 1
                                        else:
                                            errors += 1
                                    except OSError:
                                        errors += 1
                except OSError:
                    errors += 1
                finally:
                    close_directory_fd(current_fd)
                if truncated:
                    break
        finally:
            # Close queued directory descriptors if the entry limit or an
            # unexpected exception leaves work unprocessed.
            for queued_fd, _queued_path, _queued_depth in pending:
                close_directory_fd(queued_fd)

        return {
            "plugin": "file_audit",
            "target": str(root),
            "recursive": recursive,
            "scanned_entries": scanned_entries,
            "skipped_symlinks": skipped_symlinks,
            "errors": errors,
            "truncated": truncated,
            "findings_count": len(findings),
            "findings": findings,
            "read_only": True,
        }

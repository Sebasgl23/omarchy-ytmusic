"""Private, crash-resistant file persistence helpers."""

import json
import os
import shutil
import tempfile
from typing import Any


def migrate_private_file(legacy_path: str, target_path: str) -> None:
    """
    Move a legacy private file into its new location once.

    Credentials used to live in the plugin directory, which the Omarchy shell
    watches and reloads on any change; token refreshes there restarted the
    shell. Relocate an existing file so users keep their login.
    """
    if os.path.exists(target_path) or not os.path.exists(legacy_path):
        return
    directory = os.path.dirname(target_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    try:
        os.replace(legacy_path, target_path)
    except OSError:
        shutil.move(legacy_path, target_path)
    try:
        os.chmod(target_path, 0o600)
    except OSError:
        pass



def atomic_write_private_json(path: str, data: Any) -> None:
    directory = os.path.dirname(path) or "."
    prefix = f".{os.path.basename(path)}."
    fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=directory)
    try:
        os.chmod(temp_path, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output_file:
            json.dump(data, output_file, indent=2)
            output_file.flush()
            os.fsync(output_file.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            os.remove(temp_path)
        except FileNotFoundError:
            pass

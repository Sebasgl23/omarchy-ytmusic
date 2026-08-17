"""Private, crash-resistant file persistence helpers."""

import json
import os
import tempfile
from typing import Any


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

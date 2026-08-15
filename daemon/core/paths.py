"""Runtime paths configuration isolated to user runtime directory."""

import os
from pathlib import Path


def get_runtime_dir() -> Path:
    """
    Return secure, user-isolated runtime directory following XDG Base Directory Specification.
    Defaults to $XDG_RUNTIME_DIR/omarchy-ytmusic or ~/.local/state/omarchy-ytmusic/run
    with 0700 permissions.
    """
    xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
    if xdg_runtime and os.path.isdir(xdg_runtime):
        base = Path(xdg_runtime) / "omarchy-ytmusic"
    else:
        xdg_state = os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
        base = Path(xdg_state) / "omarchy-ytmusic" / "run"

    base.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(base, 0o700)
    except Exception:
        pass
    return base


RUNTIME_DIR = get_runtime_dir()
SOCKET_PATH = str(RUNTIME_DIR / "daemon.sock")
MPV_SOCKET_PATH = str(RUNTIME_DIR / "mpv.sock")
PID_FILE = str(RUNTIME_DIR / "daemon.pid")
LOG_FILE = str(RUNTIME_DIR / "daemon.log")

"""Runtime paths configuration isolated to user runtime directory."""

import os
from pathlib import Path


def _secure(path: Path) -> Path:
    """Create a private (0700) directory and return it."""
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except Exception:
        pass
    return path


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
        base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))) / "omarchy-ytmusic" / "run"
    return _secure(base)


def get_state_dir() -> Path:
    """
    Return the persistent state directory (~/.local/state/omarchy-ytmusic).

    Unlike RUNTIME_DIR, this survives reboots, so mutable credentials belong here
    rather than in the plugin tree (which the Omarchy shell watches and reloads on
    any change) or in tmpfs.
    """
    base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))) / "omarchy-ytmusic"
    return _secure(base)


RUNTIME_DIR = get_runtime_dir()
STATE_DIR = get_state_dir()
SOCKET_PATH = str(RUNTIME_DIR / "daemon.sock")
MPV_SOCKET_PATH = str(RUNTIME_DIR / "mpv.sock")
PID_FILE = str(RUNTIME_DIR / "daemon.pid")
START_LOCK_FILE = str(RUNTIME_DIR / "daemon-start.lock")
LOG_FILE = str(RUNTIME_DIR / "daemon.log")
COOKIE_FILE = str(RUNTIME_DIR / "cookies.txt")
AUTH_FILE = str(STATE_DIR / "auth.json")

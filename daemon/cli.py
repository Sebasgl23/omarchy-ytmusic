"""CLI commands handler for Omarchy YouTube Music with smart header parsing."""

import ctypes
import fcntl
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time

# Ensure daemon directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.paths import SOCKET_PATH, PID_FILE, START_LOCK_FILE, LOG_FILE, COOKIE_FILE
from core.files import atomic_write_private_json


def _request_ipc(command: str, args: dict = None, timeout: float = 15.0) -> dict:
    args = args or {}
    req = {"command": command, "args": args, "id": 1}
    payload = (json.dumps(req) + "\n").encode("utf-8")

    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(SOCKET_PATH)
        s.sendall(payload)
        
        buffer = b""
        while True:
            chunk = s.recv(8192)
            if not chunk:
                break
            buffer += chunk
            if b"\n" in chunk:
                break
        s.close()
        return json.loads(buffer.decode("utf-8").strip())
    except Exception as ex:
        return {"status": "error", "error": str(ex)}


def _socket_is_ready(timeout: float = 0.5) -> bool:
    if not os.path.exists(SOCKET_PATH):
        return False
    response = _request_ipc("ping", timeout=timeout)
    return response.get("status") == "ok" and response.get("data", {}).get("pong") is True


def send_ipc(command: str, args: dict = None, timeout: float = 15.0) -> dict:
    if not is_running() or not _socket_is_ready():
        if not start_daemon(silent=True):
            return {"status": "error", "error": "Daemon failed to start"}

    return _request_ipc(command, args=args, timeout=timeout)


def is_ytmusic_daemon_process(pid: int) -> bool:
    """Verify that the given PID exists and genuinely belongs to this YouTube Music daemon instance."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError, PermissionError):
        return False

    # Inspect /proc/<pid>/cmdline on Linux to guarantee process ownership
    cmdline_path = f"/proc/{pid}/cmdline"
    if not os.path.exists(cmdline_path):
        # Fail-closed: cannot verify process identity without /proc/<pid>/cmdline
        return False

    try:
        with open(cmdline_path, "rb") as f:
            raw_cmdline = f.read()

        # In Linux /proc/<pid>/cmdline, arguments are separated by null bytes (\x00)
        args = [arg.decode("utf-8", errors="ignore") for arg in raw_cmdline.split(b"\x00") if arg]
        if not args:
            return False

        # 1. Ensure the executing binary is Python
        exe_name = os.path.basename(os.path.realpath(args[0])).lower()
        if not exe_name.startswith("python"):
            return False

        # 2. Find the script argument passed to Python (first non-flag argument after python executable)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        expected_main = os.path.realpath(os.path.join(current_dir, "main.py"))

        script_arg = None
        i = 1
        while i < len(args):
            arg = args[i]
            if arg in ("-c", "-m"):
                # Running a raw command string or module, not our script file
                return False
            if arg in ("-W", "-X", "--check-hash-based-pycs"):
                i += 2
                continue
            if arg.startswith("-"):
                i += 1
                continue
            script_arg = arg
            break

        if not script_arg:
            return False

        return os.path.realpath(script_arg) == expected_main
    except (OSError, PermissionError):
        # Fail-closed if unable to read process details
        return False


def is_running() -> bool:
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                content = f.read().strip()
                if not content:
                    os.remove(PID_FILE)
                    return False
                pid = int(content)

            if is_ytmusic_daemon_process(pid):
                return True
            else:
                # Stale PID detected (process terminated or PID reused by another process)
                try:
                    os.remove(PID_FILE)
                except OSError:
                    pass
                if os.path.exists(SOCKET_PATH):
                    try:
                        os.remove(SOCKET_PATH)
                    except OSError:
                        pass
                return False
        except Exception:
            return False
    return False


def _pidfd_open(pid: int) -> int:
    libc = ctypes.CDLL(None, use_errno=True)
    pidfd_open = libc.pidfd_open
    pidfd_open.argtypes = [ctypes.c_int, ctypes.c_uint]
    pidfd_open.restype = ctypes.c_int
    pid_fd = pidfd_open(pid, 0)
    if pid_fd == -1:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))
    return pid_fd


def _pidfd_send_signal(pid_fd: int, signal_number: int) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    pidfd_send_signal = libc.pidfd_send_signal
    pidfd_send_signal.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_uint,
    ]
    pidfd_send_signal.restype = ctypes.c_int
    if pidfd_send_signal(pid_fd, signal_number, None, 0) == -1:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))


def terminate_verified_daemon(pid: int) -> bool:
    """Signal the verified process identity without a PID-reuse race."""
    if pid <= 0:
        return False

    try:
        pid_fd = _pidfd_open(pid)
    except (AttributeError, OSError):
        return False

    try:
        if not is_ytmusic_daemon_process(pid):
            return False
        _pidfd_send_signal(pid_fd, signal.SIGTERM)
        return True
    except (AttributeError, OSError):
        return False
    finally:
        os.close(pid_fd)


def _write_pid_file(pid: int) -> None:
    temp_pid_file = f"{PID_FILE}.{os.getpid()}.tmp"
    fd = os.open(temp_pid_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as pid_file:
            pid_file.write(str(pid))
        os.replace(temp_pid_file, PID_FILE)
        os.chmod(PID_FILE, 0o600)
    finally:
        if os.path.exists(temp_pid_file):
            os.remove(temp_pid_file)


def _clean_failed_start(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)

    try:
        with open(PID_FILE, "r") as pid_file:
            recorded_pid = int(pid_file.read().strip())
    except (OSError, ValueError):
        recorded_pid = None

    if recorded_pid == proc.pid:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass


def _start_daemon_locked(silent: bool = False) -> bool:
    if is_running() and _socket_is_ready():
        if not silent:
            print("Daemon is already running.")
        return True

    if os.path.exists(SOCKET_PATH):
        try:
            os.remove(SOCKET_PATH)
        except OSError:
            if not silent:
                print(f"Cannot remove stale daemon socket: {SOCKET_PATH}")
            return False

    daemon_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = sys.executable
    main_py = os.path.join(daemon_dir, "main.py")

    if not silent:
        print("Starting Omarchy YouTube Music Daemon in background...")
    with open(LOG_FILE, "a") as log_f:
        try:
            os.chmod(LOG_FILE, 0o600)
        except Exception:
            pass
        proc = subprocess.Popen(
            [venv_python, main_py],
            stdin=subprocess.DEVNULL,
            stdout=log_f,
            stderr=log_f,
            start_new_session=True,
        )
    _write_pid_file(proc.pid)

    for _ in range(30):
        if is_ytmusic_daemon_process(proc.pid) and _socket_is_ready():
            if not silent:
                print(f"Daemon started successfully (PID {proc.pid}).")
            return True
        if proc.poll() is not None:
            _clean_failed_start(proc)
            if not silent:
                print(f"Daemon failed to start. Check {LOG_FILE}")
            return False
        time.sleep(0.1)

    _clean_failed_start(proc)
    if not silent:
        print(f"Daemon failed to create its socket. Check {LOG_FILE}")
    return False


def start_daemon(silent: bool = False) -> bool:
    lock_fd = os.open(START_LOCK_FILE, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(lock_fd, "r+") as lock_file:
        os.chmod(START_LOCK_FILE, 0o600)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            return _start_daemon_locked(silent=silent)
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _remove_runtime_file(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _stop_daemon_locked() -> bool:
    if not os.path.exists(PID_FILE):
        _remove_runtime_file(SOCKET_PATH)
        print("Daemon is not running.")
        return True

    try:
        with open(PID_FILE, "r", encoding="utf-8") as pid_file:
            pid = int(pid_file.read().strip())
    except (OSError, ValueError):
        _remove_runtime_file(PID_FILE)
        _remove_runtime_file(SOCKET_PATH)
        print("Removed invalid daemon runtime files.")
        return True

    if not is_ytmusic_daemon_process(pid):
        _remove_runtime_file(PID_FILE)
        _remove_runtime_file(SOCKET_PATH)
        print(f"Stored PID ({pid}) is stale. Cleaned up safely.")
        return True

    print(f"Stopping daemon (PID {pid})...")
    if _socket_is_ready():
        _request_ipc("shutdown", timeout=2.0)
        for _ in range(20):
            if not is_ytmusic_daemon_process(pid):
                break
            time.sleep(0.1)

    if is_ytmusic_daemon_process(pid):
        terminate_verified_daemon(pid)
        for _ in range(20):
            if not is_ytmusic_daemon_process(pid):
                break
            time.sleep(0.1)

    if is_ytmusic_daemon_process(pid):
        print(f"Failed to stop daemon (PID {pid}); runtime files were preserved.")
        return False

    _remove_runtime_file(PID_FILE)
    _remove_runtime_file(SOCKET_PATH)
    print("Stopped.")
    return True


def stop_daemon() -> bool:
    lock_fd = os.open(START_LOCK_FILE, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(lock_fd, "r+") as lock_file:
        os.chmod(START_LOCK_FILE, 0o600)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            return _stop_daemon_locked()
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def setup_auth():
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    auth_file = os.path.join(plugin_dir, "auth.json")
    daemon_dir = os.path.dirname(os.path.abspath(__file__))
    ytmusicapi_bin = os.path.join(daemon_dir, "venv", "bin", "ytmusicapi")

    print("=" * 64)
    print("      Omarchy YouTube Music - Account Authentication Setup      ")
    print("=" * 64)
    print("1. Google OAuth (Permanent & Automatic token refresh)")
    print("2. Reset to Anonymous Mode (Clear credentials)")
    print("=" * 64)
    choice = input("Select an option [1-2]: ").strip()

    if choice == "1":
        print("\n" + "=" * 64)
        print("                   GOOGLE OAUTH SETUP (PERMANENT)                ")
        print("=" * 64)
        print("Tip: If you haven't created a Google OAuth client yet, create one in")
        print("Google Cloud Console (YouTube Data API v3 enabled, TV/Device app type).")
        print("=" * 64 + "\n")
        client_id = input("Enter your Google Client ID: ").strip()
        client_secret = input("Enter your Google Client Secret: ").strip()
        
        try:
            from ytmusicapi.auth.oauth import OAuthCredentials
            
            oauth_handler = OAuthCredentials(client_id=client_id, client_secret=client_secret)
            code_data = oauth_handler.get_code()
            
            verification_url = code_data.get("verification_url", "https://www.google.com/device")
            user_code = code_data.get("user_code", "")
            device_code = code_data.get("device_code", "")
            
            print("\n" + "=" * 64)
            print(f" 1. Open in your browser:  \033[1;34m{verification_url}\033[0m")
            print(f" 2. Enter this code:       \033[1;32m{user_code}\033[0m")
            print(f" 3. Click 'Allow' / 'Accept' on your Google account.")
            print("=" * 64)
            input("\nPress [ENTER] once you have approved the access in your browser...")
            
            token_data = oauth_handler.token_from_code(device_code)
            
            if token_data and "access_token" in token_data and "refresh_token" in token_data:
                token_dict = dict(token_data)
                token_dict["expires_at"] = int(time.time()) + int(token_dict.get("expires_in", 3600))
                if client_id and client_secret:
                    token_dict["client_id"] = client_id
                    token_dict["client_secret"] = client_secret
                
                atomic_write_private_json(auth_file, token_dict)
                
                print(f"\n[OK] Authentication successful! Saved to: {auth_file}")
                print("Restarting daemon to apply your credentials...")
                stop_daemon()
                start_daemon()
            else:
                err_msg = token_data.get("error_description") if isinstance(token_data, dict) else "Unknown"
                print(f"\n[FAILED] Authorization was not completed in time or failed ({err_msg}).")
                print("Please make sure you approved the code in your browser before pressing Enter.")
        except Exception as ex:
            print(f"\n[FAILED] OAuth error: {ex}")
            
    elif choice == "2":
        if os.path.exists(auth_file):
            os.remove(auth_file)
            print(f"\nRemoved credentials file: {auth_file}")
        if os.path.exists(COOKIE_FILE):
            os.remove(COOKIE_FILE)
        plugin_cookie = os.path.join(plugin_dir, "cookies.txt")
        if os.path.exists(plugin_cookie):
            os.remove(plugin_cookie)
        print("Configured for Anonymous Mode.")
        print("Restarting daemon...")
        stop_daemon()
        start_daemon()
    else:
        print("Invalid selection.")


def main():
    if len(sys.argv) < 2:
        print("Usage: omarchy-ytmusic {start|stop|restart|status|play [query]|toggle|next|prev|volume [0-100]|search [query]|playlists|play_playlist [id]|auth}")
        return

    action = sys.argv[1].lower()

    if action in ("start", "daemon"):
        start_daemon()
    elif action == "stop":
        stop_daemon()
    elif action == "restart":
        stop_daemon()
        time.sleep(0.5)
        start_daemon()
    elif action == "auth":
        setup_auth()
    elif action == "status":
        res = send_ipc("get_state")
        print(json.dumps(res, indent=2))
    elif action == "play":
        query = " ".join(sys.argv[2:]).strip()
        if not query:
            res = send_ipc("resume")
            print(json.dumps(res, indent=2))
        else:
            if not is_running():
                start_daemon()
            print(f"Searching for: '{query}'...")
            search_res = send_ipc("search", {"query": query})
            tracks = search_res.get("data", [])
            if tracks:
                first = tracks[0]
                print(f"Playing: {first.get('artist')} - {first.get('title')}")
                play_res = send_ipc("play_track", {"track": first})
                print("Started playback:", play_res.get("status"))
            else:
                print("No results found.")
    elif action == "toggle":
        res = send_ipc("toggle_pause")
        print(json.dumps(res, indent=2))
    elif action == "next":
        res = send_ipc("next")
        print(json.dumps(res, indent=2))
    elif action == "prev":
        res = send_ipc("prev")
        print(json.dumps(res, indent=2))
    elif action == "volume":
        vol = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        res = send_ipc("set_volume", {"volume": vol})
        print(json.dumps(res, indent=2))
    elif action == "search":
        query = " ".join(sys.argv[2:]).strip()
        res = send_ipc("search", {"query": query})
        print(json.dumps(res, indent=2))
    elif action == "home":
        res = send_ipc("get_home")
        print(json.dumps(res, indent=2))
    elif action == "play_track":
        track_str = " ".join(sys.argv[2:]).strip()
        track_data = json.loads(track_str) if track_str else {}
        res = send_ipc("play_track", {"track": track_data})
        print(json.dumps(res, indent=2))
    elif action == "add_to_queue":
        track_str = " ".join(sys.argv[2:]).strip()
        track_data = json.loads(track_str) if track_str else {}
        res = send_ipc("add_to_queue", {"track": track_data, "as_next": False})
        print(json.dumps(res, indent=2))
    elif action in ("play_next", "add_next"):
        track_str = " ".join(sys.argv[2:]).strip()
        track_data = json.loads(track_str) if track_str else {}
        res = send_ipc("add_to_queue", {"track": track_data, "as_next": True})
        print(json.dumps(res, indent=2))
    elif action == "play_playlist":
        pl_id = sys.argv[2] if len(sys.argv) > 2 else ""
        start_idx = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        res = send_ipc("play_playlist", {"playlist_id": pl_id, "start_index": start_idx})
        print(json.dumps(res, indent=2))
    elif action == "seek":
        sec = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
        res = send_ipc("seek", {"seconds": sec})
        print(json.dumps(res, indent=2))
    elif action in ("shuffle", "toggle_shuffle"):
        res = send_ipc("toggle_shuffle")
        print(json.dumps(res, indent=2))
    elif action in ("repeat", "toggle_repeat"):
        res = send_ipc("toggle_repeat")
        print(json.dumps(res, indent=2))
    elif action == "playlists":
        res = send_ipc("get_playlists")
        print(json.dumps(res, indent=2))
    elif action == "playlist_tracks":
        pl_id = sys.argv[2] if len(sys.argv) > 2 else ""
        res = send_ipc("get_playlist_tracks", {"playlist_id": pl_id})
        print(json.dumps(res, indent=2))
    elif action == "like":
        vid = sys.argv[2] if len(sys.argv) > 2 else ""
        res = send_ipc("rate_track", {"video_id": vid, "rating": "LIKE"})
        print(json.dumps(res, indent=2))
    elif action == "add_to_playlist":
        pl_id = sys.argv[2] if len(sys.argv) > 2 else ""
        vid = sys.argv[3] if len(sys.argv) > 3 else ""
        res = send_ipc("add_to_playlist", {"playlist_id": pl_id, "video_id": vid})
        print(json.dumps(res, indent=2))
    elif action == "queue":
        res = send_ipc("get_queue")
        print(json.dumps(res, indent=2))
    elif action == "play_index":
        idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        res = send_ipc("play_index", {"index": idx})
        print(json.dumps(res, indent=2))
    elif action == "remove_from_queue":
        idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        res = send_ipc("remove_from_queue", {"index": idx})
        print(json.dumps(res, indent=2))
    elif action == "clear_queue":
        res = send_ipc("clear_queue")
        print(json.dumps(res, indent=2))
    else:
        print(f"Unknown action '{action}'")


if __name__ == "__main__":
    main()

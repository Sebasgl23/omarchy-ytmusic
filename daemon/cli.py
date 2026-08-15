"""CLI commands handler for Omarchy YouTube Music with smart header parsing."""

import json
import os
import re
import socket
import subprocess
import sys
import time

# Ensure daemon directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.paths import SOCKET_PATH, PID_FILE, LOG_FILE


def send_ipc(command: str, args: dict = None, timeout: float = 15.0) -> dict:
    if not os.path.exists(SOCKET_PATH) or not is_running():
        # Auto-spawn daemon if not already started (e.g. after fresh PC reboot)
        start_daemon(silent=True)
        for _ in range(30):
            if os.path.exists(SOCKET_PATH):
                break
            time.sleep(0.1)

    if not os.path.exists(SOCKET_PATH):
        return {"status": "error", "error": "Daemon is not running. Start with 'omarchy-ytmusic start'"}

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


def is_running() -> bool:
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except Exception:
            return False
    return False


def start_daemon(silent: bool = False):
    if is_running():
        if not silent:
            print("Daemon is already running.")
        return

    daemon_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = sys.executable
    main_py = os.path.join(daemon_dir, "main.py")

    if not silent:
        print("Starting Omarchy YouTube Music Daemon in background...")
    with open(LOG_FILE, "a") as log_f:
        proc = subprocess.Popen(
            [venv_python, main_py],
            stdin=subprocess.DEVNULL,
            stdout=log_f,
            stderr=log_f,
            start_new_session=True,
        )
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))

    for _ in range(30):
        if os.path.exists(SOCKET_PATH):
            if not silent:
                print(f"Daemon started successfully (PID {proc.pid}).")
            return
        time.sleep(0.1)

    if not silent:
        print(f"Daemon process started (PID {proc.pid}), waiting for socket... check {LOG_FILE}")


def stop_daemon():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            print(f"Stopping daemon (PID {pid})...")
            os.kill(pid, 15)
        except Exception:
            pass
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
        print("Stopped.")
    else:
        print("Daemon is not running.")


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
                
                with open(auth_file, "w") as f:
                    json.dump(token_dict, f, indent=2)
                
                # Protect file permissions
                try:
                    os.chmod(auth_file, 0o600)
                except Exception:
                    pass
                
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
        cookie_file = "/tmp/omarchy_ytmusic_cookies.txt"
        if os.path.exists(cookie_file):
            os.remove(cookie_file)
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

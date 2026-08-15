"""MPV Headless Audio Player Service implementing AudioPlayer interface."""

import asyncio
import json
import logging
import os
import subprocess
from typing import Optional, Callable
from core.models import Track, PlaybackState
from core.interfaces import AudioPlayer
from core.paths import MPV_SOCKET_PATH, COOKIE_FILE

logger = logging.getLogger("mpv_player")


class MpvPlayerService(AudioPlayer):
    """Audio player implementation using headless MPV with JSON IPC over Unix socket."""

    def __init__(self, socket_path: str = MPV_SOCKET_PATH):
        self.socket_path = socket_path
        self._process: Optional[subprocess.Popen] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._state = PlaybackState()
        self._on_eof_callback: Optional[Callable[[], None]] = None
        self._request_id = 0
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None

    def get_state(self) -> PlaybackState:
        return self._state

    def set_on_eof_callback(self, callback: Callable[[], None]) -> None:
        self._on_eof_callback = callback

    async def start(self) -> None:
        """Spawn headless MPV and connect via IPC socket."""
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except OSError:
                pass

        mpv_cmd = [
            "mpv",
            "--idle=yes",
            "--no-video",
            f"--input-ipc-server={self.socket_path}",
            "--audio-display=no",
            "--gapless-audio=yes",
            "--cache=yes",
            "--demuxer-max-bytes=50MiB",
            "--demuxer-readahead-secs=20",
            "--cache-pause-initial=no",
            "--volume=100",
            "--ao=pipewire,pulse,alsa",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "--referrer=https://www.youtube.com/",
        ]
        # Check secure runtime cookies or plugin directory cookies
        plugin_cookie = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cookies.txt")
        active_cookie = COOKIE_FILE if os.path.exists(COOKIE_FILE) else (plugin_cookie if os.path.exists(plugin_cookie) else None)
        if active_cookie:
            mpv_cmd.append(f"--cookies-file={active_cookie}")

        logger.info("Starting headless MPV process: %s", " ".join(mpv_cmd))
        self._process = subprocess.Popen(
            mpv_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for socket creation
        for _ in range(30):
            if os.path.exists(self.socket_path):
                break
            await asyncio.sleep(0.1)

        if not os.path.exists(self.socket_path):
            raise RuntimeError(f"MPV IPC socket {self.socket_path} failed to initialize.")

        self._reader, self._writer = await asyncio.open_unix_connection(self.socket_path)
        self._running = True
        self._listen_task = asyncio.create_task(self._listen_mpv_events())

        # Observe properties
        await self._send_command(["observe_property", 1, "time-pos"])
        await self._send_command(["observe_property", 2, "pause"])
        await self._send_command(["observe_property", 3, "idle-active"])
        await self._send_command(["observe_property", 4, "eof-reached"])
        await self._send_command(["observe_property", 5, "duration"])
        await self._send_command(["observe_property", 6, "volume"])
        await self._send_command(["observe_property", 7, "mute"])
        logger.info("Connected to MPV IPC socket successfully.")

    async def stop(self) -> None:
        """Gracefully stop MPV and close socket connections."""
        self._running = False
        if self._listen_task:
            self._listen_task.cancel()
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except OSError:
                pass
        self._state.status = "stopped"
        self._state.current_track = None

    async def _send_command(self, command: list) -> None:
        if not self._writer:
            return
        self._request_id += 1
        payload = json.dumps({"command": command, "request_id": self._request_id}) + "\n"
        try:
            self._writer.write(payload.encode("utf-8"))
            await self._writer.drain()
        except Exception as ex:
            logger.error("Failed sending command %s to MPV: %s", command, ex)

    async def _listen_mpv_events(self) -> None:
        """Handle incoming property events from MPV."""
        while self._running and self._reader:
            try:
                line = await self._reader.readline()
                if not line:
                    break
                event = json.loads(line.decode("utf-8"))
                self._handle_event(event)
            except asyncio.CancelledError:
                break
            except Exception as ex:
                logger.debug("Error parsing MPV event: %s", ex)

    def _handle_event(self, event: dict) -> None:
        event_name = event.get("event")
        prop_name = event.get("name")
        data = event.get("data")

        if prop_name == "time-pos" and data is not None:
            self._state.position_seconds = float(data)
        elif prop_name == "duration" and data is not None:
            self._state.duration_seconds = float(data)
        elif prop_name == "idle-active" and data is True:
            if self._state.status == "playing" and self._state.position_seconds > 0 and self._state.position_seconds >= (self._state.duration_seconds - 2.0):
                if self._on_eof_callback:
                    asyncio.create_task(self._trigger_eof())
        elif prop_name == "pause" and data is not None:
            if self._state.status != "stopped":
                self._state.status = "paused" if data else "playing"
        elif prop_name == "volume" and data is not None:
            self._state.volume = int(data)
        elif prop_name == "mute" and data is not None:
            self._state.is_muted = bool(data)
        elif prop_name == "eof-reached" and data is True:
            if self._state.position_seconds > 0:
                logger.info("Track reached EOF.")
                if self._on_eof_callback:
                    asyncio.create_task(self._trigger_eof())
        elif event_name == "end-file":
            reason = event.get("reason")
            if reason == "eof" and self._state.position_seconds > 0 and self._on_eof_callback:
                asyncio.create_task(self._trigger_eof())

    async def _trigger_eof(self) -> None:
        if self._on_eof_callback:
            try:
                self._on_eof_callback()
            except Exception as ex:
                logger.error("Error in on_eof_callback: %s", ex)

    async def play_url(self, stream_url: str, track: Track) -> None:
        """Load and start playing audio stream."""
        self._state.current_track = track
        self._state.status = "playing"
        self._state.position_seconds = 0.0
        self._state.duration_seconds = track.duration_seconds or 0.0
        title = track.title or "Unknown Title"
        artist = track.artist or ""
        if artist and title:
            media_title = f"{title} · {artist}"
        else:
            media_title = title or artist or "YouTube Music"

        await self._send_command(["loadfile", stream_url, "replace"])
        await self._send_command(["set_property", "force-media-title", media_title])
        await self._send_command(["set_property", "title", title])
        await self._send_command(["set_property", "pause", False])

    async def pause(self) -> None:
        self._state.status = "paused"
        await self._send_command(["set_property", "pause", True])

    async def resume(self) -> None:
        self._state.status = "playing"
        await self._send_command(["set_property", "pause", False])

    async def toggle_playback(self) -> None:
        if self._state.status == "playing":
            await self.pause()
        elif self._state.status == "paused":
            await self.resume()

    async def seek(self, seconds: float) -> None:
        self._state.position_seconds = seconds
        await self._send_command(["seek", seconds, "absolute"])

    async def set_volume(self, volume: int) -> None:
        vol = max(0, min(100, volume))
        self._state.volume = vol
        await self._send_command(["set_property", "volume", vol])

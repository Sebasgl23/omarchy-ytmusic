"""Unix Domain Socket JSON-RPC server for Omarchy plugin communication."""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Callable, Coroutine, Optional, List
from core.models import Track
from core.interfaces import MusicRepository, AudioPlayer
from services.playback_orchestrator import PlaybackOrchestrator

logger = logging.getLogger("socket_server")

SOCKET_PATH = "/tmp/omarchy-ytmusic.sock"


class IpcServer:
    """Provides non-blocking JSON-RPC interface over Unix domain socket."""

    def __init__(self, repo: MusicRepository, player: AudioPlayer, orchestrator: PlaybackOrchestrator, socket_path: str = SOCKET_PATH):
        self.repo = repo
        self.player = player
        self.orchestrator = orchestrator
        self.socket_path = socket_path
        self._server: Optional[asyncio.Server] = None
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Coroutine[Any, Any, Any]]] = {}
        self._register_handlers()

    def _register_handlers(self) -> None:
        self._handlers = {
            "ping": self._handle_ping,
            "get_state": self._handle_get_state,
            "search": self._handle_search,
            "get_playlists": self._handle_get_playlists,
            "get_playlist_tracks": self._handle_get_playlist_tracks,
            "play_track": self._handle_play_track,
            "play_playlist": self._handle_play_playlist,
            "add_to_queue": self._handle_add_to_queue,
            "toggle_pause": self._handle_toggle_pause,
            "pause": self._handle_pause,
            "resume": self._handle_resume,
            "next": self._handle_next,
            "prev": self._handle_prev,
            "seek": self._handle_seek,
            "set_volume": self._handle_set_volume,
            "toggle_shuffle": self._handle_toggle_shuffle,
            "toggle_repeat": self._handle_toggle_repeat,
            "rate_track": self._handle_rate_track,
            "add_to_playlist": self._handle_add_to_playlist,
            "create_playlist": self._handle_create_playlist,
            "get_queue": self._handle_get_queue,
            "play_index": self._handle_play_index,
            "remove_from_queue": self._handle_remove_from_queue,
            "clear_queue": self._handle_clear_queue,
        }

    async def start(self) -> None:
        """Start listening on Unix domain socket."""
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except OSError:
                pass

        self._server = await asyncio.start_unix_server(self._handle_client, path=self.socket_path)
        # Ensure correct socket permissions
        os.chmod(self.socket_path, 0o666)
        logger.info("IPC Socket Server listening on %s", self.socket_path)

    async def stop(self) -> None:
        """Close socket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except OSError:
                pass
        logger.info("IPC Socket Server stopped.")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                
                request_str = line.decode("utf-8").strip()
                if not request_str:
                    continue

                try:
                    request = json.loads(request_str)
                    cmd = request.get("command")
                    args = request.get("args", {})
                    req_id = request.get("id")

                    handler = self._handlers.get(cmd)
                    if handler:
                        result = await handler(args)
                        response = {"id": req_id, "status": "ok", "data": result}
                    else:
                        response = {"id": req_id, "status": "error", "error": f"Unknown command '{cmd}'"}
                except Exception as ex:
                    logger.error("Error processing request: %s", ex)
                    response = {"id": request.get("id") if 'request' in locals() else None, "status": "error", "error": str(ex)}

                payload = json.dumps(response) + "\n"
                writer.write(payload.encode("utf-8"))
                await writer.drain()
        except asyncio.CancelledError:
            pass
        except Exception as err:
            logger.debug("Client connection terminated: %s", err)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    # --- Handlers ---

    async def _handle_ping(self, args: dict) -> dict:
        return {"pong": True}

    async def _handle_get_state(self, args: dict) -> dict:
        return self.orchestrator.get_state().to_dict()

    async def _handle_search(self, args: dict) -> list:
        query = args.get("query", "")
        tracks = await self.repo.search(query)
        return [t.to_dict() for t in tracks]

    async def _handle_get_playlists(self, args: dict) -> list:
        playlists = await self.repo.get_playlists()
        return [p.to_dict() for p in playlists]

    async def _handle_get_playlist_tracks(self, args: dict) -> list:
        playlist_id = args.get("playlist_id", "")
        tracks = await self.repo.get_playlist_tracks(playlist_id)
        return [t.to_dict() for t in tracks]

    async def _handle_play_track(self, args: dict) -> bool:
        track_data = args.get("track", {})
        track = Track.from_dict(track_data)
        return await self.orchestrator.play_track(track)

    async def _handle_play_playlist(self, args: dict) -> bool:
        playlist_id = args.get("playlist_id", "")
        start_index = int(args.get("start_index", 0))
        tracks = await self.repo.get_playlist_tracks(playlist_id)
        if tracks:
            return await self.orchestrator.play_queue(tracks, start_index=start_index)
        return False

    async def _handle_add_to_queue(self, args: dict) -> bool:
        track_data = args.get("track", {})
        as_next = bool(args.get("as_next", False))
        track = Track.from_dict(track_data)
        await self.orchestrator.add_to_queue(track, as_next=as_next)
        return True

    async def _handle_toggle_pause(self, args: dict) -> dict:
        await self.player.toggle_playback()
        return self.orchestrator.get_state().to_dict()

    async def _handle_pause(self, args: dict) -> dict:
        await self.player.pause()
        return self.orchestrator.get_state().to_dict()

    async def _handle_resume(self, args: dict) -> dict:
        await self.player.resume()
        return self.orchestrator.get_state().to_dict()

    async def _handle_next(self, args: dict) -> bool:
        return await self.orchestrator.next_track()

    async def _handle_prev(self, args: dict) -> bool:
        return await self.orchestrator.previous_track()

    async def _handle_seek(self, args: dict) -> float:
        seconds = float(args.get("seconds", 0.0))
        await self.player.seek(seconds)
        return seconds

    async def _handle_set_volume(self, args: dict) -> int:
        volume = int(args.get("volume", 100))
        await self.player.set_volume(volume)
        return volume

    async def _handle_toggle_shuffle(self, args: dict) -> bool:
        return await self.orchestrator.toggle_shuffle()

    async def _handle_toggle_repeat(self, args: dict) -> str:
        return self.orchestrator.toggle_repeat()

    async def _handle_rate_track(self, args: dict) -> bool:
        video_id = args.get("video_id", "")
        return await self.orchestrator.toggle_like(video_id)

    async def _handle_add_to_playlist(self, args: dict) -> dict:
        playlist_id = args.get("playlist_id", "")
        video_id = args.get("video_id", "")
        return await self.repo.add_track_to_playlist(playlist_id, video_id)

    async def _handle_create_playlist(self, args: dict) -> Optional[str]:
        title = args.get("title", "")
        description = args.get("description", "")
        return await self.repo.create_playlist(title, description)

    async def _handle_get_queue(self, args: dict) -> list:
        return [t.to_dict() for t in self.orchestrator.queue]

    async def _handle_play_index(self, args: dict) -> bool:
        index = int(args.get("index", 0))
        return await self.orchestrator.play_index(index)

    async def _handle_remove_from_queue(self, args: dict) -> bool:
        index = int(args.get("index", 0))
        return await self.orchestrator.remove_from_queue(index)

    async def _handle_clear_queue(self, args: dict) -> bool:
        return await self.orchestrator.clear_queue()

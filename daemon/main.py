"""YouTube Music Daemon Entrypoint for Omarchy."""

import asyncio
import logging
import os
import signal
import sys

# Ensure daemon path in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.ytmusic_service import YtMusicService
from services.mpv_player_service import MpvPlayerService
from services.playback_orchestrator import PlaybackOrchestrator
from ipc.socket_server import IpcServer
from core.paths import PID_FILE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ytmusic_daemon")


async def main():
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    auth_file = os.path.join(plugin_dir, "auth.json")

    logger.info("Initializing Omarchy YouTube Music Daemon...")
    repo = YtMusicService(auth_file_path=auth_file if os.path.exists(auth_file) else None)
    player = MpvPlayerService()
    orchestrator = PlaybackOrchestrator(repo, player)

    stop_event = asyncio.Event()

    def _shutdown_handler():
        logger.info("Shutdown requested.")
        stop_event.set()

    ipc = IpcServer(repo, player, orchestrator, on_shutdown=_shutdown_handler)
    player_started = False
    ipc_started = False
    try:
        await player.start()
        player_started = True
        await ipc.start()
        ipc_started = True

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _shutdown_handler)
            except NotImplementedError:
                pass

        logger.info("YouTube Music Daemon running successfully.")
        await stop_event.wait()
    finally:
        logger.info("Stopping services...")
        if ipc_started:
            await ipc.stop()
        if player_started:
            await player.stop()

        try:
            with open(PID_FILE, "r", encoding="utf-8") as pid_file:
                recorded_pid = int(pid_file.read().strip())
            if recorded_pid == os.getpid():
                os.remove(PID_FILE)
        except (OSError, ValueError):
            pass
        logger.info("Daemon cleanly terminated.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

"""Unit tests for domain models, orchestrator queue logic, and IPC message routing."""

import asyncio
import json
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock

import sys
import os

# Include daemon directory in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "daemon")))

from core.models import Track, Playlist, PlaybackState
from core.interfaces import MusicRepository, AudioPlayer
from core.paths import SOCKET_PATH, RUNTIME_DIR
from services.playback_orchestrator import PlaybackOrchestrator
from ipc.socket_server import IpcServer


class TestDomainModels(unittest.TestCase):
    """Test serialization, deserialization and default values of domain entities."""

    def test_track_serialization(self):
        track = Track(
            video_id="abc12345",
            title="Starboy",
            artist="The Weeknd",
            album="Starboy",
            duration_seconds=230,
            thumbnail_url="https://example.com/thumb.jpg",
        )
        data = track.to_dict()
        self.assertEqual(data["video_id"], "abc12345")
        self.assertEqual(data["title"], "Starboy")
        self.assertEqual(data["duration_seconds"], 230)

        reconstructed = Track.from_dict(data)
        self.assertEqual(reconstructed, track)

    def test_track_from_dict_defaults(self):
        track = Track.from_dict({"video_id": "xyz999"})
        self.assertEqual(track.video_id, "xyz999")
        self.assertEqual(track.title, "Unknown Title")
        self.assertEqual(track.artist, "Unknown Artist")
        self.assertEqual(track.duration_seconds, 0)

    def test_playlist_serialization(self):
        playlist = Playlist(
            playlist_id="LM",
            title="Liked Music",
            description="All your liked tracks",
            track_count=123,
            thumbnail_url="https://example.com/lm.jpg",
            author="YouTube Music",
        )
        data = playlist.to_dict()
        self.assertEqual(data["playlist_id"], "LM")
        self.assertEqual(data["track_count"], 123)

        reconstructed = Playlist.from_dict(data)
        self.assertEqual(reconstructed, playlist)


class TestPlaybackOrchestrator(unittest.IsolatedAsyncioTestCase):
    """Test Queue management, Play Next, Shuffle, and Repeat logic."""

    async def asyncSetUp(self):
        self.mock_repo = MagicMock(spec=MusicRepository)
        self.mock_repo.get_playlist_tracks = AsyncMock(return_value=[])
        self.mock_repo.get_stream_url = AsyncMock(return_value="https://stream.googlevideo.com/audio")
        self.mock_repo.get_radio_tracks = AsyncMock(return_value=[])
        self.mock_repo.rate_track = AsyncMock(return_value=True)

        self.mock_player = MagicMock(spec=AudioPlayer)
        self.mock_player.set_on_eof_callback = MagicMock()
        self.mock_player.play_url = AsyncMock()
        self.mock_player.pause = AsyncMock()
        self.mock_player.resume = AsyncMock()
        self.mock_player.stop = AsyncMock()
        self.mock_player.get_state = MagicMock(return_value=PlaybackState(status="stopped"))

        self.orchestrator = PlaybackOrchestrator(self.mock_repo, self.mock_player)

    async def test_add_to_queue_and_play_next(self):
        t1 = Track(video_id="1", title="Song 1", artist="Artist 1")
        t2 = Track(video_id="2", title="Song 2", artist="Artist 2")
        t3 = Track(video_id="3", title="Song 3", artist="Artist 3")

        # 1. Play first track
        await self.orchestrator.play_track(t1)
        self.assertEqual(len(self.orchestrator.queue), 1)
        self.assertEqual(self.orchestrator.current_index, 0)

        # 2. Add song 2 to end of queue
        await self.orchestrator.add_to_queue(t2, as_next=False)
        self.assertEqual(len(self.orchestrator.queue), 2)
        self.assertEqual(self.orchestrator.queue[1].video_id, "2")

        # 3. Add song 3 as Play Next (should be inserted at index current_index + 1 = 1)
        await self.orchestrator.add_to_queue(t3, as_next=True)
        self.assertEqual(len(self.orchestrator.queue), 3)
        self.assertEqual(self.orchestrator.queue[1].video_id, "3")
        self.assertEqual(self.orchestrator.queue[2].video_id, "2")

    async def test_repeat_modes(self):
        self.assertEqual(self.orchestrator.repeat_mode, "off")
        m1 = self.orchestrator.toggle_repeat()
        self.assertEqual(m1, "all")
        m2 = self.orchestrator.toggle_repeat()
        self.assertEqual(m2, "one")
        m3 = self.orchestrator.toggle_repeat()
        self.assertEqual(m3, "off")

    async def test_shuffle_toggle(self):
        tracks = [Track(video_id=str(i), title=f"Song {i}", artist="Artist") for i in range(10)]
        self.orchestrator.queue = list(tracks)
        self.orchestrator._original_queue = list(tracks)
        self.orchestrator.current_index = 0

        # Toggle shuffle on
        shuffled = await self.orchestrator.toggle_shuffle()
        self.assertTrue(shuffled)
        self.assertEqual(len(self.orchestrator.queue), 10)
        # Playing song must remain at index 0
        self.assertEqual(self.orchestrator.queue[0].video_id, "0")

        # Toggle shuffle off restores original sequence
        unshuffled = await self.orchestrator.toggle_shuffle()
        self.assertFalse(unshuffled)
        self.assertEqual([t.video_id for t in self.orchestrator.queue], [str(i) for i in range(10)])

    async def test_remove_from_queue(self):
        tracks = [Track(video_id=str(i), title=f"Song {i}", artist="Artist") for i in range(3)]
        self.orchestrator.queue = list(tracks)
        self.orchestrator._original_queue = list(tracks)
        self.orchestrator.current_index = 0

        # Remove track at index 1
        res = await self.orchestrator.remove_from_queue(1)
        self.assertTrue(res)
        self.assertEqual(len(self.orchestrator.queue), 2)
        self.assertEqual(self.orchestrator.queue[1].video_id, "2")


class TestIpcServer(unittest.IsolatedAsyncioTestCase):
    """Test JSON-RPC message dispatching and response structures."""

    async def asyncSetUp(self):
        self.mock_repo = MagicMock(spec=MusicRepository)
        self.mock_repo.get_playlist_tracks = AsyncMock(return_value=[])
        self.mock_player = MagicMock(spec=AudioPlayer)
        self.mock_player.get_state = MagicMock(return_value=PlaybackState(status="stopped"))
        self.mock_player.set_on_eof_callback = MagicMock()
        self.orchestrator = PlaybackOrchestrator(self.mock_repo, self.mock_player)
        self.test_socket = str(RUNTIME_DIR / "test-omarchy.sock")
        self.ipc = IpcServer(self.mock_repo, self.mock_player, self.orchestrator, socket_path=self.test_socket)

    async def asyncTearDown(self):
        await self.ipc.stop()

    def test_registered_handlers(self):
        expected = ["ping", "get_state", "search", "get_playlists", "play_track", "add_to_queue", "seek", "next", "prev"]
        for handler in expected:
            self.assertIn(handler, self.ipc._handlers)

    async def test_socket_lifecycle_and_permissions(self):
        await self.ipc.start()
        self.assertTrue(os.path.exists(self.test_socket))
        # Check permissions are strictly 0600 (owner only)
        mode = oct(os.stat(self.test_socket).st_mode & 0o777)
        self.assertEqual(mode, "0o600")
        await self.ipc.stop()
        self.assertFalse(os.path.exists(self.test_socket))

    async def test_shutdown_handler(self):
        shutdown_called = False
        def _on_shutdown():
            nonlocal shutdown_called
            shutdown_called = True

        test_ipc = IpcServer(self.mock_repo, self.mock_player, self.orchestrator, on_shutdown=_on_shutdown)
        res = await test_ipc._handlers["shutdown"]({})
        self.assertEqual(res, {"shutdown": True})
        # Allow loop to process call_soon
        await asyncio.sleep(0.01)
        self.assertTrue(shutdown_called)


class TestRuntimeSecurityPaths(unittest.TestCase):
    """Test that all sockets, pid, logs and cookies are securely located in private runtime directory."""

    def test_paths_are_not_in_shared_tmp(self):
        from core.paths import (
            SOCKET_PATH,
            MPV_SOCKET_PATH,
            PID_FILE,
            START_LOCK_FILE,
            LOG_FILE,
            COOKIE_FILE,
            RUNTIME_DIR,
        )

        for path in [SOCKET_PATH, MPV_SOCKET_PATH, PID_FILE, START_LOCK_FILE, LOG_FILE, COOKIE_FILE]:
            self.assertFalse(
                path.startswith("/tmp/"),
                f"Path {path} should not be located directly in shared /tmp",
            )
            self.assertTrue(
                str(RUNTIME_DIR) in path,
                f"Path {path} should reside inside RUNTIME_DIR ({RUNTIME_DIR})",
            )


class TestProcessVerificationAndStalePidSecurity(unittest.TestCase):
    """Test PID reuse protection and process verification in cli.py."""

    def test_is_ytmusic_daemon_process_unrelated_process(self):
        import os
        from cli import is_ytmusic_daemon_process
        from unittest.mock import patch, mock_open

        daemon_main = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "daemon", "main.py"))

        # Case 1: Process does not exist
        with patch("os.kill", side_effect=ProcessLookupError):
            self.assertFalse(is_ytmusic_daemon_process(99999))

        # Case 2: Process exists but is an unrelated app (e.g. firefox, bash)
        with patch("os.kill", return_value=None), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=b"/usr/bin/firefox\x00")):
            self.assertFalse(is_ytmusic_daemon_process(12345))

        # Case 3: Process exists and cmdline matches ytmusic daemon exact canonical entrypoint
        with patch("os.kill", return_value=None), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=f"python3\x00{daemon_main}\x00".encode("utf-8"))):
            self.assertTrue(is_ytmusic_daemon_process(12345))

        # Case 4: Process exists but cmdline only contains substring (e.g. nano /other/daemon/main.py or grep)
        with patch("os.kill", return_value=None), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=b"nano\x00/other/project/daemon/main.py\x00sebasgl23.ytmusic\x00")):
            self.assertFalse(is_ytmusic_daemon_process(12345))

        # Case 5: Python is running an editor/tool and our daemon path is only
        # a later argument. It must never be treated as the daemon process.
        with patch("os.kill", return_value=None), \
             patch("os.path.exists", return_value=True), \
             patch(
                 "builtins.open",
                 mock_open(
                     read_data=(
                         f"python3\x00/usr/bin/some-editor.py\x00{daemon_main}\x00"
                     ).encode("utf-8")
                 ),
             ):
            self.assertFalse(is_ytmusic_daemon_process(12345))

        # Case 6: Fail-closed when /proc/<pid>/cmdline does not exist
        with patch("os.kill", return_value=None), \
             patch("os.path.exists", return_value=False):
            self.assertFalse(is_ytmusic_daemon_process(12345))

    def test_stop_daemon_does_not_kill_unrelated_reused_pid(self):
        from cli import stop_daemon
        from unittest.mock import patch, mock_open

        # Simulate PID_FILE existing with an unrelated process PID
        with patch("os.path.exists", side_effect=lambda p: "daemon.pid" in str(p) or "omarchy-ytmusic.sock" in str(p)), \
             patch("builtins.open", mock_open(read_data="55555")), \
             patch("cli.is_ytmusic_daemon_process", return_value=False), \
             patch("os.kill") as mock_kill, \
             patch("os.remove") as mock_remove:
            
            stop_daemon()
            
            # Verify SIGTERM (15) was NEVER sent to the unrelated PID
            mock_kill.assert_not_called()
            # Verify stale PID_FILE was safely cleaned up
            self.assertTrue(any("daemon.pid" in str(c) for c in mock_remove.call_args_list))

    def test_start_daemon_serializes_before_rechecking_process_state(self):
        import cli
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as runtime_dir:
            lock_path = os.path.join(runtime_dir, "daemon-start.lock")
            with patch.object(cli, "START_LOCK_FILE", lock_path), \
                 patch("cli.is_running", return_value=True) as mock_is_running, \
                 patch("cli.subprocess.Popen") as mock_popen:
                self.assertTrue(cli.start_daemon(silent=True))

            mock_is_running.assert_called_once_with()
            mock_popen.assert_not_called()
            self.assertEqual(os.stat(lock_path).st_mode & 0o777, 0o600)

    def test_failed_start_terminates_spawned_process_and_removes_its_pid(self):
        import cli
        from unittest.mock import MagicMock, patch

        proc = MagicMock()
        proc.pid = 4242
        proc.poll.return_value = None
        proc.wait.return_value = 0

        with tempfile.TemporaryDirectory() as runtime_dir:
            pid_path = os.path.join(runtime_dir, "daemon.pid")
            with open(pid_path, "w", encoding="utf-8") as pid_file:
                pid_file.write(str(proc.pid))

            with patch.object(cli, "PID_FILE", pid_path):
                cli._clean_failed_start(proc)

            proc.terminate.assert_called_once_with()
            proc.wait.assert_called_once_with(timeout=2)
            self.assertFalse(os.path.exists(pid_path))


class TestPluginPortability(unittest.TestCase):
    """Ensure marketplace entry points do not depend on the author's home."""

    def test_qml_cli_paths_are_resolved_relative_to_the_plugin(self):
        plugin_root = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))

        for qml_name in ("Panel.qml", "Main.qml", "BarWidget.qml"):
            with self.subTest(qml=qml_name):
                with open(os.path.join(plugin_root, qml_name), encoding="utf-8") as qml_file:
                    source = qml_file.read()

                self.assertIn('Qt.resolvedUrl("bin/omarchy-ytmusic")', source)
                self.assertNotRegex(source, r"/home/[^/]+/")

    def test_bootstrap_uses_only_pinned_dependencies_under_a_lock(self):
        plugin_root = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
        requirements_path = os.path.join(plugin_root, "requirements.txt")
        wrapper_path = os.path.join(plugin_root, "bin", "omarchy-ytmusic")

        with open(requirements_path, encoding="utf-8") as requirements_file:
            requirements = [
                line.strip()
                for line in requirements_file
                if line.strip() and not line.startswith("#")
            ]
        with open(wrapper_path, encoding="utf-8") as wrapper_file:
            wrapper = wrapper_file.read()

        self.assertTrue(requirements)
        self.assertTrue(all(line.count("==") == 1 for line in requirements))
        self.assertIn('flock 9', wrapper)
        self.assertIn('--requirement "$REQUIREMENTS_FILE"', wrapper)
        self.assertNotIn("pip install --quiet ytmusicapi yt-dlp requests", wrapper)


if __name__ == "__main__":
    unittest.main()

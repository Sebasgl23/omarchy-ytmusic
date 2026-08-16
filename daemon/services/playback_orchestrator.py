"""Playback orchestrator managing queue and coordinating repository with audio player."""

import random
import logging
import asyncio
from typing import List, Optional, Set
from core.models import Track, PlaybackState
from core.interfaces import MusicRepository, AudioPlayer

logger = logging.getLogger("orchestrator")


class PlaybackOrchestrator:
    """Application use case manager for playback, queue, and music interactions."""

    def __init__(self, music_repo: MusicRepository, player: AudioPlayer):
        self.repo = music_repo
        self.player = player
        self.queue: List[Track] = []
        self.current_index: int = -1
        self.is_shuffled: bool = False
        self.repeat_mode: str = "off"  # "off", "one", "all"
        self._original_queue: List[Track] = []
        self._liked_video_ids: Set[str] = set()
        self._liked_songs_initialized: bool = False
        self._play_lock = asyncio.Lock()

        # Wire natural end-of-track callback
        self.player.set_on_eof_callback(self._handle_track_finished)

        # Trigger background initial fetch of liked songs
        asyncio.create_task(self._fetch_liked_songs())

    async def _fetch_liked_songs(self) -> None:
        """Cache user's liked video IDs in background."""
        try:
            tracks = await self.repo.get_playlist_tracks("LM")
            self._liked_video_ids = {t.video_id for t in tracks if t.video_id}
            self._liked_songs_initialized = True
            logger.info("Cached %d liked video IDs", len(self._liked_video_ids))
        except Exception as ex:
            logger.debug("Could not fetch liked songs cache: %s", ex)

    def _handle_track_finished(self) -> None:
        """Callback invoked when MPV finishes a track."""
        asyncio.create_task(self.next_track())

    def get_state(self) -> PlaybackState:
        """Aggregate current playback and queue state."""
        base_state = self.player.get_state()
        base_state.queue = self.queue
        base_state.queue_index = self.current_index
        base_state.is_shuffled = self.is_shuffled
        base_state.repeat_mode = self.repeat_mode
        if base_state.current_track and base_state.current_track.video_id:
            base_state.is_liked = base_state.current_track.video_id in self._liked_video_ids
        else:
            base_state.is_liked = False
        return base_state

    async def toggle_like(self, video_id: str) -> bool:
        """Toggle like status for a video ID with optimistic state update."""
        if not video_id:
            return False

        if video_id in self._liked_video_ids:
            # Currently liked -> remove like
            success = await self.repo.rate_track(video_id, "INDIFFERENT")
            if success:
                self._liked_video_ids.discard(video_id)
                return False
            return True
        else:
            # Currently not liked -> add like
            success = await self.repo.rate_track(video_id, "LIKE")
            if success:
                self._liked_video_ids.add(video_id)
                return True
            return False

    async def play_track(self, track: Track) -> bool:
        """Play a single track immediately and auto-populate radio queue in background."""
        self.queue = [track]
        self._original_queue = [track]
        self.current_index = 0
        res = await self._play_current_index()
        if res and track.video_id:
            asyncio.create_task(self._auto_fill_radio(track.video_id))
        return res

    async def _auto_fill_radio(self, video_id: str) -> None:
        """Fetch similar tracks and append them to queue seamlessly."""
        try:
            similar_tracks = await self.repo.get_watch_playlist(video_id, limit=20)
            if similar_tracks:
                current_vids = {t.video_id for t in self.queue}
                new_tracks = [t for t in similar_tracks if t.video_id not in current_vids]
                self.queue.extend(new_tracks)
                self._original_queue.extend(new_tracks)
                logger.info("Auto-queued %d radio tracks following %s", len(new_tracks), video_id)
        except Exception as ex:
            logger.debug("Could not auto-fill radio: %s", ex)

    async def play_queue(self, tracks: List[Track], start_index: int = 0) -> bool:
        """Load a list of tracks into queue and play from start_index."""
        if not tracks:
            return False
        self.queue = list(tracks)
        self._original_queue = list(tracks)
        self.current_index = max(0, min(start_index, len(tracks) - 1))
        return await self._play_current_index()

    async def add_to_queue(self, track: Track, as_next: bool = False) -> None:
        """Append track to current playback queue or insert as next."""
        if as_next and 0 <= self.current_index < len(self.queue):
            insert_pos = self.current_index + 1
            self.queue.insert(insert_pos, track)
            self._original_queue.insert(insert_pos, track)
        else:
            self.queue.append(track)
            self._original_queue.append(track)

        if len(self.queue) == 1 or self.current_index == -1:
            self.current_index = 0
            await self._play_current_index()

    async def _play_current_index(self) -> bool:
        async with self._play_lock:
            attempts = 0
            while self.current_index >= 0 and self.current_index < len(self.queue) and attempts < 10:
                track = self.queue[self.current_index]
                logger.info("Resolving stream URL for track: %s - %s (%s)", track.artist, track.title, track.video_id)
                stream_url = await self.repo.get_stream_url(track.video_id)
                
                if stream_url:
                    await self.player.play_url(stream_url, track)
                    # Pre-fetch next track in background for instantaneous skip
                    asyncio.create_task(self._prefetch_next_track())
                    return True
                
                logger.error("Failed to retrieve stream URL for video %s. Skipping to next.", track.video_id)
                self.current_index += 1
                attempts += 1

            return False

    async def _prefetch_next_track(self) -> None:
        """Pre-extract stream URL for upcoming track so 'Next' is instant."""
        try:
            next_idx = self.current_index + 1
            if 0 <= next_idx < len(self.queue):
                next_t = self.queue[next_idx]
                if next_t and next_t.video_id:
                    await self.repo.get_stream_url(next_t.video_id)
        except Exception:
            pass

    async def next_track(self) -> bool:
        """Advance to next track in queue with repeat / shuffle handling."""
        if not self.queue:
            return False

        if self.repeat_mode == "one":
            return await self._play_current_index()

        if self.current_index + 1 < len(self.queue):
            self.current_index += 1
            return await self._play_current_index()
        elif self.repeat_mode == "all":
            self.current_index = 0
            return await self._play_current_index()
        else:
            # Try to fetch more radio tracks before stopping
            if self.queue and self.current_index >= 0:
                last_track = self.queue[self.current_index]
                if last_track.video_id:
                    more_tracks = await self.repo.get_watch_playlist(last_track.video_id, limit=15)
                    current_vids = {t.video_id for t in self.queue}
                    new_tracks = [t for t in more_tracks if t.video_id not in current_vids]
                    if new_tracks:
                        self.queue.extend(new_tracks)
                        self._original_queue.extend(new_tracks)
                        self.current_index += 1
                        return await self._play_current_index()

            logger.info("Reached end of queue.")
            return False

    async def previous_track(self) -> bool:
        """Go back to previous track in queue or restart current song."""
        state = self.player.get_state()
        if state.position_seconds > 4.0:
            await self.player.seek(0)
            return True

        if self.current_index > 0:
            self.current_index -= 1
            return await self._play_current_index()
        else:
            await self.player.seek(0)
            return True

    async def toggle_shuffle(self) -> bool:
        """Toggle shuffle state without losing current song."""
        if not self.queue:
            return False

        self.is_shuffled = not self.is_shuffled
        current_track = self.queue[self.current_index] if 0 <= self.current_index < len(self.queue) else None

        if self.is_shuffled:
            remaining = [t for i, t in enumerate(self.queue) if i != self.current_index]
            random.shuffle(remaining)
            self.queue = ([current_track] if current_track else []) + remaining
            self.current_index = 0 if current_track else -1
        else:
            self.queue = list(self._original_queue)
            if current_track and current_track in self.queue:
                self.current_index = self.queue.index(current_track)
        return self.is_shuffled

    def toggle_repeat(self) -> str:
        """Cycle repeat mode: off -> all -> one -> off."""
        modes = ["off", "all", "one"]
        idx = modes.index(self.repeat_mode) if self.repeat_mode in modes else 0
        self.repeat_mode = modes[(idx + 1) % len(modes)]
        return self.repeat_mode

    async def play_index(self, index: int) -> bool:
        """Jump directly to track at specified index."""
        if 0 <= index < len(self.queue):
            self.current_index = index
            return await self._play_current_index()
        return False

    async def remove_from_queue(self, index: int) -> bool:
        """Remove a track from queue by its index."""
        if 0 <= index < len(self.queue):
            removed = self.queue.pop(index)
            if removed in self._original_queue:
                self._original_queue.remove(removed)
            if index < self.current_index:
                self.current_index -= 1
            elif index == self.current_index:
                if self.queue:
                    self.current_index = min(self.current_index, len(self.queue) - 1)
                    await self._play_current_index()
                else:
                    self.current_index = -1
                    await self.player.stop()
            return True
        return False

    async def clear_queue(self) -> bool:
        """Clear all tracks except currently playing."""
        if 0 <= self.current_index < len(self.queue):
            current = self.queue[self.current_index]
            self.queue = [current]
            self._original_queue = [current]
            self.current_index = 0
        else:
            self.queue = []
            self._original_queue = []
            self.current_index = -1
            await self.player.stop()
        return True

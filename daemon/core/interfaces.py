"""Abstract interfaces following Clean Architecture principles."""

from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from .models import Track, Playlist, PlaybackState


class MusicRepository(ABC):
    """Port for external YouTube Music operations."""

    @abstractmethod
    async def search(self, query: str) -> List[Track]:
        """Search YouTube Music tracks."""
        pass

    @abstractmethod
    async def get_playlists(self) -> List[Playlist]:
        """Retrieve user playlists and library playlists."""
        pass

    @abstractmethod
    async def get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        """Retrieve tracks belonging to a playlist."""
        pass

    @abstractmethod
    async def get_watch_playlist(self, video_id: str, limit: int = 25) -> List[Track]:
        """Retrieve dynamic radio watch playlist based on a song."""
        pass

    @abstractmethod
    async def get_stream_url(self, video_id: str) -> Optional[str]:
        """Extract playable direct audio stream URL."""
        pass

    @abstractmethod
    async def add_track_to_playlist(self, playlist_id: str, video_id: str) -> bool:
        """Add a track to a user playlist."""
        pass

    @abstractmethod
    async def create_playlist(self, title: str, description: str = "") -> Optional[str]:
        """Create a new user playlist."""
        pass

    @abstractmethod
    async def rate_track(self, video_id: str, rating: str) -> bool:
        """Rate track: 'LIKE', 'DISLIKE', or 'INDIFFERENT'."""
        pass


class AudioPlayer(ABC):
    """Port for audio playback engine."""

    @abstractmethod
    async def start(self) -> None:
        """Initialize the audio backend."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the player backend."""
        pass

    @abstractmethod
    async def play_url(self, stream_url: str, track: Track) -> None:
        """Stream a URL for a given track."""
        pass

    @abstractmethod
    async def pause(self) -> None:
        """Pause playback."""
        pass

    @abstractmethod
    async def resume(self) -> None:
        """Resume playback."""
        pass

    @abstractmethod
    async def toggle_playback(self) -> None:
        """Toggle between play and pause."""
        pass

    @abstractmethod
    async def seek(self, seconds: float) -> None:
        """Seek to absolute seconds."""
        pass

    @abstractmethod
    async def set_volume(self, volume: int) -> None:
        """Set volume (0-100)."""
        pass

    @abstractmethod
    def get_state(self) -> PlaybackState:
        """Get snapshot of current playback state."""
        pass

    @abstractmethod
    def set_on_eof_callback(self, callback: Callable[[], None]) -> None:
        """Register callback triggered when a track completes naturally."""
        pass

"""Domain models and DTOs for YouTube Music client."""

from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass(frozen=True)
class Track:
    video_id: str
    title: str
    artist: str
    album: str = ""
    duration_seconds: int = 0
    thumbnail_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Track":
        return cls(
            video_id=str(data.get("video_id", "")),
            title=str(data.get("title", "Unknown Title")),
            artist=str(data.get("artist", "Unknown Artist")),
            album=str(data.get("album", "")),
            duration_seconds=int(data.get("duration_seconds", 0)),
            thumbnail_url=str(data.get("thumbnail_url", "")),
        )


@dataclass(frozen=True)
class Playlist:
    playlist_id: str
    title: str
    description: str = ""
    track_count: int = 0
    thumbnail_url: str = ""
    author: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Playlist":
        return cls(
            playlist_id=str(data.get("playlist_id", "")),
            title=str(data.get("title", "Untitled Playlist")),
            description=str(data.get("description", "")),
            track_count=int(data.get("track_count", 0)),
            thumbnail_url=str(data.get("thumbnail_url", "")),
            author=str(data.get("author", "")),
        )


@dataclass
class PlaybackState:
    status: str = "stopped"  # "playing", "paused", "stopped"
    current_track: Optional[Track] = None
    position_seconds: float = 0.0
    duration_seconds: float = 0.0
    volume: int = 100
    is_muted: bool = False
    is_liked: bool = False
    repeat_mode: str = "off"  # "off", "one", "all"
    is_shuffled: bool = False
    queue: List[Track] = field(default_factory=list)
    queue_index: int = -1

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "current_track": self.current_track.to_dict() if self.current_track else None,
            "position_seconds": round(self.position_seconds, 1),
            "duration_seconds": round(self.duration_seconds, 1),
            "volume": self.volume,
            "is_muted": self.is_muted,
            "is_liked": self.is_liked,
            "repeat_mode": self.repeat_mode,
            "is_shuffled": self.is_shuffled,
            "queue_length": len(self.queue),
            "queue_index": self.queue_index,
        }

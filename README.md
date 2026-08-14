# Omarchy YouTube Music Plugin

A native, ultra-lightweight **YouTube Music** player and bar widget built specifically for **Omarchy** (Hyprland + Quickshell).

---

## Features

- **Ultra-low Memory Footprint:** Consumes ~100–200 MB RAM (compared to 700MB+ for Electron-based music apps).
- **Native Omarchy Theme Integration:** Pure QML/Quickshell interface adopting active system fonts, rounded corners, blur, and dynamic color palettes.
- **Fast Music Search:** Instant search for songs, albums, and artists with 1-click playback.
- **Playlist & Mix Browser:** Explore user library playlists and discover dynamic YouTube Music mixes with drill-down song inspection.
- **Interactive Liked Songs:** Real-time synchronized like/unlike tracking (`Liked Music`).
- **Infinite Radio / Autoplay:** Automatically populates similar tracks seamlessly in the background when playing individual tracks.
- **Permanent Google OAuth 2.0:** Secure, non-expiring login with background access token refresh via Google Cloud Console.
- **Quick Bar Controls:**
  - **Left Click:** Open/Close the popup player panel.
  - **Middle Click:** Play / Pause immediately.
  - **Right Click:** Skip to next track.
- **Marquee Scrolling:** Long track titles and artists smoothly scroll horizontally in both the status bar and the Now Playing view.
- **MPRIS & Media Keys Support:** Seamless integration with hardware media keys and desktop MPRIS controllers (`playerctl`).

---

## Requirements

- **Omarchy** (Quickshell + Hyprland environment)
- **Python 3.10+** (with `venv`)
- **MPV** (`mpv` installed and available on `PATH`)
- **PipeWire / PulseAudio / ALSA** audio backend

---

## Installation

Install and enable the plugin directly using Omarchy's built-in package manager:

```bash
omarchy plugin add https://github.com/your-username/omarchy-ytmusic.git --enable
```

> **Note:** On first launch, the plugin automatically bootstraps its isolated Python virtual environment and downloads the required lightweight dependencies (`ytmusicapi`, `yt-dlp`, `requests`). No manual `pip` installation is needed!

---

## Google Account Setup (Permanent OAuth 2.0)

By default, the plugin works in **Anonymous Mode** (enabling open searches, stream playback, and curated home mixes without signing in).

To sync your **private playlists, Liked Music, and personal library** with permanent, non-expiring credentials:

### 1. Create OAuth Client in Google Cloud (Takes ~2 min, 1-time setup):
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. `Omarchy Music`).
3. Search for **YouTube Data API v3** on the search bar and click **Enable**.
4. Navigate to **OAuth consent screen**:
   - Choose **External** -> Click **Create**.
   - Fill in App name (`Omarchy Music`) and your email address.
   - Save through the steps; under **Test users**, add your own Google email.
5. Navigate to **Credentials**:
   - Click **+ Create Credentials** -> **OAuth client ID**.
   - Application type: Select **TVs and Limited Input devices** (or *Desktop App*).
   - Click **Create** and copy your `Client ID` and `Client Secret`.

### 2. Connect Your Account:
Run the interactive authentication assistant:

```bash
~/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic auth
```

1. Select option **`1` (Google OAuth)**.
2. Enter your `Client ID` and `Client Secret`.
3. Open the provided `https://www.google.com/device` link, enter the displayed verification code, and approve access.

Your credentials and refresh token will be securely saved in `~/.config/omarchy/plugins/sebasgl23.ytmusic/auth.json` and automatically refreshed in the background.

---

## CLI Usage

The player daemon can be controlled headlessly from scripts, keybindings, or terminal:

```bash
# Daemon Management
~/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic start
~/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic stop
~/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic restart
~/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic status

# Search & Playback
~/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic play "Instant Crush"
~/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic toggle
~/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic next
~/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic prev
~/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic volume 75

# Playlists & Library
~/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic playlists
~/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic playlist_tracks "LM"
~/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic like "<video_id>"
```

---

## Architecture

```
sebasgl23.ytmusic/
├── manifest.json              # Omarchy plugin descriptor
├── Panel.qml                  # Main popup interface & state store
├── BarWidget.qml              # Status bar button & slot integration
├── ytmusic.js                 # Shared UI helpers (time formatting, JSON parsing)
├── components/
│   ├── IconButton.qml         # Theme-aware interactive button
│   ├── NowPlayingView.qml     # Player view (artwork, seekbar, volume, controls)
│   ├── SearchView.qml         # Live search view & results list
│   ├── PlaylistsView.qml      # Playlist browser & track inspector
│   ├── QueueView.qml          # Current playback queue
│   └── AddToPlaylistDialog.qml# Playlist selection dialog
├── daemon/
│   ├── main.py                # Async daemon entry point
│   ├── cli.py                 # CLI dispatcher & OAuth assistant
│   ├── core/
│   │   ├── models.py          # Domain entities (Track, Playlist, PlaybackState)
│   │   └── interfaces.py      # Abstract repository & player ports
│   ├── services/
│   │   ├── ytmusic_service.py # Hybrid YouTube Data API v3 + ytmusicapi service
│   │   ├── mpv_player_service.py # Headless MPV audio engine over Unix socket IPC
│   │   └── playback_orchestrator.py # Queue orchestrator, shuffle, repeat & radio
│   └── ipc/
│       └── socket_server.py   # JSON-RPC Unix domain socket server
└── bin/
    └── omarchy-ytmusic        # Executable binary wrapper
```

---

## License

MIT License. Crafted for the Omarchy desktop ecosystem.

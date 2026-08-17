import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "components"

Panel {
  id: root
  moduleName: "sebasgl23.ytmusic"
  ipcTarget: "sebasgl23.ytmusic"
  manageIpc: true

  readonly property color foreground: bar ? bar.foreground : Color.foreground
  readonly property color dim: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.55)

  readonly property string cliBin: {
    var url = Qt.resolvedUrl("bin/omarchy-ytmusic").toString()
    return url.startsWith("file://") ? url.substring(7) : (Quickshell.env("HOME") + "/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic")
  }

  // ── Playback state ────────────────────────────────────────────────────────
  property bool   isPlaying:       false
  property string trackTitle:      "No track playing"
  property string trackArtist:     ""
  property string trackThumbnail:  ""
  property string trackVideoId:    ""
  property real   positionSeconds: 0
  property real   durationSeconds: 0
  property int    volumeLevel:     100
  property bool   isLiked:         false
  property string repeatMode:      "off"
  property bool   isShuffled:      false

  // ── Search / Playlists state ──────────────────────────────────────────────
  property var  searchResults:       []
  property bool isSearching:         false
  property var  playlists:           []
  property bool isLoadingPlaylists:  false
  property var  openedPlaylist:      null
  property var  playlistTracks:      []
  property bool isLoadingTracks:     false
  property var  queueList:           []
  property int  queueIndex:          -1
  property var  homeData:            []
  property bool isLoadingHome:       false

  // ── UI state ──────────────────────────────────────────────────────────────
  property int  activeTab: 0
  property bool showQueueView: false
  property var  trackToAddToPlaylist: null
  property bool showAddToPlaylistDialog: false
  property var  trackToAddToQueue: null
  property bool showQueueOptionDialog: false

  // ── State helpers ─────────────────────────────────────────────────────────
  function applyState(data) {
    root.isPlaying       = (data.status === "playing")
    root.positionSeconds = data.position_seconds  || 0
    root.durationSeconds = data.duration_seconds  || 0
    root.volumeLevel     = (data.volume !== undefined) ? data.volume : 100
    root.isLiked         = !!data.is_liked
    root.repeatMode      = data.repeat_mode  || "off"
    root.isShuffled      = !!data.is_shuffled
    root.queueIndex      = (data.queue_index !== undefined) ? data.queue_index : -1
    var t = data.current_track
    if (t) {
      root.trackTitle     = t.title         || "Unknown Title"
      root.trackArtist    = t.artist        || ""
      root.trackThumbnail = t.thumbnail_url || ""
      root.trackVideoId   = t.video_id      || ""
      if (root.durationSeconds <= 0 && t.duration_seconds)
        root.durationSeconds = t.duration_seconds
    } else {
      root.trackTitle = "No track playing"; root.trackArtist = ""
      root.trackThumbnail = ""; root.trackVideoId = ""
    }
  }

  function parseObj(raw) {
    if (!raw) return null
    var s = String(raw).trim()
    var a = s.indexOf('{'), b = s.lastIndexOf('}')
    if (a !== -1 && b > a) { try { return JSON.parse(s.substring(a, b+1)) } catch(e){ return null } }
    return null
  }

  // ── Process commands ──────────────────────────────────────────────────────
  function doRefresh() {
    if (statusProc.running) return
    statusProc.command = [cliBin, "status"]
    statusProc.running = true
  }

  function doSearch(q) {
    if (!q || !String(q).trim()) return
    root.isSearching = true
    searchProc.command = [cliBin, "search", String(q).trim()]
    searchProc.running = true
  }

  function doFetchPlaylists() {
    if (playlistsProc.running) return
    root.isLoadingPlaylists = true
    playlistsProc.command = [cliBin, "playlists"]
    playlistsProc.running = true
  }

  function doFetchHome() {
    if (homeProc.running) return
    root.isLoadingHome = true
    homeProc.command = [cliBin, "home"]
    homeProc.running = true
  }

  function doFetchPlaylistTracks(pl) {
    if (!pl || !pl.playlist_id) return
    root.openedPlaylist = pl
    root.playlistTracks = []
    root.isLoadingTracks = true
    playlistTracksProc.command = [cliBin, "playlist_tracks", pl.playlist_id]
    playlistTracksProc.running = true
  }

  function doFetchQueue() {
    if (queueProc.running) return
    queueProc.command = [cliBin, "queue"]
    queueProc.running = true
  }

  function doExecute(args) {
    if (cmdProc.running) return
    cmdProc.command = [cliBin].concat(args)
    cmdProc.running = true
  }

  onOpenedChanged: {
    if (opened) {
      doRefresh()
      doFetchPlaylists()
    }
  }

  // ── Polling Timer ─────────────────────────────────────────────────────────
  Timer {
    interval: 1000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: root.doRefresh()
  }

  // ── Processes ─────────────────────────────────────────────────────────────
  Process {
    id: statusProc
    running: false
    stdout: StdioCollector {
      id: statusOut
      waitForEnd: true
      onStreamFinished: {
        var res = root.parseObj(statusOut.text)
        if (res && res.status === "ok" && res.data) root.applyState(res.data)
      }
    }
  }

  Process {
    id: cmdProc
    running: false
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: { root.doRefresh() }
    }
    onExited: function(code) { Qt.callLater(function(){ root.doRefresh() }) }
  }

  Process {
    id: addToPlaylistProc
    running: false
    stdout: StdioCollector {
      id: addPlOut
      waitForEnd: true
      onStreamFinished: {
        var res = root.parseObj(addPlOut.text)
        if (res && res.data) {
          if (res.data.already_exists) {
            addToPlDialog.setStatusMessage("This track is already in the playlist!", false)
          } else if (res.data.success) {
            addToPlDialog.setStatusMessage("Added to playlist!", true)
          } else {
            addToPlDialog.setStatusMessage("Failed to add track.", false)
          }
        } else {
          addToPlDialog.setStatusMessage("Added to playlist!", true)
        }
      }
    }
  }

  Process {
    id: searchProc
    running: false
    stdout: StdioCollector {
      id: searchOut
      waitForEnd: true
      onStreamFinished: {
        root.isSearching = false
        var res = root.parseObj(searchOut.text)
        root.searchResults = (res && res.status === "ok" && Array.isArray(res.data)) ? res.data : []
      }
    }
    onExited: function(code) { root.isSearching = false }
  }

  Process {
    id: playlistsProc
    running: false
    stdout: StdioCollector {
      id: playlistsOut
      waitForEnd: true
      onStreamFinished: {
        root.isLoadingPlaylists = false
        var res = root.parseObj(playlistsOut.text)
        if (res && res.status === "ok" && Array.isArray(res.data)) root.playlists = res.data
      }
    }
    onExited: function(code) { root.isLoadingPlaylists = false }
  }

  Process {
    id: homeProc
    running: false
    stdout: StdioCollector {
      id: homeOut
      waitForEnd: true
      onStreamFinished: {
        root.isLoadingHome = false
        var res = root.parseObj(homeOut.text)
        if (res && res.status === "ok" && Array.isArray(res.data)) root.homeData = res.data
      }
    }
    onExited: function(code) { root.isLoadingHome = false }
  }

  Process {
    id: playlistTracksProc
    running: false
    stdout: StdioCollector {
      id: playlistTracksOut
      waitForEnd: true
      onStreamFinished: {
        root.isLoadingTracks = false
        var res = root.parseObj(playlistTracksOut.text)
        if (res && res.status === "ok" && Array.isArray(res.data)) {
          root.playlistTracks = res.data
        }
      }
    }
    onExited: function(code) { root.isLoadingTracks = false }
  }

  Process {
    id: queueProc
    running: false
    stdout: StdioCollector {
      id: queueOut
      waitForEnd: true
      onStreamFinished: {
        var res = root.parseObj(queueOut.text)
        if (res && res.status === "ok" && Array.isArray(res.data)) {
          root.queueList = res.data
        }
      }
    }
  }

  // ── Bar slot ──────────────────────────────────────────────────────────────
  visible: true
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    active: root.isPlaying
    useActiveColor: false
    tooltipText: root.trackVideoId !== ""
      ? (root.trackArtist + " - " + root.trackTitle + (root.isPlaying ? " ▶" : " ⏸"))
      : "YouTube Music"
    iconComponent: Component {
      Item {
        anchors.fill: parent

        Image {
          anchors.centerIn: parent
          width: Math.round(parent.width * 0.82)
          height: Math.round(parent.height * 0.82)
          source: Qt.resolvedUrl("ytmusic-bar-icon.svg")
          fillMode: Image.PreserveAspectFit
          smooth: true
          mipmap: true
        }
      }
    }
    onPressed: function(btn) {
      if (btn === Qt.RightButton)       root.doExecute(["next"])
      else if (btn === Qt.MiddleButton) root.doExecute(["toggle"])
      else                              root.toggle()
    }
  }

  // ── Popup flyout ──────────────────────────────────────────────────────────
  KeyboardPanel {
    id: flyout
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    contentWidth: flyout.fittedContentWidth(Style.space(350))
    contentHeight: Style.space(435)

    Column {
      anchors.fill: parent
      anchors.margins: Style.space(12)
      spacing: Style.space(10)

      // Header with flex spacing
      Item {
        width: parent.width
        height: Style.space(26)

        // Brand (Left)
        Row {
          anchors.left: parent.left
          anchors.verticalCenter: parent.verticalCenter
          spacing: Style.space(6)

          Image {
            source: Qt.resolvedUrl("ytmusic-logo.svg")
            width: Style.space(16)
            height: Style.space(16)
            fillMode: Image.PreserveAspectFit
            anchors.verticalCenter: parent.verticalCenter
          }

          Text {
            text: "YT MUSIC"
            color: root.foreground
            font.bold: true
            font.pixelSize: Style.space(11)
            font.letterSpacing: 0.8
            anchors.verticalCenter: parent.verticalCenter
          }
        }

        // Tab Pill Buttons (Right)
        Row {
          anchors.right: parent.right
          anchors.verticalCenter: parent.verticalCenter
          spacing: Style.space(3)

          IconButton {
            text: "\uf001"
            toolTipText: "Now Playing"
            active: root.activeTab === 0
            buttonSize: Style.space(26)
            foreground: root.foreground
            onClicked: root.activeTab = 0
          }
          IconButton {
            text: "\uf015" // Home icon (FontAwesome)
            toolTipText: "Home"
            active: root.activeTab === 3
            buttonSize: Style.space(26)
            foreground: root.foreground
            onClicked: { root.activeTab = 3; root.doFetchHome() }
          }
          IconButton {
            text: "\uf002"
            toolTipText: "Search"
            active: root.activeTab === 1
            buttonSize: Style.space(26)
            foreground: root.foreground
            onClicked: root.activeTab = 1
          }
          IconButton {
            text: "\uf07b"
            toolTipText: "Playlists"
            active: root.activeTab === 2
            buttonSize: Style.space(26)
            foreground: root.foreground
            onClicked: { root.activeTab = 2; root.doFetchPlaylists() }
          }
        }
      }

      // Divider
      Rectangle {
        width: parent.width
        height: 1
        color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.1)
      }

      // Views Container
      Item {
        width: parent.width
        height: parent.height - Style.space(37)

        NowPlayingView {
          anchors.fill: parent
          visible: root.activeTab === 0 && !root.showAddToPlaylistDialog && !root.showQueueView
          trackTitle:     root.trackTitle
          trackArtist:    root.trackArtist
          trackThumbnail: root.trackThumbnail
          trackVideoId:   root.trackVideoId
          position:       root.positionSeconds
          duration:       root.durationSeconds
          isPlaying:      root.isPlaying
          volume:         root.volumeLevel
          isLiked:        root.isLiked
          repeatMode:     root.repeatMode
          isShuffled:     root.isShuffled
          foreground:     root.foreground
          onTogglePlay:   root.doExecute(["toggle"])
          onNextTrack:    root.doExecute(["next"])
          onPrevTrack:    root.doExecute(["prev"])
          onSeekTrack:    function(s) { root.doExecute(["seek", String(Math.floor(s))]) }
          onChangeVolume: function(v) { root.doExecute(["volume", String(v)]) }
          onToggleShuffle: root.doExecute(["shuffle"])
          onShowQueue:    { root.showQueueView = true; root.doFetchQueue() }
          onToggleLike: {
            if (root.trackVideoId) {
              root.isLiked = !root.isLiked
              root.doExecute(["like", root.trackVideoId])
            }
          }
          onAddToPlaylist: {
            if (root.trackVideoId) {
              root.trackToAddToPlaylist = { title: root.trackTitle, artist: root.trackArtist, video_id: root.trackVideoId }
              root.showAddToPlaylistDialog = true
              root.doFetchPlaylists()
            }
          }
        }

        QueueView {
          anchors.fill: parent
          visible: root.activeTab === 0 && root.showQueueView && !root.showAddToPlaylistDialog && !root.showQueueOptionDialog
          queue:        root.queueList
          currentIndex: root.queueIndex
          foreground:   root.foreground
          onPlayQueueIndexRequested: function(idx) {
            root.doExecute(["play_index", String(idx)])
            root.doFetchQueue()
          }
          onRemoveQueueIndexRequested: function(idx) {
            root.doExecute(["remove_from_queue", String(idx)])
            root.doFetchQueue()
          }
          onClearQueueRequested: {
            root.doExecute(["clear_queue"])
            root.doFetchQueue()
          }
          onCloseRequested: { root.showQueueView = false }
        }

        HomeView {
          anchors.fill: parent
          visible: root.activeTab === 3 && !root.showAddToPlaylistDialog && !root.showQueueOptionDialog
          homeData: root.homeData
          isLoadingHome: root.isLoadingHome
          foreground: root.foreground
          onItemClicked: function(item) {
            if (item.videoId) {
               // Play track
               var thumb = (item.thumbnails && item.thumbnails.length > 0) ? item.thumbnails[item.thumbnails.length - 1].url : ""
               var t = {
                 title: item.title, 
                 video_id: item.videoId,
                 artist: item.description || item.subtitle || "",
                 thumbnail_url: thumb
               }
               root.doExecute(["play_track", JSON.stringify(t)])
               root.activeTab = 0
            } else if (item.playlistId || item.browseId) {
               // Open playlist preview in Playlists tab
               var pid = item.playlistId || item.browseId
               var pl = { playlist_id: pid, title: item.title }
               root.doFetchPlaylistTracks(pl)
               root.activeTab = 2
            }
          }
        }

        SearchView {
          anchors.fill: parent
          visible: root.activeTab === 1 && !root.showAddToPlaylistDialog && !root.showQueueOptionDialog
          searchResults:  root.searchResults
          isSearching:    root.isSearching
          foreground:     root.foreground
          onSearchRequested: function(q) { root.doSearch(q) }
          onClearRequested: { root.searchResults = []; root.isSearching = false }
          onPlayTrackRequested: function(t) {
            root.doExecute(["play_track", JSON.stringify(t)]); root.activeTab = 0
          }
          onOpenQueueOptionsRequested: function(t) {
            root.trackToAddToQueue = t
            root.showQueueOptionDialog = true
          }
          onAddToPlaylistRequested: function(t) {
            root.trackToAddToPlaylist = t; root.showAddToPlaylistDialog = true; root.doFetchPlaylists()
          }
        }

        PlaylistsView {
          anchors.fill: parent
          visible: root.activeTab === 2 && !root.showAddToPlaylistDialog && !root.showQueueOptionDialog
          playlists:       root.playlists
          isLoading:       root.isLoadingPlaylists
          openedPlaylist:  root.openedPlaylist
          playlistTracks:  root.playlistTracks
          isLoadingTracks: root.isLoadingTracks
          foreground:      root.foreground
          onRefreshRequested:      root.doFetchPlaylists()
          onOpenPlaylistRequested: function(pl) { root.doFetchPlaylistTracks(pl) }
          onBackRequested:         { root.openedPlaylist = null; root.playlistTracks = [] }
          onPlayPlaylistRequested: function(plId) { root.doExecute(["play_playlist", plId, "0"]); root.activeTab = 0 }
          onPlayTrackRequested: function(t, idx) {
            if (root.openedPlaylist && root.openedPlaylist.playlist_id) {
              root.doExecute(["play_playlist", root.openedPlaylist.playlist_id, String(idx || 0)])
            } else {
              root.doExecute(["play_track", JSON.stringify(t)])
            }
            root.activeTab = 0
          }
          onOpenQueueOptionsRequested: function(t) {
            root.trackToAddToQueue = t
            root.showQueueOptionDialog = true
          }
          onAddToPlaylistRequested: function(t) {
            root.trackToAddToPlaylist = t; root.showAddToPlaylistDialog = true; root.doFetchPlaylists()
          }
        }

        AddToPlaylistDialog {
          id: addToPlDialog
          anchors.fill: parent
          visible: root.showAddToPlaylistDialog
          track:     root.trackToAddToPlaylist
          playlists: root.playlists
          foreground: root.foreground
          onPlaylistSelected: function(plId, vid) {
            addToPlaylistProc.command = [cliBin, "add_to_playlist", plId, vid]
            addToPlaylistProc.running = true
          }
          onCloseRequested: { root.showAddToPlaylistDialog = false; root.trackToAddToPlaylist = null }
        }

        QueueOptionDialog {
          anchors.fill: parent
          visible: root.showQueueOptionDialog
          track: root.trackToAddToQueue
          foreground: root.foreground
          onPlayNextRequested: function(t) {
            root.doExecute(["play_next", JSON.stringify(t)])
            root.doFetchQueue()
          }
          onAddToEndRequested: function(t) {
            root.doExecute(["add_to_queue", JSON.stringify(t)])
            root.doFetchQueue()
          }
          onCloseRequested: {
            root.showQueueOptionDialog = false
            root.trackToAddToQueue = null
          }
        }
      }
    }
  }
}

import QtQuick
import Quickshell
import Quickshell.Io

Item {
  id: root
  visible: false

  readonly property string cliBin: {
    var url = Qt.resolvedUrl("bin/omarchy-ytmusic").toString()
    return url.startsWith("file://") ? url.substring(7) : (Quickshell.env("HOME") + "/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic")
  }

  property bool   isPlaying:        false
  property string trackTitle:       "No track playing"
  property string trackArtist:      ""
  property string trackThumbnail:   ""
  property string trackVideoId:     ""
  property real   positionSeconds:  0
  property real   durationSeconds:  0
  property int    volumeLevel:      100
  property bool   isLiked:          false
  property string repeatMode:       "off"
  property bool   isShuffled:       false
  property int    queueLength:      0
  property int    queueIndex:       -1

  property var  searchResults:       []
  property bool isSearching:         false
  property var  playlists:           []
  property bool isLoadingPlaylists:  false

  function applyState(data) {
    root.isPlaying        = (data.status === "playing")
    root.positionSeconds  = data.position_seconds  || 0
    root.durationSeconds  = data.duration_seconds  || 0
    root.volumeLevel      = (data.volume !== undefined) ? data.volume : 100
    root.isLiked          = !!data.is_liked
    root.repeatMode       = data.repeat_mode  || "off"
    root.isShuffled       = !!data.is_shuffled
    root.queueLength      = data.queue_length || 0
    root.queueIndex       = (data.queue_index !== undefined) ? data.queue_index : -1

    var t = data.current_track
    if (t) {
      root.trackTitle     = t.title         || "Unknown Title"
      root.trackArtist    = t.artist        || ""
      root.trackThumbnail = t.thumbnail_url || ""
      root.trackVideoId   = t.video_id      || ""
      if (root.durationSeconds <= 0 && t.duration_seconds) {
        root.durationSeconds = t.duration_seconds
      }
    } else {
      root.trackTitle     = "No track playing"
      root.trackArtist    = ""
      root.trackThumbnail = ""
      root.trackVideoId   = ""
    }
  }

  function parseJson(raw) {
    if (!raw) return null
    var s = String(raw).trim()
    var a = s.indexOf('{'), b = s.lastIndexOf('}')
    if (a !== -1 && b > a) { try { return JSON.parse(s.substring(a, b+1)) } catch(e){} }
    return null
  }

  function refresh() {
    if (statusProc.running) return
    statusProc.command = [cliBin, "status"]
    statusProc.running = true
  }

  function search(query) {
    if (!query || !String(query).trim()) return
    root.isSearching = true
    searchProc.command = [cliBin, "search", String(query).trim()]
    searchProc.running = true
  }

  property var  homeData:            []
  property bool isLoadingHome:       false

  function fetchHome() {
    if (homeProc.running) return
    root.isLoadingHome = true
    homeProc.command = [cliBin, "home"]
    homeProc.running = true
  }

  function fetchPlaylists() {
    if (playlistsProc.running) return
    root.isLoadingPlaylists = true
    playlistsProc.command = [cliBin, "playlists"]
    playlistsProc.running = true
  }

  function execute(args) {
    if (cmdProc.running) return
    cmdProc.command = [cliBin].concat(args)
    cmdProc.running = true
  }

  Timer {
    interval: 1000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: root.refresh()
  }

  // ── statusProc uses text property of StdioCollector, NOT a parameter ────────
  Process {
    id: statusProc
    running: false
    stdout: StdioCollector {
      id: statusOut
      waitForEnd: true
      onStreamFinished: {
        var res = root.parseJson(statusOut.text)
        if (res && res.status === "ok" && res.data) {
          root.applyState(res.data)
        }
      }
    }
  }

  Process {
    id: cmdProc
    running: false
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: { root.refresh() }
    }
    onExited: function(code) { Qt.callLater(function(){ root.refresh() }) }
  }

  Process {
    id: searchProc
    running: false
    stdout: StdioCollector {
      id: searchOut
      waitForEnd: true
      onStreamFinished: {
        root.isSearching = false
        var res = root.parseJson(searchOut.text)
        if (res && res.status === "ok" && Array.isArray(res.data)) {
          root.searchResults = res.data
        } else {
          root.searchResults = []
        }
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
        var res = root.parseJson(playlistsOut.text)
        if (res && res.status === "ok" && Array.isArray(res.data)) {
          root.playlists = res.data
        }
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
        var res = root.parseJson(homeOut.text)
        if (res && res.status === "ok" && Array.isArray(res.data)) {
          root.homeData = res.data
        }
      }
    }
    onExited: function(code) { root.isLoadingHome = false }
  }
}

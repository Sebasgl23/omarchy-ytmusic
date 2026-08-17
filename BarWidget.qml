import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "ytmusic.js" as Utils

BarWidget {
  id: root
  moduleName: "sebasgl23.ytmusic"

  readonly property color foreground: bar ? bar.foreground : Color.foreground
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family

  // CLI Binary
  property string cliBin: {
    var url = Qt.resolvedUrl("bin/omarchy-ytmusic").toString()
    return url.startsWith("file://") ? url.substring(7) : (Quickshell.env("HOME") + "/.config/omarchy/plugins/sebasgl23.ytmusic/bin/omarchy-ytmusic")
  }

  // Current State
  property var playerState: ({
    status: "stopped",
    current_track: null,
    position_seconds: 0,
    duration_seconds: 0
  })

  readonly property bool hasTrack: playerState && playerState.current_track !== null
  readonly property bool isPlaying: playerState && playerState.status === "playing"
  readonly property string songTitle: hasTrack ? playerState.current_track.title : ""
  readonly property string artistName: hasTrack ? playerState.current_track.artist : ""

  readonly property string displayText: {
    if (!hasTrack) return "YT Music";
    var t = songTitle;
    if (artistName) t = artistName + " — " + t;
    return Utils.truncateString(t, 28);
  }

  // Contract properties for Omarchy Bar Popouts
  readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false
  readonly property real openPanelIndicatorWidth: button.implicitWidth
  readonly property real openPanelIndicatorHeight: Math.max(Style.space(10), Math.round(Style.bar.iconSlot * 0.55))
  readonly property bool popoutSwitchClosing: panelLoader.item ? panelLoader.item.popoutSwitchClosing === true : false

  function open() {
    if (panelLoader.item) panelLoader.item.open();
  }

  function close() {
    if (panelLoader.item) panelLoader.item.close();
  }

  function togglePanel() {
    if (panelLoader.item) panelLoader.item.toggle();
  }

  function refresh() {
    if (!statusProc.running) {
      statusProc.running = true;
    }
  }

  function injectPanel() {
    var target = panelLoader.item;
    if (!target) return;
    if ("bar" in target) target.bar = root.bar;
    if ("settings" in target) target.settings = root.settings;
    if ("anchorItem" in target) target.anchorItem = button;
    if ("hostWidget" in target) target.hostWidget = root;
  }

  onBarChanged: injectPanel()
  onSettingsChanged: injectPanel()

  // Periodic Refresh
  Timer {
    interval: 2000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: root.refresh()
  }

  // Status Poll Process
  Process {
    id: statusProc
    command: [root.cliBin, "status"]
    running: false
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: function(text) {
        var res = Utils.parseJsonSafe(text, null);
        if (res && res.status === "ok" && res.data) {
          root.playerState = res.data;
        }
      }
    }
  }

  // Quick Action Process (Toggle / Next)
  Process {
    id: actionProc
    running: false
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: function(text) {
        root.refresh();
      }
    }
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarButton {
    id: button
    anchors.fill: parent
    tooltipText: root.hasTrack ? (root.artistName + " - " + root.songTitle + " (" + (root.isPlaying ? "Playing" : "Paused") + ")\nLeft-click: Panel | Middle-click: Play/Pause | Right-click: Next") : "YouTube Music\nClick to open player"

    content: Row {
      spacing: Style.space(6)
      anchors.verticalCenter: parent.verticalCenter

      Text {
        text: root.isPlaying ? "▶" : "🎵"
        color: root.isPlaying ? Color.accent : root.foreground
        font.pixelSize: Style.font.caption
        anchors.verticalCenter: parent.verticalCenter
      }

      Text {
        text: root.displayText
        color: root.foreground
        font.family: root.fontFamily
        font.pixelSize: Style.font.caption
        font.bold: root.isPlaying
        elide: Text.ElideRight
        anchors.verticalCenter: parent.verticalCenter
      }
    }

    onClicked: root.togglePanel()
    onMiddleClicked: {
      actionProc.command = [root.cliBin, "toggle"];
      actionProc.running = true;
    }
    onRightClicked: {
      actionProc.command = [root.cliBin, "next"];
      actionProc.running = true;
    }
  }

  Loader {
    id: panelLoader
    active: true
    source: "Panel.qml"
    onLoaded: root.injectPanel()
  }
}

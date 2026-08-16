import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Ui
import "../ytmusic.js" as Utils

Item {
  id: root

  property var playlists: []
  property bool isLoading: false
  property var openedPlaylist: null
  property var playlistTracks: []
  property bool isLoadingTracks: false

  property color foreground: Color.foreground
  property color dim: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.55)

  signal refreshRequested()
  signal playPlaylistRequested(string playlistId)
  signal openPlaylistRequested(var playlist)
  signal backRequested()
  signal playTrackRequested(var track, int index)
  signal openQueueOptionsRequested(var track)
  signal addToPlaylistRequested(var track)

  Column {
    anchors.fill: parent
    spacing: Style.space(8)

    // ── Header (Contextual: All Playlists vs. Selected Playlist) ───────────
    Item {
      width: parent.width
      height: Style.space(26)

      // Back Button + Playlist Title (When inside a playlist)
      Row {
        visible: root.openedPlaylist !== null
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.space(6)

        IconButton {
          text: "\uf060"
          buttonSize: Style.space(24)
          toolTipText: "Back to Playlists"
          foreground: root.foreground
          onClicked: root.backRequested()
        }

        Text {
          text: root.openedPlaylist ? (root.openedPlaylist.title || "Playlist") : ""
          color: root.foreground
          font.bold: true
          font.pixelSize: Style.font.caption
          anchors.verticalCenter: parent.verticalCenter
          elide: Text.ElideRight
          width: root.width - Style.space(70)
        }
      }

      // Default Header (When in main list)
      Row {
        visible: root.openedPlaylist === null
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.space(6)

        Text {
          text: "PLAYLISTS & MIXES"
          color: root.dim
          font.bold: true
          font.pixelSize: Style.space(11)
          anchors.verticalCenter: parent.verticalCenter
        }
      }

      // Right Action Button (Play All vs Refresh)
      IconButton {
        visible: root.openedPlaylist !== null
        text: "\uf04b"
        buttonSize: Style.space(24)
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        toolTipText: "Play All"
        foreground: Color.accent
        onClicked: {
          if (root.openedPlaylist) root.playPlaylistRequested(root.openedPlaylist.playlist_id)
        }
      }

      IconButton {
        visible: root.openedPlaylist === null
        text: "\uf021"
        buttonSize: Style.space(24)
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        toolTipText: "Refresh Playlists"
        foreground: root.foreground
        onClicked: root.refreshRequested()
      }
    }

    // ── Main Content Area ──────────────────────────────────────────────────
    Item {
      width: parent.width
      height: parent.height - Style.space(34)

      // ==========================================
      // VIEW 1: Playlist Track Detail List
      // ==========================================
      Item {
        anchors.fill: parent
        visible: root.openedPlaylist !== null

        Text {
          anchors.centerIn: parent
          text: "Loading tracks..."
          color: root.dim
          font.pixelSize: Style.font.body
          visible: root.isLoadingTracks
        }

        Text {
          anchors.centerIn: parent
          text: "No tracks in this playlist"
          color: root.dim
          font.pixelSize: Style.font.body
          visible: !root.isLoadingTracks && (!root.playlistTracks || root.playlistTracks.length === 0)
        }

        Flickable {
          anchors.fill: parent
          contentWidth: width
          contentHeight: tracksCol.implicitHeight
          clip: true
          visible: !root.isLoadingTracks && root.playlistTracks && root.playlistTracks.length > 0
          boundsBehavior: Flickable.StopAtBounds

          Column {
            id: tracksCol
            width: parent.width
            spacing: Style.space(4)

            Repeater {
              model: root.playlistTracks || []

              delegate: Rectangle {
                width: tracksCol.width
                height: Style.space(44)
                radius: Style.cornerRadius
                color: trackMouse.containsMouse ? Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.08) : "transparent"

                MouseArea {
                  id: trackMouse
                  anchors.fill: parent
                  hoverEnabled: true
                  cursorShape: Qt.PointingHandCursor
                  onClicked: root.playTrackRequested(modelData, index)
                }

                Row {
                  anchors.fill: parent
                  anchors.leftMargin: Style.space(6)
                  anchors.rightMargin: Style.space(6)
                  spacing: Style.space(8)

                  // Thumbnail
                  Rectangle {
                    width: Style.space(32)
                    height: Style.space(32)
                    radius: Math.max(0, Style.cornerRadius - 2)
                    anchors.verticalCenter: parent.verticalCenter
                    color: Qt.rgba(0, 0, 0, 0.2)
                    clip: true

                    Image {
                      anchors.fill: parent
                      source: modelData.thumbnail_url || ""
                      fillMode: Image.PreserveAspectCrop
                      asynchronous: true
                    }
                  }

                  // Track Info (expanded width)
                  Column {
                    width: parent.width - Style.space(130)
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1

                    Text {
                      width: parent.width
                      text: modelData.title || ""
                      color: root.foreground
                      font.bold: true
                      font.pixelSize: Style.font.caption
                      elide: Text.ElideRight
                    }

                    Text {
                      width: parent.width
                      text: (modelData.artist || "") + (modelData.duration_seconds ? (" • " + Utils.formatSeconds(modelData.duration_seconds)) : "")
                      color: root.dim
                      font.pixelSize: Style.space(10)
                      elide: Text.ElideRight
                    }
                  }

                  // Play Button
                  IconButton {
                    text: "\uf04b"
                    buttonSize: Style.space(26)
                    anchors.verticalCenter: parent.verticalCenter
                    toolTipText: "Play Song"
                    foreground: root.foreground
                    onClicked: root.playTrackRequested(modelData, index)
                  }

                  // Add to Queue (Options: Next / End)
                  IconButton {
                    text: "\uf03a"
                    buttonSize: Style.space(24)
                    anchors.verticalCenter: parent.verticalCenter
                    toolTipText: "Add to Queue Options"
                    foreground: root.foreground
                    onClicked: root.openQueueOptionsRequested(modelData)
                  }

                  // Add to Playlist
                  IconButton {
                    text: "\uf067"
                    buttonSize: Style.space(24)
                    anchors.verticalCenter: parent.verticalCenter
                    toolTipText: "Add to Playlist"
                    foreground: root.foreground
                    onClicked: root.addToPlaylistRequested(modelData)
                  }
                }
              }
            }
          }
        }
      }

      // ==========================================
      // VIEW 2: Playlists Overview List
      // ==========================================
      Item {
        anchors.fill: parent
        visible: root.openedPlaylist === null

        Text {
          anchors.centerIn: parent
          text: "Loading playlists..."
          color: root.dim
          font.pixelSize: Style.font.body
          visible: root.isLoading
        }

        Text {
          anchors.centerIn: parent
          text: "No playlists found"
          color: root.dim
          font.pixelSize: Style.font.body
          visible: !root.isLoading && (!root.playlists || root.playlists.length === 0)
        }

        Flickable {
          id: plFlick
          anchors.fill: parent
          contentWidth: width
          contentHeight: plColumn.implicitHeight
          clip: true
          visible: !root.isLoading && root.playlists && root.playlists.length > 0
          boundsBehavior: Flickable.StopAtBounds

          Column {
            id: plColumn
            width: parent.width
            spacing: Style.space(4)

            Repeater {
              model: root.playlists || []

              delegate: Rectangle {
                width: plColumn.width
                height: Style.space(48)
                radius: Style.cornerRadius
                color: plMouse.containsMouse ? Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.08) : "transparent"

                // Clicking anywhere on the row opens the playlist detail view
                MouseArea {
                  id: plMouse
                  anchors.fill: parent
                  hoverEnabled: true
                  cursorShape: Qt.PointingHandCursor
                  onClicked: root.openPlaylistRequested(modelData)
                }

                Row {
                  anchors.fill: parent
                  anchors.leftMargin: Style.space(8)
                  anchors.rightMargin: Style.space(8)
                  spacing: Style.space(10)

                  // Playlist Thumbnail
                  Rectangle {
                    width: Style.space(36)
                    height: Style.space(36)
                    radius: Math.max(0, Style.cornerRadius - 2)
                    anchors.verticalCenter: parent.verticalCenter
                    color: Qt.rgba(0, 0, 0, 0.2)
                    clip: true

                    Image {
                      anchors.fill: parent
                      source: modelData.thumbnail_url || ""
                      fillMode: Image.PreserveAspectCrop
                      asynchronous: true
                    }

                    Text {
                      anchors.centerIn: parent
                      text: "\uf07b"
                      color: root.dim
                      font.pixelSize: Style.space(16)
                      visible: !modelData.thumbnail_url
                    }
                  }

                  // Playlist Details
                  Column {
                    width: parent.width - Style.space(85)
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1

                    Text {
                      width: parent.width
                      text: modelData.title || "Untitled Playlist"
                      color: root.foreground
                      font.bold: true
                      font.pixelSize: Style.font.caption
                      elide: Text.ElideRight
                    }

                    Text {
                      width: parent.width
                      text: (modelData.track_count ? (modelData.track_count + " songs") : "") + (modelData.author ? (" • " + modelData.author) : "")
                      color: root.dim
                      font.pixelSize: Style.space(10)
                      elide: Text.ElideRight
                    }
                  }

                  // Play Direct Button
                  IconButton {
                    text: "\uf04b"
                    buttonSize: Style.space(28)
                    anchors.verticalCenter: parent.verticalCenter
                    toolTipText: "Play All"
                    foreground: root.foreground
                    onClicked: root.playPlaylistRequested(modelData.playlist_id)
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}

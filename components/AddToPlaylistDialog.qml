import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Ui

Rectangle {
  id: root

  property var track: null
  property var playlists: []
  property color foreground: Color.foreground
  property color dim: Qt.darker(foreground, 1.55)
  property string statusMessage: ""
  property bool isSuccessStatus: true

  function setStatusMessage(msg, isSuccess) {
    statusMessage = msg
    isSuccessStatus = isSuccess
    closeTimer.restart()
  }

  signal playlistSelected(string playlistId, string videoId)
  signal closeRequested()

  radius: Style.cornerRadius
  color: Color.popups.background
  border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.15)
  border.width: 1

  Column {
    anchors.fill: parent
    anchors.margins: Style.space(12)
    spacing: Style.space(8)

    // Header
    Row {
      width: parent.width
      Text {
        text: "ADD TO PLAYLIST"
        color: root.dim
        font.bold: true
        font.pixelSize: Style.space(11)
        anchors.verticalCenter: parent.verticalCenter
      }

      Item {
        width: parent.width - Style.space(140)
        height: 1
      }

      IconButton {
        text: "\uf00d"
        buttonSize: Style.space(22)
        anchors.verticalCenter: parent.verticalCenter
        onClicked: root.closeRequested()
      }
    }

    Text {
      width: parent.width
      text: root.track ? (root.track.title + " • " + root.track.artist) : ""
      color: root.foreground
      font.pixelSize: Style.font.caption
      elide: Text.ElideRight
    }

    // Divider
    Rectangle {
      width: parent.width
      height: 1
      color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.1)
    }

    // Status banner (Success or Warning)
    Rectangle {
      width: parent.width
      height: Style.space(26)
      radius: Math.max(0, Style.cornerRadius - 2)
      color: root.isSuccessStatus ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.2) : Qt.rgba(229/255, 57/255, 53/255, 0.2)
      border.color: root.isSuccessStatus ? Color.accent : "#e53935"
      border.width: 1
      visible: root.statusMessage !== ""

      Text {
        anchors.centerIn: parent
        text: root.statusMessage
        color: root.isSuccessStatus ? Color.accent : "#e53935"
        font.bold: true
        font.pixelSize: Style.font.caption
      }
    }

    // Playlists list
    ListView {
      id: plList
      width: parent.width
      height: parent.height - Style.space(80)
      model: root.playlists
      clip: true
      spacing: Style.space(4)

      delegate: Rectangle {
        width: plList.width
        height: Style.space(36)
        radius: Math.max(0, Style.cornerRadius - 2)
        color: pMouse.containsMouse ? Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.08) : "transparent"

        Row {
          anchors.fill: parent
          anchors.leftMargin: Style.space(8)
          anchors.rightMargin: Style.space(8)
          spacing: Style.space(8)

          Text {
            text: "\uf07b"
            color: root.dim
            anchors.verticalCenter: parent.verticalCenter
            font.pixelSize: Style.space(13)
          }

          Text {
            width: parent.width - Style.space(50)
            text: modelData.title || ""
            color: root.foreground
            font.pixelSize: Style.font.caption
            elide: Text.ElideRight
            anchors.verticalCenter: parent.verticalCenter
          }
        }

        MouseArea {
          id: pMouse
          anchors.fill: parent
          hoverEnabled: true
          cursorShape: Qt.PointingHandCursor
          onClicked: {
            if (root.track && root.track.video_id) {
              root.statusMessage = "Adding..."
              root.isSuccessStatus = true
              root.playlistSelected(modelData.playlist_id, root.track.video_id);
            }
          }
        }
      }
    }
  }

  Timer {
    id: closeTimer
    interval: 1800
    onTriggered: {
      if (root.isSuccessStatus) {
        root.statusMessage = "";
        root.closeRequested();
      }
    }
  }
}

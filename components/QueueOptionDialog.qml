import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Ui

Rectangle {
  id: root

  property var track: null
  property color foreground: Color.foreground
  property color dim: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.55)

  signal playNextRequested(var track)
  signal addToEndRequested(var track)
  signal closeRequested()

  radius: Style.cornerRadius
  color: Color.popups.background
  border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.15)
  border.width: 1

  Column {
    anchors.fill: parent
    anchors.margins: Style.space(12)
    spacing: Style.space(12)

    // Header
    Row {
      width: parent.width

      Text {
        text: "ADD TO QUEUE"
        color: root.dim
        font.bold: true
        font.pixelSize: Style.space(11)
        anchors.verticalCenter: parent.verticalCenter
      }

      Item {
        width: parent.width - Style.space(120)
        height: 1
      }

      IconButton {
        text: "\uf00d"
        buttonSize: Style.space(22)
        anchors.verticalCenter: parent.verticalCenter
        foreground: root.foreground
        onClicked: root.closeRequested()
      }
    }

    // Track Title / Info
    Column {
      width: parent.width
      spacing: 2

      Text {
        width: parent.width
        text: root.track ? (root.track.title || "Selected Track") : ""
        color: root.foreground
        font.bold: true
        font.pixelSize: Style.font.caption
        elide: Text.ElideRight
      }

      Text {
        width: parent.width
        text: root.track ? (root.track.artist || "") : ""
        color: root.dim
        font.pixelSize: Style.space(10)
        elide: Text.ElideRight
      }
    }

    Rectangle {
      width: parent.width
      height: 1
      color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.1)
    }

    // Options Container
    Column {
      width: parent.width
      spacing: Style.space(8)

      // Option 1: Play Next (reproducir a continuación)
      Rectangle {
        width: parent.width
        height: Style.space(42)
        radius: Style.cornerRadius
        color: nextMouse.containsMouse ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.15) : Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.06)
        border.color: nextMouse.containsMouse ? Color.accent : "transparent"
        border.width: 1

        MouseArea {
          id: nextMouse
          anchors.fill: parent
          hoverEnabled: true
          cursorShape: Qt.PointingHandCursor
          onClicked: {
            root.playNextRequested(root.track)
            root.closeRequested()
          }
        }

        Row {
          anchors.fill: parent
          anchors.leftMargin: Style.space(10)
          anchors.rightMargin: Style.space(10)
          spacing: Style.space(10)

          Text {
            text: "\uf051"
            color: Color.accent
            font.pixelSize: Style.space(14)
            anchors.verticalCenter: parent.verticalCenter
          }

          Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1

            Text {
              text: "Play Next"
              color: root.foreground
              font.bold: true
              font.pixelSize: Style.font.caption
            }

            Text {
              text: "Insert right after current song"
              color: root.dim
              font.pixelSize: Style.space(9)
            }
          }
        }
      }

      // Option 2: Add to End of Queue (añadir al final)
      Rectangle {
        width: parent.width
        height: Style.space(42)
        radius: Style.cornerRadius
        color: endMouse.containsMouse ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.15) : Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.06)
        border.color: endMouse.containsMouse ? Color.accent : "transparent"
        border.width: 1

        MouseArea {
          id: endMouse
          anchors.fill: parent
          hoverEnabled: true
          cursorShape: Qt.PointingHandCursor
          onClicked: {
            root.addToEndRequested(root.track)
            root.closeRequested()
          }
        }

        Row {
          anchors.fill: parent
          anchors.leftMargin: Style.space(10)
          anchors.rightMargin: Style.space(10)
          spacing: Style.space(10)

          Text {
            text: "\uf03a"
            color: root.foreground
            font.pixelSize: Style.space(14)
            anchors.verticalCenter: parent.verticalCenter
          }

          Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1

            Text {
              text: "Add to End of Queue"
              color: root.foreground
              font.bold: true
              font.pixelSize: Style.font.caption
            }

            Text {
              text: "Append to the end of playback list"
              color: root.dim
              font.pixelSize: Style.space(9)
            }
          }
        }
      }
    }
  }
}

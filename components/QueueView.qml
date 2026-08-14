import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Ui
import "../ytmusic.js" as Utils

Item {
  id: root

  property var queue: []
  property int currentIndex: -1
  property color foreground: Color.foreground
  property color dim: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.55)

  signal playQueueIndexRequested(int index)
  signal removeQueueIndexRequested(int index)
  signal clearQueueRequested()
  signal closeRequested()

  function scrollToCurrent() {
    if (root.currentIndex >= 0 && root.currentIndex < root.queue.length && queueList.count > 0) {
      Qt.callLater(function() {
        queueList.positionViewAtIndex(root.currentIndex, ListView.Center)
      })
    }
  }

  onVisibleChanged: {
    if (visible) scrollToCurrent()
  }

  onCurrentIndexChanged: {
    if (visible) scrollToCurrent()
  }

  onQueueChanged: {
    if (visible) scrollToCurrent()
  }

  Column {
    anchors.fill: parent
    spacing: Style.space(8)

    // Header with actions
    Item {
      width: parent.width
      height: Style.space(26)

      Row {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.space(6)

        IconButton {
          text: "\uf060"
          buttonSize: Style.space(24)
          toolTipText: "Back to Player"
          foreground: root.foreground
          onClicked: root.closeRequested()
        }

        Text {
          text: "PLAYBACK QUEUE (" + root.queue.length + ")"
          color: root.dim
          font.bold: true
          font.pixelSize: Style.space(11)
          anchors.verticalCenter: parent.verticalCenter
        }
      }

      IconButton {
        text: "\uf1f8"
        buttonSize: Style.space(24)
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        toolTipText: "Clear Queue"
        foreground: root.foreground
        visible: root.queue.length > 1
        onClicked: root.clearQueueRequested()
      }
    }

    // Queue List
    Item {
      width: parent.width
      height: parent.height - Style.space(34)

      Text {
        anchors.centerIn: parent
        text: "Queue is empty."
        color: root.dim
        font.pixelSize: Style.font.caption
        visible: root.queue.length === 0
      }

      ListView {
        id: queueList
        anchors.fill: parent
        model: root.queue
        clip: true
        spacing: Style.space(3)
        boundsBehavior: Flickable.StopAtBounds
        visible: root.queue.length > 0
        currentIndex: root.currentIndex

        delegate: Rectangle {
          id: trackRow
          width: queueList.width
          height: Style.space(42)
          radius: Style.cornerRadius
          color: index === root.currentIndex ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.15) : (trackMouse.containsMouse ? Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.08) : "transparent")

          MouseArea {
            id: trackMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.playQueueIndexRequested(index)
          }

          Row {
            anchors.fill: parent
            anchors.leftMargin: Style.space(6)
            anchors.rightMargin: Style.space(6)
            spacing: Style.space(8)

            // Index or Playing Icon
            Text {
              width: Style.space(20)
              text: index === root.currentIndex ? "\uf028" : String(index + 1)
              color: index === root.currentIndex ? Color.accent : root.dim
              font.bold: index === root.currentIndex
              font.pixelSize: Style.font.caption
              anchors.verticalCenter: parent.verticalCenter
              horizontalAlignment: Text.AlignHCenter
            }

            // Track Details
            Column {
              width: parent.width - Style.space(65)
              anchors.verticalCenter: parent.verticalCenter
              spacing: 1

              Text {
                width: parent.width
                text: modelData.title || "Unknown Title"
                color: index === root.currentIndex ? Color.accent : root.foreground
                font.bold: index === root.currentIndex
                font.pixelSize: Style.font.caption
                elide: Text.ElideRight
              }

              Text {
                width: parent.width
                text: modelData.artist || "Unknown Artist"
                color: root.dim
                font.pixelSize: Style.space(10)
                elide: Text.ElideRight
              }
            }

            // Remove Button
            IconButton {
              text: "\uf00d"
              buttonSize: Style.space(24)
              anchors.verticalCenter: parent.verticalCenter
              toolTipText: "Remove from Queue"
              foreground: root.foreground
              visible: index !== root.currentIndex && (trackMouse.containsMouse || root.queue.length < 5)
              onClicked: root.removeQueueIndexRequested(index)
            }
          }
        }
      }
    }
  }
}

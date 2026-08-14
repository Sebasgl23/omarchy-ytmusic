import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Ui
import "../ytmusic.js" as Utils

Item {
  id: root

  property var searchResults: []
  property bool isSearching: false
  property color foreground: Color.foreground
  property color dim: Qt.darker(foreground, 1.55)

  signal searchRequested(string query)
  signal clearRequested()
  signal playTrackRequested(var track)
  signal openQueueOptionsRequested(var track)
  signal addToPlaylistRequested(var track)

  implicitWidth: Style.space(340)
  implicitHeight: Style.space(380)

  Column {
    anchors.fill: parent
    spacing: Style.space(10)

    // Search Input Bar
    Rectangle {
      width: parent.width
      height: Style.space(36)
      radius: Style.cornerRadius
      color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.08)
      border.color: searchInput.activeFocus ? Color.accent : "transparent"
      border.width: 1

      Row {
        anchors.fill: parent
        anchors.leftMargin: Style.space(10)
        anchors.rightMargin: Style.space(10)
        spacing: Style.space(8)

        Text {
          text: "\uf002"
          color: root.dim
          font.pixelSize: Style.space(13)
          anchors.verticalCenter: parent.verticalCenter
        }

        TextInput {
          id: searchInput
          width: parent.width - Style.space(60)
          height: parent.height
          color: root.foreground
          verticalAlignment: TextInput.AlignVCenter
          font.pixelSize: Style.font.body
          selectByMouse: true
          clip: true

          Text {
            text: "Search YouTube Music..."
            color: root.dim
            font.pixelSize: Style.font.body
            anchors.verticalCenter: parent.verticalCenter
            visible: !searchInput.text && !searchInput.activeFocus
          }

          onTextChanged: {
            if (text.trim().length >= 3) {
              searchDebounceTimer.restart();
            } else if (text.trim().length === 0) {
              searchDebounceTimer.stop();
              root.clearRequested();
            }
          }

          onAccepted: {
            searchDebounceTimer.stop();
            if (text.trim() !== "") {
              root.searchRequested(text.trim());
            }
          }
        }

        Timer {
          id: searchDebounceTimer
          interval: 500
          repeat: false
          onTriggered: {
            if (searchInput.text.trim().length >= 3) {
              root.searchRequested(searchInput.text.trim());
            }
          }
        }

        IconButton {
          visible: searchInput.text !== ""
          text: "\uf00d"
          buttonSize: Style.space(22)
          anchors.verticalCenter: parent.verticalCenter
          onClicked: {
            searchInput.text = "";
            searchDebounceTimer.stop();
            root.clearRequested();
          }
        }
      }
    }

    // Results & Status Container
    Item {
      width: parent.width
      height: parent.height - Style.space(46)

      // Searching State
      Text {
        anchors.centerIn: parent
        text: "Searching..."
        color: root.dim
        font.pixelSize: Style.font.body
        visible: root.isSearching
      }

      // Empty State
      Column {
        anchors.centerIn: parent
        spacing: Style.space(6)
        visible: !root.isSearching && (!root.searchResults || root.searchResults.length === 0)

        Text {
          anchors.horizontalCenter: parent.horizontalCenter
          text: "\uf001"
          color: root.dim
          font.pixelSize: Style.space(28)
        }

        Text {
          anchors.horizontalCenter: parent.horizontalCenter
          text: "Type to search songs & artists"
          color: root.dim
          font.pixelSize: Style.font.caption
        }
      }

      // Scrollable Results List
      Flickable {
        id: resultsFlick
        anchors.fill: parent
        contentWidth: width
        contentHeight: resultsColumn.implicitHeight
        clip: true
        visible: !root.isSearching && root.searchResults && root.searchResults.length > 0
        boundsBehavior: Flickable.StopAtBounds

        Column {
          id: resultsColumn
          width: parent.width
          spacing: Style.space(4)

          Repeater {
            model: root.searchResults || []

            delegate: Rectangle {
              id: trackDelegate
              width: resultsColumn.width
              height: Style.space(46)
              radius: Style.cornerRadius
              color: itemMouse.containsMouse ? Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.08) : "transparent"

              MouseArea {
                id: itemMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.playTrackRequested(modelData)
              }

              Row {
                anchors.fill: parent
                anchors.leftMargin: Style.space(6)
                anchors.rightMargin: Style.space(6)
                spacing: Style.space(8)

                // Thumbnail
                Rectangle {
                  width: Style.space(34)
                  height: Style.space(34)
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

                // Info
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

                // Play Action
                IconButton {
                  text: "\uf04b"
                  buttonSize: Style.space(26)
                  anchors.verticalCenter: parent.verticalCenter
                  toolTipText: "Play Now"
                  foreground: root.foreground
                  onClicked: root.playTrackRequested(modelData)
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
  }
}

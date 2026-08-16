import QtQuick
import QtQuick.Controls
import Quickshell
import qs.Commons
import qs.Ui

Item {
  id: root

  property var  homeData: []
  property bool isLoadingHome: false
  property var  foreground: Qt.rgba(1, 1, 1, 1)
  
  signal itemClicked(var item)

  property color dim: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.6)

  // Loading state
  Text {
    anchors.centerIn: parent
    text: "Loading Home..."
    color: root.dim
    visible: root.isLoadingHome && (!root.homeData || root.homeData.length === 0)
  }

  ScrollView {
    anchors.fill: parent
    contentWidth: availableWidth
    clip: true
    visible: !root.isLoadingHome || (root.homeData && root.homeData.length > 0)

    Column {
      width: parent.width
      spacing: Style.space(24)
      padding: Style.space(16)

      Repeater {
        model: root.homeData

        Column {
          width: parent.width
          spacing: Style.space(12)

          Text {
            text: modelData.title || "Section"
            color: root.foreground
            font.bold: true
            font.pixelSize: Style.space(18)
          }

          ListView {
            width: parent.width
            height: Style.space(220)
            orientation: ListView.Horizontal
            spacing: Style.space(16)
            clip: false
            model: modelData.contents

            delegate: Item {
              width: Style.space(130)
              height: parent.height

              Rectangle {
                id: card
                anchors.fill: parent
                color: "transparent"

                Column {
                  anchors.fill: parent
                  spacing: Style.space(8)

                  // Thumbnail
                  Rectangle {
                    width: parent.width
                    height: parent.width
                    radius: Style.cornerRadius
                    color: Qt.rgba(0, 0, 0, 0.3)
                    clip: true

                    Image {
                      anchors.fill: parent
                      fillMode: Image.PreserveAspectCrop
                      source: (modelData.thumbnails && modelData.thumbnails.length > 0) 
                              ? modelData.thumbnails[modelData.thumbnails.length - 1].url 
                              : ""
                      asynchronous: true
                    }
                  }

                  // Title
                  Text {
                    width: parent.width
                    text: modelData.title || ""
                    color: root.foreground
                    font.bold: true
                    font.pixelSize: Style.space(13)
                    elide: Text.ElideRight
                    maximumLineCount: 2
                    wrapMode: Text.Wrap
                  }

                  // Subtitle
                  Text {
                    width: parent.width
                    text: modelData.description || modelData.subtitle || ""
                    color: root.dim
                    font.pixelSize: Style.space(11)
                    elide: Text.ElideRight
                    maximumLineCount: 1
                  }
                }

                MouseArea {
                  anchors.fill: parent
                  cursorShape: Qt.PointingHandCursor
                  onClicked: root.itemClicked(modelData)
                }
              }
            }
          }
        }
      }
    }
  }
}

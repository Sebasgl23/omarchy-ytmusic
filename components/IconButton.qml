import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Ui

Item {
  id: root

  property string text: ""
  property string toolTipText: ""
  property bool active: false
  property bool primary: false
  property real buttonSize: Style.space(32)
  property color foreground: Color.foreground
  property color activeColor: Color.accent

  signal clicked()

  implicitWidth: buttonSize
  implicitHeight: buttonSize

  Rectangle {
    id: bg
    anchors.fill: parent
    radius: root.primary ? height / 2 : Style.cornerRadius
    color: {
      if (root.primary) return mouseArea.pressed ? Qt.darker(Color.accent, 1.2) : (mouseArea.containsMouse ? Qt.lighter(Color.accent, 1.1) : Color.accent)
      if (root.active) return Qt.rgba(root.activeColor.r, root.activeColor.g, root.activeColor.b, 0.2)
      return mouseArea.containsMouse ? Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.12) : "transparent"
    }

    Behavior on color {
      ColorAnimation { duration: 120 }
    }

    Text {
      id: iconLabel
      anchors.centerIn: parent
      text: root.text
      font.pixelSize: root.primary ? Style.space(16) : Style.space(13)
      color: {
        if (root.primary) return "#FFFFFF"
        if (root.active) return root.activeColor
        return mouseArea.containsMouse ? root.foreground : Qt.darker(root.foreground, 1.3)
      }
    }
  }

  MouseArea {
    id: mouseArea
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onClicked: root.clicked()
  }

  ToolTip {
    visible: mouseArea.containsMouse && root.toolTipText !== ""
    text: root.toolTipText
    delay: 400
  }
}

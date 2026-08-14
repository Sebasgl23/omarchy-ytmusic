import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Ui
import "../ytmusic.js" as Utils

Item {
  id: root

  property string trackTitle: "No track playing"
  property string trackArtist: ""
  property string trackThumbnail: ""
  property string trackVideoId: ""
  property real position: 0
  property real duration: 0
  property bool isPlaying: false
  property int volume: 100
  property int lastNonZeroVolume: 100
  property bool isLiked: false
  property string repeatMode: "off"
  property bool isShuffled: false

  property color foreground: Color.foreground
  property color dim: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.55)

  readonly property real progress: duration > 0 ? Math.max(0, Math.min(1, position / duration)) : 0

  signal togglePlay()
  signal nextTrack()
  signal prevTrack()
  signal seekTrack(real seconds)
  signal changeVolume(int level)
  signal toggleShuffle()
  signal toggleRepeat()
  signal toggleLike()
  signal addToPlaylist()
  signal showQueue()

  Column {
    anchors.fill: parent
    spacing: Style.space(12)

    // Center Card: Album Art + Titles
    Column {
      width: parent.width
      spacing: Style.space(10)

      // Album Art Container (Expanded, perfectly centered)
      Rectangle {
        id: artContainer
        width: Style.space(145)
        height: Style.space(145)
        radius: Style.cornerRadius
        color: Qt.rgba(0, 0, 0, 0.25)
        anchors.horizontalCenter: parent.horizontalCenter
        clip: true

        Image {
          anchors.fill: parent
          source: root.trackThumbnail
          fillMode: Image.PreserveAspectCrop
          asynchronous: true
          visible: root.trackThumbnail !== ""
        }

        // Subtle, minimalist empty state icon
        Text {
          anchors.centerIn: parent
          text: "\uf001"
          color: root.dim
          font.pixelSize: Style.space(32)
          opacity: 0.35
          visible: root.trackThumbnail === ""
        }
      }

      // Title & Artist with Marquee Scrolling for Long Titles
      Column {
        width: parent.width
        spacing: Style.space(2)

        Item {
          id: titleClip
          width: parent.width
          height: titleText.implicitHeight
          clip: true

          Text {
            id: titleText
            text: root.trackTitle
            color: root.foreground
            font.bold: true
            font.pixelSize: Style.font.body
            anchors.verticalCenter: parent.verticalCenter
            
            readonly property bool needsScroll: implicitWidth > titleClip.width

            x: needsScroll ? 0 : (titleClip.width - implicitWidth) / 2

            SequentialAnimation on x {
              running: titleText.needsScroll && root.isPlaying
              loops: Animation.Infinite

              PauseAnimation { duration: 1500 }
              NumberAnimation {
                from: 0
                to: -(titleText.implicitWidth - titleClip.width + 12)
                duration: Math.max(3000, (titleText.implicitWidth - titleClip.width) * 35)
                easing.type: Easing.Linear
              }
              PauseAnimation { duration: 2000 }
              NumberAnimation {
                to: 0
                duration: 600
                easing.type: Easing.InOutQuad
              }
            }
          }
        }

        Item {
          id: artistClip
          width: parent.width
          height: artistText.implicitHeight
          clip: true

          Text {
            id: artistText
            text: root.trackArtist
            color: root.dim
            font.pixelSize: Style.font.caption
            anchors.verticalCenter: parent.verticalCenter

            readonly property bool needsScroll: implicitWidth > artistClip.width

            x: needsScroll ? 0 : (artistClip.width - implicitWidth) / 2

            SequentialAnimation on x {
              running: artistText.needsScroll && root.isPlaying
              loops: Animation.Infinite

              PauseAnimation { duration: 1500 }
              NumberAnimation {
                from: 0
                to: -(artistText.implicitWidth - artistClip.width + 12)
                duration: Math.max(3000, (artistText.implicitWidth - artistClip.width) * 35)
                easing.type: Easing.Linear
              }
              PauseAnimation { duration: 2000 }
              NumberAnimation {
                to: 0
                duration: 600
                easing.type: Easing.InOutQuad
              }
            }
          }
        }
      }
    }

    // Seekbar & Timestamps
    Column {
      width: parent.width
      spacing: Style.space(3)

      Rectangle {
        id: seekTrack
        width: parent.width
        height: Style.space(6)
        radius: height / 2
        color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.15)

        Rectangle {
          width: parent.width * root.progress
          height: parent.height
          radius: parent.radius
          color: Color.accent
        }

        MouseArea {
          anchors.fill: parent
          cursorShape: Qt.PointingHandCursor
          onClicked: function(mouse) {
            var ratio = Math.max(0, Math.min(1, mouse.x / width))
            root.seekTrack(ratio * root.duration)
          }
        }
      }

      Item {
        width: parent.width
        height: Style.space(12)

        Text {
          anchors.left: parent.left
          anchors.verticalCenter: parent.verticalCenter
          text: Utils.formatSeconds(root.position)
          color: root.dim
          font.pixelSize: Style.space(10)
        }

        Text {
          anchors.right: parent.right
          anchors.verticalCenter: parent.verticalCenter
          text: Utils.formatSeconds(root.duration)
          color: root.dim
          font.pixelSize: Style.space(10)
        }
      }
    }

    // Controls Row (Shuffle, Prev, Play/Pause, Next, Repeat)
    Row {
      anchors.horizontalCenter: parent.horizontalCenter
      spacing: Style.space(8)

      IconButton {
        text: "\uf074"
        active: root.isShuffled
        buttonSize: Style.space(32)
        toolTipText: "Shuffle"
        foreground: root.foreground
        onClicked: root.toggleShuffle()
      }

      IconButton {
        text: "\uf049"
        buttonSize: Style.space(32)
        toolTipText: "Previous Track"
        foreground: root.foreground
        onClicked: root.prevTrack()
      }

      IconButton {
        primary: true
        text: root.isPlaying ? "\uf04c" : "\uf04b"
        buttonSize: Style.space(38)
        toolTipText: root.isPlaying ? "Pause" : "Play"
        foreground: root.foreground
        onClicked: root.togglePlay()
      }

      IconButton {
        text: "\uf050"
        buttonSize: Style.space(32)
        toolTipText: "Next Track"
        foreground: root.foreground
        onClicked: root.nextTrack()
      }

      IconButton {
        text: root.repeatMode === "one" ? "\uf01e" : "\uf021"
        active: root.repeatMode !== "off"
        buttonSize: Style.space(32)
        toolTipText: "Repeat (" + root.repeatMode + ")"
        foreground: root.foreground
        onClicked: root.toggleRepeat()
      }
    }

    // Bottom Action Row (Like, Add to Playlist, Volume Slider)
    Item {
      width: parent.width
      height: Style.space(32)

      Row {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.space(6)

        IconButton {
          text: root.isLiked ? "\uf004" : "\uf08a"
          active: root.isLiked
          activeColor: "#e53935"
          buttonSize: Style.space(28)
          toolTipText: root.isLiked ? "Liked" : "Like Song"
          foreground: root.foreground
          onClicked: root.toggleLike()
        }

        IconButton {
          text: "\uf067"
          buttonSize: Style.space(28)
          toolTipText: "Add to Playlist"
          foreground: root.foreground
          onClicked: root.addToPlaylist()
        }

        IconButton {
          text: "\uf03a"
          buttonSize: Style.space(28)
          toolTipText: "Playback Queue"
          foreground: root.foreground
          onClicked: root.showQueue()
        }
      }

      // Volume Slider + Mute/Unmute Icon
      Row {
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.space(6)

        IconButton {
          text: root.volume === 0 ? "\uf026" : (root.volume < 50 ? "\uf027" : "\uf028")
          buttonSize: Style.space(24)
          toolTipText: root.volume === 0 ? "Unmute" : "Mute"
          foreground: root.volume === 0 ? root.dim : root.foreground
          anchors.verticalCenter: parent.verticalCenter
          onClicked: {
            if (root.volume > 0) {
              root.lastNonZeroVolume = root.volume
              root.changeVolume(0)
            } else {
              root.changeVolume(root.lastNonZeroVolume > 0 ? root.lastNonZeroVolume : 100)
            }
          }
        }

        Rectangle {
          id: volTrack
          width: Style.space(75)
          height: Style.space(4)
          radius: height / 2
          color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.15)
          anchors.verticalCenter: parent.verticalCenter

          Rectangle {
            width: parent.width * (Math.max(0, Math.min(100, root.volume)) / 100)
            height: parent.height
            radius: parent.radius
            color: Color.accent
          }

          MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: function(mouse) {
              var ratio = Math.max(0, Math.min(1, mouse.x / width))
              var newVol = Math.round(ratio * 100)
              if (newVol > 0) root.lastNonZeroVolume = newVol
              root.changeVolume(newVol)
            }
          }
        }
      }
    }
  }
}

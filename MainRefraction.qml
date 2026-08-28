import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Window {
    id: root
    width: 960
    height: 780
    minimumWidth: 860
    minimumHeight: 700
    visible: true
    color: "transparent"
    flags: Qt.Window | Qt.FramelessWindowHint
    title: "VBL Macro"

    property bool armed: false
    property bool robloxFocused: false
    property int fires: 0
    property string lastKey: "—"
    property string lastTime: "—"
    property real uptime: 0
    property real t: 0
    property real reactive: 0
    property string toastText: ""
    property int toastVersion: 0

    function hhmmss(total) {
        var s = Math.floor(total)
        var h = Math.floor(s / 3600)
        var m = Math.floor((s % 3600) / 60)
        var sec = s % 60
        return (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m + ":" + (sec < 10 ? "0" : "") + sec
    }

    function rate() {
        return uptime > 1 ? Math.round(fires / (uptime / 60)) : 0
    }

    function fire(key, steps) {
        fires += 1
        lastKey = key
        lastTime = Qt.formatTime(new Date(), "hh:mm:ss")
        reactive = 1
        toastText = key + "  •  COMBO EXECUTED"
        toastVersion += 1
        comboProgress = steps
        comboTimer.restart()
    }

    property int comboProgress: 0

    Connections {
        target: bridge
        function onStateChanged(started, focused) {
            root.armed = started
            root.robloxFocused = focused
            if (started && uptime === 0) uptimeTimer.restart()
            if (!started) uptime = 0
        }
        function onFired(key, steps) { root.fire(key, steps) }
        function onTelemetry(count, key, stamp) {
            root.fires = count
            root.lastKey = key
            root.lastTime = stamp
        }
        function onLogLine(line) { logModel.append({ text: line }) }
    }

    ListModel { id: logModel }

    Timer {
        interval: 40
        running: true
        repeat: true
        onTriggered: {
            root.t += 0.025
            root.reactive *= 0.82
        }
    }

    Timer {
        id: uptimeTimer
        interval: 1000
        repeat: true
        running: root.armed
        onTriggered: root.uptime += 1
    }

    Timer {
        id: comboTimer
        interval: 750
        repeat: false
        onTriggered: root.comboProgress = 0
    }

    // Everything here is the scene behind the real glass. The glass shader
    // samples this item as a texture and bends its pixels at the panel rim.
    Item {
        id: backgroundScene
        anchors.fill: parent

        Rectangle {
            anchors.fill: parent
            color: "#05070d"
        }

        Rectangle {
            width: 520; height: 520; radius: 260
            x: -130 + Math.sin(root.t * 0.75) * 60
            y: -180 + Math.cos(root.t * 0.55) * 45
            color: Qt.rgba(0.10, 0.35, 1.0, 0.25)
        }
        Rectangle {
            width: 430; height: 430; radius: 215
            x: parent.width - 260 + Math.cos(root.t * 0.65) * 65
            y: 70 + Math.sin(root.t * 0.82) * 55
            color: Qt.rgba(0.95, 0.08, 0.75, 0.20)
        }
        Rectangle {
            width: 390; height: 390; radius: 195
            x: parent.width * 0.28 + Math.sin(root.t * 0.52) * 80
            y: parent.height - 250 + Math.cos(root.t * 0.72) * 45
            color: Qt.rgba(0.05, 0.80, 0.98, 0.14)
        }

        Repeater {
            model: 14
            Rectangle {
                width: 2
                height: 2
                radius: 1
                x: (index * 137) % Math.max(1, backgroundScene.width)
                y: (index * 83 + 47) % Math.max(1, backgroundScene.height)
                color: Qt.rgba(1, 1, 1, 0.12 + ((index % 3) * 0.04))
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 180
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(0.0, 0.0, 0.0, 0.0) }
                GradientStop { position: 1.0; color: Qt.rgba(0.0, 0.0, 0.0, 0.42) }
            }
        }
    }

    // Full-size background capture used by all LiquidGlass components.
    ShaderEffectSource {
        id: glassCapture
        sourceItem: backgroundScene
        live: true
        recursive: false
        hideSource: false
        textureSize: Qt.size(root.width, root.height)
    }

    Rectangle {
        anchors.fill: parent
        radius: 34
        color: Qt.rgba(0.02, 0.025, 0.05, 0.34)
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.16)
        clip: true

        // RGB edge rail.
        Canvas {
            id: rgbRail
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 4
            onPaint: {
                var ctx = getContext("2d")
                var g = ctx.createLinearGradient(0, 0, width, 0)
                for (var i = 0; i <= 8; ++i) {
                    var hue = (root.t * 0.06 + i / 8) % 1
                    var value = Math.min(1, 0.88 + root.reactive * 0.18)
                    g.addColorStop(i / 8, Qt.hsva(hue, 0.83, value, 1))
                }
                ctx.fillStyle = g
                ctx.fillRect(0, 0, width, height)
            }
        }

        Connections {
            target: root
            function onTChanged() { rgbRail.requestPaint() }
            function onReactiveChanged() { rgbRail.requestPaint() }
        }

        // Custom title bar.
        RowLayout {
            id: titleBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 58
            anchors.leftMargin: 26
            anchors.rightMargin: 18
            anchors.topMargin: 5
            spacing: 9

            Text { text: "VBL"; color: "#4be4ff"; font.pixelSize: 11; font.bold: true }
            Text { text: "MACRO"; color: "white"; font.pixelSize: 18; font.bold: true }
            Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 18; color: Qt.rgba(1,1,1,0.12) }
            Text { text: "LIQUID GLASS EDITION"; color: "#8d98b2"; font.pixelSize: 8; font.bold: true; font.letterSpacing: 1.1 }
            Item { Layout.fillWidth: true }
            Rectangle {
                Layout.preferredWidth: 42; Layout.preferredHeight: 32; radius: 16
                color: Qt.rgba(1,1,1,0.055); border.width: 1; border.color: Qt.rgba(1,1,1,0.10)
                Text { anchors.centerIn: parent; text: "×"; color: "#dde3f2"; font.pixelSize: 18 }
                MouseArea { anchors.fill: parent; onClicked: bridge.quitApp() }
            }
        }

        MouseArea {
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            height: 58
            propagateComposedEvents: true
            onPressed: {
                if (mouse.x < width - 60) root.startSystemMove()
            }
        }

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.leftMargin: 26
            anchors.rightMargin: 26
            anchors.topMargin: 78
            anchors.bottomMargin: 24
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: root.robloxFocused ? "●  ROBLOX LOCK ACQUIRED" : "●  WAITING FOR ROBLOX"
                    color: root.robloxFocused ? "#52eca4" : "#ffd966"
                    font.pixelSize: 10; font.bold: true; font.letterSpacing: 1.0
                }
                Item { Layout.fillWidth: true }
                Text { text: root.fires + " FIRES"; color: "#48ddff"; font.pixelSize: 9; font.bold: true; font.letterSpacing: 0.9 }
                Text { text: "  /  " + root.rate() + "/MIN"; color: "#78839b"; font.pixelSize: 9; font.bold: true }
            }

            // HERO GLASS
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 286

                LiquidGlass {
                    anchors.fill: parent
                    rootWidth: root.width
                    rootHeight: root.height
                    sourceTexture: glassCapture
                    time: root.t
                    distortion: 0.013 + root.reactive * 0.004
                    aberration: 0.60
                    blur: 0.0035
                    tintOpacity: 0.10
                    tintColor: root.robloxFocused ? "#7effbc" : "#fff1a0"
                }

                Rectangle {
                    anchors.fill: parent
                    radius: 26
                    color: Qt.rgba(0.10,0.12,0.19,0.18)
                    border.width: 1
                    border.color: Qt.rgba(1,1,1,0.12)
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 26

                    Item {
                        Layout.preferredWidth: 180
                        Layout.fillHeight: true

                        Canvas {
                            anchors.centerIn: parent
                            width: 150; height: 150
                            onPaint: {
                                var c = getContext("2d")
                                var cx = width/2, cy = height/2
                                c.clearRect(0,0,width,height)
                                var pulse = (Math.sin(root.t*4)+1)/2 + root.reactive
                                for (var i=0;i<7;i++) {
                                    var r = 31 + i*4 + pulse*2
                                    var alpha = Math.max(0.02, 0.13 - i*0.016)
                                    c.beginPath(); c.arc(cx,cy,r,0,Math.PI*2)
                                    c.strokeStyle = Qt.rgba(root.armed?0.25:0.55, root.armed?1:0.75, 1, alpha)
                                    c.lineWidth = 2
                                    c.stroke()
                                }
                                c.beginPath(); c.arc(cx,cy,31+pulse*2,0,Math.PI*2)
                                c.fillStyle = Qt.rgba(root.armed?0.05:0.18, root.armed?0.15:0.16, 0.28, 0.72)
                                c.fill(); c.strokeStyle = root.robloxFocused ? "#48ed9f" : "#ffd75b"; c.lineWidth=2.2; c.stroke()
                                c.beginPath(); c.arc(cx,cy,12+pulse,0,Math.PI*2); c.fillStyle="#f8fbff"; c.fill()
                            }
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            text: root.armed ? (root.robloxFocused ? "LIVE" : "WAITING") : "STANDBY"
                            color: root.armed ? (root.robloxFocused ? "#49eba0" : "#ffd85d") : "#7d879b"
                            font.pixelSize: 10; font.bold: true; font.letterSpacing: 1.4
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 10
                        Text { text: "ENGINE STATUS"; color: "#7f8aa2"; font.pixelSize: 9; font.bold: true; font.letterSpacing: 1.1 }
                        Text {
                            text: !root.armed ? "STANDING BY" : (root.robloxFocused ? "ENGINE LIVE" : "WAITING FOR ROBLOX")
                            color: !root.armed ? "#eef2fb" : (root.robloxFocused ? "#52eea4" : "#ffe078")
                            font.pixelSize: 28; font.bold: true
                        }
                        Text {
                            text: !root.armed ? "Ready to arm the precision input engine" : (root.robloxFocused ? "Focus protection is active" : "Focus Roblox to unlock the input engine")
                            color: "#7d879c"; font.pixelSize: 10
                        }
                        Item { Layout.fillHeight: true }

                        Button {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 58
                            text: root.armed ? "■   STOP MACRO" : "▶   START MACRO"
                            font.pixelSize: 13; font.bold: true
                            background: Rectangle {
                                radius: 21
                                border.width: 1
                                border.color: Qt.rgba(1,1,1,0.17)
                                gradient: Gradient {
                                    GradientStop { position: 0; color: root.armed ? "#ff718c" : "#638fff" }
                                    GradientStop { position: 1; color: root.armed ? "#e74b6e" : "#4169e7" }
                                }
                            }
                            contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font: parent.font }
                            onClicked: bridge.toggle()
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "UPTIME  " + root.hhmmss(root.uptime); color: "#7b86a0"; font.pixelSize: 8; font.letterSpacing: 0.8 }
                            Item { Layout.fillWidth: true }
                            Text { text: "FOCUS LOCK  ON"; color: "#4be7a0"; font.pixelSize: 8; font.bold: true; font.letterSpacing: 0.8 }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 174
                spacing: 14

                Repeater {
                    model: [
                        { key: "`", title: "RIGHT CLICK  →  SPACE  →  LEFT CLICK", steps: 3, accent: "#35dcff" },
                        { key: "R", title: "RIGHT CLICK  →  SPACE", steps: 2, accent: "#a46cff" }
                    ]
                    delegate: Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        LiquidGlass {
                            anchors.fill: parent
                            rootWidth: root.width
                            rootHeight: root.height
                            sourceTexture: glassCapture
                            time: root.t
                            distortion: 0.010
                            aberration: 0.45
                            blur: 0.0028
                            tintOpacity: 0.07
                            tintColor: modelData.accent
                        }

                        Rectangle { anchors.fill: parent; radius: 22; color: Qt.rgba(0.06,0.08,0.13,0.20); border.width: 1; border.color: Qt.rgba(1,1,1,0.10) }

                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 18; spacing: 8
                            RowLayout {
                                Layout.fillWidth: true
                                Rectangle { Layout.preferredWidth: 30; Layout.preferredHeight: 30; radius: 10; color: modelData.accent; Text { anchors.centerIn: parent; text: modelData.key; color: "#06101c"; font.pixelSize: 11; font.bold: true } }
                                Text { text: "COMBO PROFILE"; color: "#a3adc1"; font.pixelSize: 8; font.bold: true; font.letterSpacing: 1.0 }
                                Item { Layout.fillWidth: true }
                                Text { text: modelData.steps + "-STEP"; color: modelData.accent; font.pixelSize: 8; font.bold: true }
                            }
                            Text { text: modelData.title; color: "#e9edf8"; font.pixelSize: 10; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                            Item { Layout.fillHeight: true }
                            Row {
                                spacing: 18
                                Repeater {
                                    model: modelData.steps
                                    delegate: Column {
                                        spacing: 4
                                        Rectangle { width: 25; height: 25; radius: 12.5; color: ((modelData.key === "`" ? root.comboProgress : Math.min(root.comboProgress, 2)) >= (index+1)) ? modelData.accent : Qt.rgba(1,1,1,0.06); border.width: 1; border.color: ((modelData.key === "`" ? root.comboProgress : Math.min(root.comboProgress, 2)) >= (index+1)) ? modelData.accent : Qt.rgba(1,1,1,0.10); Text { anchors.centerIn: parent; text: index+1; color: ((modelData.key === "`" ? root.comboProgress : Math.min(root.comboProgress, 2)) >= (index+1)) ? "#06101c" : "#6f7890"; font.pixelSize: 8; font.bold: true } }
                                        Text { text: index===0?"RMB":(index===1?"SPACE":"LMB"); color: "#7d879e"; font.pixelSize: 7; font.bold: true }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // TELEMETRY
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 108
                LiquidGlass { anchors.fill: parent; rootWidth: root.width; rootHeight: root.height; sourceTexture: glassCapture; time: root.t; distortion: 0.008; aberration: 0.35; blur: 0.0025; tintOpacity: 0.045; tintColor: "#55dfff" }
                Rectangle { anchors.fill: parent; radius: 22; color: Qt.rgba(0.06,0.08,0.13,0.18); border.width: 1; border.color: Qt.rgba(1,1,1,0.09) }
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 17; spacing: 9
                    RowLayout { Layout.fillWidth: true; Text { text: "SESSION TELEMETRY"; color: "#7f8aa2"; font.pixelSize: 8; font.bold: true; font.letterSpacing: 1.0 }; Item { Layout.fillWidth: true }; Text { text: "LIVE"; color: "#4be69e"; font.pixelSize: 8; font.bold: true; font.letterSpacing: 1.0 } }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        Metric { label: "FIRES"; value: root.fires; accent: "#35dcff" }
                        Metric { label: "RATE"; value: root.rate()+"/MIN"; accent: "#a46cff" }
                        Metric { label: "LAST KEY"; value: root.lastKey; accent: "#ff59d9" }
                        Metric { label: "UPTIME"; value: root.hhmmss(root.uptime); accent: "#4be69e" }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Text { text: "VBL MACRO  •  LIQUID GLASS"; color: "#4f586f"; font.pixelSize: 8; font.bold: true }
                Item { Layout.fillWidth: true }
                Text { text: "ESC  QUIT  •  FOCUS PROTECTION ON"; color: "#59647c"; font.pixelSize: 8; font.bold: true }
            }
        }
    }

    // Toast: appears on real macro fire and then fades away.
    Rectangle {
        id: toast
        visible: root.toastText.length > 0
        width: 245; height: 48; radius: 24
        anchors.right: parent.right; anchors.rightMargin: 24
        anchors.bottom: parent.bottom; anchors.bottomMargin: 24
        color: Qt.rgba(0.10,0.12,0.18,0.88)
        border.width: 1; border.color: Qt.rgba(1,1,1,0.13)
        scale: 1.0
        opacity: 1.0
        Text { anchors.centerIn: parent; text: "⚡  " + root.toastText; color: "#ecf2ff"; font.pixelSize: 10; font.bold: true }
        SequentialAnimation {
            id: toastAnim
            running: false
            onStarted: { toast.opacity = 0; toast.scale = 0.88 }
            NumberAnimation { target: toast; property: "opacity"; to: 1; duration: 140; easing.type: Easing.OutCubic }
            NumberAnimation { target: toast; property: "scale"; to: 1; duration: 180; easing.type: Easing.OutBack }
            PauseAnimation { duration: 900 }
            ParallelAnimation {
                NumberAnimation { target: toast; property: "opacity"; to: 0; duration: 220 }
                NumberAnimation { target: toast; property: "scale"; to: 0.94; duration: 220 }
            }
            ScriptAction { script: root.toastText = "" }
        }
        Connections {
            target: root
            function onToastVersionChanged() { toastAnim.restart() }
        }
    }
}

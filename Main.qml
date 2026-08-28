import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Window {
    id: win
    width: 900
    height: 760
    minimumWidth: 820
    minimumHeight: 680
    visible: true
    color: "transparent"
    flags: Qt.Window | Qt.FramelessWindowHint
    title: "VBL Macro"

    property bool armed: false
    property bool robloxFocused: false
    property int fires: 0
    property string lastKey: "—"
    property string lastTime: "—"
    property real pulse: 0
    property real rgbPhase: 0
    property bool settingsOpen: false
    property string toastText: ""
    property int toastEpoch: 0
    property real startedAt: 0
    property int visualStep: 0
    property real visualEpoch: 0
    property int rgbMode: 0

    function uptimeSeconds() {
        if (!armed || startedAt === 0) return 0
        return Math.max(0, (Date.now() - startedAt) / 1000)
    }

    function fmtTime(sec) {
        var s = Math.floor(sec)
        var h = Math.floor(s / 3600)
        var m = Math.floor((s % 3600) / 60)
        var r = s % 60
        return (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m + ":" + (r < 10 ? "0" : "") + r
    }

    function fireRate() {
        var up = uptimeSeconds()
        return up > 1 ? Math.round(fires / (up / 60)) : 0
    }

    function glass(c, alpha) {
        return Qt.rgba(c.r, c.g, c.b, alpha)
    }

    function toast(text) {
        toastText = text
        toastEpoch++
    }

    function setStep(key, steps) {
        visualStep = steps
        visualEpoch++
        coreBurst.restart()
        rgbBurst.restart()
        toast((key === "R" ? "R" : "`") + "  •  COMBO EXECUTED")
        stepTimer.restart()
    }

    Connections {
        target: bridge
        function onStateChanged(started, focused) {
            win.armed = started
            win.robloxFocused = focused
            if (started && win.startedAt === 0) win.startedAt = Date.now()
            if (!started) win.startedAt = 0
        }
        function onFired(key, steps) {
            win.fires += 1
            win.lastKey = key
            win.lastTime = Qt.formatTime(new Date(), "hh:mm:ss")
            win.setStep(key, steps)
        }
        function onTelemetry(count, key, stamp) {
            win.fires = count
            win.lastKey = key
            win.lastTime = stamp
        }
        function onLogLine(line) { logModel.append({text: line}) }
    }

    ListModel { id: logModel }

    Timer {
        id: pulseTimer
        interval: 30
        running: true
        repeat: true
        onTriggered: {
            win.rgbPhase += 0.0025
            win.pulse += 0.055
        }
    }

    Timer {
        id: stepTimer
        interval: 560
        repeat: false
        onTriggered: win.visualStep = 0
    }

    Timer {
        id: coreBurst
        interval: 380
        repeat: false
    }

    SequentialAnimation {
        id: rgbBurst
        PropertyAction { target: win; property: "pulse"; value: win.pulse + 0.9 }
        NumberAnimation { target: win; property: "pulse"; to: win.pulse + 0.15; duration: 360; easing.type: Easing.OutCubic }
    }

    Rectangle {
        id: backdrop
        anchors.fill: parent
        radius: 32
        color: Qt.rgba(0.035, 0.045, 0.08, 0.90)
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.13)
        clip: true

        // Simulated Apple liquid-glass light blooms.
        Rectangle {
            width: 430; height: 430; radius: 215
            x: -150 + Math.sin(win.rgbPhase * 1.7) * 65
            y: -190 + Math.cos(win.rgbPhase * 1.1) * 40
            color: Qt.rgba(0.16, 0.40, 1.0, 0.11)
            opacity: 0.9
        }
        Rectangle {
            width: 360; height: 360; radius: 180
            x: parent.width - 210 + Math.cos(win.rgbPhase * 1.3) * 55
            y: 165 + Math.sin(win.rgbPhase * 1.5) * 55
            color: Qt.rgba(0.84, 0.20, 1.0, 0.09)
        }
        Rectangle {
            width: 310; height: 310; radius: 155
            x: parent.width * 0.34 + Math.sin(win.rgbPhase * 1.8) * 45
            y: parent.height - 190
            color: Qt.rgba(0.10, 0.92, 1.0, 0.065)
        }

        // Specular top wash.
        Rectangle {
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            height: 120
            radius: 32
            color: Qt.rgba(1,1,1,0.035)
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(1,1,1,0.07) }
                GradientStop { position: 1.0; color: Qt.rgba(1,1,1,0.0) }
            }
        }

        Rectangle {
            id: topRgb
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            height: 5
            color: "transparent"
            Canvas {
                anchors.fill: parent
                onPaint: {
                    var ctx = getContext("2d")
                    var g = ctx.createLinearGradient(0, 0, width, 0)
                    for (var i = 0; i <= 7; i++) {
                        var h = (win.rgbPhase + i / 7) % 1
                        g.addColorStop(i / 7, Qt.hsva(h, 0.86, Math.min(1, 0.86 + Math.min(0.22, Math.sin(win.pulse)*0.11)), 1))
                    }
                    ctx.fillStyle = g
                    ctx.fillRect(0, 0, width, height)
                }
            }
        }

        MouseArea {
            anchors.left: parent.left; anchors.right: parent.right; top: parent.top
            height: 54
            onPressed: win.startSystemMove()
        }

        RowLayout {
            id: titleBar
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 54
            anchors.leftMargin: 24
            anchors.rightMargin: 16
            anchors.topMargin: 5
            spacing: 10

            Text { text: "VBL"; color: "#40ddff"; font.pixelSize: 11; font.bold: true }
            Text { text: "MACRO"; color: "#f7f9ff"; font.pixelSize: 17; font.bold: true }
            Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 17; color: Qt.rgba(1,1,1,0.12) }
            Text { text: "PRECISION INPUT"; color: "#8994af"; font.pixelSize: 9; font.letterSpacing: 1.1 }
            Item { Layout.fillWidth: true }
            Rectangle {
                Layout.preferredWidth: 38; Layout.preferredHeight: 30; radius: 15
                color: Qt.rgba(1,1,1,0.045); border.color: Qt.rgba(1,1,1,0.10); border.width: 1
                Text { anchors.centerIn: parent; text: "⚙"; color: "#b8c1d7"; font.pixelSize: 14 }
                MouseArea { anchors.fill: parent; onClicked: win.settingsOpen = !win.settingsOpen }
            }
            Rectangle {
                Layout.preferredWidth: 38; Layout.preferredHeight: 30; radius: 15
                color: Qt.rgba(1,1,1,0.045); border.color: Qt.rgba(1,1,1,0.10); border.width: 1
                Text { anchors.centerIn: parent; text: "×"; color: "#b8c1d7"; font.pixelSize: 17 }
                MouseArea { anchors.fill: parent; onClicked: bridge.quitApp() }
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: 26
            anchors.rightMargin: 26
            anchors.topMargin: 72
            anchors.bottomMargin: 24
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Text {
                    text: win.robloxFocused ? "ROBLOX LOCK ACQUIRED" : "ROBLOX NOT FOCUSED"
                    color: win.robloxFocused ? "#41ea96" : "#ffd95f"
                    font.pixelSize: 10; font.bold: true; font.letterSpacing: 1.0
                }
                Item { Layout.fillWidth: true }
                Text { text: win.fires + " FIRES"; color: "#56dcff"; font.pixelSize: 9; font.bold: true; font.letterSpacing: 0.9 }
                Text { text: "•"; color: "#4c5670"; font.pixelSize: 9 }
                Text { text: fireRate() + "/MIN"; color: "#9da7c0"; font.pixelSize: 9; font.bold: true; font.letterSpacing: 0.9 }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 270
                radius: 26
                color: Qt.rgba(0.075, 0.09, 0.15, 0.72)
                border.width: 1
                border.color: Qt.rgba(1,1,1,0.11)
                clip: true

                // Glass streaks
                Rectangle { x: 20; y: 18; width: parent.width - 40; height: 1; color: Qt.rgba(1,1,1,0.08) }
                Rectangle { x: parent.width - 190; y: 26; width: 135; height: 2; radius: 1; color: Qt.rgba(1,1,1,0.12); opacity: 0.5 }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 24

                    Item {
                        Layout.preferredWidth: 145
                        Layout.fillHeight: true
                        EnergyCanvas { anchors.centerIn: parent }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 10
                        Text { text: "ENGINE STATUS"; color: "#8490aa"; font.pixelSize: 9; font.bold: true; font.letterSpacing: 1.0 }
                        Text {
                            text: !win.armed ? "STANDING BY" : (win.robloxFocused ? "ENGINE LIVE" : "WAITING FOR ROBLOX")
                            color: !win.armed ? "#d9deeb" : (win.robloxFocused ? "#48ee9d" : "#ffd85e")
                            font.pixelSize: 24; font.bold: true
                        }
                        Text {
                            text: !win.armed ? "Arm the input engine to begin" : (win.robloxFocused ? "Focus protection active" : "Focus Roblox to enable input")
                            color: "#75819a"; font.pixelSize: 10
                        }
                        Item { Layout.fillHeight: true }

                        Button {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 56
                            text: win.armed ? "■   STOP MACRO" : "▶   START MACRO"
                            font.pixelSize: 13; font.bold: true
                            background: Rectangle {
                                radius: 19
                                color: win.armed ? "#ff5c79" : "#4e7cff"
                                border.width: 1
                                border.color: Qt.rgba(1,1,1,0.14)
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: win.armed ? "#ff6c86" : "#5b88ff" }
                                    GradientStop { position: 1.0; color: win.armed ? "#e94869" : "#4168e6" }
                                }
                            }
                            contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font: parent.font }
                            onClicked: bridge.toggle()
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "UPTIME  " + fmtTime(uptimeSeconds()); color: "#78849f"; font.pixelSize: 8; font.letterSpacing: 0.7 }
                            Item { Layout.fillWidth: true }
                            Text { text: "FOCUS LOCK  ON"; color: "#4de7a0"; font.pixelSize: 8; font.bold: true; font.letterSpacing: 0.7 }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 196
                spacing: 14

                GlassPanel {
                    Layout.fillWidth: true; Layout.fillHeight: true; accent: "#36dcff"
                    title: "COMBO PROFILE  •  `"
                    subtitle: "RIGHT CLICK  →  SPACE  →  LEFT CLICK"
                    accentText: "3-STEP"
                    Visualizer { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.bottomMargin: 18; steps: 3 }
                }
                GlassPanel {
                    Layout.fillWidth: true; Layout.fillHeight: true; accent: "#a36cff"
                    title: "COMBO PROFILE  •  R"
                    subtitle: "RIGHT CLICK  →  SPACE"
                    accentText: "2-STEP"
                    Visualizer { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.bottomMargin: 18; steps: 2 }
                }
            }

            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 116
                radius: 24
                color: Qt.rgba(0.065,0.078,0.125,0.70)
                border.width: 1; border.color: Qt.rgba(1,1,1,0.10)

                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 10
                    RowLayout {
                        Text { text: "SESSION TELEMETRY"; color: "#818da7"; font.pixelSize: 9; font.bold: true; font.letterSpacing: 1.0 }
                        Item { Layout.fillWidth: true }
                        Text { text: "LIVE"; color: "#43e89b"; font.pixelSize: 8; font.bold: true; letterSpacing: 1.0 }
                    }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        Metric { label: "FIRES"; value: win.fires; accent: "#35dcff" }
                        Metric { label: "RATE"; value: fireRate() + "/MIN"; accent: "#a36cff" }
                        Metric { label: "LAST KEY"; value: win.lastKey; accent: "#ff59d9" }
                        Metric { label: "UPTIME"; value: fmtTime(uptimeSeconds()); accent: "#43e99a" }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Text { text: "VBL MACRO  •  GLASS EDITION"; color: "#4f596f"; font.pixelSize: 8; font.bold: true; font.letterSpacing: 1.0 }
                Item { Layout.fillWidth: true }
                Text { text: "RGB  ON  •  FOCUS PROTECTION  ON"; color: "#4c5b72"; font.pixelSize: 8; font.letterSpacing: 0.8 }
            }
        }

        Rectangle {
            id: toastBox
            width: 270; height: 48; radius: 24
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom; anchors.bottomMargin: 18
            color: Qt.rgba(0.08,0.09,0.14,0.92)
            border.width: 1; border.color: Qt.rgba(1,1,1,0.13)
            visible: win.toastText !== ""
            opacity: visible ? 1 : 0
            Text { anchors.centerIn: parent; text: "⚡  " + win.toastText; color: "#f5f7ff"; font.pixelSize: 10; font.bold: true; font.letterSpacing: 0.5 }
            Timer { interval: 1100; running: toastBox.visible; repeat: false; onTriggered: win.toastText = "" }
        }

        Rectangle {
            id: drawer
            width: 310; height: parent.height - 24
            anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.right: parent.right; anchors.margins: 12
            radius: 26
            color: Qt.rgba(0.055,0.065,0.105,0.96)
            border.width: 1; border.color: Qt.rgba(1,1,1,0.13)
            visible: win.settingsOpen
            opacity: visible ? 1 : 0
            z: 50
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 22; spacing: 16
                RowLayout {
                    Text { text: "GLASS SETTINGS"; color: "#f1f4fb"; font.pixelSize: 15; font.bold: true }
                    Item { Layout.fillWidth: true }
                    Text { text: "×"; color: "#9aa4bb"; font.pixelSize: 19 }
                    MouseArea { width: 28; height: 28; anchors.right: parent.right; onClicked: win.settingsOpen = false }
                }
                Text { text: "RGB LIGHTING"; color: "#75819b"; font.pixelSize: 9; font.bold: true; font.letterSpacing: 1.1 }
                RowLayout {
                    Layout.fillWidth: true
                    Repeater {
                        model: ["RAINBOW", "OCEAN", "AURORA"]
                        delegate: Button {
                            Layout.fillWidth: true; Layout.preferredHeight: 38
                            text: modelData; font.pixelSize: 8; font.bold: true
                            background: Rectangle { radius: 14; color: index === win.rgbMode ? Qt.rgba(0.2,0.55,1,0.28) : Qt.rgba(1,1,1,0.045); border.width: 1; border.color: Qt.rgba(1,1,1,0.09) }
                            contentItem: Text { text: parent.text; color: index === win.rgbMode ? "#55dcff" : "#97a2ba"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font: parent.font }
                            onClicked: win.rgbMode = index
                        }
                    }
                }
                Text { text: "OVERLAY"; color: "#75819b"; font.pixelSize: 9; font.bold: true; font.letterSpacing: 1.1 }
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Always on top"; color: "#dfe5f3"; font.pixelSize: 10 }
                    Item { Layout.fillWidth: true }
                    Switch { checked: true; enabled: false }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Focus protection"; color: "#dfe5f3"; font.pixelSize: 10 }
                    Item { Layout.fillWidth: true }
                    Switch { checked: true; enabled: false }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Qt.rgba(1,1,1,0.08) }
                Text { text: "SESSION"; color: "#75819b"; font.pixelSize: 9; font.bold: true; font.letterSpacing: 1.1 }
                Button {
                    Layout.fillWidth: true; Layout.preferredHeight: 42; text: "RESET TELEMETRY"
                    background: Rectangle { radius: 15; color: Qt.rgba(1,1,1,0.05); border.width: 1; border.color: Qt.rgba(1,1,1,0.09) }
                    contentItem: Text { text: parent.text; color: "#a7b0c5"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font: parent.font }
                    onClicked: bridge.clearStats()
                }
                Item { Layout.fillHeight: true }
                Text { text: "VBL Macro\nGlass Edition"; color: "#505b71"; font.pixelSize: 9; lineHeight: 1.3 }
            }
        }
    }

    component GlassPanel: Rectangle {
        id: panel
        property color accent: "#36dcff"
        property string title: ""
        property string subtitle: ""
        property string accentText: ""
        radius: 22
        color: Qt.rgba(0.07,0.085,0.135,0.72)
        border.width: 1
        border.color: Qt.rgba(1,1,1,0.10)
        clip: true
        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 2; color: accent; opacity: 0.75 }
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 16; spacing: 7
            RowLayout {
                Layout.fillWidth: true
                Text { text: panel.title; color: "#8b96ad"; font.pixelSize: 8; font.bold: true; font.letterSpacing: 0.6 }
                Item { Layout.fillWidth: true }
                Text { text: panel.accentText; color: panel.accent; font.pixelSize: 8; font.bold: true }
            }
            Text { text: panel.subtitle; color: "#dde3f1"; font.pixelSize: 9; font.bold: true }
            Item { Layout.fillHeight: true }
        }
    }

    component Visualizer: Item {
        property int steps: 3
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 0
            Repeater {
                model: visualizerParent.steps
                delegate: Item {
                    id: nodeItem
                    width: 92; height: 50
                    Rectangle { x: 0; y: 22; width: 92; height: 2; color: Qt.rgba(1,1,1,0.09) }
                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter; y: 8; width: 28; height: 28; radius: 14
                        color: index < win.visualStep ? (index === 0 ? "#36dcff" : index === 1 ? "#a36cff" : "#ff59d9") : "#182036"
                        border.width: 1; border.color: index < win.visualStep ? Qt.rgba(1,1,1,0.25) : "#273149"
                        scale: index < win.visualStep ? 1.12 : 1.0
                        Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
                        Text { anchors.centerIn: parent; text: index + 1; color: index < win.visualStep ? "#071019" : "#71809c"; font.pixelSize: 8; font.bold: true }
                    }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; anchors.topMargin: 40; text: index === 0 ? "RMB" : index === 1 ? "SPACE" : "LMB"; color: index < win.visualStep ? "#dbe5f5" : "#64708a"; font.pixelSize: 7; font.bold: true }
                }
            }
        }
    }

    component Metric: Rectangle {
        property string label: ""
        property string value: ""
        property color accent: "#36dcff"
        Layout.fillWidth: true
        Layout.preferredHeight: 58
        radius: 15
        color: Qt.rgba(1,1,1,0.028)
        border.width: 1; border.color: Qt.rgba(1,1,1,0.065)
        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 2; radius: 1; color: accent; opacity: 0.65 }
        Column {
            anchors.centerIn: parent; spacing: 3
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: label; color: "#66718a"; font.pixelSize: 7; font.bold: true; font.letterSpacing: 0.7 }
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: value; color: "#e7ebf5"; font.pixelSize: 14; font.bold: true }
        }
    }

    component EnergyCanvas: Canvas {
        id: energy
        width: 130; height: 160
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0,0,width,height)
            var stateColor = !win.armed ? Qt.rgba(0.45,0.50,0.62,1) : (win.robloxFocused ? Qt.rgba(0.23,0.91,0.58,1) : Qt.rgba(1,0.84,0.37,1))
            var cx = width/2, cy = 66
            var breathe = (Math.sin(win.pulse*0.9)+1)/2
            var boost = Math.min(18, Math.abs(Math.sin(win.pulse*0.9))*6 + (win.visualStep ? 9 : 0))
            for (var i=4;i>=0;i--) {
                var r=26+i*7+boost
                ctx.strokeStyle = Qt.rgba(stateColor.r,stateColor.g,stateColor.b,0.08+(4-i)*0.025)
                ctx.lineWidth=2
                ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.stroke()
            }
            var grad=ctx.createRadialGradient(cx-5,cy-7,2,cx,cy,30)
            grad.addColorStop(0,"#ffffff")
            grad.addColorStop(0.14,Qt.rgba(stateColor.r,stateColor.g,stateColor.b,0.95))
            grad.addColorStop(1,Qt.rgba(stateColor.r,stateColor.g,stateColor.b,0.22))
            ctx.fillStyle=grad;ctx.beginPath();ctx.arc(cx,cy,25+boost/3,0,Math.PI*2);ctx.fill()
            ctx.fillStyle="rgba(255,255,255,0.97)";ctx.beginPath();ctx.arc(cx-6,cy-7,6,0,Math.PI*2);ctx.fill()
            ctx.fillStyle=Qt.rgba(stateColor.r,stateColor.g,stateColor.b,0.96);ctx.font="bold 9px sans-serif";ctx.textAlign="center"
            ctx.fillText(!win.armed ? "STANDBY" : (win.robloxFocused ? "LIVE" : "WAITING"),cx,112)
            ctx.fillStyle="rgba(130,143,166,0.9)";ctx.font="8px sans-serif";ctx.fillText("VBL ENERGY CORE",cx,129)
        }
    }
}
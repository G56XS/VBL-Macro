import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Window {
    id: root
    width: 920
    height: 780
    minimumWidth: 820
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
    property int rgbMode: 0
    property real hue: 0.58
    property real breathe: 0
    property real startedAt: 0
    property int visualStep: 0
    property string toastText: ""
    property bool settingsOpen: false

    function uptime() {
        return armed && startedAt ? Math.max(0, (Date.now() - startedAt) / 1000) : 0
    }
    function fmtTime(sec) {
        var s = Math.floor(sec), h = Math.floor(s/3600), m = Math.floor((s%3600)/60), r = s%60
        return (h<10?"0":"")+h+":"+(m<10?"0":"")+m+":"+(r<10?"0":"")+r
    }
    function rate() {
        var u = uptime(); return u > 1 ? Math.round(fires / (u/60)) : 0
    }
    function rgbColor(offset) {
        if (rgbMode === 1) return Qt.hsva(0.53 + offset*0.08, 0.82, 1, 1)
        if (rgbMode === 2) return Qt.hsva(0.78 + offset*0.18, 0.78, 1, 1)
        return Qt.hsva((hue + offset)%1, 0.88, 1, 1)
    }
    function notify(text) { toastText = text; toastTimer.restart() }

    Connections {
        target: bridge
        function onStateChanged(started, focused) {
            root.armed = started
            root.robloxFocused = focused
            if (started && root.startedAt === 0) root.startedAt = Date.now()
            if (!started) root.startedAt = 0
        }
        function onFired(key, steps) {
            root.visualStep = steps
            root.notify(key + "  •  COMBO EXECUTED")
            stepTimer.restart()
            burst.restart()
        }
        function onTelemetry(count, key, stamp) {
            root.fires = count; root.lastKey = key; root.lastTime = stamp
        }
        function onLogLine(line) {
            logModel.append({text: line})
            if (logModel.count > 50) logModel.remove(0, logModel.count-50)
        }
    }
    ListModel { id: logModel }

    Timer { id: pulseTimer; interval: 40; running: true; repeat: true; onTriggered: { root.hue += 0.0022; root.breathe += 0.09 } }
    Timer { id: toastTimer; interval: 1150; repeat: false; onTriggered: root.toastText = "" }
    Timer { id: stepTimer; interval: 620; repeat: false; onTriggered: root.visualStep = 0 }
    SequentialAnimation { id: burst; NumberAnimation { target: root; property: "breathe"; to: root.breathe + 1.2; duration: 120 } NumberAnimation { target: root; property: "breathe"; to: root.breathe; duration: 360; easing.type: Easing.OutCubic } }

    Rectangle {
        id: glass
        anchors.fill: parent
        radius: 34
        clip: true
        color: Qt.rgba(0.035, 0.045, 0.08, 0.93)
        border.width: 1
        border.color: Qt.rgba(1,1,1,0.16)

        // Liquid-glass light fields.
        Rectangle { width: 470; height: 470; radius: 235; x: -210 + Math.sin(root.hue*7)*55; y: -230 + Math.cos(root.hue*5)*40; color: Qt.rgba(0.10,0.40,1.0,0.13) }
        Rectangle { width: 430; height: 430; radius: 215; x: parent.width-250 + Math.cos(root.hue*6)*60; y: 120 + Math.sin(root.hue*4)*70; color: Qt.rgba(0.82,0.14,1.0,0.095) }
        Rectangle { width: 320; height: 320; radius: 160; x: parent.width*.42 + Math.sin(root.hue*8)*45; y: parent.height-160; color: Qt.rgba(0.05,0.88,1.0,0.075) }
        Rectangle { anchors.fill: parent; color: Qt.rgba(1,1,1,0.018) }

        // Glossy edge and RGB rail.
        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 76; gradient: Gradient { GradientStop {position:0;color:Qt.rgba(1,1,1,.085)} GradientStop {position:1;color:Qt.rgba(1,1,1,0)} } }
        Rectangle {
            anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; height: 5
            gradient: Gradient {
                GradientStop { position: 0; color: root.rgbColor(0) }
                GradientStop { position: .28; color: root.rgbColor(.28) }
                GradientStop { position: .53; color: root.rgbColor(.53) }
                GradientStop { position: .78; color: root.rgbColor(.78) }
                GradientStop { position: 1; color: root.rgbColor(1) }
            }
        }

        MouseArea { anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; height: 58; onPressed: root.startSystemMove() }

        RowLayout {
            anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
            anchors.topMargin: 7; anchors.leftMargin: 24; anchors.rightMargin: 18; height: 50
            Text { text:"VBL"; color:"#49dfff"; font.pixelSize:11; font.bold:true }
            Text { text:"MACRO"; color:"#fbfcff"; font.pixelSize:17; font.bold:true }
            Rectangle { Layout.preferredWidth:1; Layout.preferredHeight:18; color:Qt.rgba(1,1,1,.13) }
            Text { text:"GLASS EDITION"; color:"#8a96ae"; font.pixelSize:8; font.bold:true; font.letterSpacing:1.0 }
            Item { Layout.fillWidth:true }
            Rectangle { Layout.preferredWidth:38; Layout.preferredHeight:30; radius:15; color:Qt.rgba(1,1,1,.055); border.width:1; border.color:Qt.rgba(1,1,1,.10); Text{anchors.centerIn:parent;text:"⚙";color:"#b6c0d5";font.pixelSize:14};MouseArea{anchors.fill:parent;onClicked:root.settingsOpen=!root.settingsOpen} }
            Rectangle { Layout.preferredWidth:38; Layout.preferredHeight:30; radius:15; color:Qt.rgba(1,1,1,.055); border.width:1; border.color:Qt.rgba(1,1,1,.10); Text{anchors.centerIn:parent;text:"×";color:"#b6c0d5";font.pixelSize:18};MouseArea{anchors.fill:parent;onClicked:bridge.quitApp()} }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: 24; anchors.rightMargin: 24; anchors.topMargin: 70; anchors.bottomMargin: 22
            spacing: 13

            RowLayout {
                Layout.fillWidth: true
                Text { text: root.robloxFocused ? "●  ROBLOX LOCK ACQUIRED" : "●  ROBLOX NOT FOCUSED"; color: root.robloxFocused ? "#47ea9c" : "#ffda62"; font.pixelSize:9; font.bold:true; font.letterSpacing:1.0 }
                Item { Layout.fillWidth:true }
                Text { text: root.fires + " FIRES"; color:"#5bdfff"; font.pixelSize:8; font.bold:true }
                Text { text:"  /  "; color:"#4b566c"; font.pixelSize:8 }
                Text { text: rate()+" / MIN"; color:"#929db5"; font.pixelSize:8; font.bold:true }
            }

            Rectangle {
                Layout.fillWidth:true; Layout.preferredHeight:278; radius:28
                color: Qt.rgba(.065,.08,.13,.70); border.width:1; border.color:Qt.rgba(1,1,1,.105); clip:true
                Rectangle { anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; height:2; color: root.robloxFocused?"#46e99b":"#ffda62"; opacity:.70 }
                RowLayout { anchors.fill:parent; anchors.margins:22; spacing:22
                    Item { Layout.preferredWidth:170; Layout.fillHeight:true; EnergyCore{anchors.centerIn:parent} }
                    ColumnLayout { Layout.fillWidth:true; Layout.fillHeight:true; spacing:8
                        Text { text:"ENGINE STATUS"; color:"#8793ab"; font.pixelSize:8; font.bold:true; font.letterSpacing:1.0 }
                        Text { text: !root.armed ? "STANDING BY" : (root.robloxFocused ? "ENGINE LIVE" : "WAITING FOR ROBLOX"); color: !root.armed?"#e1e5ee":(root.robloxFocused?"#4ae99d":"#ffda62"); font.pixelSize:24; font.bold:true }
                        Text { text: !root.armed ? "Arm the input engine to begin" : (root.robloxFocused ? "Focus protection is active" : "Input is safely paused"); color:"#76829b"; font.pixelSize:10 }
                        Item{Layout.fillHeight:true}
                        Button { Layout.fillWidth:true; Layout.preferredHeight:58; text:root.armed?"■   STOP MACRO":"▶   START MACRO"; onClicked:bridge.toggle(); background:Rectangle{radius:19;border.width:1;border.color:Qt.rgba(1,1,1,.16);gradient:Gradient{GradientStop{position:0;color:root.armed?"#ff7189":"#668fff"}GradientStop{position:1;color:root.armed?"#e74769":"#3e61d7"}}}; contentItem:Text{text:parent.text;color:"white";horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;font.pixelSize:13;font.bold:true} }
                        RowLayout{Layout.fillWidth:true;Text{text:"UPTIME  "+fmtTime(root.uptime());color:"#73809a";font.pixelSize:8};Item{Layout.fillWidth:true};Text{text:"FOCUS LOCK  ON";color:"#4be69d";font.pixelSize:8;font.bold:true}}
                    }
                }
            }

            RowLayout { Layout.fillWidth:true; Layout.preferredHeight:188; spacing:13
                Profile { Layout.fillWidth:true; Layout.fillHeight:true; accent:"#3addff"; keyName:"`"; steps:3; sequence:"RMB   →   SPACE   →   LMB" }
                Profile { Layout.fillWidth:true; Layout.fillHeight:true; accent:"#a56cff"; keyName:"R"; steps:2; sequence:"RMB   →   SPACE" }
            }

            Rectangle { Layout.fillWidth:true; Layout.preferredHeight:120; radius:23; color:Qt.rgba(.06,.073,.115,.72); border.width:1;border.color:Qt.rgba(1,1,1,.09)
                ColumnLayout{anchors.fill:parent;anchors.margins:17;spacing:9
                    RowLayout{Text{text:"SESSION TELEMETRY";color:"#8290a8";font.pixelSize:8;font.bold:true;font.letterSpacing:1};Item{Layout.fillWidth:true};Text{text:"LIVE";color:"#4be89d";font.pixelSize:8;font.bold:true}}
                    RowLayout{Layout.fillWidth:true;spacing:9
                        Metric{Layout.fillWidth:true;label:"FIRES";value:root.fires;accent:"#3addff"}
                        Metric{Layout.fillWidth:true;label:"RATE";value:rate()+"/MIN";accent:"#a56cff"}
                        Metric{Layout.fillWidth:true;label:"LAST KEY";value:root.lastKey;accent:"#ff59da"}
                        Metric{Layout.fillWidth:true;label:"LAST TIME";value:root.lastTime;accent:"#46e89d"}
                    }
                }
            }

            RowLayout{Layout.fillWidth:true;Text{text:"ESC  QUIT";color:"#525e74";font.pixelSize:8;font.bold:true};Item{Layout.fillWidth:true};Text{text:"VBL MACRO  •  INPUT ENGINE  •  FOCUS PROTECTED";color:"#525e74";font.pixelSize:8}}
        }

        Rectangle { id:toast; width:290;height:46;radius:23;anchors.horizontalCenter:parent.horizontalCenter;anchors.bottom:parent.bottom;anchors.bottomMargin:17;visible:root.toastText!=="";color:Qt.rgba(.075,.085,.13,.94);border.width:1;border.color:Qt.rgba(1,1,1,.14);Text{anchors.centerIn:parent;text:"⚡  "+root.toastText;color:"#eef2fb";font.pixelSize:9;font.bold:true} }

        Rectangle { id:drawer; width:330; anchors.top:parent.top;anchors.bottom:parent.bottom;anchors.right:parent.right;anchors.margins:12;radius:27;color:Qt.rgba(.045,.055,.09,.97);border.width:1;border.color:Qt.rgba(1,1,1,.15);visible:root.settingsOpen;z:30
            ColumnLayout{anchors.fill:parent;anchors.margins:22;spacing:15
                RowLayout{Text{text:"GLASS SETTINGS";color:"#f0f3fa";font.pixelSize:16;font.bold:true};Item{Layout.fillWidth:true};Text{text:"×";color:"#9ca6bb";font.pixelSize:20};MouseArea{width:30;height:30;onClicked:root.settingsOpen=false}}
                Text{text:"RGB THEME";color:"#75829b";font.pixelSize:8;font.bold:true;font.letterSpacing:1}
                RowLayout{Layout.fillWidth:true;Repeater{model:["RAINBOW","OCEAN","AURORA"];delegate:Button{Layout.fillWidth:true;Layout.preferredHeight:38;text:modelData;background:Rectangle{radius:14;color:index===root.rgbMode?Qt.rgba(.20,.55,1,.24):Qt.rgba(1,1,1,.045);border.width:1;border.color:Qt.rgba(1,1,1,.08)};contentItem:Text{text:parent.text;color:index===root.rgbMode?"#54ddff":"#98a3b9";horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;font.pixelSize:8;font.bold:true};onClicked:root.rgbMode=index}}}
                Text{text:"ALWAYS ON TOP";color:"#dce3f1";font.pixelSize:10;font.bold:true}
                Text{text:"Focus protection remains enabled while armed.";color:"#737f98";font.pixelSize:9;wrapMode:Text.WordWrap}
                Rectangle{Layout.fillWidth:true;height:1;color:Qt.rgba(1,1,1,.08)}
                Text{text:"SESSION";color:"#75829b";font.pixelSize:8;font.bold:true;font.letterSpacing:1}
                Button{Layout.fillWidth:true;Layout.preferredHeight:43;text:"RESET TELEMETRY";background:Rectangle{radius:15;color:Qt.rgba(1,1,1,.05);border.width:1;border.color:Qt.rgba(1,1,1,.08)};contentItem:Text{text:parent.text;color:"#a9b2c5";horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;font.pixelSize:8;font.bold:true};onClicked:bridge.clearStats()}
                Item{Layout.fillHeight:true}
                Text{text:"VBL Macro\nLiquid Glass Interface";color:"#505b72";font.pixelSize:9}
            }
        }
    }

    component Metric: Rectangle {
        property string label:""; property string value:""; property color accent:"#3addff"
        radius:15;color:Qt.rgba(1,1,1,.027);border.width:1;border.color:Qt.rgba(1,1,1,.06)
        Rectangle{anchors.top:parent.top;anchors.left:parent.left;anchors.right:parent.right;height:2;radius:1;color:accent;opacity:.7}
        Column{anchors.centerIn:parent;spacing:3;Text{anchors.horizontalCenter:parent.horizontalCenter;text:label;color:"#66728a";font.pixelSize:7;font.bold:true};Text{anchors.horizontalCenter:parent.horizontalCenter;text:value;color:"#e9edf6";font.pixelSize:13;font.bold:true}}
    }

    component Profile: Rectangle {
        property color accent:"#3addff"; property string keyName:"`"; property int steps:3; property string sequence:""
        radius:23;color:Qt.rgba(.065,.08,.13,.72);border.width:1;border.color:Qt.rgba(1,1,1,.09);clip:true
        Rectangle{anchors.left:parent.left;anchors.right:parent.right;anchors.top:parent.top;height:2;color:accent;opacity:.8}
        ColumnLayout{anchors.fill:parent;anchors.margins:17;spacing:6
            RowLayout{Layout.fillWidth:true;Text{text:"COMBO PROFILE  •  "+keyName;color:"#8a96ad";font.pixelSize:8;font.bold:true};Item{Layout.fillWidth:true};Text{text:steps+"-STEP";color:accent;font.pixelSize:8;font.bold:true}}
            Text{text:sequence;color:"#dde4f2";font.pixelSize:8;font.bold:true}
            Item{Layout.fillHeight:true}
            Row{Layout.alignment:Qt.AlignHCenter
                Repeater{model:steps;delegate:Item{width:Math.max(65,(parent.width/steps));height:58
                    Rectangle{anchors.verticalCenter:parent.verticalCenter;width:parent.width;height:2;color:Qt.rgba(1,1,1,.08);visible:index<steps-1}
                    Rectangle{x:parent.width/2-15;y:4;width:30;height:30;radius:15;color:index<root.visualStep?(index===0?"#3addff":index===1?"#a56cff":"#ff59da"):"#182038";border.width:1;border.color:index<root.visualStep?Qt.rgba(1,1,1,.24):"#28344a";scale:index<root.visualStep?1.10:1;Behavior on scale{NumberAnimation{duration:140}}
                        Text{anchors.centerIn:parent;text:index+1;color:index<root.visualStep?"#061018":"#71809a";font.pixelSize:8;font.bold:true}}
                    Text{anchors.horizontalCenter:parent.horizontalCenter;anchors.top:parent.top;anchors.topMargin:39;text:index===0?"RMB":index===1?"SPACE":"LMB";color:index<root.visualStep?"#e6ebf4":"#65718b";font.pixelSize:7;font.bold:true}
                }}
            }
        }
    }

    component EnergyCore: Item {
        width:150;height:155
        Canvas{anchors.fill:parent;onPaint:{var ctx=getContext("2d");ctx.clearRect(0,0,width,height);var c=!root.armed?Qt.rgba(.45,.51,.62,1):(root.robloxFocused?Qt.rgba(.24,.93,.60,1):Qt.rgba(1,.84,.36,1));var cx=75,cy=64;var boost=root.visualStep?8:0;var wave=(Math.sin(root.breathe*.65)+1)/2;for(var i=4;i>=0;i--){var r=24+i*7+boost;ctx.strokeStyle=Qt.rgba(c.r,c.g,c.b,.06+(4-i)*.03);ctx.lineWidth=2;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.stroke()}var g=ctx.createRadialGradient(cx-6,cy-7,2,cx,cy,29);g.addColorStop(0,"#ffffff");g.addColorStop(.16,Qt.rgba(c.r,c.g,c.b,.98));g.addColorStop(1,Qt.rgba(c.r,c.g,c.b,.2));ctx.fillStyle=g;ctx.beginPath();ctx.arc(cx,cy,25+boost/3,0,Math.PI*2);ctx.fill();ctx.fillStyle="rgba(255,255,255,.96)";ctx.beginPath();ctx.arc(cx-6,cy-7,6,0,Math.PI*2);ctx.fill();ctx.fillStyle=Qt.rgba(c.r,c.g,c.b,.96);ctx.font="bold 9px sans-serif";ctx.textAlign="center";ctx.fillText(!root.armed?"STANDBY":(root.robloxFocused?"LIVE":"WAITING"),cx,112);ctx.fillStyle="rgba(130,143,166,.9)";ctx.font="8px sans-serif";ctx.fillText("VBL ENERGY CORE",cx,129)}}
    }
}
import QtQuick 2.15
import QtQuick.Layouts 1.15

ColumnLayout {
    property string label: "METRIC"
    property string value: "—"
    property color accent: "#35dcff"
    Layout.fillWidth: true
    spacing: 3

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 2
        radius: 1
        color: accent
        opacity: 0.82
    }

    Text {
        text: label
        color: "#6f7890"
        font.pixelSize: 7
        font.bold: true
        font.letterSpacing: 0.9
    }

    Text {
        text: value
        color: "#eef2fb"
        font.pixelSize: 16
        font.bold: true
    }
}

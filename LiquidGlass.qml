import QtQuick 2.15

Item {
    id: glass

    property var sourceTexture
    property Item coordinateRoot
    property real rootWidth: 1
    property real rootHeight: 1
    property real time: 0
    property real distortion: 0.010
    property real aberration: 0.55
    property real blur: 0.0032
    property real tintOpacity: 0.10
    property color tintColor: "#ffffff"
    property bool enabled: true

    function mappedX() {
        if (!coordinateRoot) return x
        return mapToItem(coordinateRoot, 0, 0).x
    }

    function mappedY() {
        if (!coordinateRoot) return y
        return mapToItem(coordinateRoot, 0, 0).y
    }

    ShaderEffect {
        anchors.fill: parent
        visible: glass.enabled
        blending: true
        property var source: glass.sourceTexture
        property vector4d sourceRect: Qt.vector4d(
            glass.mappedX() / glass.rootWidth,
            glass.mappedY() / glass.rootHeight,
            glass.width / glass.rootWidth,
            glass.height / glass.rootHeight
        )
        property vector4d fxParams: Qt.vector4d(
            glass.time,
            glass.distortion,
            glass.aberration,
            glass.blur
        )
        fragmentShader: "shaders/liquid_glass.frag.qsb"
    }

    Rectangle {
        anchors.fill: parent
        radius: Math.min(width, height) * 0.12
        color: Qt.rgba(glass.tintColor.r, glass.tintColor.g, glass.tintColor.b, glass.tintOpacity)
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.16)
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 22
        anchors.rightMargin: 22
        y: 4
        height: 1
        radius: 1
        color: Qt.rgba(1, 1, 1, 0.15)
    }
}

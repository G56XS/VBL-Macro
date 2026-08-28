"""VBL Macro premium desktop application.

Python owns the input engine; Qt Quick/QML owns the visual layer.  Keeping
these responsibilities separate makes it easy to iterate on the UI without
changing the established macro behavior.
"""

import ctypes
import os
import sys
import threading
import time

import keyboard
import pydirectinput
from PySide6.QtCore import QObject, Signal, Slot, QTimer, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

pydirectinput.PAUSE = 0

IS_WINDOWS = sys.platform.startswith("win")
ROBLOX_TITLE_MATCH = "roblox"
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

running = False
roblox_focused = False
event_count = 0
last_key = "—"
last_time = "—"
held = set()


def active_title():
    if not IS_WINDOWS:
        return ""
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    return buff.value


def is_roblox_focused():
    return ROBLOX_TITLE_MATCH in active_title().lower()


def combo_tilde():
    pydirectinput.rightClick()
    pydirectinput.press("space")
    pydirectinput.leftClick()


def combo_r():
    pydirectinput.rightClick()
    pydirectinput.press("space")


class Bridge(QObject):
    stateChanged = Signal(bool, bool)
    fired = Signal(str, int)
    logLine = Signal(str)

    def __init__(self):
        super().__init__()
        self.started_at = None
        self.last_log = ""

    @Slot()
    def toggle(self):
        global running
        running = not running
        self.started_at = time.monotonic() if running else None
        self.stateChanged.emit(running, roblox_focused)
        msg = f"{time.strftime('%H:%M:%S')}   ENGINE {'ARMED' if running else 'DISARMED'}"
        self.logLine.emit(msg)

    @Slot()
    def quitApp(self):
        QApplication.quit()

    @Slot()
    def clearStats(self):
        global event_count, last_key, last_time
        event_count = 0
        last_key = "—"
        last_time = "—"
        self.logLine.emit(f"{time.strftime('%H:%M:%S')}   SESSION RESET")

    @Slot()
    def signalRoblox(self):
        self.stateChanged.emit(running, roblox_focused)


def keyboard_handler(key, action, bridge):
    def on_event(event):
        global event_count, last_key, last_time
        if not running:
            return
        if IS_WINDOWS and not roblox_focused:
            return
        if event.event_type == "down":
            if key in held:
                return
            held.add(key)
            action()
            event_count += 1
            last_key = key.upper()
            last_time = time.strftime("%H:%M:%S")
            bridge.fired.emit(last_key, 3 if key == "`" else 2)
            bridge.logLine.emit(f"{last_time}   {last_key}   COMBO EXECUTED   #{event_count}")
        elif event.event_type == "up":
            held.discard(key)
    return on_event


def roblox_poll(bridge):
    global roblox_focused
    while True:
        focused = is_roblox_focused()
        if focused != roblox_focused:
            roblox_focused = focused
            bridge.stateChanged.emit(running, roblox_focused)
        time.sleep(0.15)


def uptime_tick(bridge):
    # Emit a harmless state packet so QML can refresh its clock without
    # needing Python timers crossing thread boundaries.
    bridge.stateChanged.emit(running, roblox_focused)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VBL Macro")
    app.setApplicationDisplayName("VBL Macro")
    app.setOrganizationName("G56XS")

    bridge = Bridge()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("bridge", bridge)

    qml_path = os.path.join(BASE_DIR, "Main.qml")
    engine.load(QUrl.fromLocalFile(qml_path))
    if not engine.rootObjects():
        raise RuntimeError(f"Could not load QML interface: {qml_path}")

    keyboard.hook_key("`", keyboard_handler("`", combo_tilde, bridge))
    keyboard.hook_key("r", keyboard_handler("r", combo_r, bridge))
    keyboard.add_hotkey("esc", bridge.quitApp, suppress=False)

    if IS_WINDOWS:
        threading.Thread(target=roblox_poll, args=(bridge,), daemon=True).start()

    timer = QTimer()
    timer.timeout.connect(lambda: uptime_tick(bridge))
    timer.start(500)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

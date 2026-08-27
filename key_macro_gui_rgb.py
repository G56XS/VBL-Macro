"""VBL Macro — premium reactive RGB gaming dashboard.

The input engine intentionally remains the same: ` and r trigger the
existing click/space combinations only while the app is armed and Roblox
is focused on Windows. This module focuses on the visual/UX layer.
"""

import colorsys
import ctypes
import math
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import font as tkfont

import keyboard
import pydirectinput

pydirectinput.PAUSE = 0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS = sys.platform.startswith("win")
ROBLOX_TITLE_MATCH = "roblox"

BG = "#070910"
SURFACE = "#0d111b"
SURFACE2 = "#121827"
SURFACE3 = "#171e30"
STROKE = "#252d41"
TEXT = "#f5f7ff"
MUTED = "#838ca6"
DIM = "#555e74"
CYAN = "#32ddff"
BLUE = "#4d7cff"
PURPLE = "#a36cff"
PINK = "#ff59d9"
GREEN = "#3bea91"
RED = "#ff5d78"
YELLOW = "#ffd962"
BLACK = "#020306"

running = False
roblox_focused = False
event_count = 0
last_action = "—"
last_action_time = "—"
held = set()


def resource_path(name):
    base = getattr(sys, "_MEIPASS", BASE_DIR) if getattr(sys, "frozen", False) else BASE_DIR
    return os.path.join(base, name)


def family(preferred, fallbacks):
    try:
        available = set(tkfont.families())
    except Exception:
        available = set()
    if preferred in available:
        return preferred
    for value in fallbacks:
        if value in available:
            return value
    return "TkDefaultFont"


def rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    ar, ag, ab = rgb(a)
    br, bg, bb = rgb(b)
    t = max(0.0, min(1.0, t))
    return "#%02x%02x%02x" % (
        round(ar + (br - ar) * t),
        round(ag + (bg - ag) * t),
        round(ab + (bb - ab) * t),
    )


def rainbow(h, s=0.9, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def rr(x1, y1, x2, y2, radius):
    radius = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    return [
        x1 + radius, y1, x2 - radius, y1, x2, y1,
        x2, y1 + radius, x2, y2 - radius, x2, y2,
        x2 - radius, y2, x1 + radius, y2, x1, y2,
        x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]


def active_title():
    if not IS_WINDOWS:
        return ""
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def is_roblox():
    return ROBLOX_TITLE_MATCH in active_title().lower()


def combo_tilde():
    pydirectinput.rightClick()
    pydirectinput.press("space")
    pydirectinput.leftClick()


def combo_r():
    pydirectinput.rightClick()
    pydirectinput.press("space")


def make_handler(key, action, log_fn):
    def on_event(event):
        global event_count, last_action, last_action_time
        if not running:
            return
        if IS_WINDOWS and not roblox_focused:
            return
        if event.event_type == "down" and key not in held:
            held.add(key)
            action()
            event_count += 1
            last_action = key.upper()
            last_action_time = time.strftime("%H:%M:%S")
            log_fn(f"{last_action_time}   {key.upper()}   COMBO EXECUTED   #{event_count}")
        elif event.event_type == "up":
            held.discard(key)
    return on_event


class RGBStrip(tk.Canvas):
    """Animated RGB light strip. Brightens briefly whenever the macro fires."""
    def __init__(self, master, height=8):
        super().__init__(master, height=height, bg=BG, highlightthickness=0)
        self.phase = 0.0
        self.reactive = 0.0
        self.bind("<Configure>", self.draw)
        self.after(30, self.tick)

    def pulse(self):
        self.reactive = 1.0

    def draw(self, _=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2:
            return
        boost = 0.25 * self.reactive
        for x in range(w):
            c = rainbow(self.phase + x / max(w, 1), 0.87, min(1.0, 0.88 + boost))
            self.create_line(x, 0, x, h, fill=c)
        # soft white moving highlight
        glow_x = (math.sin(self.phase * 7.0) + 1) * 0.5 * w
        self.create_line(glow_x, 0, glow_x + 32, h, fill=mix(TEXT, CYAN, 0.68), width=1)

    def tick(self):
        self.phase += 0.0027
        self.reactive *= 0.88
        self.draw()
        self.after(30, self.tick)


class Card(tk.Frame):
    def __init__(self, master, accent, fill=SURFACE):
        super().__init__(master, bg=BG)
        self.accent = accent
        self.fill = fill
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=fill)
        self.window = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.canvas.bind("<Configure>", self.redraw)

    def finalize(self, height=None):
        self.body.update_idletasks()
        self.canvas.configure(height=height or self.body.winfo_reqheight())
        self.redraw()

    def redraw(self, _=None):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 4 or h < 4:
            return
        self.canvas.delete("shape")
        self.canvas.create_polygon(
            rr(1, 1, w - 1, h - 1, 21),
            fill=mix(self.accent, BG, 0.91), outline="", smooth=True, tags="shape"
        )
        self.canvas.create_polygon(
            rr(3, 3, w - 3, h - 3, 19),
            fill=self.fill, outline=STROKE, width=1, smooth=True, tags="shape"
        )
        self.canvas.create_line(
            24, 4, w - 24, 4,
            fill=mix(self.accent, TEXT, 0.58), width=2, capstyle="round", tags="shape"
        )
        self.canvas.tag_lower("shape")
        self.canvas.coords(self.window, 0, 0)
        self.canvas.itemconfigure(self.window, width=w, height=h)


class Button(tk.Canvas):
    def __init__(self, master, text, command, color):
        super().__init__(master, height=60, bg=master.cget("bg"), highlightthickness=0, cursor="hand2")
        self.text = text
        self.command = command
        self.color = color
        self.hover = False
        self.pressed = False
        self.bind("<Configure>", self.draw)
        self.bind("<Enter>", lambda _: self.set_hover(True))
        self.bind("<Leave>", lambda _: self.set_hover(False))
        self.bind("<Button-1>", lambda _: self.set_pressed(True))
        self.bind("<ButtonRelease-1>", self.release)

    def set_hover(self, value):
        self.hover = value
        self.draw()

    def set_pressed(self, value):
        self.pressed = value
        self.draw()

    def draw(self, _=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 3:
            return
        c = self.color
        if self.hover:
            c = mix(c, TEXT, 0.11)
        if self.pressed:
            c = mix(c, BLACK, 0.18)
        self.create_polygon(rr(2, 2, w - 2, h - 2, h / 2), fill=c, outline="", smooth=True)
        self.create_line(28, 5, w - 28, 5, fill=mix(c, TEXT, 0.34), width=1.5, capstyle="round")
        self.create_text(
            w / 2, h / 2, text=self.text, fill=TEXT,
            font=(family("Segoe UI Semibold", ["Segoe UI"]), 13, "bold")
        )

    def release(self, event):
        self.pressed = False
        self.draw()
        if 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self.command()

    def set(self, text, color):
        self.text, self.color = text, color
        self.draw()


class Chip(tk.Canvas):
    def __init__(self, master, text, color, width=None):
        super().__init__(master, height=29, bg=master.cget("bg"), highlightthickness=0, width=width or 180)
        self.text, self.color = text, color
        self.bind("<Configure>", self.draw)

    def draw(self, _=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2:
            return
        self.create_polygon(
            rr(0, 0, w, h, h / 2),
            fill=mix(self.color, SURFACE, 0.82),
            outline=mix(self.color, SURFACE, 0.45), smooth=True
        )
        self.create_oval(9, h / 2 - 4, 17, h / 2 + 4, fill=self.color, outline="")
        self.create_text(
            25, h / 2, anchor="w", text=self.text, fill=self.color,
            font=(family("Segoe UI", ["Arial"]), 8, "bold")
        )

    def set(self, text, color):
        self.text, self.color = text, color
        self.draw()


class EnergyCore(tk.Canvas):
    """Animated central status orb. A fresh pulse is triggered for each macro."""
    def __init__(self, master):
        super().__init__(master, width=112, height=112, bg=SURFACE, highlightthickness=0)
        self.phase = 0.0
        self.burst = 0.0
        self.state = "idle"
        self.after(35, self.tick)

    def set_state(self, state):
        self.state = state

    def fire(self):
        self.burst = 1.0

    def tick(self):
        self.delete("all")
        colors = {"idle": DIM, "waiting": YELLOW, "live": GREEN}
        color = colors.get(self.state, DIM)
        pulse = (math.sin(self.phase * 4.5) + 1) / 2
        glow = pulse * 4 + self.burst * 10
        cx = cy = 56
        for extra, amount in ((glow + 12, 0.90), (glow + 7, 0.82), (glow + 3, 0.68)):
            self.create_oval(cx-extra, cy-extra, cx+extra, cy+extra, fill=mix(color, SURFACE, amount), outline="")
        outer = 32 + pulse * 2 + self.burst * 5
        self.create_oval(cx-outer, cy-outer, cx+outer, cy+outer, fill=SURFACE2, outline=color, width=1)
        inner = 23 + pulse * 2 + self.burst * 5
        self.create_oval(cx-inner, cy-inner, cx+inner, cy+inner, fill=mix(color, BLACK, 0.23), outline="")
        self.create_oval(cx-7, cy-7, cx+7, cy+7, fill=TEXT, outline="")
        self.create_text(cx, cy + 41, text={"idle":"STANDBY","waiting":"WAITING","live":"LIVE"}.get(self.state, "STANDBY"),
                         fill=color, font=(family("Segoe UI Semibold", ["Segoe UI"]), 8, "bold"))
        self.phase += 0.05
        self.burst *= 0.72
        self.after(35, self.tick)


class ComboVisualizer(tk.Canvas):
    """Three-step pipeline that lights up on every ` combo."""
    def __init__(self, master):
        super().__init__(master, height=62, bg=SURFACE, highlightthickness=0)
        self.progress = 0
        self.cooldown = 0
        self.after(40, self.tick)

    def trigger(self, steps=3):
        self.progress = steps
        self.cooldown = 8

    def tick(self):
        if self.cooldown:
            self.cooldown -= 1
        elif self.progress:
            self.progress -= 1
        self.draw()
        self.after(40, self.tick)

    def draw(self, _=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        labels = [(45, "RMB", CYAN), (w/2, "SPACE", PURPLE), (w-45, "LMB", PINK)]
        for index, (x, label, color) in enumerate(labels, start=1):
            active = index <= self.progress
            fill = color if active else SURFACE3
            outline = color if active else STROKE
            self.create_oval(x-17, 13, x+17, 47, fill=fill, outline=outline, width=1)
            self.create_text(x, 30, text=str(index), fill=BLACK if active else MUTED,
                             font=(family("Cascadia Mono", ["Consolas"]), 9, "bold"))
            self.create_text(x, 56, text=label, fill=color if active else MUTED,
                             font=(family("Cascadia Mono", ["Consolas"]), 7, "bold"))
        for x1, x2 in ((62, w/2-18), (w/2+18, w-62)):
            self.create_line(x1, 30, x2, 30, fill=STROKE, width=2)


class Overlay:
    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)
        try:
            self.win.attributes("-alpha", 0.96)
        except Exception:
            pass
        matte = "#010203"
        if IS_WINDOWS:
            try:
                self.win.configure(bg=matte)
                self.win.attributes("-transparentcolor", matte)
            except Exception:
                pass
        else:
            self.win.configure(bg=BG)
        self.W, self.H = 312, 92
        screen_h = self.win.winfo_screenheight()
        self.win.geometry(f"{self.W}x{self.H}+24+{screen_h-self.H-90}")
        self.canvas = tk.Canvas(self.win, width=self.W, height=self.H,
                                bg=matte if IS_WINDOWS else BG, highlightthickness=0)
        self.canvas.pack()
        self.phase = 0.0
        self.state = "stopped"
        self.drag = (0, 0)
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag_to)
        self.animate()

    def start_drag(self, event):
        self.drag = (event.x, event.y)

    def drag_to(self, _event):
        self.win.geometry(f"+{self.win.winfo_pointerx()-self.drag[0]}+{self.win.winfo_pointery()-self.drag[1]}")

    def update(self, is_running, is_focused):
        self.state = "stopped" if not is_running else ("waiting" if IS_WINDOWS and not is_focused else "active")

    def animate(self):
        self.canvas.delete("all")
        color = {"stopped": RED, "waiting": YELLOW, "active": GREEN}[self.state]
        title = {"stopped": "OFFLINE", "waiting": "WAITING", "active": "LIVE"}[self.state]
        detail = {
            "stopped": "Macro disarmed",
            "waiting": "Waiting for Roblox focus",
            "active": "Hotkeys ready   •   ` + R",
        }[self.state]
        self.canvas.create_polygon(rr(2, 2, self.W-2, self.H-2, 22), fill=SURFACE2, outline=STROKE, smooth=True)
        for i in range(52):
            x = 18 + i * (276/52)
            self.canvas.create_line(x, 4, x+5, 4, fill=rainbow(self.phase+i/52, .85, 1), width=2)
        pulse = (math.sin(self.phase * 8) + 1) / 2
        radius = 6 + pulse
        self.canvas.create_oval(27-radius-4, 45-radius-4, 27+radius+4, 45+radius+4,
                                fill=mix(color, SURFACE2, .82), outline="")
        self.canvas.create_oval(27-radius, 45-radius, 27+radius, 45+radius, fill=color, outline="")
        self.canvas.create_oval(25, 43, 27, 45, fill=TEXT, outline="")
        self.canvas.create_text(51, 34, anchor="w", text=title, fill=color,
                                font=(family("Segoe UI Semibold", ["Segoe UI"]), 13, "bold"))
        self.canvas.create_text(51, 58, anchor="w", text=detail, fill=MUTED,
                                font=(family("Segoe UI", ["Arial"]), 9))
        self.phase += 0.008
        self.win.after(40, self.animate)


class App:
    def __init__(self, root):
        self.root = root
        root.title("VBL Macro")
        root.configure(bg=BG)
        root.geometry("640x820")
        root.minsize(580, 720)

        ico, png = resource_path("app_icon.ico"), resource_path("icon_512.png")
        try:
            if IS_WINDOWS and os.path.exists(ico):
                root.iconbitmap(default=ico)
            elif os.path.exists(png):
                self.icon = tk.PhotoImage(file=png)
                root.iconphoto(True, self.icon)
        except Exception:
            pass

        self.fd = family("Segoe UI Semibold", ["Segoe UI", "Helvetica"])
        self.ft = family("Segoe UI", ["Arial", "Helvetica"])
        self.fm = family("Cascadia Mono", ["Consolas", "Courier New"])

        self.rgb_strip = RGBStrip(root, 8)
        self.rgb_strip.pack(fill="x", side="top")

        outer = tk.Frame(root, bg=BG)
        outer.pack(fill="both", expand=True, padx=26, pady=22)

        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x")
        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left")
        tk.Label(brand, text="VBL", font=(self.fd, 11, "bold"), fg=CYAN, bg=BG).pack(anchor="w")
        tk.Label(brand, text="MACRO", font=(self.fd, 28, "bold"), fg=TEXT, bg=BG).pack(anchor="w")
        tk.Label(brand, text="REACTIVE INPUT SYSTEM  •  ROBLOX", font=(self.ft, 9), fg=MUTED, bg=BG).pack(anchor="w")
        self.status = Chip(header, "OFFLINE", RED, width=154)
        self.status.pack(side="right", pady=9)

        runtime = tk.Frame(outer, bg=BG)
        runtime.pack(fill="x", pady=(18, 16))
        self.rbx = Chip(runtime, "ROBLOX NOT FOCUSED" if IS_WINDOWS else "WINDOW DETECTION: WINDOWS ONLY",
                        RED if IS_WINDOWS else MUTED, width=330)
        self.rbx.pack(side="left", fill="x", expand=True)
        self.counter = tk.Label(runtime, text="0 FIRES", font=(self.fm, 8, "bold"), fg=CYAN, bg=BG)
        self.counter.pack(side="right", padx=(12, 0))

        hero = Card(outer, BLUE)
        hero.pack(fill="x", pady=(0, 16))
        hb = hero.body
        head = tk.Frame(hb, bg=SURFACE)
        head.pack(fill="x", padx=20, pady=(16, 2))
        tk.Label(head, text="MASTER CONTROL", font=(self.ft, 9, "bold"), fg=MUTED, bg=SURFACE).pack(side="left")
        self.session = tk.Label(head, text="SESSION 00:00", font=(self.fm, 8, "bold"), fg=DIM, bg=SURFACE)
        self.session.pack(side="right")

        core_row = tk.Frame(hb, bg=SURFACE)
        core_row.pack(fill="x", padx=20, pady=(1, 8))
        self.core = EnergyCore(core_row)
        self.core.pack(side="left", padx=(0, 16))
        info = tk.Frame(core_row, bg=SURFACE)
        info.pack(fill="both", expand=True, pady=12)
        tk.Label(info, text="ENGINE STATUS", font=(self.ft, 8, "bold"), fg=MUTED, bg=SURFACE).pack(anchor="w")
        self.mode = tk.Label(info, text="STANDING BY", font=(self.fd, 16, "bold"), fg=TEXT, bg=SURFACE)
        self.mode.pack(anchor="w", pady=(4, 3))
        self.last = tk.Label(info, text="Last action: —", font=(self.fm, 8), fg=DIM, bg=SURFACE)
        self.last.pack(anchor="w")
        self.button = Button(hb, "▶   START MACRO", self.toggle, BLUE)
        self.button.pack(fill="x", padx=20, pady=(0, 9))
        self.helper = tk.Label(hb, text="Focus protection ON  •  ESC quits instantly", font=(self.ft, 8), fg=DIM, bg=SURFACE)
        self.helper.pack(anchor="w", padx=22, pady=(0, 16))
        hero.finalize()

        combos = Card(outer, PURPLE)
        combos.pack(fill="x", pady=(0, 16))
        cb = combos.body
        top = tk.Frame(cb, bg=SURFACE)
        top.pack(fill="x", padx=20, pady=(15, 0))
        tk.Label(top, text="COMBO PROFILES", font=(self.ft, 9, "bold"), fg=MUTED, bg=SURFACE).pack(side="left")
        tk.Label(top, text="REACTIVE", font=(self.fm, 8, "bold"), fg=CYAN, bg=SURFACE).pack(side="right")
        self.bind_row(cb, "`", "RIGHT CLICK  →  SPACE  →  LEFT CLICK", CYAN, "3-STEP")
        self.bind_row(cb, "R", "RIGHT CLICK  →  SPACE", PURPLE, "2-STEP")
        tk.Label(cb, text="Live visualizer lights each step during execution.", font=(self.ft, 8), fg=DIM, bg=SURFACE).pack(anchor="w", padx=20, pady=(8, 2))
        self.visualizer = ComboVisualizer(cb)
        self.visualizer.pack(fill="x", padx=18, pady=(0, 10))
        combos.finalize()

        stats = Card(outer, PINK)
        stats.pack(fill="x", pady=(0, 16))
        sb = stats.body
        tk.Label(sb, text="SESSION TELEMETRY", font=(self.ft, 9, "bold"), fg=MUTED, bg=SURFACE).pack(anchor="w", padx=20, pady=(15, 9))
        grid = tk.Frame(sb, bg=SURFACE)
        grid.pack(fill="x", padx=20, pady=(0, 15))
        self.stat_widgets = {}
        self.add_stat(grid, 0, "TOTAL FIRES", "0", CYAN)
        self.add_stat(grid, 1, "LAST KEY", "—", PURPLE)
        self.add_stat(grid, 2, "LAST TIME", "—", PINK)
        self.add_stat(grid, 3, "UPTIME", "00:00", GREEN)
        stats.finalize()

        activity = Card(outer, CYAN)
        activity.pack(fill="both", expand=True)
        ab = activity.body
        ah = tk.Frame(ab, bg=SURFACE)
        ah.pack(fill="x", padx=20, pady=(15, 8))
        tk.Label(ah, text="LIVE ACTIVITY", font=(self.ft, 9, "bold"), fg=MUTED, bg=SURFACE).pack(side="left")
        self.live = tk.Label(ah, text="● IDLE", font=(self.ft, 8, "bold"), fg=DIM, bg=SURFACE)
        self.live.pack(side="right")
        self.box = tk.Text(ab, bg=BLACK, fg="#dce4f8", insertbackground=TEXT, relief="flat", bd=0,
                           font=(self.fm, 8), wrap="word", state="disabled", padx=14, pady=12)
        self.box.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        activity.canvas.configure(height=198)

        footer = tk.Frame(outer, bg=BG)
        footer.pack(fill="x", pady=(11, 0))
        tk.Label(footer, text="VBL MACRO  •  RGB ENGINE", font=(self.fm, 8), fg=DIM, bg=BG).pack(side="left")
        tk.Label(footer, text="SAFE INPUT MODE", font=(self.fm, 8, "bold"), fg=GREEN, bg=BG).pack(side="right")

        self.started_at = None
        self.overlay = Overlay(root)
        keyboard.hook_key("`", make_handler("`", combo_tilde, self.log))
        keyboard.hook_key("r", make_handler("r", combo_r, self.log))
        keyboard.add_hotkey("esc", self.request_exit, suppress=False)

        self.last_roblox = None
        if IS_WINDOWS:
            threading.Thread(target=self.poll_roblox, daemon=True).start()
        threading.Thread(target=self.poll_overlay, daemon=True).start()
        self.refresh()
        self.log("System initialized — click START MACRO to arm the engine.")
        if IS_WINDOWS:
            self.log("Roblox focus protection is enabled.")
        else:
            self.log("Windows focus detection unavailable on this OS.")

    def add_stat(self, parent, column, label, value, accent):
        frame = tk.Frame(parent, bg=SURFACE3)
        frame.grid(row=0, column=column, sticky="nsew", padx=4)
        parent.grid_columnconfigure(column, weight=1)
        tk.Frame(frame, bg=accent, height=2).pack(fill="x")
        tk.Label(frame, text=label, font=(self.ft, 7, "bold"), fg=MUTED, bg=SURFACE3).pack(anchor="w", padx=10, pady=(8, 1))
        value_label = tk.Label(frame, text=value, font=(self.fd, 12, "bold"), fg=TEXT, bg=SURFACE3)
        value_label.pack(anchor="w", padx=10, pady=(0, 9))
        self.stat_widgets[label] = value_label

    def bind_row(self, parent, key, description, color, tag):
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill="x", padx=20, pady=4)
        badge = tk.Label(row, text=f" {key} ", font=(self.fm, 10, "bold"), fg=BLACK, bg=color, padx=8, pady=4)
        badge.pack(side="left")
        tk.Label(row, text=description, font=(self.ft, 10), fg=TEXT, bg=SURFACE).pack(side="left", padx=11)
        tk.Label(row, text=tag, font=(self.fm, 7, "bold"), fg=color, bg=mix(color, SURFACE, .88), padx=6, pady=3).pack(side="right")

    def poll_roblox(self):
        global roblox_focused
        while True:
            focused = is_roblox()
            if focused != roblox_focused:
                roblox_focused = focused
                self.root.after(0, self.update_roblox, focused)
            time.sleep(0.2)

    def poll_overlay(self):
        last = None
        while True:
            state = (running, roblox_focused)
            if state != last:
                last = state
                self.root.after(0, self.overlay.update, *state)
                self.root.after(0, self.refresh)
            self.root.after(0, self.refresh)
            time.sleep(0.25)

    def update_roblox(self, focused):
        self.rbx.set("ROBLOX FOCUSED  •  INPUT READY" if focused else "ROBLOX NOT FOCUSED", GREEN if focused else RED)
        self.refresh()

    def refresh(self):
        if running:
            if IS_WINDOWS and not roblox_focused:
                self.mode.config(text="WAITING FOR ROBLOX", fg=YELLOW)
                self.live.config(text="● WAITING", fg=YELLOW)
                self.core.set_state("waiting")
            else:
                self.mode.config(text="ENGINE ONLINE", fg=GREEN)
                self.live.config(text="● LIVE", fg=GREEN)
                self.core.set_state("live")
        else:
            self.mode.config(text="STANDING BY", fg=TEXT)
            self.live.config(text="● IDLE", fg=DIM)
            self.core.set_state("idle")
        self.counter.config(text=f"{event_count} FIRES")
        self.stat_widgets["TOTAL FIRES"].config(text=str(event_count))
        self.stat_widgets["LAST KEY"].config(text=last_action)
        self.stat_widgets["LAST TIME"].config(text=last_action_time)
        if self.started_at:
            elapsed = max(0, int(time.time() - self.started_at))
            self.stat_widgets["UPTIME"].config(text=time.strftime("%H:%M:%S", time.gmtime(elapsed)))
            self.session.config(text=f"SESSION {time.strftime('%H:%M:%S', time.gmtime(elapsed))}")
        else:
            self.stat_widgets["UPTIME"].config(text="00:00")
            self.session.config(text="SESSION 00:00")
        self.last.config(text=f"Last action: {last_action}  •  {last_action_time}")

    def toggle(self):
        global running
        running = not running
        if running:
            self.started_at = time.time()
            self.button.set("■   STOP MACRO", RED)
            self.status.set("ONLINE", GREEN)
            self.log(f"{time.strftime('%H:%M:%S')}   ENGINE ARMED")
        else:
            self.button.set("▶   START MACRO", BLUE)
            self.status.set("OFFLINE", RED)
            self.log(f"{time.strftime('%H:%M:%S')}   ENGINE DISARMED")
        self.overlay.update(running, roblox_focused)
        self.refresh()

    def log(self, message):
        def append():
            self.box.configure(state="normal")
            self.box.insert("end", message + "\n")
            lines = int(self.box.index("end-1c").split(".")[0])
            if lines > 90:
                self.box.delete("1.0", "6.0")
            self.box.see("end")
            self.box.configure(state="disabled")
            if "COMBO EXECUTED" in message:
                self.rgb_strip.pulse()
                self.core.fire()
                key = message.split()[1] if len(message.split()) > 1 else "`"
                self.visualizer.trigger(3 if key == "`" else 2)
            self.refresh()
        self.root.after(0, append)

    def request_exit(self):
        self.root.after(0, self.exit_app)

    def exit_app(self):
        try:
            self.overlay.win.destroy()
            self.root.destroy()
        finally:
            os._exit(0)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

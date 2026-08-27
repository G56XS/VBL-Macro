"""VBL Macro — Apple-glass inspired reactive RGB dashboard.

The macro engine remains intentionally simple and unchanged in behavior:
` -> right click, space, left click
r -> right click, space
Both only fire while armed and, on Windows, while Roblox is focused.
"""

import colorsys
import ctypes
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

# Apple-glass inspired palette: dark translucent surfaces + bright spectral light.
BG = "#07090f"
GLASS = "#10141f"
GLASS_2 = "#151a28"
GLASS_3 = "#1b2233"
EDGE = "#2a3348"
TEXT = "#f7f9ff"
MUTED = "#8b95ae"
DIM = "#596277"
CYAN = "#32dcff"
BLUE = "#5a82ff"
PURPLE = "#a76cff"
PINK = "#ff5ad8"
GREEN = "#43e99a"
RED = "#ff5e79"
YELLOW = "#ffd968"
BLACK = "#020307"

running = False
roblox_focused = False
event_count = 0
last_action = "—"
last_action_time = "—"
session_start = time.time()
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
    for item in fallbacks:
        if item in available:
            return item
    return "TkDefaultFont"


def rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, amount):
    ar, ag, ab = rgb(a)
    br, bg, bb = rgb(b)
    amount = max(0.0, min(1.0, amount))
    return "#%02x%02x%02x" % (
        round(ar + (br - ar) * amount),
        round(ag + (bg - ag) * amount),
        round(ab + (bb - ab) * amount),
    )


def rainbow(h, s=.9, v=1.0):
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
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def is_roblox():
    return ROBLOX_TITLE_MATCH in active_title().lower()


def combo_tilde():
    pydirectinput.rightClick()
    pydirectinput.press("space")
    pydirectinput.leftClick()


def combo_r():
    pydirectinput.rightClick()
    pydirectinput.press("space")


def make_handler(key, action, app):
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
            app.root.after(0, app.macro_fired, key)
            app.log(f"{last_action_time}   {key.upper()}   COMBO EXECUTED   #{event_count}")
        elif event.event_type == "up":
            held.discard(key)
    return on_event


class GlassBackground(tk.Canvas):
    """Slow-moving colored light blooms behind the glass UI."""
    def __init__(self, master):
        super().__init__(master, bg=BG, highlightthickness=0)
        self.phase = 0.0
        self.bind("<Configure>", self.draw)
        self.after(50, self.tick)

    def draw(self, _=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10:
            return
        blobs = [
            (w * .17 + w * .03 * __import__('math').sin(self.phase), h * .18, 180, PURPLE, .90),
            (w * .86 + w * .025 * __import__('math').cos(self.phase * .8), h * .34, 230, CYAN, .93),
            (w * .68, h * .88 + h * .02 * __import__('math').sin(self.phase * .7), 280, PINK, .95),
        ]
        for cx, cy, radius, color, fade in blobs:
            for ring in range(7, 0, -1):
                r = radius * ring / 7
                self.create_oval(cx-r, cy-r, cx+r, cy+r,
                                 fill=mix(color, BG, fade - ring * .025), outline="")
        self.phase += .018

    def tick(self):
        self.draw()
        self.after(50, self.tick)


class RGBStrip(tk.Canvas):
    """Spectral top strip that flashes brighter for a macro event."""
    def __init__(self, master):
        super().__init__(master, height=7, bg=BG, highlightthickness=0)
        self.phase = 0.0
        self.flash = 0.0
        self.bind("<Configure>", self.draw)
        self.after(30, self.tick)

    def pulse(self):
        self.flash = 1.0

    def draw(self, _=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2:
            return
        for x in range(w):
            c = rainbow(self.phase + x / max(w, 1), .86, min(1.0, .9 + self.flash * .1))
            self.create_line(x, 0, x, h, fill=c)
        sweep = ((self.phase * 0.15) % 1.0) * w
        self.create_line(sweep, 0, sweep + 50, h, fill=mix(TEXT, CYAN, .65), width=1)

    def tick(self):
        self.phase += .0028
        self.flash *= .84
        self.draw()
        self.after(30, self.tick)


class GlassCard(tk.Frame):
    """Rounded translucent-looking surface with inner highlight and RGB edge."""
    def __init__(self, master, accent, fill=GLASS):
        super().__init__(master, bg=BG)
        self.accent = accent
        self.fill = fill
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=fill)
        self.item = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.canvas.bind("<Configure>", self.draw)

    def finalize(self, height=None):
        self.body.update_idletasks()
        self.canvas.configure(height=height or self.body.winfo_reqheight())
        self.draw()

    def draw(self, _=None):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 5 or h < 5:
            return
        self.canvas.delete("shape")
        self.canvas.create_polygon(rr(1, 1, w-1, h-1, 23), fill=mix(self.accent, BG, .94), outline="", smooth=True, tags="shape")
        self.canvas.create_polygon(rr(3, 3, w-3, h-3, 21), fill=self.fill, outline=EDGE, width=1, smooth=True, tags="shape")
        self.canvas.create_line(25, 4, w-25, 4, fill=mix(self.accent, TEXT, .66), width=1.7, capstyle="round", tags="shape")
        self.canvas.create_line(28, h-4, w-60, h-4, fill=mix(self.fill, TEXT, .05), width=1, capstyle="round", tags="shape")
        self.canvas.tag_lower("shape")
        self.canvas.coords(self.item, 0, 0)
        self.canvas.itemconfigure(self.item, width=w, height=h)


class GlassButton(tk.Canvas):
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
        c = mix(self.color, TEXT, .12 if self.hover else 0)
        if self.pressed:
            c = mix(c, BLACK, .18)
        self.create_polygon(rr(2, 2, w-2, h-2, h/2), fill=mix(c, BLACK, .08), outline="", smooth=True)
        self.create_line(26, 5, w-26, 5, fill=mix(c, TEXT, .36), width=1.5, capstyle="round")
        self.create_text(w/2, h/2, text=self.text, fill=TEXT,
                         font=(family("Segoe UI Semibold", ["Segoe UI"]), 12, "bold"))

    def release(self, event):
        self.pressed = False
        self.draw()
        if 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self.command()

    def set(self, text, color):
        self.text, self.color = text, color
        self.draw()


class Pill(tk.Canvas):
    def __init__(self, master, text, color, width=180):
        super().__init__(master, height=28, width=width, bg=master.cget("bg"), highlightthickness=0)
        self.text, self.color = text, color
        self.bind("<Configure>", self.draw)

    def draw(self, _=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        self.create_polygon(rr(0, 0, w, h, h/2), fill=mix(self.color, GLASS, .82), outline=mix(self.color, GLASS, .44), smooth=True)
        self.create_oval(9, h/2-4, 17, h/2+4, fill=self.color, outline="")
        self.create_text(25, h/2, anchor="w", text=self.text, fill=self.color,
                         font=(family("Segoe UI", ["Arial"]), 8, "bold"))

    def set(self, text, color):
        self.text, self.color = text, color
        self.draw()


class EnergyCore(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, width=124, height=124, bg=GLASS, highlightthickness=0)
        self.phase = 0.0
        self.burst = 0.0
        self.state = "idle"
        self.after(40, self.tick)

    def set_state(self, state):
        self.state = state

    def fire(self):
        self.burst = 1.0

    def tick(self):
        import math
        self.delete("all")
        color = {"idle": DIM, "waiting": YELLOW, "live": GREEN}.get(self.state, DIM)
        pulse = (math.sin(self.phase) + 1) / 2
        cx = cy = 62
        glow = pulse * 4 + self.burst * 12
        for extra, alpha in ((30+glow, .90), (23+glow, .84), (18+glow, .72)):
            self.create_oval(cx-extra, cy-extra, cx+extra, cy+extra, fill=mix(color, GLASS, alpha), outline="")
        outer = 35 + pulse*1.6 + self.burst*5
        self.create_oval(cx-outer, cy-outer, cx+outer, cy+outer, fill=GLASS_2, outline=color, width=1)
        inner = 25 + pulse*1.2 + self.burst*4
        self.create_oval(cx-inner, cy-inner, cx+inner, cy+inner, fill=mix(color, BLACK, .18), outline="")
        self.create_oval(cx-8, cy-8, cx+8, cy+8, fill=TEXT, outline="")
        self.create_oval(cx-3.5, cy-4.5, cx-.3, cy-.3, fill=WHITEISH, outline="") if False else None
        self.create_text(cx, 108, text={"idle":"STANDBY","waiting":"WAITING","live":"LIVE"}.get(self.state, "STANDBY"),
                         fill=color, font=(family("Segoe UI Semibold", ["Segoe UI"]), 8, "bold"))
        self.phase += .11
        self.burst *= .72
        self.after(40, self.tick)


class ComboVisualizer(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, height=70, bg=GLASS, highlightthickness=0)
        self.progress = 0
        self.steps = 3
        self.cooldown = 0

    def trigger(self, steps=3):
        self.progress = 0
        self.steps = steps
        self.cooldown = 1
        self.after(70, self.advance)

    def advance(self):
        if self.progress < self.steps:
            self.progress += 1
            self.draw()
            self.after(85, self.advance)
        else:
            self.after(260, self.reset)

    def reset(self):
        self.progress = 0
        self.draw()

    def draw(self, _=None):
        self.delete("all")
        w, _h = self.winfo_width(), self.winfo_height()
        labels = [(42, "RMB", CYAN), (w/2, "SPACE", PURPLE), (w-42, "LMB", PINK)]
        active_steps = self.progress
        for i, (x, label, color) in enumerate(labels, 1):
            active = i <= active_steps
            fill = color if active else GLASS_3
            outline = color if active else EDGE
            self.create_oval(x-18, 10, x+18, 46, fill=fill, outline=outline, width=1)
            self.create_text(x, 28, text=str(i), fill=BLACK if active else MUTED,
                             font=(family("Cascadia Mono", ["Consolas"]), 9, "bold"))
            self.create_text(x, 58, text=label, fill=color if active else MUTED,
                             font=(family("Cascadia Mono", ["Consolas"]), 7, "bold"))
        for x1, x2 in ((60, w/2-20), (w/2+20, w-60)):
            self.create_line(x1, 28, x2, 28, fill=EDGE, width=2)
        # 2-step R combo shares the same visualizer; the last node simply stays dim.


class EventToast:
    def __init__(self, root):
        self.label = tk.Label(root, text="", bg=GLASS_3, fg=TEXT,
                              font=(family("Segoe UI Semibold", ["Segoe UI"]), 9, "bold"),
                              padx=14, pady=7, bd=0)
        self.after_id = None

    def show(self, text, color):
        self.label.config(text=text, fg=color)
        self.label.place(relx=1.0, rely=1.0, x=-28, y=-24, anchor="se")
        if self.after_id:
            try:
                self.label.after_cancel(self.after_id)
            except Exception:
                pass
        self.after_id = self.label.after(1200, self.hide)

    def hide(self):
        self.label.place_forget()


class Overlay:
    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)
        try:
            self.win.attributes("-alpha", .95)
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
        self.W, self.H = 310, 94
        sh = self.win.winfo_screenheight()
        self.win.geometry(f"{self.W}x{self.H}+24+{sh-self.H-88}")
        self.canvas = tk.Canvas(self.win, width=self.W, height=self.H,
                                bg=matte if IS_WINDOWS else BG, highlightthickness=0)
        self.canvas.pack()
        self.phase = 0.0
        self.state = "stopped"
        self.drag = (0, 0)
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag_move)
        self.animate()

    def start_drag(self, e):
        self.drag = (e.x, e.y)

    def drag_move(self, _):
        self.win.geometry(f"+{self.win.winfo_pointerx()-self.drag[0]}+{self.win.winfo_pointery()-self.drag[1]}")

    def update(self, r, f):
        self.state = "stopped" if not r else ("waiting" if IS_WINDOWS and not f else "active")

    def animate(self):
        self.canvas.delete("all")
        color = {"stopped": RED, "waiting": YELLOW, "active": GREEN}[self.state]
        title = {"stopped":"OFFLINE", "waiting":"WAITING", "active":"LIVE"}[self.state]
        detail = {"stopped":"Macro disarmed", "waiting":"Waiting for Roblox focus", "active":"Hotkeys ready  •  ` + R"}[self.state]
        self.canvas.create_polygon(rr(2,2,self.W-2,self.H-2,24), fill=GLASS_2, outline=EDGE, width=1, smooth=True)
        for i in range(56):
            x = 20 + i*(270/56)
            self.canvas.create_line(x, 4, x+5, 4, fill=rainbow(self.phase+i/56,.82,1), width=2)
        import math
        pulse = (math.sin(self.phase*8)+1)/2
        r = 6 + pulse
        self.canvas.create_oval(27-r-4,45-r-4,27+r+4,45+r+4, fill=mix(color,GLASS_2,.8), outline="")
        self.canvas.create_oval(27-r,45-r,27+r,45+r, fill=color, outline="")
        self.canvas.create_oval(25,43,27,45, fill=TEXT, outline="")
        self.canvas.create_text(50,34,anchor="w",text=title,fill=color,font=(family("Segoe UI Semibold",["Segoe UI"]),13,"bold"))
        self.canvas.create_text(50,59,anchor="w",text=detail,fill=MUTED,font=(family("Segoe UI",["Arial"]),9))
        self.phase += .008
        self.win.after(40, self.animate)


class App:
    def __init__(self, root):
        self.root = root
        self.fd = family("Segoe UI Semibold", ["Segoe UI"])
        self.ft = family("Segoe UI", ["Arial"])
        self.fm = family("Cascadia Mono", ["Consolas", "Courier New"])
        root.title("VBL Macro")
        root.configure(bg=BG)
        root.geometry("600x790")
        root.minsize(540, 700)
        try:
            root.attributes("-alpha", .97)
        except Exception:
            pass

        ico, png = resource_path("app_icon.ico"), resource_path("icon_512.png")
        try:
            if IS_WINDOWS and os.path.exists(ico):
                root.iconbitmap(default=ico)
            elif os.path.exists(png):
                self.icon = tk.PhotoImage(file=png)
                root.iconphoto(True, self.icon)
        except Exception:
            pass

        # Full-window glassy background layer.
        self.bg = GlassBackground(root)
        self.bg.place(x=0, y=0, relwidth=1, relheight=1)
        RGBStrip(root).place(x=0, y=0, relwidth=1, height=7)

        outer = tk.Frame(root, bg=BG)
        outer.place(x=26, y=30, relwidth=.913, relheight=.925)

        # Header
        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", pady=(0, 14))
        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left")
        tk.Label(brand, text="VBL", font=(self.fd, 10, "bold"), fg=CYAN, bg=BG).pack(anchor="w")
        tk.Label(brand, text="MACRO", font=(self.fd, 27, "bold"), fg=TEXT, bg=BG).pack(anchor="w")
        tk.Label(brand, text="REACTIVE INPUT SYSTEM  •  ROBLOX", font=(self.ft, 9), fg=MUTED, bg=BG).pack(anchor="w")
        self.status = Pill(header, "OFFLINE", RED, 150)
        self.status.pack(side="right", pady=12)

        focus_row = tk.Frame(outer, bg=BG)
        focus_row.pack(fill="x", pady=(0, 15))
        self.focus = Pill(focus_row, "ROBLOX NOT FOCUSED" if IS_WINDOWS else "WINDOW DETECTION: WINDOWS ONLY",
                          RED if IS_WINDOWS else MUTED, 320)
        self.focus.pack(side="left", fill="x", expand=True)
        self.count = tk.Label(focus_row, text="0 FIRES", font=(self.fm, 8, "bold"), fg=CYAN, bg=BG)
        self.count.pack(side="right", padx=(12, 0))

        # Master glass card
        master = GlassCard(outer, BLUE)
        master.pack(fill="x", pady=(0, 15))
        mb = master.body
        cap = tk.Frame(mb, bg=GLASS)
        cap.pack(fill="x", padx=20, pady=(17, 6))
        tk.Label(cap, text="MASTER CONTROL", font=(self.ft, 9, "bold"), fg=MUTED, bg=GLASS).pack(side="left")
        self.session = tk.Label(cap, text="SESSION 00:00:00", font=(self.fm, 8), fg=DIM, bg=GLASS)
        self.session.pack(side="right")

        center = tk.Frame(mb, bg=GLASS)
        center.pack(fill="x", padx=18, pady=(4, 8))
        self.core = EnergyCore(center)
        self.core.pack(side="left", padx=(4, 16))
        details = tk.Frame(center, bg=GLASS)
        details.pack(side="left", fill="both", expand=True, pady=(6, 0))
        self.engine_caption = tk.Label(details, text="ENGINE STATUS", font=(self.ft, 8, "bold"), fg=MUTED, bg=GLASS)
        self.engine_caption.pack(anchor="w")
        self.engine_status = tk.Label(details, text="STANDBY", font=(self.fd, 17, "bold"), fg=TEXT, bg=GLASS)
        self.engine_status.pack(anchor="w", pady=(3, 2))
        self.last = tk.Label(details, text="Last action  •  —", font=(self.fm, 8), fg=DIM, bg=GLASS)
        self.last.pack(anchor="w")

        self.toggle = GlassButton(mb, "▶   START MACRO", self.toggle_macro, BLUE)
        self.toggle.pack(fill="x", padx=20, pady=(0, 11))
        foot = tk.Frame(mb, bg=GLASS)
        foot.pack(fill="x", padx=22, pady=(0, 17))
        self.engine_hint = tk.Label(foot, text="Focus protection ON", font=(self.ft, 8), fg=DIM, bg=GLASS)
        self.engine_hint.pack(side="left")
        tk.Label(foot, text="ESC  QUIT", font=(self.fm, 8), fg=DIM, bg=GLASS).pack(side="right")
        master.finalize()

        # Combo cards
        combos = GlassCard(outer, PURPLE)
        combos.pack(fill="x", pady=(0, 15))
        cb = combos.body
        head = tk.Frame(cb, bg=GLASS)
        head.pack(fill="x", padx=20, pady=(15, 6))
        tk.Label(head, text="COMBO PROFILES", font=(self.ft, 9, "bold"), fg=MUTED, bg=GLASS).pack(side="left")
        tk.Label(head, text="REACTIVE", font=(self.fm, 8, "bold"), fg=CYAN, bg=GLASS).pack(side="right")
        self.combo_row(cb, "`", "RIGHT CLICK  →  SPACE  →  LEFT CLICK", CYAN, "3-STEP")
        self.combo_row(cb, "R", "RIGHT CLICK  →  SPACE", PURPLE, "2-STEP")
        self.visual = ComboVisualizer(cb)
        self.visual.pack(fill="x", padx=20, pady=(9, 3))
        tk.Label(cb, text="Visual pipeline lights each stage during execution.", font=(self.ft, 8), fg=DIM, bg=GLASS).pack(anchor="w", padx=20, pady=(0, 14))
        combos.finalize()

        # Telemetry
        telemetry = GlassCard(outer, PINK)
        telemetry.pack(fill="both", expand=True, pady=(0, 12))
        tb = telemetry.body
        th = tk.Frame(tb, bg=GLASS)
        th.pack(fill="x", padx=20, pady=(15, 9))
        tk.Label(th, text="SESSION TELEMETRY", font=(self.ft, 9, "bold"), fg=MUTED, bg=GLASS).pack(side="left")
        self.live = tk.Label(th, text="● IDLE", font=(self.ft, 8, "bold"), fg=DIM, bg=GLASS)
        self.live.pack(side="right")

        stats = tk.Frame(tb, bg=GLASS)
        stats.pack(fill="x", padx=20, pady=(0, 10))
        self.stat_labels = []
        for title, value, accent in (("TOTAL FIRES", "0", CYAN), ("LAST KEY", "—", PURPLE), ("LAST TIME", "—", PINK), ("UPTIME", "00:00:00", GREEN)):
            box = tk.Frame(stats, bg=GLASS_2)
            box.pack(side="left", fill="both", expand=True, padx=3)
            tk.Frame(box, bg=accent, height=2).pack(fill="x")
            tk.Label(box, text=title, font=(self.ft, 7, "bold"), fg=MUTED, bg=GLASS_2).pack(anchor="w", padx=9, pady=(7, 2))
            lbl = tk.Label(box, text=value, font=(self.fd, 13, "bold"), fg=TEXT, bg=GLASS_2)
            lbl.pack(anchor="w", padx=9, pady=(0, 8))
            self.stat_labels.append(lbl)

        tk.Label(tb, text="ACTIVITY", font=(self.ft, 8, "bold"), fg=MUTED, bg=GLASS).pack(anchor="w", padx=20, pady=(2, 5))
        self.box = tk.Text(tb, bg=BLACK, fg="#e3e9f8", insertbackground=TEXT, relief="flat", bd=0,
                           font=(self.fm, 8), height=6, wrap="word", state="disabled", padx=12, pady=10)
        self.box.pack(fill="both", expand=True, padx=17, pady=(0, 16))
        telemetry.canvas.configure(height=225)

        self.toast = EventToast(root)
        self.overlay = Overlay(root)

        keyboard.hook_key("`", make_handler("`", combo_tilde, self))
        keyboard.hook_key("r", make_handler("r", combo_r, self))
        keyboard.add_hotkey("esc", self.request_exit, suppress=False)

        self.last_focus = None
        if IS_WINDOWS:
            threading.Thread(target=self.poll_roblox, daemon=True).start()
        threading.Thread(target=self.poll_overlay, daemon=True).start()
        self.root.after(250, self.update_session)

        self.log("System initialized — glass engine ready.")
        if IS_WINDOWS:
            self.log("Roblox focus protection enabled.")
        self.log("Press START MACRO to arm input.")

    def combo_row(self, parent, key, text, accent, tag):
        row = tk.Frame(parent, bg=GLASS)
        row.pack(fill="x", padx=20, pady=4)
        badge = tk.Label(row, text=f" {key} ", font=(self.fm, 10, "bold"), fg=BLACK, bg=accent, padx=8, pady=5)
        badge.pack(side="left")
        tk.Label(row, text=text, font=(self.ft, 10), fg=TEXT, bg=GLASS).pack(side="left", padx=12)
        tk.Label(row, text=tag, font=(self.fm, 7, "bold"), fg=accent, bg=mix(accent, GLASS, .86), padx=7, pady=3).pack(side="right")

    def poll_roblox(self):
        global roblox_focused
        while True:
            focused = is_roblox()
            if focused != roblox_focused:
                roblox_focused = focused
                self.root.after(0, self.update_focus, focused)
            time.sleep(.2)

    def poll_overlay(self):
        previous = None
        while True:
            state = (running, roblox_focused)
            if state != previous:
                previous = state
                self.root.after(0, self.overlay.update, *state)
                self.root.after(0, self.refresh_state)
            time.sleep(.1)

    def refresh_state(self):
        if running:
            if IS_WINDOWS and not roblox_focused:
                self.live.config(text="● WAITING", fg=YELLOW)
                self.engine_status.config(text="WAITING FOR ROBLOX", fg=YELLOW)
                self.core.set_state("waiting")
                self.engine_hint.config(text="Armed  •  waiting for Roblox focus")
            else:
                self.live.config(text="● LIVE", fg=GREEN)
                self.engine_status.config(text="INPUT LIVE", fg=GREEN)
                self.core.set_state("live")
                self.engine_hint.config(text="Input armed  •  focus lock active")
        else:
            self.live.config(text="● IDLE", fg=DIM)
            self.engine_status.config(text="STANDBY", fg=TEXT)
            self.core.set_state("idle")
            self.engine_hint.config(text="Focus protection ON")
        self.count.config(text=f"{event_count} FIRES")
        self.stat_labels[0].config(text=str(event_count))
        self.stat_labels[1].config(text=last_action)
        self.stat_labels[2].config(text=last_action_time)
        self.stat_labels[3].config(text=self.uptime())
        self.last.config(text=f"Last action  •  {last_action_time if last_action_time != '—' else '—'}")

    def update_focus(self, focused):
        self.focus.set("ROBLOX FOCUSED  •  INPUT READY" if focused else "ROBLOX NOT FOCUSED", GREEN if focused else RED)
        self.refresh_state()

    def toggle_macro(self):
        global running, session_start
        running = not running
        if running:
            session_start = time.time()
            self.toggle.set("■   STOP MACRO", RED)
            self.status.set("ONLINE", GREEN)
            self.log(f"{time.strftime('%H:%M:%S')}   ENGINE ARMED")
        else:
            self.toggle.set("▶   START MACRO", BLUE)
            self.status.set("OFFLINE", RED)
            self.log(f"{time.strftime('%H:%M:%S')}   ENGINE DISARMED")
        self.refresh_state()
        self.overlay.update(running, roblox_focused)

    def macro_fired(self, key):
        self.core.fire()
        self.visual.trigger(3 if key == "`" else 2)
        # Make the otherwise hidden 3rd node stay dim for the 2-step combo.
        if key == "r":
            self.root.after(120, self.visual.draw)
        self.toast.show(f"⚡  {key.upper()}  COMBO EXECUTED", CYAN if key == "`" else PURPLE)

        # Reactive top strip lives on the root and is found by the first Canvas widget.
        for child in self.root.winfo_children():
            if isinstance(child, RGBStrip):
                child.pulse()
                break

    def uptime(self):
        elapsed = max(0, int(time.time() - session_start)) if running else 0
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def update_session(self):
        self.refresh_state()
        self.root.after(250, self.update_session)

    def log(self, message):
        def append():
            self.box.configure(state="normal")
            self.box.insert("end", message + "\n")
            lines = int(self.box.index("end-1c").split(".")[0])
            if lines > 80:
                self.box.delete("1.0", "4.0")
            self.box.see("end")
            self.box.configure(state="disabled")
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

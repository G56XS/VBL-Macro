"""
Click Macro — GUI version.

Hotkeys (only fire while the app is Started AND Roblox is the focused
window — Windows only; on other OSes the Roblox check is skipped):
    `  ->  Right Click, Space, Left Click   (instant, no delay)
    r  ->  Right Click, Space

Requires:
    pip install keyboard pydirectinput pillow

Run:
    python key_macro_gui.py

Notes:
- On Windows, run as Administrator if the hotkeys don't register in a game
  (elevated games ignore input from non-elevated processes).
- Click "Start" to arm the hotkeys, "Stop" to disarm them. Even while
  Started, the hotkeys stay inactive unless Roblox is the focused window.
- Press ESC at any time to quit the app immediately.
- A small always-on-top overlay (draggable) shows live status — stopped /
  waiting for Roblox / active — so you can see it on top of the game
  without alt-tabbing.
- Roblox detection checks the foreground window's title for "Roblox" and
  polls every 200ms — this covers the Roblox client window (and the
  browser tab title, if you play Roblox in a browser tab titled
  "Roblox - ...", since it also focuses that same OS window).
- app_icon.ico / icon_512.png must be in the same folder as this script.
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


def resource_path(filename):
    """Resolve a path to a bundled file, whether running as a plain script
    or as a PyInstaller-frozen executable (onefile extracts data files to
    a temp folder referenced by sys._MEIPASS)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = BASE_DIR
    return os.path.join(base, filename)
IS_WINDOWS = sys.platform.startswith("win")

# Window title is matched case-insensitively against this substring.
ROBLOX_TITLE_MATCH = "roblox"


def get_active_window_title():
    """Return the title of the currently focused window (Windows only)."""
    if not IS_WINDOWS:
        return ""
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    return buff.value


def is_roblox_focused():
    title = get_active_window_title()
    return ROBLOX_TITLE_MATCH in title.lower()

# ---- theme -----------------------------------------------------------------
BG = "#0f1220"
PANEL = "#171b2e"
PANEL_BORDER = "#2a2f4a"
ACCENT1 = "#7c3aed"   # violet
ACCENT2 = "#22d3ee"   # cyan
TEXT = "#e7e9f5"
SUBTEXT = "#8b90b3"
GREEN = "#34d399"
RED = "#f87171"
YELLOW = "#facc15"

_held = set()
running = False
roblox_focused = False
event_count = 0


def combo_tilde():
    pydirectinput.rightClick()
    pydirectinput.press("space")
    pydirectinput.leftClick()


def combo_r():
    pydirectinput.rightClick()
    pydirectinput.press("space")


def make_handler(key, action, log_fn):
    def handler(event):
        global event_count
        if not running:
            return
        if IS_WINDOWS and not roblox_focused:
            return
        if event.event_type == "down":
            if key not in _held:
                _held.add(key)
                action()
                event_count += 1
                log_fn(f"[{time.strftime('%H:%M:%S')}]  '{key}'  fired  (#{event_count})")
        elif event.event_type == "up":
            _held.discard(key)
    return handler


class GradientBar(tk.Canvas):
    """A thin horizontal violet->cyan gradient strip used as a decorative accent."""

    def __init__(self, master, height=4, **kw):
        super().__init__(master, height=height, highlightthickness=0, bg=PANEL, **kw)
        self.bind("<Configure>", self._draw)

    def _hex_to_rgb(self, h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        c1 = self._hex_to_rgb(ACCENT1)
        c2 = self._hex_to_rgb(ACCENT2)
        steps = max(w, 1)
        for i in range(steps):
            t = i / steps
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            self.create_line(i, 0, i, h, fill=f"#{r:02x}{g:02x}{b:02x}")


def _lerp_color(hex1, hex2, t):
    """Blend two hex colors; t=0 -> hex1, t=1 -> hex2."""
    h1 = hex1.lstrip("#")
    h2 = hex2.lstrip("#")
    r1, g1, b1 = int(h1[0:2], 16), int(h1[2:4], 16), int(h1[4:6], 16)
    r2, g2, b2 = int(h2[0:2], 16), int(h2[2:4], 16), int(h2[4:6], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _hsv_hex(h, s, v):
    """h, s, v in [0, 1] -> '#rrggbb'."""
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def _round_rect_points(x1, y1, x2, y2, radius):
    """Point list for a smoothed rounded-rectangle polygon on a Canvas."""
    r = radius
    return [
        x1 + r, y1,  x2 - r, y1,  x2, y1,
        x2, y1 + r,  x2, y2 - r,  x2, y2,
        x2 - r, y2,  x1 + r, y2,  x1, y2,
        x1, y2 - r,  x1, y1 + r,  x1, y1,
    ]


class Overlay:
    """A tiny always-on-top, borderless window showing live macro status,
    so it's visible on top of Roblox while you play."""

    STATE_COLORS = {
        "stopped": RED,
        "waiting": YELLOW,   # started, but Roblox isn't focused
        "active": GREEN,     # armed and ready to fire
    }
    STATE_TEXT = {
        "stopped": "STOPPED",
        "waiting": "WAITING",
        "active": "ACTIVE",
    }
    STATE_DETAIL = {
        "stopped": "Click START to arm",
        "waiting": "Waiting for Roblox focus",
        "active": "Hotkeys ready: ` and r",
    }

    W, H = 232, 78
    RADIUS = 16

    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)          # no title bar / borders
        self.win.attributes("-topmost", True)     # stay above Roblox
        self.win.resizable(False, False)

        # True click-through-looking transparency on Windows; a plain
        # semi-transparent panel elsewhere. Everything outside the rounded
        # rect we draw stays this color, so it "disappears" on Windows.
        matte = "#010203"
        try:
            if IS_WINDOWS:
                self.win.configure(bg=matte)
                self.win.attributes("-transparentcolor", matte)
                canvas_bg = matte
            else:
                self.win.configure(bg=BG)
                self.win.attributes("-alpha", 0.92)
                canvas_bg = BG
        except Exception:
            self.win.configure(bg=BG)
            canvas_bg = BG

        # Bottom-left placement keeps it clear of top-of-screen game HUD
        # (score bar, round/skull indicator, window buttons) and off the
        # OS taskbar at the very bottom. Still fully draggable afterward.
        screen_w = self.win.winfo_screenwidth()
        screen_h = self.win.winfo_screenheight()
        self.win.geometry(f"{self.W}x{self.H}+24+{screen_h - self.H - 90}")

        self.canvas = tk.Canvas(
            self.win, width=self.W, height=self.H, bg=canvas_bg,
            highlightthickness=0
        )
        self.canvas.place(x=0, y=0, width=self.W, height=self.H)

        pad = 1  # keep the border stroke fully inside the canvas
        self._panel = self.canvas.create_polygon(
            _round_rect_points(pad, pad, self.W - pad, self.H - pad, self.RADIUS),
            fill=PANEL, outline=PANEL_BORDER, width=1.4, smooth=True
        )

        # RGB light strip hugging the top inside edge — a slowly cycling
        # rainbow rather than a fixed gradient, like an RGB LED strip.
        self._strip_inset = self.RADIUS * 0.55
        self._strip_y = pad + 4
        self._strip_steps = 48
        x0 = pad + self._strip_inset
        x1 = self.W - pad - self._strip_inset
        span = x1 - x0
        self._strip_ids = []
        for i in range(self._strip_steps):
            t0 = i / self._strip_steps
            t1 = (i + 1) / self._strip_steps
            seg = self.canvas.create_line(
                x0 + span * t0, self._strip_y, x0 + span * t1, self._strip_y,
                fill=ACCENT1, width=3, capstyle="round"
            )
            self._strip_ids.append((seg, (t0 + t1) / 2))

        # Glowing status dot: a smooth, lamp-like halo built from many thin
        # concentric rings whose spacing/blend both taper non-linearly, so
        # it reads as a soft continuous glow rather than a few hard bands.
        # Coordinates are re-drawn every animation tick to breathe.
        self.dot_cx, self.dot_cy, self.dot_r = 22, 42, 3.5
        self._glow_layers = 10
        self._glow_max_extra = 8 / 1.5   # outer halo diameter, shrunk 1.5x
        self._glow_ids = [
            self.canvas.create_oval(0, 0, 0, 0, fill=PANEL, outline="")
            for _ in range(self._glow_layers)
        ]

        self._core_layer_ids = [
            self.canvas.create_oval(0, 0, 0, 0, fill=RED, outline="")
            for _ in range(4)
        ]
        self._highlight_id = self.canvas.create_oval(0, 0, 0, 0, fill=TEXT, outline="")

        self.status_text_id = self.canvas.create_text(
            self.dot_cx + 18, self.dot_cy, anchor="w",
            text=self.STATE_TEXT["stopped"], fill=RED,
            font=("Segoe UI", 13, "bold")
        )
        self.detail_text_id = self.canvas.create_text(
            self.dot_cx - self.dot_r, self.dot_cy + 21, anchor="w",
            text=self.STATE_DETAIL["stopped"], fill=SUBTEXT,
            font=("Segoe UI", 8)
        )

        # Let the overlay itself be dragged to a new spot.
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._do_drag)
        self._drag = (0, 0)

        # Animation state: a breathing sine phase for the dot and a
        # slowly-rotating hue offset for the RGB strip. One shared
        # ~30fps tick drives both, independent of macro state.
        self._state = "stopped"
        self._phase = 0.0
        self._hue = 0.0
        self._animate()

    def _start_drag(self, event):
        self._drag = (event.x, event.y)

    def _do_drag(self, event):
        x = self.win.winfo_pointerx() - self._drag[0]
        y = self.win.winfo_pointery() - self._drag[1]
        self.win.geometry(f"+{x}+{y}")

    def update(self, running_, roblox_focused_):
        if not running_:
            state = "stopped"
        elif IS_WINDOWS and not roblox_focused_:
            state = "waiting"
        else:
            state = "active"

        self._state = state
        color = self.STATE_COLORS[state]
        self.canvas.itemconfig(self.status_text_id, text=self.STATE_TEXT[state], fill=color)
        self.canvas.itemconfig(self.detail_text_id, text=self.STATE_DETAIL[state])
        # Colors/geometry for the dot itself are painted continuously by
        # _animate(); no need to touch them here.

    def _animate(self):
        # ---- breathing status dot: dim -> bright -> dim, smooth sine ----
        pulse = (math.sin(self._phase) + 1) / 2       # 0 (dim) .. 1 (bright)
        color = self.STATE_COLORS[self._state]
        core_dim = _lerp_color(color, "#000000", 0.45)
        core_bright = _lerp_color(color, "#ffffff", 0.55)
        base_color = _lerp_color(core_dim, core_bright, pulse)

        r = self.dot_r + pulse * 1.0
        cx, cy = self.dot_cx, self.dot_cy

        # Radial gradient: nested ovals shrinking toward the center while
        # lightening toward white, so the dot reads as a glossy little
        # sphere instead of a flat circle.
        n = len(self._core_layer_ids)
        for i, layer in enumerate(self._core_layer_ids):
            t = i / (n - 1)
            lr = r * (1 - t * 0.72)
            layer_color = _lerp_color(base_color, "#ffffff", 0.12 + t * 0.6)
            self.canvas.coords(layer, cx - lr, cy - lr, cx + lr, cy + lr)
            self.canvas.itemconfig(layer, fill=layer_color)

        # Small specular highlight, offset toward the upper-left, to sell
        # the glossy/3D feel.
        hl_r = r * 0.30
        hl_cx, hl_cy = cx - r * 0.32, cy - r * 0.32
        self.canvas.coords(
            self._highlight_id,
            hl_cx - hl_r, hl_cy - hl_r * 0.75, hl_cx + hl_r, hl_cy + hl_r * 0.75
        )
        self.canvas.itemconfig(self._highlight_id, fill=_lerp_color("#ffffff", base_color, 0.2))

        for i, ring in enumerate(self._glow_ids):
            t = (i + 1) / self._glow_layers          # 0 (near core) .. 1 (outer edge)
            # Non-linear spacing packs more rings close to the core and
            # spreads them out toward the edge, which reads as a smooth
            # continuous taper instead of discrete steps.
            extra = self._glow_max_extra * (t ** 1.6) + pulse * (2.3 * (1 - t * 0.4))
            re = self.dot_r + extra
            self.canvas.coords(ring, cx - re, cy - re, cx + re, cy + re)
            # Fade smoothly from the state color (near core) toward the
            # panel color (outer edge); breathing also lifts overall glow.
            # Capped below 1.0 so the outermost ring still holds a visible
            # tint instead of dissolving fully into the panel background.
            fade = min(0.82, (t ** 1.15) * 0.68 + (1 - pulse) * 0.14)
            self.canvas.itemconfig(ring, fill=_lerp_color(color, PANEL, fade))

        # ---- RGB strip: colors slowly cycle through the hue wheel ----
        for seg, t in self._strip_ids:
            hue = (self._hue + t * 0.6) % 1.0
            self.canvas.itemconfig(seg, fill=_hsv_hex(hue, 0.85, 1.0))

        self._phase += 0.11        # ~2.3s per full breathing cycle at 40ms
        self._hue = (self._hue + 0.0035) % 1.0
        self.win.after(40, self._animate)


class App:
    def __init__(self, root):
        self.root = root
        root.title("Click Macro")
        root.configure(bg=BG)
        root.geometry("420x480")
        root.minsize(380, 440)

        icon_ico = resource_path("app_icon.ico")
        icon_png = resource_path("icon_512.png")
        try:
            if IS_WINDOWS and os.path.exists(icon_ico):
                # default=True makes this the icon for the titlebar AND the
                # taskbar, and is inherited by any child windows too.
                root.iconbitmap(default=icon_ico)
            elif os.path.exists(icon_png):
                self._icon_img = tk.PhotoImage(file=icon_png)
                root.iconphoto(True, self._icon_img)
        except Exception:
            pass

        title_font = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        mono_font = tkfont.Font(family="Consolas", size=10)
        label_font = tkfont.Font(family="Segoe UI", size=10)
        small_font = tkfont.Font(family="Segoe UI", size=9)

        outer = tk.Frame(root, bg=BG)
        outer.pack(fill="both", expand=True, padx=18, pady=18)

        # Header
        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x")
        tk.Label(header, text="⚡ Click Macro", font=title_font, fg=TEXT, bg=BG).pack(side="left")

        self.status_dot = tk.Canvas(header, width=14, height=14, bg=BG, highlightthickness=0)
        self.status_dot.pack(side="right", padx=(0, 4), pady=4)
        self.status_circle = self.status_dot.create_oval(2, 2, 12, 12, fill=RED, outline="")

        self.status_label = tk.Label(header, text="STOPPED", font=small_font, fg=RED, bg=BG)
        self.status_label.pack(side="right", padx=(0, 6))

        GradientBar(outer, height=3).pack(fill="x", pady=(10, 12))

        # Roblox detection row
        rbx_row = tk.Frame(outer, bg=BG)
        rbx_row.pack(fill="x", pady=(0, 12))

        self.rbx_dot = tk.Canvas(rbx_row, width=12, height=12, bg=BG, highlightthickness=0)
        self.rbx_dot.pack(side="left", pady=2)
        self.rbx_circle = self.rbx_dot.create_oval(2, 2, 10, 10, fill=RED, outline="")

        self.rbx_label = tk.Label(
            rbx_row, text="Roblox not focused", font=("Segoe UI", 9), fg=SUBTEXT, bg=BG
        )
        self.rbx_label.pack(side="left", padx=(8, 0))

        if not IS_WINDOWS:
            self.rbx_label.configure(text="Auto-detect requires Windows — hotkeys always active")

        # Bindings panel
        panel = tk.Frame(outer, bg=PANEL, highlightbackground=PANEL_BORDER, highlightthickness=1)
        panel.pack(fill="x", pady=(0, 16))

        tk.Label(panel, text="HOTKEYS", font=small_font, fg=SUBTEXT, bg=PANEL).pack(
            anchor="w", padx=14, pady=(12, 4))

        self._binding_row(panel, "`", "Right Click → Space → Left Click", ACCENT2, mono_font, label_font)
        self._binding_row(panel, "r", "Right Click → Space", ACCENT1, mono_font, label_font)

        tk.Frame(panel, bg=PANEL, height=10).pack()

        # Start/Stop button
        self.toggle_btn = tk.Button(
            outer, text="▶  START", font=("Segoe UI", 12, "bold"),
            bg=ACCENT1, fg="white", activebackground=ACCENT2, activeforeground="white",
            relief="flat", bd=0, cursor="hand2", command=self.toggle,
            padx=10, pady=10
        )
        self.toggle_btn.pack(fill="x", pady=(0, 14))

        # Log panel
        log_frame = tk.Frame(outer, bg=PANEL, highlightbackground=PANEL_BORDER, highlightthickness=1)
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="ACTIVITY", font=small_font, fg=SUBTEXT, bg=PANEL).pack(
            anchor="w", padx=14, pady=(10, 4))

        self.log_box = tk.Text(
            log_frame, bg="#0c0e1a", fg=TEXT, insertbackground=TEXT,
            font=mono_font, relief="flat", bd=0, height=10, wrap="word",
            state="disabled"
        )
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        footer_text = (
            "Hotkeys only work while Started AND a Roblox window is focused. "
            "Press ESC anytime to quit. "
            "Drag the small overlay to reposition it."
            if IS_WINDOWS else
            "Press ESC anytime to quit."
        )
        footer = tk.Label(
            outer, text=footer_text,
            font=small_font, fg=SUBTEXT, bg=BG, wraplength=380, justify="left"
        )
        footer.pack(fill="x", pady=(10, 0))

        keyboard.hook_key("`", make_handler("`", combo_tilde, self.log))
        keyboard.hook_key("r", make_handler("r", combo_r, self.log))
        keyboard.add_hotkey("esc", self._request_exit, suppress=False)

        self.overlay = Overlay(root)

        self._last_roblox_state = None
        if IS_WINDOWS:
            threading.Thread(target=self._poll_roblox, daemon=True).start()

        threading.Thread(target=self._poll_overlay, daemon=True).start()

        self.log("Ready. Click START to arm hotkeys.")
        if IS_WINDOWS:
            self.log("Hotkeys will only fire while a Roblox window is focused.")
        self.log("Press ESC anytime to quit.")

    def _poll_roblox(self):
        global roblox_focused
        while True:
            focused = is_roblox_focused()
            if focused != roblox_focused:
                roblox_focused = focused
                self.root.after(0, self._update_roblox_indicator, focused)
            time.sleep(0.2)

    def _poll_overlay(self):
        last_state = None
        while True:
            state = (running, roblox_focused)
            if state != last_state:
                last_state = state
                self.root.after(0, self.overlay.update, *state)
            time.sleep(0.1)

    def _request_exit(self):
        # keyboard callbacks run on a non-GUI thread; hop back to the main
        # thread before touching tkinter.
        self.root.after(0, self._exit_app)

    def _exit_app(self):
        self.log(f"[{time.strftime('%H:%M:%S')}]  ESC pressed — closing.")
        try:
            self.root.destroy()
        finally:
            os._exit(0)

    def _update_roblox_indicator(self, focused):
        if focused:
            self.rbx_dot.itemconfig(self.rbx_circle, fill=GREEN)
            self.rbx_label.configure(text="Roblox focused", fg=GREEN)
        else:
            self.rbx_dot.itemconfig(self.rbx_circle, fill=RED)
            self.rbx_label.configure(text="Roblox not focused", fg=SUBTEXT)

    def _binding_row(self, parent, key, desc, color, mono_font, label_font):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=14, pady=4)
        key_badge = tk.Label(
            row, text=f" {key} ", font=mono_font, fg="#0c0e1a", bg=color,
            padx=6, pady=2
        )
        key_badge.pack(side="left")
        tk.Label(row, text=desc, font=label_font, fg=TEXT, bg=PANEL).pack(side="left", padx=10)

    def log(self, msg):
        def _append():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.root.after(0, _append)

    def toggle(self):
        global running
        running = not running
        if running:
            self.toggle_btn.configure(text="■  STOP", bg=RED, activebackground="#dc2626")
            self.status_label.configure(text="RUNNING", fg=GREEN)
            self.status_dot.itemconfig(self.status_circle, fill=GREEN)
            self.log(f"[{time.strftime('%H:%M:%S')}]  Hotkeys armed.")
        else:
            self.toggle_btn.configure(text="▶  START", bg=ACCENT1, activebackground=ACCENT2)
            self.status_label.configure(text="STOPPED", fg=RED)
            self.status_dot.itemconfig(self.status_circle, fill=RED)
            self.log(f"[{time.strftime('%H:%M:%S')}]  Hotkeys disarmed.")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

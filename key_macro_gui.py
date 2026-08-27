"""
Click Macro — GUI version (iOS-styled redesign).

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
  without alt-tabbing. It's styled like a floating iOS notification card.
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

# ---- theme -------------------------------------------------------------
# iOS-inspired dark palette (system dark-mode colors).
BG = "#000000"          # systemBackground
CARD = "#1c1c1e"         # secondarySystemBackground
CARD2 = "#2c2c2e"        # tertiarySystemBackground / elevated chip
PANEL = CARD             # kept for any leftover references
PANEL_BORDER = "#38383a"  # separator
BORDER = PANEL_BORDER
ACCENT1 = "#0A84FF"      # iOS blue
ACCENT2 = "#5E5CE6"      # iOS indigo
TEXT = "#FFFFFF"         # label
SUBTEXT = "#98989D"      # secondaryLabel
GREEN = "#30D158"
RED = "#FF453A"
YELLOW = "#FFD60A"

# Font stacks — SF Pro on macOS/iOS, graceful fallback elsewhere.
FONT_DISPLAY = "SF Pro Display"
FONT_TEXT = "SF Pro Text"
FONT_MONO = "SF Mono"


def _pick_family(preferred, fallbacks):
    try:
        available = set(tkfont.families())
    except Exception:
        available = set()
    for name in [preferred, *fallbacks]:
        if name in available:
            return name
    return fallbacks[-1]


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


# ---- shared drawing helpers ---------------------------------------------

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lerp_color(hex1, hex2, t):
    """Blend two hex colors; t=0 -> hex1, t=1 -> hex2."""
    r1, g1, b1 = _hex_to_rgb(hex1)
    r2, g2, b2 = _hex_to_rgb(hex2)
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


class GradientBar(tk.Canvas):
    """A thin horizontal blue->indigo gradient strip used as a decorative accent."""

    def __init__(self, master, height=3, **kw):
        super().__init__(master, height=height, highlightthickness=0, bg=CARD, **kw)
        self.bind("<Configure>", self._draw)

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        c1 = _hex_to_rgb(ACCENT1)
        c2 = _hex_to_rgb(ACCENT2)
        steps = max(w, 1)
        for i in range(steps):
            t = i / steps
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            self.create_line(i, 0, i, h, fill=f"#{r:02x}{g:02x}{b:02x}")


class RoundedCard(tk.Frame):
    """A frame with a smooth rounded-rectangle background, iOS 'card' style.

    Pack/grid the RoundedCard instance itself into your layout, then pack
    child widgets into `.body` (a plain Frame whose bg matches the drawn
    rounded rect, so the corners blend seamlessly). Call `.finalize()`
    once all children have been added so the card sizes itself to fit.
    """

    def __init__(self, master, radius=18, fill=CARD, border=PANEL_BORDER,
                 border_width=1, outer_bg=None, **kw):
        outer_bg = outer_bg or master.cget("bg")
        super().__init__(master, bg=outer_bg, **kw)
        self.radius = radius
        self.fill_color = fill
        self.border_color = border
        self.border_width = border_width
        self._fixed_height = None

        self.canvas = tk.Canvas(self, bg=outer_bg, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.body = tk.Frame(self.canvas, bg=fill)
        self._body_win = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.canvas.bind("<Configure>", self._redraw)

    def finalize(self):
        self.body.update_idletasks()
        self._fixed_height = self.body.winfo_reqheight()
        self.canvas.configure(height=self._fixed_height)
        self._redraw()

    def _redraw(self, event=None):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 4 or h < 4:
            return
        self.canvas.delete("card_bg")
        pts = _round_rect_points(1, 1, w - 1, h - 1, self.radius)
        poly = self.canvas.create_polygon(
            pts, fill=self.fill_color, outline=self.border_color,
            width=self.border_width, smooth=True, tags="card_bg"
        )
        self.canvas.tag_lower(poly)
        self.canvas.coords(self._body_win, 0, 0)
        self.canvas.itemconfig(self._body_win, width=w, height=h)


class PillButton(tk.Canvas):
    """A fully-rounded, iOS-style capsule button drawn on a Canvas so it can
    have true rounded ends regardless of platform theming."""

    def __init__(self, master, text, command, fill=ACCENT1, active_fill=None,
                 fg="white", font=None, height=52, outer_bg=None, **kw):
        outer_bg = outer_bg or master.cget("bg")
        super().__init__(master, height=height, bg=outer_bg,
                          highlightthickness=0, cursor="hand2", **kw)
        self.command = command
        self.fill_color = fill
        self.active_fill = active_fill or _lerp_color(fill, "#000000", 0.18)
        self.fg = fg
        self.font = font
        self.text = text
        self._pressed = False

        self.bind("<Configure>", self._redraw)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _redraw(self, event=None):
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 4 or h < 4:
            return
        self.delete("all")
        r = h / 2
        color = self.active_fill if self._pressed else self.fill_color
        pts = _round_rect_points(1, 1, w - 1, h - 1, r)
        self.create_polygon(pts, fill=color, outline="", smooth=True)
        self.create_text(w / 2, h / 2, text=self.text, fill=self.fg, font=self.font)

    def _on_press(self, _event):
        self._pressed = True
        self._redraw()

    def _on_release(self, event):
        self._pressed = False
        self._redraw()
        w, h = self.winfo_width(), self.winfo_height()
        if 0 <= event.x <= w and 0 <= event.y <= h and self.command:
            self.command()

    def set_text(self, text):
        self.text = text
        self._redraw()

    def set_colors(self, fill, active_fill=None):
        self.fill_color = fill
        self.active_fill = active_fill or _lerp_color(fill, "#000000", 0.18)
        self._redraw()


class StatusChip(tk.Canvas):
    """A small rounded 'badge' — dot + label — tinted with a translucent-
    looking wash of the state color, like an iOS status pill."""

    def __init__(self, master, text, color, font=None, outer_bg=None,
                 height=26, **kw):
        outer_bg = outer_bg or master.cget("bg")
        super().__init__(master, height=height, bg=outer_bg,
                          highlightthickness=0, **kw)
        self.font = font
        self.text = text
        self.color = color
        self.bind("<Configure>", self._redraw)

    def _redraw(self, event=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        self.delete("all")
        wash = _lerp_color(self.color, CARD2, 0.78)
        pts = _round_rect_points(0, 0, w, h, h / 2)
        self.create_polygon(pts, fill=wash, outline="", smooth=True)
        cy = h / 2
        r = h * 0.16
        self.create_oval(10 - r, cy - r, 10 + r, cy + r, fill=self.color, outline="")
        self.create_text(10 + r + 7, cy, anchor="w", text=self.text,
                          fill=self.color, font=self.font)

    def set(self, text, color):
        self.text = text
        self.color = color
        self._redraw()


class Overlay:
    """A small always-on-top, borderless window showing live macro status —
    styled like a floating iOS notification / glass card, draggable, so
    it's visible on top of Roblox while you play."""

    STATE_COLORS = {
        "stopped": RED,
        "waiting": YELLOW,   # started, but Roblox isn't focused
        "active": GREEN,     # armed and ready to fire
    }
    STATE_TEXT = {
        "stopped": "Stopped",
        "waiting": "Waiting",
        "active": "Active",
    }
    STATE_DETAIL = {
        "stopped": "Tap Start to arm",
        "waiting": "Waiting for Roblox",
        "active": "Hotkeys ready · ` and r",
    }

    W, H = 250, 84
    RADIUS = 22

    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)          # no title bar / borders
        self.win.attributes("-topmost", True)     # stay above Roblox
        self.win.resizable(False, False)

        self.title_family = _pick_family(FONT_DISPLAY, ["Segoe UI Semibold", "Segoe UI", "Helvetica"])
        self.text_family = _pick_family(FONT_TEXT, ["Segoe UI", "Helvetica"])

        # True click-through-looking transparency on Windows; a plain
        # semi-transparent glass panel elsewhere. Everything outside the
        # rounded rect we draw stays this matte color, so it "disappears"
        # on Windows and the card reads as floating over the game.
        matte = "#010203"
        try:
            if IS_WINDOWS:
                self.win.configure(bg=matte)
                self.win.attributes("-transparentcolor", matte)
                canvas_bg = matte
            else:
                self.win.configure(bg=BG)
                self.win.attributes("-alpha", 0.94)
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
        glass_fill = _lerp_color(CARD, "#3a3a3c", 0.25)
        self._panel = self.canvas.create_polygon(
            _round_rect_points(pad, pad, self.W - pad, self.H - pad, self.RADIUS),
            fill=glass_fill, outline="#48484a", width=1.2, smooth=True
        )

        # A thin brighter arc hugging the top edge simulates a soft glass
        # highlight/sheen, like light catching the top of an iOS card.
        sheen_inset = self.RADIUS * 0.9
        self._sheen = self.canvas.create_line(
            pad + sheen_inset, pad + 2.5, self.W - pad - sheen_inset, pad + 2.5,
            fill=_lerp_color(glass_fill, "#ffffff", 0.22), width=1.4, capstyle="round"
        )

        # Glowing status dot: a smooth, lamp-like halo built from many thin
        # concentric rings whose spacing/blend both taper non-linearly, so
        # it reads as a soft continuous glow rather than a few hard bands.
        # Coordinates are re-drawn every animation tick to breathe.
        self.dot_cx, self.dot_cy, self.dot_r = 27, self.H / 2, 4.5
        self._glow_layers = 10
        self._glow_max_extra = 9 / 1.5   # outer halo diameter, shrunk 1.5x
        self._glow_ids = [
            self.canvas.create_oval(0, 0, 0, 0, fill=glass_fill, outline="")
            for _ in range(self._glow_layers)
        ]

        self._core_layer_ids = [
            self.canvas.create_oval(0, 0, 0, 0, fill=RED, outline="")
            for _ in range(4)
        ]
        self._highlight_id = self.canvas.create_oval(0, 0, 0, 0, fill=TEXT, outline="")

        self.status_text_id = self.canvas.create_text(
            self.dot_cx + 22, self.dot_cy - 12, anchor="w",
            text=self.STATE_TEXT["stopped"], fill=RED,
            font=(self.title_family, 14, "bold")
        )
        self.detail_text_id = self.canvas.create_text(
            self.dot_cx + 22, self.dot_cy + 11, anchor="w",
            text=self.STATE_DETAIL["stopped"], fill=SUBTEXT,
            font=(self.text_family, 9)
        )

        # Let the overlay itself be dragged to a new spot.
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._do_drag)
        self._drag = (0, 0)

        # Animation state: a breathing sine phase for the dot and a
        # slow shimmer for the sheen. One shared ~25fps tick drives both,
        # independent of macro state.
        self._state = "stopped"
        self._phase = 0.0
        self._shimmer = 0.0
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
        core_dim = _lerp_color(color, "#000000", 0.4)
        core_bright = _lerp_color(color, "#ffffff", 0.55)
        base_color = _lerp_color(core_dim, core_bright, pulse)

        r = self.dot_r + pulse * 1.1
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
            # glass panel color (outer edge); breathing also lifts overall
            # glow. Capped below 1.0 so the outermost ring still holds a
            # visible tint instead of dissolving fully into the panel.
            fade = min(0.82, (t ** 1.15) * 0.68 + (1 - pulse) * 0.14)
            glass_fill = _lerp_color(CARD, "#3a3a3c", 0.25)
            self.canvas.itemconfig(ring, fill=_lerp_color(color, glass_fill, fade))

        # ---- top sheen: gentle shimmer in brightness, like light drifting
        # across glass ----
        shimmer_t = (math.sin(self._shimmer) + 1) / 2
        glass_fill = _lerp_color(CARD, "#3a3a3c", 0.25)
        sheen_color = _lerp_color(glass_fill, "#ffffff", 0.16 + shimmer_t * 0.18)
        self.canvas.itemconfig(self._sheen, fill=sheen_color)

        self._phase += 0.11        # ~2.3s per full breathing cycle at 40ms
        self._shimmer += 0.025
        self.win.after(40, self._animate)


class App:
    def __init__(self, root):
        self.root = root
        root.title("Click Macro")
        root.configure(bg=BG)
        root.geometry("420x520")
        root.minsize(380, 480)

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

        title_family = _pick_family(FONT_DISPLAY, ["Segoe UI Semibold", "Segoe UI", "Helvetica"])
        text_family = _pick_family(FONT_TEXT, ["Segoe UI", "Helvetica"])
        mono_family = _pick_family(FONT_MONO, ["Consolas", "Courier New"])

        title_font = tkfont.Font(family=title_family, size=20, weight="bold")
        mono_font = tkfont.Font(family=mono_family, size=10)
        label_font = tkfont.Font(family=text_family, size=11)
        small_font = tkfont.Font(family=text_family, size=9)
        chip_font = tkfont.Font(family=text_family, size=10, weight="bold")
        button_font = tkfont.Font(family=title_family, size=13, weight="bold")

        outer = tk.Frame(root, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x")
        tk.Label(header, text="⚡ Click Macro", font=title_font, fg=TEXT, bg=BG).pack(side="left")

        self.status_chip = StatusChip(header, "Stopped", RED, font=chip_font, height=28)
        self.status_chip.pack(side="right")

        GradientBar(outer, height=3).pack(fill="x", pady=(14, 14))

        # Roblox detection chip
        rbx_row = tk.Frame(outer, bg=BG)
        rbx_row.pack(fill="x", pady=(0, 14))

        rbx_text = "Roblox not focused" if IS_WINDOWS else "Auto-detect requires Windows — hotkeys always active"
        rbx_color = RED if IS_WINDOWS else SUBTEXT
        self.rbx_chip = StatusChip(rbx_row, rbx_text, rbx_color, font=small_font, height=26)
        self.rbx_chip.pack(fill="x")

        # Bindings card
        panel_card = RoundedCard(outer, radius=18)
        panel_card.pack(fill="x", pady=(0, 16))
        panel = panel_card.body

        tk.Label(panel, text="HOTKEYS", font=small_font, fg=SUBTEXT, bg=CARD).pack(
            anchor="w", padx=16, pady=(14, 6))

        self._binding_row(panel, "`", "Right Click → Space → Left Click", ACCENT2, mono_font, label_font)
        self._binding_row(panel, "r", "Right Click → Space", ACCENT1, mono_font, label_font)

        tk.Frame(panel, bg=CARD, height=12).pack()
        panel_card.finalize()

        # Start/Stop button — full iOS capsule pill
        self.toggle_btn = PillButton(
            outer, text="▶  Start", command=self.toggle,
            fill=ACCENT1, active_fill=_lerp_color(ACCENT1, "#000000", 0.2),
            fg="white", font=button_font, height=54
        )
        self.toggle_btn.pack(fill="x", pady=(0, 16))

        # Log card
        log_card = RoundedCard(outer, radius=18)
        log_card.pack(fill="both", expand=True)
        log_frame = log_card.body

        tk.Label(log_frame, text="ACTIVITY", font=small_font, fg=SUBTEXT, bg=CARD).pack(
            anchor="w", padx=16, pady=(12, 6))

        self.log_box = tk.Text(
            log_frame, bg="#0c0c0e", fg=TEXT, insertbackground=TEXT,
            font=mono_font, relief="flat", bd=0, height=10, wrap="word",
            state="disabled", padx=10, pady=8
        )
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        # Log card grows with the window, so no finalize() height-lock here;
        # give it a sensible starting height instead.
        log_card.canvas.configure(height=220)

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
        footer.pack(fill="x", pady=(12, 0))

        keyboard.hook_key("`", make_handler("`", combo_tilde, self.log))
        keyboard.hook_key("r", make_handler("r", combo_r, self.log))
        keyboard.add_hotkey("esc", self._request_exit, suppress=False)

        self.overlay = Overlay(root)

        self._last_roblox_state = None
        if IS_WINDOWS:
            threading.Thread(target=self._poll_roblox, daemon=True).start()

        threading.Thread(target=self._poll_overlay, daemon=True).start()

        self.log("Ready. Click Start to arm hotkeys.")
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
            self.rbx_chip.set("Roblox focused", GREEN)
        else:
            self.rbx_chip.set("Roblox not focused", RED)

    def _binding_row(self, parent, key, desc, color, mono_font, label_font):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=16, pady=5)
        key_badge = tk.Label(
            row, text=f" {key} ", font=mono_font, fg="#0c0c0e", bg=color,
            padx=7, pady=3
        )
        key_badge.pack(side="left")
        tk.Label(row, text=desc, font=label_font, fg=TEXT, bg=CARD).pack(side="left", padx=10)

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
            self.toggle_btn.set_text("■  Stop")
            self.toggle_btn.set_colors(RED, _lerp_color(RED, "#000000", 0.2))
            self.status_chip.set("Running", GREEN)
            self.log(f"[{time.strftime('%H:%M:%S')}]  Hotkeys armed.")
        else:
            self.toggle_btn.set_text("▶  Start")
            self.toggle_btn.set_colors(ACCENT1, _lerp_color(ACCENT1, "#000000", 0.2))
            self.status_chip.set("Stopped", RED)
            self.log(f"[{time.strftime('%H:%M:%S')}]  Hotkeys disarmed.")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

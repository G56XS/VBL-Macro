"""VBL Macro premium RGB gaming GUI.

Keeps the original macro behavior while replacing the UI with an animated
RGB/neon gaming dashboard and a compact always-on-top status overlay.
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
BG, SURFACE, SURFACE2 = "#070910", "#0e111a", "#131827"
STROKE, TEXT, MUTED, DIM = "#252b3b", "#f4f7ff", "#858da4", "#586176"
BLUE, CYAN, PURPLE, PINK = "#4d7cff", "#2fe0ff", "#9b6cff", "#ff55d8"
GREEN, RED, YELLOW, BLACK = "#39e58c", "#ff5676", "#ffd75b", "#020307"
running = False
roblox_focused = False
event_count = 0
held = set()


def resource_path(name):
    base = getattr(sys, "_MEIPASS", BASE_DIR) if getattr(sys, "frozen", False) else BASE_DIR
    return os.path.join(base, name)


def family(preferred, fallbacks):
    try:
        available = set(tkfont.families())
    except Exception:
        available = set()
    return preferred if preferred in available else next((x for x in fallbacks if x in available), "TkDefaultFont")


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    ar, ag, ab = rgb(a); br, bg, bb = rgb(b)
    return "#%02x%02x%02x" % (round(ar+(br-ar)*t), round(ag+(bg-ag)*t), round(ab+(bb-ab)*t))


def rainbow(h, s=.88, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return "#%02x%02x%02x" % (int(r*255), int(g*255), int(b*255))


def rr(x1, y1, x2, y2, r):
    r = min(r, (x2-x1)/2, (y2-y1)/2)
    return [x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]


def active_title():
    if not IS_WINDOWS:
        return ""
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n+1)
    user32.GetWindowTextW(hwnd, buf, n+1)
    return buf.value


def is_roblox():
    return ROBLOX_TITLE_MATCH in active_title().lower()


def combo_tilde():
    pydirectinput.rightClick(); pydirectinput.press("space"); pydirectinput.leftClick()


def combo_r():
    pydirectinput.rightClick(); pydirectinput.press("space")


def handler(key, action, log):
    def on_event(event):
        global event_count
        if not running or (IS_WINDOWS and not roblox_focused):
            return
        if event.event_type == "down" and key not in held:
            held.add(key); action(); event_count += 1
            log(f"{time.strftime('%H:%M:%S')}   {key.upper()}   combo fired   #{event_count}")
        elif event.event_type == "up":
            held.discard(key)
    return on_event


class RGBStrip(tk.Canvas):
    def __init__(self, master, height=8):
        super().__init__(master, height=height, bg=BG, highlightthickness=0)
        self.phase = 0.0
        self.bind("<Configure>", self.draw)
        self.after(30, self.tick)

    def draw(self, _=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2: return
        for x in range(w):
            c = rainbow(self.phase + x/max(w,1), .9, 1)
            self.create_line(x, 0, x, h, fill=c)

    def tick(self):
        self.phase += .0025
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
        self.item = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.canvas.bind("<Configure>", self.redraw)

    def finalize(self, height=None):
        self.body.update_idletasks()
        self.canvas.configure(height=height or self.body.winfo_reqheight())
        self.redraw()

    def redraw(self, _=None):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 4 or h < 4: return
        self.canvas.delete("shape")
        self.canvas.create_polygon(rr(1,1,w-1,h-1,20), fill=mix(self.accent, BG, .93), outline="", smooth=True, tags="shape")
        self.canvas.create_polygon(rr(3,3,w-3,h-3,18), fill=self.fill, outline=STROKE, width=1, smooth=True, tags="shape")
        self.canvas.create_line(24, 4, w-24, 4, fill=mix(self.accent, TEXT, .62), width=2, capstyle="round", tags="shape")
        self.canvas.tag_lower("shape")
        self.canvas.coords(self.item, 0, 0)
        self.canvas.itemconfigure(self.item, width=w, height=h)


class Button(tk.Canvas):
    def __init__(self, master, text, command, color):
        super().__init__(master, height=62, bg=master.cget("bg"), highlightthickness=0, cursor="hand2")
        self.text, self.command, self.color, self.pressed, self.hover = text, command, color, False, False
        self.bind("<Configure>", self.draw); self.bind("<Enter>", self.enter); self.bind("<Leave>", self.leave)
        self.bind("<Button-1>", self.press); self.bind("<ButtonRelease-1>", self.release)
    def draw(self, _=None):
        self.delete("all"); w,h=self.winfo_width(),self.winfo_height()
        c = mix(self.color, TEXT, .12) if self.hover else self.color
        if self.pressed: c = mix(c, BLACK, .18)
        self.create_polygon(rr(2,2,w-2,h-2,h/2), fill=c, outline="", smooth=True)
        self.create_line(28, 5, w-28, 5, fill=mix(c,TEXT,.35), width=1.5, capstyle="round")
        self.create_text(w/2,h/2,text=self.text,fill=TEXT,font=(family("Segoe UI Semibold",["Segoe UI"]),13,"bold"))
    def enter(self,_): self.hover=True; self.draw()
    def leave(self,_): self.hover=False; self.draw()
    def press(self,_): self.pressed=True; self.draw()
    def release(self,e):
        self.pressed=False; self.draw()
        if 0<=e.x<=self.winfo_width() and 0<=e.y<=self.winfo_height(): self.command()
    def set(self,text,color): self.text,self.color=text,color; self.draw()


class Chip(tk.Canvas):
    def __init__(self, master, text, color):
        super().__init__(master,height=29,bg=master.cget("bg"),highlightthickness=0)
        self.text,self.color=text,color; self.bind("<Configure>",self.draw)
    def draw(self,_=None):
        self.delete("all"); w,h=self.winfo_width(),self.winfo_height()
        if w<2:return
        self.create_polygon(rr(0,0,w,h,h/2),fill=mix(self.color,SURFACE,.82),outline=mix(self.color,SURFACE,.45),smooth=True)
        self.create_oval(9, h/2-4, 17, h/2+4, fill=self.color, outline="")
        self.create_text(24,h/2,anchor="w",text=self.text,fill=self.color,font=(family("Segoe UI",["Arial"]),9,"bold"))
    def set(self,text,color): self.text,self.color=text,color; self.draw()


class Overlay:
    def __init__(self, root):
        self.win=tk.Toplevel(root); self.win.overrideredirect(True); self.win.attributes("-topmost",True); self.win.resizable(False,False)
        try:self.win.attributes("-alpha",.96)
        except Exception:pass
        matte="#010203"
        if IS_WINDOWS:
            try:self.win.configure(bg=matte); self.win.attributes("-transparentcolor",matte)
            except Exception:pass
        else:self.win.configure(bg=BG)
        W,H=300,90; self.W,self.H=W,H
        sh=self.win.winfo_screenheight(); self.win.geometry(f"{W}x{H}+24+{sh-H-90}")
        self.canvas=tk.Canvas(self.win,width=W,height=H,bg=matte if IS_WINDOWS else BG,highlightthickness=0);self.canvas.pack()
        self.phase=0.; self.state="stopped"; self.drag=(0,0)
        self.canvas.bind("<Button-1>",self.start); self.canvas.bind("<B1-Motion>",self.move); self.animate()
    def start(self,e):self.drag=(e.x,e.y)
    def move(self,_):self.win.geometry(f"+{self.win.winfo_pointerx()-self.drag[0]}+{self.win.winfo_pointery()-self.drag[1]}")
    def update(self,r,f):self.state="stopped" if not r else ("waiting" if IS_WINDOWS and not f else "active")
    def animate(self):
        self.canvas.delete("all"); c={"stopped":RED,"waiting":YELLOW,"active":GREEN}[self.state]
        text={"stopped":"OFFLINE","waiting":"WAITING","active":"LIVE"}[self.state]
        detail={"stopped":"Macro disarmed","waiting":"Waiting for Roblox focus","active":"Hotkeys ready  •  ` + R"}[self.state]
        self.canvas.create_polygon(rr(2,2,self.W-2,self.H-2,22),fill=SURFACE2,outline=STROKE,width=1,smooth=True)
        for i in range(48):
            x=20+i*(260/48); self.canvas.create_line(x,4,x+6,4,fill=rainbow(self.phase+i/48,.85,1),width=2)
        pulse=(math.sin(self.phase*8)+1)/2; r=6+pulse
        self.canvas.create_oval(27-r-4,45-r-4,27+r+4,45+r+4,fill=mix(c,SURFACE2,.82),outline="")
        self.canvas.create_oval(27-r,45-r,27+r,45+r,fill=c,outline="")
        self.canvas.create_oval(25,43,27,45,fill=TEXT,outline="")
        self.canvas.create_text(50,34,anchor="w",text=text,fill=c,font=(family("Segoe UI Semibold",["Segoe UI"]),13,"bold"))
        self.canvas.create_text(50,58,anchor="w",text=detail,fill=MUTED,font=(family("Segoe UI",["Arial"]),9))
        self.phase+=.008; self.win.after(40,self.animate)


class App:
    def __init__(self,root):
        global running
        self.root=root; root.title("VBL Macro"); root.configure(bg=BG); root.geometry("560x720"); root.minsize(500,650)
        ico,png=resource_path("app_icon.ico"),resource_path("icon_512.png")
        try:
            if IS_WINDOWS and os.path.exists(ico): root.iconbitmap(default=ico)
            elif os.path.exists(png): self.icon=tk.PhotoImage(file=png);root.iconphoto(True,self.icon)
        except Exception:pass
        self.fd=family("Segoe UI Semibold",["Segoe UI"]); self.ft=family("Segoe UI",["Arial"]); self.fm=family("Cascadia Mono",["Consolas","Courier New"])
        outer=tk.Frame(root,bg=BG);outer.pack(fill="both",expand=True,padx=24,pady=22)
        RGBStrip(root,8).pack(fill="x",side="top")
        brand=tk.Frame(outer,bg=BG);brand.pack(fill="x")
        left=tk.Frame(brand,bg=BG);left.pack(side="left")
        tk.Label(left,text="VBL",font=(self.fd,11,"bold"),fg=CYAN,bg=BG).pack(anchor="w")
        tk.Label(left,text="MACRO",font=(self.fd,26,"bold"),fg=TEXT,bg=BG).pack(anchor="w")
        tk.Label(left,text="PRECISION INPUT  •  ROBLOX",font=(self.ft,9),fg=MUTED,bg=BG).pack(anchor="w")
        self.status=Chip(brand,"OFFLINE",RED);self.status.pack(side="right",pady=8)
        row=tk.Frame(outer,bg=BG);row.pack(fill="x",pady=(18,16))
        self.rbx=Chip(row,"ROBLOX NOT FOCUSED" if IS_WINDOWS else "WINDOW DETECTION: WINDOWS ONLY",RED if IS_WINDOWS else MUTED);self.rbx.pack(side="left",fill="x",expand=True)
        self.counter=tk.Label(row,text="0 FIRES",font=(self.fm,8,"bold"),fg=CYAN,bg=BG);self.counter.pack(side="right",padx=(12,0))
        hero=Card(outer,BLUE);hero.pack(fill="x",pady=(0,16)); b=hero.body
        tk.Label(b,text="MASTER CONTROL",font=(self.ft,9,"bold"),fg=MUTED,bg=SURFACE).pack(anchor="w",padx=20,pady=(17,10))
        self.button=Button(b,"▶   START MACRO",self.toggle,BLUE);self.button.pack(fill="x",padx=20)
        self.mode=tk.Label(b,text="Engine is standing by",font=(self.ft,9),fg=MUTED,bg=SURFACE);self.mode.pack(anchor="w",padx=22,pady=(10,17));hero.finalize()
        hk=Card(outer,PURPLE);hk.pack(fill="x",pady=(0,16)); hb=hk.body
        tk.Label(hb,text="COMBO PROFILES",font=(self.ft,9,"bold"),fg=MUTED,bg=SURFACE).pack(anchor="w",padx=20,pady=(16,9))
        self.bind_row(hb,"`","RIGHT CLICK  →  SPACE  →  LEFT CLICK",CYAN)
        self.bind_row(hb,"R","RIGHT CLICK  →  SPACE",PURPLE)
        tk.Label(hb,text="Focus protection stays enabled while the engine is armed.",font=(self.ft,9),fg=DIM,bg=SURFACE).pack(anchor="w",padx=20,pady=(10,16));hk.finalize()
        log=Card(outer,PINK);log.pack(fill="both",expand=True); lb=log.body
        top=tk.Frame(lb,bg=SURFACE);top.pack(fill="x",padx=20,pady=(15,8))
        tk.Label(top,text="LIVE ACTIVITY",font=(self.ft,9,"bold"),fg=MUTED,bg=SURFACE).pack(side="left")
        self.live=tk.Label(top,text="● IDLE",font=(self.ft,8,"bold"),fg=DIM,bg=SURFACE);self.live.pack(side="right")
        self.box=tk.Text(lb,bg=BLACK,fg="#dfe6f7",insertbackground=TEXT,relief="flat",bd=0,font=(self.fm,9),wrap="word",state="disabled",padx=14,pady=12)
        self.box.pack(fill="both",expand=True,padx=16,pady=(0,16));log.canvas.configure(height=230)
        foot=tk.Frame(outer,bg=BG);foot.pack(fill="x",pady=(11,0))
        tk.Label(foot,text="VBL MACRO  •  RGB INTERFACE",font=(self.fm,8),fg=DIM,bg=BG).pack(side="left")
        tk.Label(foot,text="FOCUS PROTECTION ON",font=(self.fm,8,"bold"),fg=GREEN,bg=BG).pack(side="right")
        self.overlay=Overlay(root)
        keyboard.hook_key("`",handler("`",combo_tilde,self.log));keyboard.hook_key("r",handler("r",combo_r,self.log));keyboard.add_hotkey("esc",self.exit_request,suppress=False)
        if IS_WINDOWS:threading.Thread(target=self.poll_roblox,daemon=True).start()
        threading.Thread(target=self.poll_overlay,daemon=True).start()
        self.log("System initialized — click START MACRO to arm the engine.")
        self.log("Roblox focus protection is enabled.")
        self.log("ESC closes the application immediately.")
    def bind_row(self,parent,key,text,color):
        r=tk.Frame(parent,bg=SURFACE);r.pack(fill="x",padx=20,pady=4)
        tk.Label(r,text=f" {key} ",font=(self.fm,10,"bold"),fg=BLACK,bg=color,padx=8,pady=5).pack(side="left")
        tk.Label(r,text=text,font=(self.ft,10),fg=TEXT,bg=SURFACE).pack(side="left",padx=12)
        tk.Label(r,text="INSTANT",font=(self.fm,7,"bold"),fg=color,bg=mix(color,SURFACE,.87),padx=6,pady=3).pack(side="right")
    def poll_roblox(self):
        global roblox_focused
        while True:
            f=is_roblox()
            if f!=roblox_focused:
                roblox_focused=f;self.root.after(0,self.update_focus,f)
            time.sleep(.2)
    def poll_overlay(self):
        last=None
        while True:
            state=(running,roblox_focused)
            if state!=last:last=state;self.root.after(0,self.refresh)
            time.sleep(.1)
    def update_focus(self,f):
        self.rbx.set("ROBLOX FOCUSED  •  INPUT READY" if f else "ROBLOX NOT FOCUSED",GREEN if f else RED);self.refresh()
    def refresh(self):
        self.overlay.update(running,roblox_focused);self.counter.config(text=f"{event_count} FIRES")
        if running and IS_WINDOWS and not roblox_focused:self.live.config(text="● WAITING",fg=YELLOW);self.mode.config(text="Armed — waiting for Roblox focus")
        elif running:self.live.config(text="● LIVE",fg=GREEN);self.mode.config(text="Engine online — hotkeys armed")
        else:self.live.config(text="● IDLE",fg=DIM);self.mode.config(text="Engine is standing by")
    def toggle(self):
        global running
        running=not running
        if running:self.button.set("■   STOP MACRO",RED);self.status.set("ONLINE",GREEN);self.log(f"{time.strftime('%H:%M:%S')}   ENGINE ARMED")
        else:self.button.set("▶   START MACRO",BLUE);self.status.set("OFFLINE",RED);self.log(f"{time.strftime('%H:%M:%S')}   ENGINE DISARMED")
        self.refresh()
    def log(self,msg):
        def add():
            self.box.config(state="normal");self.box.insert("end",msg+"\n");self.box.see("end");self.box.config(state="disabled")
        self.root.after(0,add)
    def exit_request(self):self.root.after(0,self.exit_app)
    def exit_app(self):
        try:self.overlay.win.destroy();self.root.destroy()
        finally:os._exit(0)


def main():
    root=tk.Tk();App(root);root.mainloop()

if __name__=="__main__":main()

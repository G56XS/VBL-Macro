# Building Click Macro into a standalone .exe

## 1. Folder layout

Put these four files in the **same folder**, on Windows:

```
key_macro_gui.py
build_exe.bat
app_icon.ico      <- your icon, must be a real .ico (not a renamed .png)
icon_512.png      <- optional fallback, keep it if you already have it
```

Don't have an `.ico` yet? Convert any PNG at a site like icoconvert.com or
convertico.com — make sure the generated `.ico` includes at least a 256×256
size, or Windows will show a blurry taskbar icon.

## 2. Build

Double-click **`build_exe.bat`** (or run it from a terminal). It will:

- install PyInstaller and the app's dependencies,
- bundle everything into one file,
- bake `app_icon.ico` in as the exe's icon.

Your app comes out at **`dist\ClickMacro.exe`** — that's the whole thing,
no Python install needed to run it on another machine.

Pin `ClickMacro.exe` to your taskbar or desktop like any normal app.

## 3. If hotkeys don't register in-game

Some games run elevated and ignore input from non-elevated processes. Two
options:

- Right-click `ClickMacro.exe` → **Run as administrator** each time, or
- Build with **`build_exe_admin.bat`** instead — it adds `--uac-admin` so
  the exe automatically prompts for admin rights every time you launch it.

## 4. Heads-up: antivirus false positives

Global keyboard hooks + a one-file PyInstaller exe is a pattern some
antivirus/Windows Defender heuristics flag (it looks similar to keylogger
packaging, even though this script only reacts to `` ` ``, `r`, and `Esc`
to fire the combo/quit). If it gets quarantined, you'll likely need to
allow it manually or add an exclusion. This is a common false positive for
PyInstaller + `keyboard`, not a sign anything is wrong with the script.

## 5. Rebuilding after edits

Just re-run `build_exe.bat` — it overwrites `dist\ClickMacro.exe`. Delete
the `build\` and `dist\` folders first if you ever want a totally clean
rebuild.

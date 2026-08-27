@echo off
REM ============================================================
REM  Click Macro — build script
REM  Run this on Windows, from the folder containing:
REM      key_macro_gui.py
REM      app_icon.ico     (your taskbar / titlebar icon)
REM      icon_512.png     (fallback icon, optional but keep it)
REM  Output exe lands in:  dist\ClickMacro.exe
REM ============================================================

setlocal

REM 1. Make sure pip + pyinstaller are up to date
python -m pip install --upgrade pip
python -m pip install --upgrade pyinstaller keyboard pydirectinput pillow

REM 2. Sanity check the icon exists (PyInstaller needs a real .ico file,
REM    not a renamed .png)
if not exist "app_icon.ico" (
    echo.
    echo [!] app_icon.ico not found in this folder.
    echo     Put your icon file here first, named exactly app_icon.ico
    echo     (Convert a PNG at e.g. https://icoconvert.com if needed —
    echo      include at least the 256x256 size inside the .ico.)
    pause
    exit /b 1
)

REM 3. Build a single-file, windowed (no console) exe with the icon baked
REM    in, plus the icon files bundled as data so the app can load them
REM    again at runtime (window/taskbar icon).
pyinstaller --noconfirm --onefile --windowed ^
    --name "ClickMacro" ^
    --icon "app_icon.ico" ^
    --add-data "app_icon.ico;." ^
    --add-data "icon_512.png;." ^
    --hidden-import "keyboard._winkeyboard" ^
    --hidden-import "keyboard._winmouse" ^
    key_macro_gui.py

echo.
echo ============================================================
echo Done. Your app is at:  dist\ClickMacro.exe
echo Pin it to the taskbar / desktop like any other .exe.
echo ============================================================
pause

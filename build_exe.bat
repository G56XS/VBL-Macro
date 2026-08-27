@echo off
REM ============================================================
REM  VBL Macro — standard Windows build script
REM  Output exe: dist\VBL-Macro.exe
REM ============================================================

setlocal

python -m pip install --upgrade pip
python -m pip install --upgrade pyinstaller keyboard pydirectinput pillow

if not exist "app_icon.ico" (
    echo.
    echo [!] app_icon.ico not found in this folder.
    echo     Put your icon file here first, named exactly app_icon.ico
    pause
    exit /b 1
)

pyinstaller --noconfirm --onefile --windowed ^
    --name "VBL-Macro" ^
    --icon "app_icon.ico" ^
    --add-data "app_icon.ico;." ^
    --add-data "icon_512.png;." ^
    --hidden-import "keyboard._winkeyboard" ^
    --hidden-import "keyboard._winmouse" ^
    key_macro_gui.py

echo.
echo ============================================================
echo Build complete: dist\VBL-Macro.exe
echo ============================================================
echo.
pause

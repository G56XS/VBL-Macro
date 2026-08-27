@echo off
REM ============================================================
REM  VBL Macro — administrator Windows build script
REM  Output exe: dist\VBL-Macro.exe
REM  The executable requests admin rights on launch.
REM ============================================================

setlocal

python -m pip install --upgrade pip
python -m pip install --upgrade pyinstaller keyboard pydirectinput pillow

if not exist "app_icon.ico" (
    echo [!] app_icon.ico not found in this folder. Add it first.
    pause
    exit /b 1
)

pyinstaller --noconfirm --onefile --windowed --uac-admin ^
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
 echo This build requests administrator rights on launch.
echo ============================================================
echo.
pause

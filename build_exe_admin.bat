@echo off
REM ============================================================
REM  VBL Macro — premium Qt/QML administrator build
REM  Output exe: dist\VBL-Macro.exe
REM  The executable requests admin rights on launch.
REM ============================================================

setlocal

python -m pip install --upgrade pip
python -m pip install --upgrade pyinstaller keyboard pydirectinput pillow PySide6

if not exist "app_icon.ico" (
    echo [!] app_icon.ico not found in this folder.
    pause
    exit /b 1
)

if not exist "Glass.qml" (
    echo [!] Glass.qml not found. The premium UI cannot be packaged.
    pause
    exit /b 1
)

pyinstaller --noconfirm --clean --onefile --windowed --uac-admin ^
    --name "VBL-Macro" ^
    --icon "app_icon.ico" ^
    --add-data "app_icon.ico;." ^
    --add-data "icon_512.png;." ^
    --add-data "Glass.qml;." ^
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

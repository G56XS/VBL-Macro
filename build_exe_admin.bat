@echo off
REM Same as build_exe.bat, but the resulting exe will show a UAC prompt
REM and auto-run elevated every time it's launched. Use this variant if
REM your hotkeys don't register while playing (some games run elevated
REM and ignore input from non-elevated processes).

setlocal

python -m pip install --upgrade pip
python -m pip install --upgrade pyinstaller keyboard pydirectinput pillow

if not exist "app_icon.ico" (
    echo [!] app_icon.ico not found in this folder. Add it first.
    pause
    exit /b 1
)

pyinstaller --noconfirm --onefile --windowed --uac-admin ^
    --name "ClickMacro" ^
    --icon "app_icon.ico" ^
    --add-data "app_icon.ico;." ^
    --add-data "icon_512.png;." ^
    --hidden-import "keyboard._winkeyboard" ^
    --hidden-import "keyboard._winmouse" ^
    key_macro_gui.py

echo.
echo Done. dist\ClickMacro.exe will prompt for admin rights on launch.
pause

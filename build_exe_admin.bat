@echo off
REM ============================================================
REM  VBL Macro — Liquid Glass administrator Windows build
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

if not exist "MainRefraction.qml" (
    echo [!] MainRefraction.qml not found.
    pause
    exit /b 1
)

if not exist "LiquidGlass.qml" (
    echo [!] LiquidGlass.qml not found.
    pause
    exit /b 1
)

if not exist "Metric.qml" (
    echo [!] Metric.qml not found.
    pause
    exit /b 1
)

if not exist "shaders\liquid_glass.frag" (
    echo [!] shaders\liquid_glass.frag not found.
    pause
    exit /b 1
)

for /f "delims=" %%Q in ('python -c "from PySide6.QtCore import QLibraryInfo; print(QLibraryInfo.path(QLibraryInfo.BinariesPath))"') do set "QT_BIN=%%Q"

if not exist "%QT_BIN%\qsb.exe" (
    echo [!] qsb.exe was not found in:
    echo     %QT_BIN%
    echo.
    echo Run build_shaders.bat first or reinstall PySide6.
    pause
    exit /b 1
)

if not exist "shaders" mkdir shaders

"%QT_BIN%\qsb.exe" --qt6 -o "shaders\liquid_glass.frag.qsb" "shaders\liquid_glass.frag"
if errorlevel 1 (
    echo [!] Liquid glass shader compilation failed.
    pause
    exit /b 1
)

pyinstaller --noconfirm --clean --onefile --windowed --uac-admin ^
    --name "VBL-Macro" ^
    --icon "app_icon.ico" ^
    --add-data "app_icon.ico;." ^
    --add-data "icon_512.png;." ^
    --add-data "MainRefraction.qml;." ^
    --add-data "LiquidGlass.qml;." ^
    --add-data "Metric.qml;." ^
    --add-data "shaders;shaders" ^
    --hidden-import "keyboard._winkeyboard" ^
    --hidden-import "keyboard._winmouse" ^
    key_macro_gui.py

if errorlevel 1 (
    echo [!] PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo VBL Macro administrator build complete:
echo   dist\VBL-Macro.exe
echo ============================================================
echo.
pause

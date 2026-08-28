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

REM PySide6 exposes the Qt Shader Baker as pyside6-qsb.exe.
REM Find it from PATH first, then Python's Scripts directory.
set "QSB="
for /f "delims=" %%Q in ('where pyside6-qsb 2^>nul') do if not defined QSB set "QSB=%%Q"
if not defined QSB (
    for /f "delims=" %%Q in ('python -c "import os,sys; print(os.path.join(os.path.dirname(sys.executable), 'Scripts', 'pyside6-qsb.exe'))"') do if exist "%%Q" set "QSB=%%Q"
)

if not defined QSB (
    echo [!] pyside6-qsb.exe was not found.
    echo PySide6 is installed, but the shader compiler could not be located.
    echo Try: where pyside6-qsb
    pause
    exit /b 1
)

echo Using shader compiler:
echo   %QSB%
echo.

if not exist "shaders" mkdir shaders
"%QSB%" --qt6 -o "shaders\liquid_glass.frag.qsb" "shaders\liquid_glass.frag"
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
echo This build requests administrator rights on launch.
echo ============================================================
echo.
pause

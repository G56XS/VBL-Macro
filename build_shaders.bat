@echo off
REM ============================================================
REM  VBL Macro — Qt Shader Baker
REM  Builds GLSL -> portable .qsb shader package for Qt Quick.
REM ============================================================

setlocal

python -m pip install --upgrade PySide6

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
    echo Reinstall PySide6 or use the Qt Shader Tools package.
    pause
    exit /b 1
)

if not exist "shaders" mkdir shaders

"%QT_BIN%\qsb.exe" --qt6 -o "shaders\liquid_glass.frag.qsb" "shaders\liquid_glass.frag"
if errorlevel 1 (
    echo.
    echo [!] Shader compilation failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Shader build complete:
echo   shaders\liquid_glass.frag.qsb
echo ============================================================
echo.
pause

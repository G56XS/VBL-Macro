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

REM PySide6 installs the shader baker as pyside6-qsb.exe.
REM Prefer PATH, then Python's Scripts directory.
set "QSB="
for /f "delims=" %%Q in ('where pyside6-qsb 2^>nul') do if not defined QSB set "QSB=%%Q"

if not defined QSB (
    for /f "delims=" %%Q in ('python -c "import os,sys; print(os.path.join(os.path.dirname(sys.executable), 'Scripts', 'pyside6-qsb.exe'))"') do if exist "%%Q" set "QSB=%%Q"
)

if not defined QSB (
    echo [!] pyside6-qsb.exe was not found.
    echo.
    echo PySide6 is installed, but its Qt Shader Tools command was not found.
    echo Try this in Command Prompt:
    echo     where pyside6-qsb
    echo.
    echo Qt documents pyside6-qsb as the PySide6 shader compiler.
    pause
    exit /b 1
)

echo Using shader compiler:
echo   %QSB%

echo.

if not exist "shaders" mkdir shaders

"%QSB%" --qt6 -o "shaders\liquid_glass.frag.qsb" "shaders\liquid_glass.frag"
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

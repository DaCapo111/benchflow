@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: BenchFlow Windows build script
:: Produces:  dist\windows\BenchFlow\BenchFlow.exe
::            releases\BenchFlow-1.0.0-windows.zip
::
:: Usage:
::   build_windows.bat
::   build_windows.bat --no-clean
:: ─────────────────────────────────────────────────────────────────────────────
setlocal enabledelayedexpansion

set VERSION=1.0.0
set APP_NAME=BenchFlow
set SPEC_FILE=BenchFlow_windows.spec
set DIST_DIR=dist\windows
set RELEASES_DIR=releases
set ZIP_NAME=%APP_NAME%-%VERSION%-windows.zip

set DO_CLEAN=1
for %%A in (%*) do (
    if "%%A"=="--no-clean" set DO_CLEAN=0
)

echo.
echo ╔══════════════════════════════════════╗
echo ║   BenchFlow Windows Build  v%VERSION%   ║
echo ╚══════════════════════════════════════╝
echo.

:: ── Python check ─────────────────────────────────────────────────────────────
echo [1/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo        Download from https://www.python.org/downloads/
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo       %%v

:: ── PyInstaller check ────────────────────────────────────────────────────────
echo [2/6] Checking PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo       Installing PyInstaller...
    pip install pyinstaller --quiet
)
for /f "tokens=*" %%v in ('python -m PyInstaller --version 2^>^&1') do echo       PyInstaller %%v

:: ── Requirements ─────────────────────────────────────────────────────────────
echo [3/6] Installing requirements...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: pip install failed.
    exit /b 1
)
echo       Done.

:: ── Generate AppIcon.ico ─────────────────────────────────────────────────────
echo [4/6] Generating AppIcon.ico...
if not exist AppIcon.ico (
    python -c "from PIL import Image; img=Image.open('AppIcon.icns'); img.save('AppIcon.ico', format='ICO', sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])" 2>nul
    if errorlevel 1 (
        echo       WARNING: Could not convert icon. Building without icon.
    ) else (
        echo       AppIcon.ico created.
    )
) else (
    echo       AppIcon.ico already exists.
)

:: ── Clean ─────────────────────────────────────────────────────────────────────
if %DO_CLEAN%==1 (
    echo [5/6] Cleaning old artifacts...
    if exist build         rmdir /s /q build
    if exist "%DIST_DIR%"  rmdir /s /q "%DIST_DIR%"
    echo       Done.
) else (
    echo [5/6] Skipping clean (--no-clean).
)

if not exist "%DIST_DIR%"   mkdir "%DIST_DIR%"
if not exist "%RELEASES_DIR%" mkdir "%RELEASES_DIR%"

:: ── Build ─────────────────────────────────────────────────────────────────────
echo [6/6] Building %APP_NAME%.exe...
python -m PyInstaller --noconfirm ^
    --distpath "%DIST_DIR%" ^
    --workpath build ^
    "%SPEC_FILE%"

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

set EXE_PATH=%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe
if not exist "%EXE_PATH%" (
    echo ERROR: %EXE_PATH% not found after build.
    exit /b 1
)

:: ── Zip for distribution ─────────────────────────────────────────────────────
echo Zipping for distribution...
set ZIP_PATH=%DIST_DIR%\%ZIP_NAME%
powershell -Command "Compress-Archive -Path '%DIST_DIR%\%APP_NAME%\*' -DestinationPath '%ZIP_PATH%' -Force"
if exist "%ZIP_PATH%" (
    echo       %ZIP_NAME% created.
    copy "%ZIP_PATH%" "%RELEASES_DIR%\%ZIP_NAME%" >nul
    echo       Copied to %RELEASES_DIR%\%ZIP_NAME%
)

:: ── Summary ───────────────────────────────────────────────────────────────────
echo.
echo ══════════════════════════════════════════
echo   Build complete!
echo.
echo   Output: %DIST_DIR%\
dir "%DIST_DIR%" /b
echo.
echo   To run: %EXE_PATH%
echo ══════════════════════════════════════════
endlocal

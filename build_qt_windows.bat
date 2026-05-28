@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: BenchFlow Qt (PySide6) Windows build script
:: Produces:  dist\win_qt\BenchFlow_Qt\BenchFlow_Qt.exe
::            releases\BenchFlow-Qt-<version>-Windows.zip
::
:: Usage:
::   build_qt_windows.bat
::   build_qt_windows.bat --no-clean
:: ─────────────────────────────────────────────────────────────────────────────
setlocal enabledelayedexpansion

cd /d "%~dp0"

:: ── Config ───────────────────────────────────────────────────────────────────
set /p VERSION=<VERSION
set VERSION=%VERSION: =%
set APP_NAME=BenchFlow_Qt
set SPEC_FILE=BenchFlow_Qt.spec
set DIST_DIR=dist\win_qt
set RELEASES_DIR=releases
set ZIP_NAME=BenchFlow-Qt-v%VERSION%-Windows.zip

set DO_CLEAN=1
for %%a in (%*) do (
  if "%%a"=="--no-clean" set DO_CLEAN=0
)

echo.
echo  ====================================================
echo    BenchFlow Qt Windows Build  v%VERSION%
echo  ====================================================
echo.

:: ── Python ───────────────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] python not found. Install Python 3.10+ and add to PATH.
  exit /b 1
)
python --version

:: ── PyInstaller ───────────────────────────────────────────────────────────────
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo Installing PyInstaller...
  python -m pip install pyinstaller --quiet
)
echo [OK] PyInstaller found

:: ── PySide6 ───────────────────────────────────────────────────────────────────
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
  echo Installing PySide6...
  python -m pip install PySide6 --quiet
)
echo [OK] PySide6 found

:: ── Optional deps ────────────────────────────────────────────────────────────
python -c "import reportlab" >nul 2>&1
if errorlevel 1 (
  echo [WARN] reportlab not installed - PDF export unavailable
) else (
  echo [OK] reportlab found
)
python -c "import docx" >nul 2>&1
if errorlevel 1 (
  echo [WARN] python-docx not installed - Word export unavailable
) else (
  echo [OK] python-docx found
)

:: ── Requirements ─────────────────────────────────────────────────────────────
if exist requirements_qt.txt (
  echo Installing requirements_qt.txt...
  python -m pip install -r requirements_qt.txt --quiet
  echo [OK] Requirements installed
)

:: ── Clean ─────────────────────────────────────────────────────────────────────
if %DO_CLEAN%==1 (
  echo Cleaning old artifacts...
  if exist build rmdir /s /q build
  if exist %DIST_DIR% rmdir /s /q %DIST_DIR%
  echo [OK] Cleaned
)

if not exist %DIST_DIR% mkdir %DIST_DIR%
if not exist %RELEASES_DIR% mkdir %RELEASES_DIR%

:: ── Build ─────────────────────────────────────────────────────────────────────
echo Building %APP_NAME%.exe...
python -m PyInstaller --noconfirm ^
  --distpath %DIST_DIR% ^
  --workpath build ^
  %SPEC_FILE%

if not exist "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe" (
  echo [ERROR] Build failed - %APP_NAME%.exe not found.
  exit /b 1
)
echo [OK] %APP_NAME%.exe built

:: ── ZIP ───────────────────────────────────────────────────────────────────────
echo Creating %ZIP_NAME%...
powershell -Command ^
  "Compress-Archive -Path '%DIST_DIR%\%APP_NAME%' -DestinationPath '%RELEASES_DIR%\%ZIP_NAME%' -Force"
if exist "%RELEASES_DIR%\%ZIP_NAME%" (
  echo [OK] %ZIP_NAME% created in releases\
) else (
  echo [WARN] ZIP creation failed - folder still available in %DIST_DIR%
)

:: ── Summary ───────────────────────────────────────────────────────────────────
echo.
echo  ====================================================
echo    BenchFlow Qt build complete!
echo.
echo    Executable: %DIST_DIR%\%APP_NAME%\%APP_NAME%.exe
echo    ZIP:        releases\%ZIP_NAME%
echo.
echo    To run from source:
echo      python qt_app\main.py
echo  ====================================================
endlocal

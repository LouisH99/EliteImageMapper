@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Build EliteImageMapper EXE

echo ================================================
echo   Elite Image Mapper 0.9.2 - Windows EXE Builder
echo ================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python Launcher ^("py"^) was not found.
    echo Please install 64-bit Python for Windows first.
    pause
    exit /b 1
)

if not exist venv (
    echo [INFO] Creating virtual environment...
    py -3 -m venv venv
    if errorlevel 1 goto :fail
)

call venv\Scripts\activate.bat
if errorlevel 1 goto :fail

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [INFO] Installing build dependencies...
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :fail

echo [INFO] Cleaning old build folders...
if exist build rmdir /s /q build
if exist EliteImageMapper rmdir /s /q EliteImageMapper

echo [INFO] Building EXE...
pyinstaller --noconfirm --distpath EliteImageMapper --workpath build EliteImageMapper.spec
if errorlevel 1 goto :fail

if not exist EliteImageMapper\output mkdir EliteImageMapper\output
copy /Y README_BUILD.txt EliteImageMapper\README.txt >nul
if exist README.md copy /Y README.md EliteImageMapper\README.md >nul

echo.
echo [OK] Build finished.
echo App folder:
echo   %CD%\EliteImageMapper
echo.
echo The EXE is here:
echo   %CD%\EliteImageMapper\EliteImageMapper.exe
pause
exit /b 0

:fail
echo.
echo [ERROR] Build failed.
pause
exit /b 1

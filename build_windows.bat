@echo off
title Building LiveLeak Archive Search v1.0.0
echo ================================================
echo  LiveLeak Archive Search v1.0.0
echo  Created by HIGHTECHDUDE
echo  Building Windows Installer...
echo ================================================
echo.

echo Checking Python...
py --version
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo.
echo Installing required packages...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

echo.
echo [1/2] Creating executable with PyInstaller...
py -m PyInstaller --noconfirm --onefile --windowed ^
  --name "LiveLeakSearch" ^
  --icon "icon.ico" ^
  --hidden-import=cdx_toolkit ^
  --hidden-import=customtkinter ^
  --hidden-import=elasticsearch ^
  --collect-all customtkinter ^
  liveleak_gui.py

if not exist "dist\LiveLeakSearch.exe" (
    echo.
    echo ERROR: PyInstaller failed to create the executable.
    pause
    exit /b 1
)

echo.
echo [2/2] Creating installer with Inno Setup...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\LiveLeakSearch.iss

echo.
echo ================================================
echo  BUILD FINISHED
echo  Check the dist and dist_installer folders
echo ================================================
pause
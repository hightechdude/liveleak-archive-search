#!/bin/bash

echo "================================================"
echo " LiveLeak Archive Search v1.0.0"
echo " Created by HIGHTECHDUDE"
echo " Building macOS Application + DMG..."
echo "================================================"
echo

pip3 install -r requirements.txt

echo
echo "[1/2] Creating application with PyInstaller..."
pyinstaller --noconfirm --onefile --windowed \
  --name "LiveLeakSearch" \
  --icon "icon.icns" \
  --hidden-import=cdx_toolkit \
  --hidden-import=customtkinter \
  --hidden-import=elasticsearch \
  --collect-all customtkinter \
  liveleak_gui.py

if [ ! -d "dist/LiveLeakSearch.app" ]; then
    echo
    echo "ERROR: PyInstaller failed to create the .app"
    exit 1
fi

echo
echo "[2/2] Creating DMG..."
./create_dmg.sh

echo
echo "================================================"
echo " BUILD SUCCESSFUL!"
echo " DMG: dist/LiveLeakSearch_v1.0.0.dmg"
echo "================================================"
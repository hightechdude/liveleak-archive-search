#!/bin/bash

APP_NAME="LiveLeakSearch"
APP_PATH="dist/${APP_NAME}.app"
DMG_NAME="LiveLeakSearch_v1.0.0"
VOLUME_NAME="LiveLeak Archive Search"
DMG_PATH="dist/${DMG_NAME}.dmg"

echo "Creating macOS DMG for LiveLeak Archive Search v1.0.0..."
echo "Created by HIGHTECHDUDE"
echo

if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: ${APP_PATH} not found. Run build_macos.sh first."
    exit 1
fi

# Remove old DMG if it exists
rm -f "$DMG_PATH"

# Create temporary folder
TMP_DIR=$(mktemp -d)
cp -R "$APP_PATH" "$TMP_DIR/"

# Add Applications shortcut
ln -s /Applications "$TMP_DIR/Applications"

# Create the DMG
hdiutil create -volname "$VOLUME_NAME" \
  -srcfolder "$TMP_DIR" \
  -ov -format UDZO \
  "$DMG_PATH"

# Cleanup
rm -rf "$TMP_DIR"

echo
echo "DMG created successfully:"
echo "  → $DMG_PATH"
#!/bin/bash

# ESP32 HoverBot - Build and Flash Script
# This script activates ESP-IDF and builds/flashes the firmware

# Activate ESP-IDF environment
echo "Activating ESP-IDF environment..."
source ~/esp/v5.5.1/esp-idf/export.sh

# Build the project
echo "Building project..."
idf.py build

# Check if build succeeded
if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo ""
    echo "To flash the firmware:"
    echo "  idf.py -p /dev/tty.usbserial-140 flash"
    echo ""
    echo "To monitor serial output:"
    echo "  idf.py -p /dev/tty.usbserial-140 monitor"
else
    echo "❌ Build failed!"
    exit 1
fi

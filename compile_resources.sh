#!/bin/bash
# Script to compile QGIS plugin resources
# Run this after modifying resources.qrc

echo "Compiling resources.qrc to resources.py..."

# Try to find pyrcc5
if command -v pyrcc5 &> /dev/null; then
    pyrcc5 resources.qrc -o resources.py
    echo "Success! resources.py created."
elif command -v pyrcc5-qt5 &> /dev/null; then
    pyrcc5-qt5 resources.qrc -o resources.py
    echo "Success! resources.py created."
else
    echo "ERROR: Could not find pyrcc5 or pyrcc5-qt5"
    echo "Please install PyQt5 tools or run from QGIS Python console"
    exit 1
fi





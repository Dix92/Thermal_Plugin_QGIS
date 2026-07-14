@echo off
REM Script to compile QGIS plugin resources
REM Run this after modifying resources.qrc

echo Compiling resources.qrc to resources.py...

REM Try to find pyrcc5 in common QGIS installation paths
set PYTHONPATH=
set PYTHON_EXE=

REM Windows QGIS paths
if exist "C:\Program Files\QGIS 3.34.0\bin\pyrcc5.exe" (
    "C:\Program Files\QGIS 3.34.0\bin\pyrcc5.exe" resources.qrc -o resources.py
    goto :done
)

if exist "C:\Program Files\QGIS 3.32.0\bin\pyrcc5.exe" (
    "C:\Program Files\QGIS 3.32.0\bin\pyrcc5.exe" resources.qrc -o resources.py
    goto :done
)

REM Try to find it in PATH
where pyrcc5 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    pyrcc5 resources.qrc -o resources.py
    goto :done
)

echo ERROR: Could not find pyrcc5.exe
echo Please run this from QGIS Python console or install PyQt5 tools
echo You can also compile manually: pyrcc5 resources.qrc -o resources.py

:done
if exist resources.py (
    echo Success! resources.py created.
) else (
    echo Failed to create resources.py
)
pause





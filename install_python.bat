@echo off
chcp 65001 >nul 2>&1
title Install Python 3.12 for KUS Pro

echo.
echo  ========================================
echo     Python 3.12 Auto-Installer
echo  ========================================
echo.

:: Check if Python 3.10+ already exists
set FOUND_PY=0

where py >nul 2>&1
if not errorlevel 1 (
    py -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" 2>nul
    if not errorlevel 1 (
        echo  Python 3.10+ already installed:
        py --version
        set FOUND_PY=1
    )
)

if "%FOUND_PY%"=="1" (
    echo.
    echo  No need to install. Run run.bat
    echo.
    pause
    goto :eof
)

echo  Python 3.10+ not found.
echo  Current Python 3.8 is not compatible with KUS Pro.
echo.
echo  Downloading Python 3.12 installer...
echo.

:: Download Python 3.12 installer
set URL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
set INSTALLER=%TEMP%\python-3.12.10-amd64.exe

:: Try with curl first, then powershell
curl -L -o "%INSTALLER%" "%URL%" 2>nul
if errorlevel 1 (
    powershell -Command "Invoke-WebRequest -Uri '%URL%' -OutFile '%INSTALLER%'" 2>nul
)

if not exist "%INSTALLER%" (
    echo  [!] Download failed.
    echo  [!] Download manually: https://www.python.org/downloads/
    echo  [!] Run the installer and check "Add Python to PATH"
    echo.
    pause
    goto :eof
)

echo  Downloaded. Installing Python 3.12...
echo  (May take 1-2 minutes)
echo.

:: Install Python 3.12 silently with PATH
"%INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0

echo.
echo  Installation complete!
echo.

:: Clean up
del "%INSTALLER%" 2>nul

echo  Now run run.bat to start KUS Pro
echo.
pause

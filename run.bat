@echo off
chcp 65001 >nul 2>&1
title KUS Pro

cd /d "%~dp0"

if not exist "main.py" (
    echo  [!] main.py not found!
    echo  [!] Run from project folder.
    echo.
    pause
    goto :eof
)

echo.
echo  ========================================
echo     KUS Pro
echo  ========================================
echo.

set PY=
set NEED_INSTALL=0

:: Check if Python 3.10+ exists via py launcher
where py >nul 2>&1
if not errorlevel 1 (
    py -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" 2>nul
    if not errorlevel 1 (
        set PY=py
        goto :deps
    )
)

:: Check direct python
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" 2>nul
    if not errorlevel 1 (
        set PY=python
        goto :deps
    )
)

:: Check installed Pythons
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (set "PY=%LOCALAPPDATA%\Programs\Python\Python314\python.exe" & goto :deps)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe" & goto :deps)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe" & goto :deps)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe" & goto :deps)
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (set "PY=%LOCALAPPDATA%\Programs\Python\Python310\python.exe" & goto :deps)

:: No Python 3.10+ found - need to install
echo  [!] Python 3.10+ not found!
echo.
echo  Current Python 3.8 is not compatible.
echo  Installing Python 3.12 automatically...
echo.

set INSTALLER=%TEMP%\python-3.12.10-amd64.exe
set URL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe

:: Download
echo  Downloading Python 3.12...
curl -L -o "%INSTALLER%" "%URL%" 2>nul
if errorlevel 1 (
    powershell -Command "Invoke-WebRequest -Uri '%URL%' -OutFile '%INSTALLER%'" 2>nul
)

if not exist "%INSTALLER%" (
    echo  [!] Download failed.
    echo  [!] Download manually: https://www.python.org/downloads/
    echo  [!] Check "Add Python to PATH" during install.
    echo  [!] Then run this file again.
    echo.
    pause
    goto :eof
)

echo  Installing Python 3.12 (1-2 min)...
"%INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0

:: Wait for install
timeout /t 10 /nobreak >nul

:: Find newly installed Python
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe" & goto :deps)
if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe" (set "PY=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe" & goto :deps)

:: Try py launcher again
where py >nul 2>&1
if not errorlevel 1 (set "PY=py" & goto :deps)

echo  [!] Install completed but Python not found.
echo  [!] Close this window and run run.bat again.
echo.
del "%INSTALLER%" 2>nul
pause
goto :eof

:deps
echo  Python: %PY%
"%PY%" --version
echo.

:: Disable proxy
set OLD_HTTP=%HTTP_PROXY%
set OLD_HTTPS=%HTTPS_PROXY%
set OLD_http=%http_proxy%
set OLD_https=%https_proxy%
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=

:: Check if PyQt is installed
"%PY%" -c "import PyQt6" 2>nul
if not errorlevel 1 goto :check_psutil

"%PY%" -c "import PyQt5" 2>nul
if not errorlevel 1 goto :check_psutil

:: Install dependencies
echo  Installing dependencies...

"%PY%" -c "import sys; v=sys.version_info; sys.exit(0 if v>=(3,10) else 1)" 2>nul
if errorlevel 1 (
    "%PY%" -m pip install PyQt5 psutil certifi -q
) else (
    "%PY%" -m pip install PyQt6 psutil certifi -q
)

:check_psutil
"%PY%" -c "import psutil" 2>nul
if errorlevel 1 "%PY%" -m pip install psutil certifi -q

:: Restore proxy
set HTTP_PROXY=%OLD_HTTP%
set HTTPS_PROXY=%OLD_HTTPS%
set http_proxy=%OLD_http%
set https_proxy=%OLD_https%

:: Verify
"%PY%" -c "import PyQt5" 2>nul
if not errorlevel 1 goto :run
"%PY%" -c "import PyQt6" 2>nul
if not errorlevel 1 goto :run

echo  [!] Install failed. Try: pip install PyQt5 psutil certifi
pause
goto :eof

:run
echo  OK.
echo.
echo  Starting...
echo.
"%PY%" main.py > run_log.txt 2>&1
set EXITCODE=%ERRORLEVEL%

type run_log.txt

echo.
echo  ========================================
echo     Done (code: %EXITCODE%)
echo  ========================================
echo.

if not "%EXITCODE%"==0 (
    echo  [!] Error. See run_log.txt
    echo.
)

echo  Press any key...
pause >nul

:eof

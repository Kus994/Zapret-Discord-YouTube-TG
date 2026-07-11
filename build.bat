@echo off
chcp 65001 >nul 2>&1
title KUS Pro — Build

cd /d "%~dp0"

echo.
echo  ========================================
echo     KUS Pro — Сборка standalone .exe
echo  ========================================
echo.

:: Ищем Python
set PY=

where py >nul 2>&1
if not errorlevel 1 set PY=py
if not "%PY%"=="" goto :build

where python >nul 2>&1
if not errorlevel 1 set PY=python
if not "%PY%"=="" goto :build

echo  [ERROR] Python не найден!
echo  Установите Python 3.10+ с python.org
pause
goto :eof

:build
echo  Python: %PY%
"%PY%" --version
echo.

:: Устанавливаем зависимости
echo  Установка зависимостей...
"%PY%" -m pip install PyQt5 psutil certifi pyinstaller --quiet
echo  OK.
echo.

:: Запускаем сборку
echo  Запуск сборки...
echo.
"%PY%" build.py
set EXITCODE=%ERRORLEVEL%

echo.
if "%EXITCODE%"=="0" (
    echo  ========================================
    echo     Сборка завершена успешно!
    echo     EXE: dist\KUS_Pro\KUS_Pro.exe
    echo  ========================================
) else (
    echo  ========================================
    echo     Ошибка сборки!
    echo     Проверьте вывод выше
    echo  ========================================
)
echo.

echo  Нажмите любую клавишу, чтобы закрыть это окно...
pause >nul

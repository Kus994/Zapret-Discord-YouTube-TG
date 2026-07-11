@echo off
chcp 65001 >nul
title KUS Pro — Сборка установщика

echo ============================================================
echo   KUS Pro — Сборка установщика через Inno Setup
echo ============================================================
echo.

REM 1. Сборка EXE
echo [1/3] Сборка EXE через PyInstaller...
python build.py --skip-version
if %ERRORLEVEL% NEQ 0 (
    echo ОШИБКА: Сборка EXE не удалась!
    pause
    exit /b 1
)
echo [OK] EXE собран
echo.

REM 2. Проверка Inno Setup
echo [2/3] Проверка Inno Setup...
where iscc >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ОШИБКА: Inno Setup не найден!
    echo Скачайте с: https://jrsoftware.org/isinfo.php
    echo Установите и добавьте в PATH
    pause
    exit /b 1
)
echo [OK] Inno Setup найден
echo.

REM 3. Сборка установщика
echo [3/3] Сборка установщика...
iscc installer.iss
if %ERRORLEVEL% NEQ 0 (
    echo ОШИБКА: Сборка установщика не удалась!
    pause
    exit /b 1
)
echo.

echo ============================================================
echo   Готово!
echo   EXE:      dist\KUS_Pro.exe
echo   Installer: installer\KUS_Pro_Setup_3.2.0.exe
echo ============================================================
echo.
pause

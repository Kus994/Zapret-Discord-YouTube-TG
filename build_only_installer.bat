@echo off
chcp 65001 >nul
title KUS Pro — Только установщик

echo ============================================================
echo   KUS Pro — Сборка установщика
echo ============================================================
echo.

REM Проверяем наличие EXE
if not exist "dist\KUS_Pro.exe" (
    echo ОШИБКА: dist\KUS_Pro.exe не найден!
    echo Сначала запустите: python build.py
    pause
    exit /b 1
)

REM Проверяем Inno Setup
where iscc >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ОШИБКА: Inno Setup не найден!
    echo Скачайте: https://jrsoftware.org/isinfo.php
    pause
    exit /b 1
)

echo Сборка установщика...
iscc installer.iss

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo   Готово!
    echo   Установщик: installer\KUS_Pro_Setup_3.2.0.exe
    echo ============================================================
) else (
    echo ОШИБКА при сборке!
)

echo.
pause

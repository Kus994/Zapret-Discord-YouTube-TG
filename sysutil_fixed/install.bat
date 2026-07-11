@echo off
:: ============================================================
:: install.bat — установка Kus на любой ПК с Windows
:: Запускать от имени администратора!
:: ============================================================

setlocal EnableDelayedExpansion
chcp 65001 > nul

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Kus — Установщик утилиты               ║
echo  ╚══════════════════════════════════════════╝
echo.

:: --- 1. Проверка Python -------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo  [!] Python не найден.
    echo  Скачайте Python 3.10+ с https://www.python.org/downloads/
    echo  При установке ОБЯЗАТЕЛЬНО поставьте галочку "Add Python to PATH"
    pause & exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [OK] Python %PYVER% обнаружен.

:: --- 2. pip install ------------------------------------------------
echo.
echo  Установка зависимостей...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [!] Ошибка установки зависимостей. Проверьте интернет-соединение.
    pause & exit /b 1
)
echo  [OK] Зависимости установлены.

:: --- 3. Ярлык на рабочем столе ------------------------------------
echo.
set SCRIPT_DIR=%~dp0
set SHORTCUT_PATH=%USERPROFILE%\Desktop\Kus.lnk
set TARGET=%SCRIPT_DIR%launch.bat

:: Создаём launch.bat рядом с утилитой
echo @echo off > "%SCRIPT_DIR%launch.bat"
echo cd /d "%SCRIPT_DIR%" >> "%SCRIPT_DIR%launch.bat"
echo python main.py >> "%SCRIPT_DIR%launch.bat"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); ^
   $s.TargetPath = '%TARGET%'; ^
   $s.WorkingDirectory = '%SCRIPT_DIR%'; ^
   $s.Description = 'Kus — утилита администратора'; ^
   $s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo  [OK] Ярлык "Kus" создан на рабочем столе.
) else (
    echo  [~] Ярлык не создан (без прав или другая ошибка).
)

:: --- 4. (Опционально) Сборка в EXE --------------------------------
echo.
set /p BUILD=  Собрать в один .exe файл? (требует ~5 мин) [y/N]: 
if /i "!BUILD!"=="y" (
    echo.
    echo  Установка PyInstaller...
    python -m pip install pyinstaller --quiet
    echo  Сборка...
    python -m PyInstaller kus.spec --clean --noconfirm
    if errorlevel 1 (
        echo  [!] Ошибка сборки EXE. Утилита всё равно работает через python main.py.
    ) else (
        echo  [OK] Готово! Файл: dist\Kus.exe
        echo  Скопируйте dist\Kus.exe на любой ПК — Python не нужен.
    )
)

echo.
echo  ══════════════════════════════════════════
echo  Установка завершена!
echo  Запуск: двойной клик по ярлыку "Kus" на рабочем столе
echo       или: python main.py
echo  ══════════════════════════════════════════
echo.
pause

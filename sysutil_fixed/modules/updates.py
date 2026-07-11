"""
modules/updates.py
-------------------
Модуль обновлений Windows/драйверов и интеграции с Планировщиком задач.

Функции:
  - Поиск и установка обновлений Windows через модуль PowerShell PSWindowsUpdate
    (если установлен) либо через usoclient как запасной вариант.
  - Поиск обновлений драйверов через Windows Update (категория Drivers).
  - Создание/удаление задачи в Планировщике задач для регулярного
    автоматического запуска проверки обновлений (schtasks).
"""

import subprocess
import sys
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000


def _run_powershell(script: str, log_func, timeout: int = 600) -> str:
    """Запускает PowerShell-команду и возвращает её вывод построчно в лог."""
    try:
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output_lines = []
        for line in process.stdout:
            line = line.rstrip()
            if line:
                log_func(line)
                output_lines.append(line)
        process.wait(timeout=timeout)
        return "\n".join(output_lines)
    except subprocess.TimeoutExpired:
        log_func("Превышено время ожидания операции.")
        return ""
    except Exception as exc:
        log_func(f"Ошибка PowerShell: {exc}")
        return ""


def check_pswindowsupdate_installed(log_func) -> bool:
    """Проверяет, установлен ли модуль PSWindowsUpdate."""
    script = "Get-Module -ListAvailable -Name PSWindowsUpdate | Select-Object -First 1 | ForEach-Object { $_.Name }"
    out = _run_powershell(script, log_func, timeout=30)
    return "PSWindowsUpdate" in out


def install_pswindowsupdate_module(log_func, progress_func):
    """Устанавливает модуль PSWindowsUpdate из PowerShell Gallery."""
    log_func("Модуль PSWindowsUpdate не найден. Установка...")
    progress_func(0.1)
    script = (
        "Set-PSRepository -Name PSGallery -InstallationPolicy Trusted; "
        "Install-Module -Name PSWindowsUpdate -Force -Confirm:$false -Scope CurrentUser"
    )
    _run_powershell(script, log_func, timeout=180)
    progress_func(0.3)


def search_and_install_windows_updates(log_func, progress_func, auto_install: bool = True):
    """
    Ищет доступные обновления Windows и при auto_install=True устанавливает их.
    Использует модуль PSWindowsUpdate как наиболее надёжный механизм.
    """
    log_func("=== Проверка обновлений Windows ===")
    progress_func(0.0)

    if not check_pswindowsupdate_installed(log_func):
        install_pswindowsupdate_module(log_func, progress_func)

    progress_func(0.35)
    log_func("Поиск доступных обновлений...")

    if auto_install:
        script = (
            "Import-Module PSWindowsUpdate; "
            "Get-WindowsUpdate -AcceptAll -Install -AutoReboot:$false -Verbose"
        )
    else:
        script = (
            "Import-Module PSWindowsUpdate; "
            "Get-WindowsUpdate -Verbose"
        )

    _run_powershell(script, log_func, timeout=1800)
    progress_func(0.9)
    log_func("Проверка обновлений Windows завершена. "
              "Если устанавливались обновления — может потребоваться перезагрузка.")
    progress_func(1.0)


def search_driver_updates(log_func, progress_func):
    """
    Ищет обновления драйверов через категорию 'Drivers' Windows Update.
    """
    log_func("=== Поиск обновлений драйверов ===")
    progress_func(0.1)

    if not check_pswindowsupdate_installed(log_func):
        install_pswindowsupdate_module(log_func, progress_func)

    script = (
        "Import-Module PSWindowsUpdate; "
        "Get-WindowsUpdate -UpdateType Driver -Verbose"
    )
    _run_powershell(script, log_func, timeout=600)
    progress_func(1.0)
    log_func("Поиск обновлений драйверов завершён.")


# --------------------------------------------------------------------------
# Планировщик задач Windows (schtasks)
# --------------------------------------------------------------------------

TASK_NAME = "SysUtil_AutoUpdateCheck"


def register_scheduled_task(log_func, progress_func, schedule: str = "DAILY", time_str: str = "03:00"):
    """
    Создаёт задачу в Планировщике задач Windows, которая запускает
    проверку обновлений по расписанию (по умолчанию — каждый день в 03:00).

    schedule: DAILY | WEEKLY | ONLOGON
    """
    log_func(f"Регистрация задачи в Планировщике: {schedule} в {time_str}...")
    progress_func(0.2)

    python_exe = sys.executable
    script_path = Path(__file__).resolve().parent.parent / "main.py"

    cmd = (
        f'schtasks /Create /TN "{TASK_NAME}" '
        f'/TR "\\"{python_exe}\\" \\"{script_path}\\" --silent-update-check" '
        f'/SC {schedule} /ST {time_str} /RL HIGHEST /F'
    )

    result = subprocess.run(
        ["cmd.exe", "/c", cmd],
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
        text=False,
    )
    out = result.stdout.decode("cp866", errors="replace")
    err = result.stderr.decode("cp866", errors="replace")
    progress_func(0.8)

    if result.returncode == 0:
        log_func(f"Задача '{TASK_NAME}' успешно создана.")
        log_func(out.strip())
        success = True
    else:
        log_func(f"Не удалось создать задачу: {err.strip() or out.strip()}")
        success = False

    progress_func(1.0)
    return success


def unregister_scheduled_task(log_func, progress_func):
    """Удаляет ранее созданную задачу автообновления."""
    log_func(f"Удаление задачи '{TASK_NAME}'...")
    progress_func(0.3)
    result = subprocess.run(
        ["cmd.exe", "/c", f'schtasks /Delete /TN "{TASK_NAME}" /F'],
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    )
    progress_func(1.0)
    if result.returncode == 0:
        log_func("Задача удалена.")
    else:
        log_func("Задача не найдена либо уже удалена.")
    return result.returncode == 0


def is_task_registered(log_func=None) -> bool:
    """Проверяет, существует ли задача в Планировщике."""
    result = subprocess.run(
        ["cmd.exe", "/c", f'schtasks /Query /TN "{TASK_NAME}"'],
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    )
    return result.returncode == 0

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


def _run_powershell(script: str, log_func, timeout: int = 600) -> tuple:
    """Запускает PowerShell-команду и возвращает (output_text, returncode)."""
    try:
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout, stderr = process.communicate(timeout=timeout)
        output_lines = []
        for line in stdout.splitlines():
            line = line.rstrip()
            if line:
                log_func(line)
                output_lines.append(line)
        if process.returncode != 0 and stderr.strip():
            for line in stderr.splitlines():
                line = line.rstrip()
                if line:
                    log_func("[ошибка] {}".format(line), "ERR")
                    output_lines.append("[ошибка] {}".format(line))
        return "\n".join(output_lines), process.returncode
    except subprocess.TimeoutExpired:
        process.kill()
        log_func("Превышено время ожидания операции.", "ERR")
        return "", -1
    except Exception as exc:
        log_func("Ошибка PowerShell: {}".format(exc), "ERR")
        return "", -1


def check_pswindowsupdate_installed(log_func) -> bool:
    """Проверяет, установлен ли модуль PSWindowsUpdate."""
    script = "Get-Module -ListAvailable -Name PSWindowsUpdate | Select-Object -First 1 | ForEach-Object { $_.Name }"
    out, code = _run_powershell(script, log_func, timeout=30)
    return "PSWindowsUpdate" in out


def install_pswindowsupdate_module(log_func, progress_func) -> bool:
    """Устанавливает модуль PSWindowsUpdate из PowerShell Gallery."""
    log_func("Модуль PSWindowsUpdate не найден. Установка из PowerShell Gallery...")
    progress_func(0.1)
    script = (
        "Set-PSRepository -Name PSGallery -InstallationPolicy Trusted; "
        "Install-Module -Name PSWindowsUpdate -Force -Confirm:$false -Scope CurrentUser"
    )
    out, code = _run_powershell(script, log_func, timeout=180)
    progress_func(0.3)
    if code != 0:
        log_func("Не удалось установить PSWindowsUpdate (код: {}).".format(code), "ERR")
        log_func("Попробуйте установить вручную: Install-Module PSWindowsUpdate", "WARN")
        return False
    # Проверяем что модуль реально установился
    if check_pswindowsupdate_installed(log_func):
        log_func("PSWindowsUpdate установлен успешно.", "OK")
        return True
    log_func("PSWindowsUpdate не обнаружен после установки.", "ERR")
    return False


def _fallback_usoclient(log_func, progress_func) -> bool:
    """Запасной вариант: use usoclient для проверки обновлений."""
    log_func("Пробуем usoclient как запасной вариант...")
    progress_func(0.5)
    out, code = _run_powershell("usoclient StartScan", log_func, timeout=300)
    if code == 0:
        log_func("Проверка через usoclient завершена. Откройте Параметры → Обновление Windows.", "OK")
        return True
    log_func("usoclient не сработал (код: {}).".format(code), "WARN")
    return False


def search_and_install_windows_updates(log_func, progress_func, auto_install: bool = True) -> bool:
    """
    Ищет доступные обновления Windows и при auto_install=True устанавливает их.
    Использует модуль PSWindowsUpdate как наиболее надёжный механизм.
    Возвращает True при успехе, False при ошибке.
    """
    log_func("=== Проверка обновлений Windows ===")
    progress_func(0.0)

    if not check_pswindowsupdate_installed(log_func):
        if not install_pswindowsupdate_module(log_func, progress_func):
            log_func("Не удалось установить PSWindowsUpdate. Обновления недоступны.", "ERR")
            progress_func(1.0)
            return False

    progress_func(0.35)
    log_func("Поиск доступных обновлений...")

    if auto_install:
        script = (
            "Import-Module PSWindowsUpdate -ErrorAction Stop; "
            "Get-WindowsUpdate -AcceptAll -Install -AutoReboot:$false -Verbose"
        )
    else:
        script = (
            "Import-Module PSWindowsUpdate -ErrorAction Stop; "
            "Get-WindowsUpdate -Verbose"
        )

    out, code = _run_powershell(script, log_func, timeout=1800)
    progress_func(0.9)

    if code != 0:
        log_func("Ошибка при проверке/установке обновлений (код: {}).".format(code), "ERR")
        if "argumentexception" in out.lower():
            log_func("PSWindowsUpdate несовместим с этой версией Windows.", "WARN")
            log_func("Пробуем запасной вариант (usoclient)...", "INFO")
            return _fallback_usoclient(log_func, progress_func)
        # Другая ошибка — тоже пробуем запасной вариант
        log_func("Пробуем запасной вариант (usoclient)...", "INFO")
        return _fallback_usoclient(log_func, progress_func)
    else:
        log_func("Проверка обновлений Windows завершена.", "OK")
        if auto_install:
            log_func("Если устанавливались обновления — может потребоваться перезагрузка.", "INFO")

    progress_func(1.0)
    return code == 0


def search_driver_updates(log_func, progress_func) -> bool:
    """
    Ищет обновления драйверов через категорию 'Drivers' Windows Update.
    Возвращает True при успехе, False при ошибке.

    Примечание: параметр -UpdateType Driver устарел в новых версиях
    PSWindowsUpdate и вызывает ArgumentException. Используем
    -Category "Drivers" как рекомендуемую альтернативу.
    """
    log_func("=== Поиск обновлений драйверов ===")
    progress_func(0.1)

    if not check_pswindowsupdate_installed(log_func):
        if not install_pswindowsupdate_module(log_func, progress_func):
            log_func("Не удалось установить PSWindowsUpdate.", "ERR")
            progress_func(1.0)
            return False

    # Способ 1: -Category "Drivers" (работает в PSWindowsUpdate 2.2+)
    script = (
        "Import-Module PSWindowsUpdate -ErrorAction Stop; "
        "Get-WindowsUpdate -Category 'Drivers' -Verbose"
    )
    out, code = _run_powershell(script, log_func, timeout=600)

    # Способ 2: если -Category не сработал, пробуем фильтрацию через Where-Object
    if code != 0 and "argumentexception" not in out.lower():
        log_func("Пробуем альтернативный способ поиска драйверов...", "INFO")
        script = (
            "Import-Module PSWindowsUpdate -ErrorAction Stop; "
            "Get-WindowsUpdate -Verbose | Where-Object { $_.Categories -match 'Driver' }"
        )
        out, code = _run_powershell(script, log_func, timeout=600)

    # Способ 3: через COM-объект Microsoft.Update.Session (запасной)
    if code != 0:
        log_func("Пробуем поиск через Microsoft.Update.Session...", "INFO")
        script = (
            "$session = New-Object -ComObject Microsoft.Update.Session; "
            "$searcher = $session.CreateUpdateSearcher(); "
            "$criteria = \"Type='Driver'\"; "
            "$result = $searcher.Search($criteria); "
            "if ($result.Updates.Count -eq 0) { Write-Host 'Обновления драйверов не найдены.' } "
            "else { $result.Updates | ForEach-Object { Write-Host $_.Title } }"
        )
        out, code = _run_powershell(script, log_func, timeout=600)

    progress_func(1.0)

    if code != 0:
        log_func("Ошибка при поиске обновлений драйверов (код: {}).".format(code), "ERR")
        if "argumentexception" in out.lower():
            log_func("Попробуйте: обновите драйверы через Диспетчер устройств.", "WARN")
        return False

    log_func("Поиск обновлений драйверов завершён.", "OK")
    return True


# --------------------------------------------------------------------------
# Планировщик задач Windows (schtasks)
# --------------------------------------------------------------------------

TASK_NAME = "SysUtil_AutoUpdateCheck"


def register_scheduled_task(log_func, progress_func, schedule: str = "DAILY", time_str: str = "03:00"):
    """
    Создаёт задачу в Планировщике задач Windows, которая запускает
    проверку обновлений по расписанию (по умолчанию — каждый день в 03:00).

    schedule: "DAILY", "WEEKLY" or "ONLOGON"
    """
    log_func(f"Регистрация задачи в Планировщике: {schedule} в {time_str}...")
    progress_func(0.2)

    # В frozen-режиме (PyInstaller .exe) запускаем .exe напрямую,
    # в dev-режиме — python main.py
    if getattr(sys, "frozen", False):
        exe_path = Path(sys.executable).resolve()
        cmd = (
            f'schtasks /Create /TN "{TASK_NAME}" '
            f'/TR "\\"{exe_path}\\" --silent-update-check" '
            f'/SC {schedule} /ST {time_str} /RL HIGHEST /F'
        )
    else:
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

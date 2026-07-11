"""
modules/optimizer.py
--------------------
Оптимизация производительности Windows.
Очистка + отключение ненужных служб + оптимизация системы.
"""

import subprocess
import os
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000

# Службы, которые можно безопасно отключать для повышения производительности
OPTIMIZABLE_SERVICES = {
    "SysMain": "Суперфетч — ускоряет запуск программ за счёт кэширования",
    "DiagTrack": "Телеметрия Microsoft — сбор данных",
    "dmwappushservice": "WAP Push — не нужна большинству пользователей",
    "WSearch": "Windows Search — индексирование (если не нужен поиск)",
    "RetailDemo": "Демо-режим — не нужен на домашнем ПК",
    "MapsBroker": "Карты — если не используете встроенные карты",
    "lfsvc": "Геолокация — если не нужна",
    "SharedAccess": "Мастер общего доступа к интернету",
    "RemoteRegistry": "Удалённый реестр — риск безопасности",
    "XblAuthManager": "Xbox Live Auth — если не играете в Xbox",
    "XblGameSave": "Xbox Game Save — если не играете в Xbox",
    "XboxGipSvc": "Xbox Peripheral — если нет геймпада Xbox",
    "XboxNetApiSvc": "Xbox Network — если не играете в Xbox",
}

# Службы, которые НЕЛЬЗЯ отключать
CRITICAL_SERVICES = {
    "RpcSs", "DcomLaunch", "PlugPlay", "Power", "Schedule",
    "WinDefend", "mpssvc", "WdNisSvc", "SecurityHealthService",
}


def _run_cmd(cmd, timeout=30):
    """Выполняет команду и возвращает (stdout, returncode)."""
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", cmd],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=timeout,
        )
        out = result.stdout.decode("cp866", errors="replace")
        return out, result.returncode
    except Exception as e:
        return str(e), -1


def optimize_system(log_func, progress_func, options=None):
    """
    Оптимизация системы с учётом выбранных опций.

    options: dict с ключами:
        temp: bool       — очистка Temp-папок
        recycle: bool    — очистка корзины
        services: bool   — отключение ненужных служб
        dns: bool        — очистка DNS кэша
        browser: bool    — очистка кэша браузеров
        prefetch: bool   — очистка Prefetch
        update_cache: bool — очистка кэша обновлений Windows
    """
    if options is None:
        options = {"temp": True, "recycle": True, "services": True,
                   "dns": True, "browser": False, "prefetch": False,
                   "update_cache": False}

    log_func("=== Оптимизация системы ===")
    progress_func(0.0)

    total_freed = 0
    steps = sum(1 for v in options.values() if v)
    step = 0

    def _pct():
        return min(0.95, step / max(steps, 1))

    # 1. Очистка Temp
    if options.get("temp"):
        log_func("Очистка временных файлов...")
        from modules.cleanup import clean_temp_folders
        freed = clean_temp_folders(
            log_func, progress_func,
            include_all_disks=True,
            include_user_temp=True,
            include_system_temp=True,
        )
        total_freed += freed
        step += 1
        progress_func(_pct())

    # 2. Очистка кэша обновлений
    if options.get("update_cache"):
        log_func("Очистка кэша обновлений Windows...")
        from modules.cleanup import clean_update_cache
        freed = clean_update_cache(log_func, progress_func)
        total_freed += freed
        step += 1
        progress_func(_pct())

    # 3. Очистка корзины
    if options.get("recycle"):
        log_func("Очистка корзины...")
        from modules.cleanup import empty_recycle_bin
        empty_recycle_bin(log_func, progress_func)
        step += 1
        progress_func(_pct())

    # 4. Очистка кэша браузеров
    if options.get("browser"):
        log_func("Очистка кэша браузеров...")
        from modules.cleanup import clean_browser_cache, detect_installed_browsers
        browsers = detect_installed_browsers()
        if browsers:
            log_func("  Найдены: {}".format(", ".join(browsers)))
            freed = clean_browser_cache(log_func, progress_func)
            total_freed += freed
        else:
            log_func("  Браузеры с кэшем не найдены", "WARN")
        step += 1
        progress_func(_pct())

    # 5. Очистка Prefetch
    if options.get("prefetch"):
        log_func("Очистка Prefetch...")
        from modules.cleanup import clean_prefetch
        freed = clean_prefetch(log_func, progress_func)
        total_freed += freed
        step += 1
        progress_func(_pct())

    # 6. Отключение ненужных служб
    if options.get("services"):
        log_func("Отключение ненужных служб...")
        disabled = 0
        services = list(OPTIMIZABLE_SERVICES.keys())
        for i, service in enumerate(services):
            if service in CRITICAL_SERVICES:
                continue
            try:
                out, code = _run_cmd('sc config "{}" start= disabled'.format(service))
                if code == 0:
                    disabled += 1
                    log_func("  {} — отключена".format(service), "OK")
                else:
                    log_func("  {} — не удалось отключить".format(service), "WARN")
            except Exception:
                pass
            progress_func(_pct() + 0.1 * (i + 1) / max(len(services), 1))
        log_func("Отключено служб: {}".format(disabled))
        step += 1
        progress_func(_pct())

    # 7. Оптимизация производительности Windows
    log_func("Оптимизация параметров Windows...")
    _optimize_windows_performance(log_func)
    step += 1
    progress_func(_pct())

    # 8. Очистка DNS кэша
    if options.get("dns"):
        log_func("Очистка DNS кэша...")
        _run_cmd("ipconfig /flushdns")
        step += 1
        progress_func(_pct())

    progress_func(1.0)
    from modules.cleanup import human_size
    log_func("=== Оптимизация завершена. Освобождено: {} ===".format(human_size(total_freed)), "OK")
    return total_freed


def _optimize_windows_performance(log_func):
    """Оптимизация параметров производительности Windows через реестр."""
    try:
        import winreg

        # Отключаем визуальные эффекты для производительности
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "VisualFXSetting", 0, winreg.REG_DWORD, 2)
            log_func("  Визуальные эффекты оптимизированы", "OK")
        except Exception:
            pass

        # Отключаем прозрачность
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "EnableTransparency", 0, winreg.REG_DWORD, 0)
            log_func("  Прозрачность отключена", "OK")
        except Exception:
            pass

    except Exception as e:
        log_func("  Ошибка оптимизации: {}".format(str(e)[:50]), "WARN")


def get_optimization_estimate(log_func, progress_func):
    """Оценивает объём мусора и список оптимизаций."""
    log_func("=== Оценка оптимизации ===")
    progress_func(0.0)

    from modules.cleanup import estimate_junk_size
    junk_size = estimate_junk_size(log_func, progress_func)

    # Проверяем отключённые службы
    log_func("")
    log_func("Ненужные службы:")
    disabled_count = 0
    for service, desc in OPTIMIZABLE_SERVICES.items():
        try:
            out, _ = _run_cmd('sc qc "{}"'.format(service))
            if "DISABLED" in out.upper():
                log_func("  {} — уже отключена".format(service))
            else:
                log_func("  {} — {}".format(service, desc))
                disabled_count += 1
        except Exception:
            pass

    progress_func(1.0)
    from modules.cleanup import human_size
    log_func("=== Итого: мусор {} , служб к отключению: {} ===".format(
        human_size(junk_size), disabled_count
    ), "OK")

    return {
        "junk_size": junk_size,
        "services_to_disable": disabled_count,
    }

"""
modules/game_mode.py — KUS Pro

Игровой/рабочий режим: быстрое переключение между «тяжёлым» набором
фоновых приложений (виджеты, оверлеи, синхронизация) и «лёгким» режимом
для игр/максимальной производительности.

Логика портирована из пользовательских .bat-скриптов
(«Оптимизация.bat» — закрыть лишнее перед игрой, «Возврат.bat» —
вернуть всё после игры) и переписана на Python:

  • пути и список процессов не зашиты в код — берутся из config.json
    (секция "game_mode"), поэтому скрипт не привязан к чужому диску
    или имени пользователя;
  • вместо `taskkill /f` используется psutil — это работает без
    разворачивания консоли и даёт точный список того, что реально
    было закрыто;
  • изменения реестра (прозрачность, авто-скрытие панели задач)
    делаются через winreg, без вызова cmd/powershell;
  • каждое действие отдельно логируется через log_func, как и в
    остальных модулях приложения.
"""

import os
import subprocess
import sys
import time

try:
    import psutil
except ImportError:
    psutil = None

# Список приложений, которые по умолчанию считаются "фоновыми" —
# их пользователь, скорее всего, захочет закрыть перед игрой и
# запустить обратно после. Можно дополнить/изменить через UI настроек
# (хранится в config.json -> game_mode.apps).
DEFAULT_APPS = [
    {"label": "Wallpaper Engine", "process": "wallpaper64.exe", "path": ""},
    {"label": "PowerToys",        "process": "PowerToys.exe",   "path": ""},
    {"label": "Windhawk",         "process": "windhawk.exe",    "path": ""},
    {"label": "QuickLook",        "process": "QuickLook.exe",   "path": ""},
    {"label": "AnVir Task Manager", "process": "AnVir.exe",     "path": ""},
    {"label": "Everything",       "process": "Everything.exe",  "path": ""},
    {"label": "AnyDesk",          "process": "AnyDesk.exe",     "path": ""},
]

# Доп. процессы, которые скрипт-источник закрывал, но не перезапускал
# обратно (системные/сторонние компоненты Windows) — их можно закрыть
# при входе в игровой режим, но кнопка "восстановить" их не трогает.
EXTRA_KILL_ONLY = [
    "Microsoft.CmdPal.Ext.PowerToys.exe",
    "PhoneExperienceHost.exe",
    "RuntimeBroker.exe",
]

PERSONALIZE_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
TASKBAR_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StuckRects3"


def _set_registry_dword(hkey_path, name, value, log_func):
    """Устанавливает DWORD-значение в HKEY_CURRENT_USER без вызова cmd."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, hkey_path,
                            0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
        return True
    except FileNotFoundError:
        log_func("Ключ реестра не найден: {}".format(hkey_path), "WARN")
        return False
    except Exception as e:
        log_func("Не удалось изменить реестр ({}): {}".format(hkey_path, e), "ERR")
        return False


def _restart_explorer(log_func):
    """Перезапускает explorer.exe — нужно, чтобы изменения панели
    задач (авто-скрытие) применились немедленно."""
    try:
        for p in psutil.process_iter(["name"]):
            if (p.info["name"] or "").lower() == "explorer.exe":
                p.terminate()
        time.sleep(1.0)
        subprocess.Popen(["explorer.exe"])
        log_func("Explorer перезапущен.", "OK")
    except Exception as e:
        log_func("Не удалось перезапустить Explorer: {}".format(e), "ERR")


def set_transparency(enabled: bool, log_func):
    ok = _set_registry_dword(PERSONALIZE_KEY, "EnableTransparency",
                             1 if enabled else 0, log_func)
    if ok:
        log_func("Прозрачность окон: {}".format("включена" if enabled else "выключена"), "OK")


def set_taskbar_autohide(enabled: bool, log_func, restart=True):
    """Включает/выключает автоскрытие панели задач через StuckRects3.
    Требует перезапуска explorer.exe, чтобы вступить в силу."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, TASKBAR_KEY,
                            0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
            raw, _ = winreg.QueryValueEx(key, "Settings")
            data = bytearray(raw)
            # 9-й байт структуры StuckRects3 хранит флаги панели задач;
            # бит автоскрытия — 0x01.
            if enabled:
                data[8] |= 0x01
            else:
                data[8] &= ~0x01
            winreg.SetValueEx(key, "Settings", 0, winreg.REG_BINARY, bytes(data))
        log_func("Автоскрытие панели задач: {}".format("включено" if enabled else "выключено"), "OK")
        if restart:
            _restart_explorer(log_func)
        return True
    except FileNotFoundError:
        log_func("Настройки панели задач не найдены в реестре.", "WARN")
        return False
    except Exception as e:
        log_func("Не удалось изменить панель задач: {}".format(e), "ERR")
        return False


def _proc_running(name: str) -> bool:
    name = name.lower()
    for p in psutil.process_iter(["name"]):
        if (p.info["name"] or "").lower() == name:
            return True
    return False


def close_apps(apps, log_func, progress_func, extra_kill_only=None):
    """Закрывает список приложений по имени процесса.
    apps: [{"label", "process", "path"}, ...]"""
    total = len(apps) + len(extra_kill_only or [])
    closed, missing = [], []

    # Single scan: build a map of running process names
    running_names = {}
    for p in psutil.process_iter(["name", "pid"]):
        name_lower = (p.info["name"] or "").lower()
        running_names.setdefault(name_lower, []).append(p)

    for i, app in enumerate(apps):
        name = app["process"].lower()
        matches = running_names.get(name, [])
        if matches:
            for p in matches:
                try:
                    p.terminate()
                except Exception:
                    pass
            log_func("{} закрыт.".format(app["label"]), "OK")
            closed.append(app["label"])
        else:
            log_func("{} не найден (не запущен).".format(app["label"]))
            missing.append(app["label"])
        progress_func((i + 1) / max(total, 1) * 0.7)

    # Доп. процессы "только закрыть" — системные службы вроде Phone Link
    for j, name in enumerate(extra_kill_only or []):
        name_lower = name.lower()
        matches = running_names.get(name_lower, [])
        for p in matches:
            try:
                p.terminate()
            except Exception:
                pass
        progress_func(0.7 + (j + 1) / max(len(extra_kill_only or [1]), 1) * 0.2)

    return closed, missing


def start_apps(apps, log_func, progress_func):
    """Запускает список приложений по сохранённому пути к .exe.
    Если путь не указан или файл не найден — приложение пропускается
    с предупреждением (а не падением)."""
    total = len(apps)
    started, skipped = [], []

    for i, app in enumerate(apps):
        path = (app.get("path") or "").strip()
        label = app["label"]

        if not path:
            log_func("{}: путь не задан в настройках — пропуск.".format(label), "WARN")
            skipped.append(label)
            progress_func((i + 1) / max(total, 1))
            continue

        if not os.path.isfile(path):
            log_func("{}: файл не найден по пути «{}» — пропуск.".format(label, path), "WARN")
            skipped.append(label)
            progress_func((i + 1) / max(total, 1))
            continue

        try:
            subprocess.Popen([path], cwd=os.path.dirname(path) or None)
            log_func("{} запущен.".format(label), "OK")
            started.append(label)
        except Exception as e:
            log_func("{}: не удалось запустить — {}".format(label, e), "ERR")
            skipped.append(label)

        progress_func((i + 1) / max(total, 1))

    return started, skipped


def activate_game_mode(log_func, progress_func, apps=None, extra_kill_only=None,
                       disable_transparency=True, enable_taskbar_autohide=True):
    """Полный сценарий «Игровой режим»: закрыть фоновые приложения,
    отключить прозрачность, включить авто-скрытие панели задач."""
    apps = apps if apps is not None else DEFAULT_APPS
    extra_kill_only = extra_kill_only if extra_kill_only is not None else EXTRA_KILL_ONLY

    log_func("=== Включение игрового режима ===")
    progress_func(0.0)

    closed, missing = close_apps(apps, log_func, progress_func, extra_kill_only)

    if disable_transparency:
        set_transparency(False, log_func)
    if enable_taskbar_autohide:
        set_taskbar_autohide(True, log_func)

    progress_func(1.0)
    log_func("=== Игровой режим включён. Закрыто: {} ===".format(len(closed)), "OK")
    return {"closed": closed, "missing": missing}


def deactivate_game_mode(log_func, progress_func, apps=None,
                         enable_transparency=True, disable_taskbar_autohide=True):
    """Полный сценарий «Обычный режим»: вернуть фоновые приложения,
    включить прозрачность, выключить авто-скрытие панели задач."""
    apps = apps if apps is not None else DEFAULT_APPS

    log_func("=== Возврат к обычному режиму ===")
    progress_func(0.0)

    started, skipped = start_apps(apps, log_func, progress_func)

    if enable_transparency:
        set_transparency(True, log_func)
    if disable_taskbar_autohide:
        set_taskbar_autohide(False, log_func)

    progress_func(1.0)
    log_func("=== Обычный режим восстановлен. Запущено: {} ===".format(len(started)), "OK")
    return {"started": started, "skipped": skipped}

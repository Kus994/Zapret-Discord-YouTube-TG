"""
modules/security.py — KUS Pro

Базовая проверка автозагрузки Windows: какие программы стартуют
автоматически вместе с системой и откуда (реестр Run — включая
Wow6432Node для 32-битных программ — и папка автозагрузки), плюс
простая эвристика "подозрительности" записи — НЕ антивирусная
проверка, а скорее быстрый аудит "что вообще автоматически
запускается на этом ПК и откуда", который помогает заметить забытые
или нежелательные записи автозагрузки самостоятельно.

ПРИМЕЧАНИЕ: автозапуск через Планировщик заданий (Task Scheduler)
сюда НЕ входит. Причина — не лень, а надёжность: единственный простой
способ прочитать список задач (`schtasks /query`) отдаёт текст
триггеров ("При входе в систему" и т.п.) на языке интерфейса Windows,
и парсить его надёжно нельзя — на англоязычной системе та же строка
будет "At log on", и любое жёстко зашитое сравнение текста будет
регулярно ломаться. Надёжный способ (PowerShell Get-ScheduledTask с
разбором объектов, а не текста) — отдельная задача, пока не сделана.

Эвристика подозрительности — это явно промаркированные предупреждения
("ярлык ссылается на несуществующий файл", "запуск напрямую из Temp"),
а не вердикт "вирус/не вирус". Окончательное решение остаётся за
пользователем; модуль не удаляет записи автоматически, только
показывает и удаляет по явному действию пользователя в UI.
"""

import os
import re
from pathlib import Path

REG_RUN_PATHS = [
    (r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
    (r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
    # ФИКС: 32-битные программы на 64-битной Windows регистрируют
    # автозагрузку в отдельной "теневой" ветке Wow6432Node — реестр её
    # не подставляет автоматически (в отличие от файловой системы с
    # редиректом System32/SysWOW64). Без этого пути автозагрузка
    # некоторых 32-битных приложений просто не находилась.
    (r"HKEY_LOCAL_MACHINE\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
]

SUSPICIOUS_DIRS = ("temp", "tmp", "appdata\\local\\temp")


def _expand_command(cmd: str) -> str:
    """Разворачивает переменные среды (%windir%, %userprofile% и т.п.)
    внутри значения команды автозагрузки."""
    try:
        return os.path.expandvars(cmd)
    except Exception:
        return cmd


def _extract_exe_path(cmd: str) -> str:
    """Извлекает путь к исполняемому файлу из строки команды автозагрузки,
    которая может содержать аргументы и быть в кавычках:
    '"C:\\Program Files\\App\\app.exe" --silent' -> 'C:\\Program Files\\App\\app.exe'
    """
    cmd = cmd.strip()
    if cmd.startswith('"'):
        m = re.match(r'"([^"]+)"', cmd)
        if m:
            return m.group(1)
    # без кавычек — берём до первого пробела перед "-" или "/" (аргументом),
    # но при простом "C:\path with spaces\app.exe" такая эвристика не
    # справится — в таком случае возвращаем всю строку как есть.
    parts = cmd.split(" ")
    if parts and parts[0].lower().endswith(".exe"):
        return parts[0]
    return cmd


def _classify_entry(name: str, command: str, source: str) -> dict:
    """Простая эвристика подозрительности одной записи автозагрузки."""
    warnings = []
    exe_path = _extract_exe_path(_expand_command(command))

    if exe_path and not exe_path.lower().startswith(("http://", "https://")):
        p = Path(exe_path)
        if p.exists():
            exists = True
        else:
            exists = False
            warnings.append("Файл не найден по указанному пути")

        low = str(p).lower()
        if any(td in low for td in SUSPICIOUS_DIRS):
            warnings.append("Расположен во временной папке (Temp)")
    else:
        exists = None  # не файловый путь (например, URL или rundll32-вызов)

    if re.search(r"powershell.*-enc(odedcommand)?\b", command, re.IGNORECASE):
        warnings.append("Запуск через закодированную команду PowerShell")

    return {
        "name": name,
        "command": command,
        "source": source,
        "exe_path": exe_path,
        "exists": exists,
        "warnings": warnings,
    }


def get_registry_autostart(log_func, progress_func) -> list:
    """Считывает записи автозагрузки из HKCU/HKLM ...\\Run через winreg."""
    import winreg

    log_func("Чтение автозагрузки из реестра (Run)...")
    progress_func(0.1)

    hive_map = {
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
    }
    results = []

    for path, label in REG_RUN_PATHS:
        hive_name, subkey = path.split("\\", 1)
        hive = hive_map.get(label)
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                    except OSError:
                        break
                    entry = _classify_entry(name, str(value), "Реестр ({})".format(label))
                    # ФИКС: раньше запись помнила только куст (HKCU/HKLM),
                    # а remove_autostart_entry всегда удалял из ОДНОГО
                    # жёстко прописанного пути Run. Теперь помним точный
                    # subkey, из которого запись реально прочитана (важно
                    # для Wow6432Node — путь там другой), чтобы удаление
                    # било туда же, откуда прочитали, а не молча "не
                    # находило" запись в обычном Run.
                    entry["reg_subkey"] = subkey
                    results.append(entry)
                    i += 1
        except FileNotFoundError:
            pass
        except Exception as exc:
            log_func("Не удалось прочитать {}: {}".format(path, exc), "WARN")

    progress_func(0.6)
    return results


def get_startup_folder_entries(log_func, progress_func) -> list:
    """Считывает ярлыки из папки автозагрузки (shell:startup)."""
    log_func("Чтение папки автозагрузки...")
    progress_func(0.7)

    results = []
    appdata = os.environ.get("APPDATA", "")
    startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    if startup_dir.exists():
        for item in startup_dir.iterdir():
            if item.is_file():
                entry = _classify_entry(item.stem, str(item), "Папка автозагрузки")
                results.append(entry)

    progress_func(0.85)
    return results


def get_all_autostart_entries(log_func, progress_func) -> list:
    """Объединяет все источники автозагрузки в единый список."""
    log_func("=== Анализ автозагрузки ===")
    progress_func(0.0)

    entries = []
    entries += get_registry_autostart(log_func, progress_func)
    entries += get_startup_folder_entries(log_func, progress_func)

    suspicious_count = sum(1 for e in entries if e["warnings"])
    progress_func(1.0)
    log_func(
        "Найдено записей автозагрузки: {}. С предупреждениями: {}.".format(
            len(entries), suspicious_count
        ),
        "OK" if suspicious_count == 0 else "WARN",
    )
    return entries


def remove_autostart_entry(log_func, progress_func, entry: dict) -> bool:
    """Удаляет конкретную запись автозагрузки (реестр или файл ярлыка).
    Требует точно тот же словарь entry, что вернул get_all_autostart_entries
    (используются поля name/source)."""
    import winreg

    source = entry.get("source", "")
    name = entry.get("name", "")

    try:
        if source.startswith("Реестр"):
            label = "HKCU" if "HKCU" in source else "HKLM"
            hive = winreg.HKEY_CURRENT_USER if label == "HKCU" else winreg.HKEY_LOCAL_MACHINE
            # Используем точный subkey, из которого запись была прочитана
            # (см. get_registry_autostart) — с запасным вариантом для
            # обратной совместимости, если по какой-то причине его нет.
            subkey = entry.get("reg_subkey") or r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
            log_func("Удалена запись автозагрузки из реестра: {}".format(name), "OK")
            return True

        elif "Папка автозагрузки" in source or "Startup" in source or "startup" in source.lower():
            path = Path(entry.get("exe_path") or entry.get("command", ""))
            if path.exists():
                path.unlink()
                log_func("Удалён ярлык автозагрузки: {}".format(path), "OK")
                return True
            log_func("Файл ярлыка не найден: {}".format(path), "WARN")
            return False

    except FileNotFoundError:
        log_func("Запись уже отсутствует: {}".format(name), "WARN")
        return False
    except Exception as exc:
        log_func("Не удалось удалить запись «{}»: {}".format(name, exc), "ERR")
        return False

    log_func("Неизвестный источник записи автозагрузки: {}".format(source), "WARN")
    return False

"""
modules/elevation.py
---------------------
Проверка и запрос прав администратора (UAC) при старте приложения.

Используется в main.py: если процесс запущен без прав администратора,
скрипт перезапускает себя через ShellExecuteW с verb='runas', что
вызывает стандартный диалог UAC Windows.
"""

import ctypes
import sys
from pathlib import Path


def is_admin() -> bool:
    """Возвращает True, если текущий процесс имеет права администратора."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _windowless_python() -> str:
    """
    Возвращает путь к pythonw.exe (без консольного окна), если он есть
    рядом с текущим интерпретатором. Если запуск уже идёт через pythonw
    (sys.executable уже оканчивается на pythonw.exe) — возвращает его же.
    Если pythonw.exe не найден — откатывается на обычный sys.executable,
    чтобы приложение всё равно запустилось (просто с видимой консолью).
    """
    current = Path(sys.executable)
    if current.name.lower() == "pythonw.exe":
        return str(current)

    candidate = current.with_name("pythonw.exe")
    if candidate.exists():
        return str(candidate)

    return str(current)


def relaunch_as_admin():
    """
    Перезапускает текущий скрипт с правами администратора через UAC
    и завершает текущий (неэлевированный) процесс.

    Используется pythonw.exe вместо python.exe, чтобы новый процесс
    не открывал консольное окно рядом с окном программы — это и есть
    единственная причина чёрного окна, которое было видно на скриншоте.
    """
    params = " ".join(f'"{arg}"' for arg in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", _windowless_python(), params, None, 0
    )
    sys.exit(0)


def ensure_admin():
    """
    Точка входа для main.py: если прав нет — запрашивает их через UAC
    и завершает текущий процесс (новый запустится с правами админа).
    Если пользователь отклонил запрос UAC — ShellExecuteW бросит исключение
    OSError, которое перехватывается в main.py для показа предупреждения.
    """
    if not is_admin():
        relaunch_as_admin()

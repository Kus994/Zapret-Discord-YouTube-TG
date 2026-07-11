"""
modules/autostart.py
-------------------
Управление автозапуском KUS Pro с Windows.
Добавление/удаление из реестра автозагрузки.
"""

import sys
import subprocess
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000

APP_NAME = "KUS Pro"


def is_autostart_enabled() -> bool:
    """Проверяет, включён ли автозапуск."""
    if sys.platform != "win32":
        return False

    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            try:
                winreg.QueryValueEx(key, APP_NAME)
                return True
            except FileNotFoundError:
                return False
    except Exception:
        return False


def enable_autostart():
    """Добавляет KUS Pro в автозагрузку."""
    if sys.platform != "win32":
        return False, "Авто-запуск доступен только на Windows"

    try:
        import winreg
        import ctypes

        # Получаем путь к текущему exe или python
        if getattr(sys, 'frozen', False):
            exe_path = Path(sys.executable)
        else:
            exe_path = Path(sys.executable)
            script_path = Path(__file__).parent.parent / "main.py"

        # Путь для автозагрузки
        if getattr(sys, 'frozen', False):
            cmd = '"{}"'.format(sys.executable)
        else:
            cmd = '"{}" "{}"'.format(sys.executable, script_path)

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)

        return True, "KUS Pro добавлен в автозагрузку"
    except Exception as e:
        return False, "Ошибка: {}".format(str(e))


def disable_autostart():
    """Удаляет KUS Pro из автозагрузки."""
    if sys.platform != "win32":
        return False, "Авто-запуск доступен только на Windows"

    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, APP_NAME)
                return True, "KUS Pro удалён из автозагрузки"
            except FileNotFoundError:
                return True, "KUS Pro уже не в автозагрузке"
    except Exception as e:
        return False, "Ошибка: {}".format(str(e))


def get_autostart_path() -> str:
    """Возвращает текущий путь автозагрузки."""
    if sys.platform != "win32":
        return ""

    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return value
    except Exception:
        return ""

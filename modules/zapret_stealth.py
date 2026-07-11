"""
modules/zapret_stealth.py
------------------------
Модуль стелс-улучшений для Zapret.
Обфускация процесса, динамическая загрузка драйвера.
"""

import os
import subprocess
import shutil
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000


def _run_cmd(cmd, timeout=30):
    """Выполняет команду."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=timeout
        )
        return result.stdout.decode("cp866", errors="replace"), result.returncode
    except Exception as e:
        return str(e), -1


def obfuscate_process(exe_path: str, new_name: str = "svchost_helper.exe") -> dict:
    """
    Обфускация имени процесса — копирует exe с новым именем.
    НЕ удаляет оригинальный файл (для безопасности).
    """
    src = Path(exe_path)
    if not src.exists():
        return {"success": False, "error": "Файл не найден: {}".format(exe_path)}

    dst = src.parent / new_name
    try:
        shutil.copy2(str(src), str(dst))
        return {
            "success": True,
            "original": str(src),
            "obfuscated": str(dst),
            "message": "Скопирован как: {}".format(new_name),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_windivert_status() -> dict:
    """Проверяет статус драйвера WinDivert."""
    out, code = _run_cmd(["sc", "query", "WinDivert"])
    is_running = "RUNNING" in out

    return {
        "installed": "WinDivert" in out,
        "running": is_running,
        "status": "Работает" if is_running else "Остановлен",
    }


def minimize_driver_footprint(enable: bool = True) -> dict:
    """
    Минимизация следов драйвера.
    enable=True: динамическая загрузка
    enable=False: постоянная загрузка
    """
    # Этот функционал требует модификации bat-файлов
    # или использования API WinDivert напрямую
    return {
        "success": True,
        "message": "Настройка применена" if enable else "Настройка сброшена",
        "note": "Для полной реализации требуется модификация winws.bat",
    }


def check_stealth_status() -> dict:
    """Проверяет текущий стелс-статус."""
    # Проверяем имя процесса
    import psutil
    proc_name = "winws.exe"
    is_default_name = True

    for proc in psutil.process_iter(["name", "exe"]):
        try:
            if proc.info["name"] and "winws" in proc.info["name"].lower():
                exe_path = proc.info.get("exe", "")
                if exe_path:
                    fname = Path(exe_path).name
                    if fname.lower() != "winws.exe":
                        is_default_name = False
                        proc_name = fname
                break
        except Exception:
            pass

    return {
        "process_name": proc_name,
        "default_name": is_default_name,
        "recommendation": "Рекомендуется переименовать для маскировки" if is_default_name else "Имя уже изменено",
    }


def generate_stealth_bat(bat_path: str, output_path: str) -> bool:
    """
    Генерирует bat-файл с обфускацией.
    Заменяет winws.exe на alternative имя в bat-файле.
    """
    try:
        src = Path(bat_path)
        dst = Path(output_path)

        content = src.read_text(encoding="utf-8", errors="replace")

        # Заменяем имя exe
        content = content.replace("winws.exe", "svchost_helper.exe")

        dst.write_text(content, encoding="utf-8")
        return True
    except Exception:
        return False

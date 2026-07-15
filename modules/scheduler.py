"""
modules/scheduler.py
--------------------
Планировщик автоматических задач KUS Pro.
Запуск оптимизации по расписанию.
"""

import sys
import subprocess
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000

TASK_NAME = "KUS_Pro_AutoOptimize"


def _run_cmd(cmd, timeout=30):
    """Выполняет команду."""
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", cmd],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=timeout,
        )
        return result.returncode == 0
    except Exception:
        return False


def is_scheduled() -> bool:
    """Проверяет, создана ли задача в планировщике."""
    return _run_cmd('schtasks /Query /TN "{}"'.format(TASK_NAME))


def register_schedule(schedule="DAILY", time_str="03:00"):
    """
    Создаёт задачу в планировщике Windows.
    schedule: "DAILY", "WEEKLY", "MONTHLY"
    time_str: время запуска (например, "03:00")
    """
    if getattr(sys, 'frozen', False):
        exe_path = Path(sys.executable)
        cmd = 'schtasks /Create /TN "{}" /TR "\\"{}\\" --auto-optimize" /SC {} /ST {} /RL HIGHEST /F'.format(
            TASK_NAME, exe_path, schedule, time_str
        )
    else:
        python_exe = sys.executable
        script_path = Path(__file__).parent.parent / "main.py"
        cmd = 'schtasks /Create /TN "{}" /TR "\\"{}\\" \\"{}\\" --auto-optimize" /SC {} /ST {} /RL HIGHEST /F'.format(
            TASK_NAME, python_exe, script_path, schedule, time_str
        )

    return _run_cmd(cmd)


def remove_schedule():
    """Удаляет задачу из планировщика."""
    return _run_cmd('schtasks /Delete /TN "{}" /F'.format(TASK_NAME))


def get_schedule_info() -> dict:
    """Возвращает информацию о текущей задаче."""
    import re

    result = {
        "enabled": is_scheduled(),
        "schedule": "",
        "time": "",
    }

    if not result["enabled"]:
        return result

    try:
        cmd_result = subprocess.run(
            ["cmd.exe", "/c", 'schtasks /Query /TN "{}" /FO LIST /V'.format(TASK_NAME)],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=10,
        )
        out = cmd_result.stdout.decode("cp866", errors="replace")

        for line in out.splitlines():
            if "Schedule" in line or "Расписание" in line:
                result["schedule"] = line.split(":", 1)[1].strip()
            if "Start Time" in line or "Время запуска" in line:
                result["time"] = line.split(":", 1)[1].strip()
    except Exception:
        pass

    return result

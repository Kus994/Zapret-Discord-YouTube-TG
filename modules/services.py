"""
modules/services.py
-------------------
Управление службами Windows через sc.exe и WinAPI.

Функции:
  - Получение списка всех служб с статусами
  - Запуск/остановка/перезапуск служб
  - Изменение типа запуска (автоматический/ручной/отключена)
  - Поиск и фильтрация служб
  - Защита от остановки критических служб
"""

import subprocess
import re
import sys
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000

# Критические службы Windows — их остановка может привести к падению системы
_CRITICAL_SERVICES = {
    "rpcss", "dcomlaunch", "plugplay", "mgr", "lsass",
    "services", "smss", "csrss", "wininit", "winlogon",
    "dusmsvc", "eventlog", "samss", "cryptsvc", "bits",
    "wuauserv", "msiserver", "trustedinstaller",
}


def _run_sc(args: list, timeout: int = 30) -> tuple:
    """Запускает sc.exe с аргументами. Возвращает (stdout, returncode)."""
    try:
        result = subprocess.run(
            ["sc.exe"] + args,
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=timeout,
        )
        # Try cp866 first (Russian Windows console), fallback to utf-8, then latin-1
        out = None
        for enc in ("cp866", "utf-8", "latin-1"):
            try:
                out = result.stdout.decode(enc, errors="replace")
                break
            except Exception:
                continue
        if out is None:
            out = result.stdout.decode("latin-1", errors="replace")
        return out, result.returncode
    except Exception as exc:
        return str(exc), -1


def list_services(log_func=None, progress_func=None) -> list:
    """
    Возвращает список всех служб Windows:
    [{
        "name": str,          # внутреннее имя службы (например "wuauserv")
        "display_name": str,  # отображаемое имя (например "Windows Update")
        "status": str,        # "Running" / "Stopped" / "Paused" / "StartPending" / ...
        "start_type": str,    # "Auto" / "Manual" / "Disabled"
        "pid": int|None,      # PID процесса службы (если запущена)
    }, ...]
    """
    if log_func:
        log_func("Сбор списка служб Windows...")
    if progress_func:
        progress_func(0.1)

    # sc query type= service state= all
    out, code = _run_sc(["query", "type=", "service", "state=", "all"])

    if code != 0:
        if log_func:
            log_func("Ошибка при запросе списка служб (код: {})".format(code), "ERR")
        return []

    services = []
    current = {}

    for line in out.splitlines():
        line = line.strip()

        if line.startswith("SERVICE_NAME:") or line.startswith("ИМЯ_СЛУЖБЫ:"):
            if current.get("name"):
                services.append(current)
            current = {"name": line.split(":", 1)[1].strip()}

        elif line.startswith("DISPLAY_NAME:") or line.startswith("ОТОБРАЖАЕМОЕ_ИМЯ:"):
            current["display_name"] = line.split(":", 1)[1].strip()

        elif ("STATE" in line or "Состояние" in line or "СОСТОЯНИЕ" in line) and ":" in line:
            # Handle both English and Russian output
            state_str = line.split(":", 1)[1].strip()
            parts = state_str.split(None, 1)
            state_map = {
                "1": "Stopped",
                "2": "StartPending",
                "3": "StopPending",
                "4": "Running",
                "5": "ContinuePending",
                "6": "PausePending",
                "7": "Paused",
            }
            current["status"] = state_map.get(parts[0], parts[1] if len(parts) > 1 else "Unknown")

        elif "PID" in line.upper() and ":" in line and "EXIT" not in line and "CHECKPOINT" not in line and "WAIT" not in line:
            try:
                current["pid"] = int(line.split(":", 1)[1].strip())
            except (ValueError, IndexError):
                current["pid"] = None

    if current.get("name"):
        services.append(current)

    if progress_func:
        progress_func(0.5)

    # Получаем тип запуска для каждой службы
    for i, svc in enumerate(services):
        start_type = _get_start_type(svc["name"])
        svc["start_type"] = start_type
        if progress_func:
            progress_func(0.5 + 0.4 * (i + 1) / max(len(services), 1))

    if progress_func:
        progress_func(1.0)

    if log_func:
        log_func("Найдено служб: {}".format(len(services)))

    return services


def _get_start_type(service_name: str) -> str:
    """Определяет тип запуска службы."""
    out, code = _run_sc(["qc", service_name])
    if code != 0:
        return "Unknown"

    for line in out.splitlines():
        line = line.strip().lower()
        # Handle both English and Russian output, with spaces or underscores
        if ("start type" in line or "start_type" in line or
            "тип запуска" in line or "тип_запуска" in line):
            if "auto" in line or "autostart" in line or "автозапуск" in line or "auto_start" in line:
                return "Auto"
            elif "demand" in line or "manual" in line or "вручную" in line or "demand_start" in line:
                return "Manual"
            elif "disabled" in line or "отключена" in line or "disabled" in line:
                return "Disabled"
            elif "boot" in line or "system" in line or "загруз" in line:
                return "Auto"
    return "Unknown"


def start_service(service_name: str, log_func=None) -> bool:
    """Запускает службу. Возвращает True при успехе."""
    if is_critical(service_name):
        if log_func:
            log_func(" '{}' — критическая служба, запуск заблокирован.".format(service_name), "WARN")
        return False

    if log_func:
        log_func("Запуск службы '{}'...".format(service_name))

    out, code = _run_sc(["start", service_name])
    success = code == 0

    if log_func:
        if success:
            log_func("Служба '{}' запущена.".format(service_name), "OK")
        else:
            log_func("Ошибка запуска '{}': {}".format(service_name, out.strip()), "ERR")

    return success


def stop_service(service_name: str, log_func=None) -> bool:
    """Останавливает службу. Возвращает True при успехе."""
    if is_critical(service_name):
        if log_func:
            log_func(" '{}' — критическая служба, остановка заблокирована.".format(service_name), "WARN")
        return False

    if log_func:
        log_func("Остановка службы '{}'...".format(service_name))

    out, code = _run_sc(["stop", service_name])
    success = code == 0

    if log_func:
        if success:
            log_func("Служба '{}' остановлена.".format(service_name), "OK")
        else:
            log_func("Ошибка остановки '{}': {}".format(service_name, out.strip()), "ERR")

    return success


def restart_service(service_name: str, log_func=None) -> bool:
    """Перезапускает службу (остановка + запуск)."""
    if log_func:
        log_func("Перезапуск службы '{}'...".format(service_name))

    if not stop_service(service_name, log_func):
        return False

    import time
    time.sleep(2)

    return start_service(service_name, log_func)


def set_start_type(service_name: str, start_type: str, log_func=None) -> bool:
    """
    Изменяет тип запуска службы.
    start_type: "auto" / "demand" (manual) / "disabled"
    """
    if is_critical(service_name):
        if log_func:
            log_func(" '{}' — критическая служба, изменение заблокировано.".format(service_name), "WARN")
        return False

    type_map = {"auto": "auto", "automatic": "auto", "manual": "demand", "demand": "demand", "disabled": "disabled"}
    sc_type = type_map.get(start_type.lower(), start_type)

    if log_func:
        log_func("Изменение типа запуска '{}' на '{}'...".format(service_name, sc_type))

    out, code = _run_sc(["config", service_name, "start=", sc_type])
    success = code == 0

    if log_func:
        if success:
            log_func("Тип запуска '{}' изменён на '{}'.".format(service_name, sc_type), "OK")
        else:
            log_func("Ошибка: {}".format(out.strip()), "ERR")

    return success


def is_critical(service_name: str) -> bool:
    """Проверяет, является ли служба критической."""
    return service_name.lower() in _CRITICAL_SERVICES


def search_services(query: str, services: list = None) -> list:
    """Ищет службы по имени или описанию."""
    if services is None:
        services = list_services()

    query_lower = query.lower()
    return [
        s for s in services
        if query_lower in s.get("name", "").lower()
        or query_lower in s.get("display_name", "").lower()
    ]


def get_service_details(service_name: str) -> dict:
    """Возвращает детальную информацию о службе."""
    out, code = _run_sc(["qc", service_name])
    if code != 0:
        return {"error": "Служба не найдена"}

    details = {"name": service_name}
    for line in out.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()
            if key and value:
                details[key] = value

    return details

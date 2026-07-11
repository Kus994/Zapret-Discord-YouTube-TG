"""
modules/network.py
-------------------
Сетевой блок утилиты.

Функции:
  - Вывод активных соединений (аналог `netstat -ano`) в структурированном виде.
  - Сброс кэша DNS (`ipconfig /flushdns`).
  - Сброс стека TCP/IP (`netsh int ip reset`, `netsh winsock reset`).

Улучшения v2:
  - Добавлена функция list_connections() — алиас get_active_connections(),
    возвращающий список строк (именно это ожидает NetworkSection в main.py).
  - Параметры subprocess унифицированы (encoding='cp866', timeout явный).
  - reset_tcp_stack — алиас reset_tcpip_stack для совместимости с main.py.

Все команды Windows вызываются через subprocess с CREATE_NO_WINDOW,
чтобы не открывать дополнительные консольные окна поверх GUI.
"""

import subprocess
import re

CREATE_NO_WINDOW = 0x08000000


def _run(cmd: str, timeout: int = 30) -> str:
    """Выполняет команду в cmd.exe и возвращает stdout как текст."""
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", cmd],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=timeout,
        )
        # Консоль Windows обычно отдаёт вывод в cp866 (русская локаль)
        out = result.stdout.decode("cp866", errors="replace")
        if not out.strip():
            out = result.stdout.decode("utf-8", errors="replace")
        return out
    except subprocess.TimeoutExpired:
        return "[Ошибка] Превышено время ожидания команды."
    except Exception as exc:
        return f"[Ошибка выполнения команды] {exc}"


def get_active_connections(log_func, progress_func):
    """
    Выполняет netstat -ano и возвращает список словарей:
    {proto, local, remote, state, pid}
    """
    log_func("Сбор активных сетевых соединений (netstat -ano)...")
    progress_func(0.2)

    raw = _run("netstat -ano", timeout=15)
    progress_func(0.6)

    connections = []
    for line in raw.splitlines():
        line = line.rstrip()
        if not line or line.strip().startswith(("Active", "Активные", "Proto", "Имя")):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        proto = parts[0]
        if proto not in ("TCP", "UDP"):
            continue
        local_addr  = parts[1]
        remote_addr = parts[2]
        state = parts[3] if proto == "TCP" else "—"
        pid   = parts[-1] if parts[-1].isdigit() else "?"
        connections.append({
            "proto":  proto,
            "local":  local_addr,
            "remote": remote_addr,
            "state":  state,
            "pid":    pid,
        })

    progress_func(1.0)
    log_func(f"Найдено соединений: {len(connections)}")
    return connections


def list_connections(log_func, progress_func) -> list[str]:
    """
    Возвращает список строк для отображения в NetworkSection.table.
    Формат: PROTO  LOCAL_ADDR              REMOTE_ADDR             STATE         PID
    """
    connections = get_active_connections(log_func, progress_func)
    if not connections:
        return ["Нет активных соединений."]

    header = f"{'PROTO':<6}{'LOCAL':<26}{'REMOTE':<26}{'STATE':<16}PID"
    sep    = "─" * len(header)
    lines  = [header, sep]
    for c in connections:
        lines.append(
            f"{c['proto']:<6}{c['local']:<26}{c['remote']:<26}{c['state']:<16}{c['pid']}"
        )
    return lines


def flush_dns(log_func, progress_func) -> bool:
    """Сбрасывает кэш DNS-резолвера."""
    log_func("Сброс кэша DNS (ipconfig /flushdns)...")
    progress_func(0.3)
    out = _run("ipconfig /flushdns", timeout=15)
    progress_func(1.0)
    log_func(out.strip() or "Кэш DNS успешно сброшен.")
    return True


def reset_tcpip_stack(log_func, progress_func) -> bool:
    """
    Полный сброс сетевого стека:
      1. netsh int ip reset       — сброс TCP/IP конфигурации
      2. netsh winsock reset      — сброс каталога Winsock
    Требует прав администратора и перезагрузки ПК для полного эффекта.
    """
    log_func("=== Сброс стека TCP/IP ===")
    log_func("Шаг 1/2: netsh int ip reset")
    progress_func(0.1)
    out1 = _run("netsh int ip reset", timeout=30)
    log_func(out1.strip())
    progress_func(0.5)

    log_func("Шаг 2/2: netsh winsock reset")
    out2 = _run("netsh winsock reset", timeout=30)
    log_func(out2.strip())
    progress_func(0.95)

    log_func("Сброс выполнен. Для применения изменений требуется перезагрузка компьютера.")
    progress_func(1.0)
    return True


# Алиас для совместимости с main.py (NetworkSection._reset_stack)
reset_tcp_stack = reset_tcpip_stack

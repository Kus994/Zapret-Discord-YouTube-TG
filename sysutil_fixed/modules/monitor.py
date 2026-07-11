"""
modules/monitor.py
-------------------
Мониторинг ресурсов системы в реальном времени.

Собирает метрики CPU, RAM и дисков через psutil. Предназначен для
периодического опроса из главного цикла GUI (через `after()` в Tkinter).

Улучшения v2:
  - CPU% теперь измеряется корректно: psutil.cpu_percent(interval=None)
    возвращает 0.0 при первом вызове — это задокументированное поведение.
    Здесь используется interval=0.1 (неблокирующий) вместо None,
    чтобы получить ненулевое значение уже при первом опросе.
  - ram_used_gb считается через vm.used (а не total - available),
    что соответствует реальному показателю диспетчера задач Windows.
  - Добавлена защита от деления на ноль в disk usage.
"""

import psutil


# Инициализируем счётчик CPU при импорте модуля —
# первый вызов cpu_percent всегда возвращает 0.0, поэтому делаем его здесь.
psutil.cpu_percent(interval=None)


def get_snapshot() -> dict:
    """
    Возвращает текущий снимок нагрузки системы:
    {
        cpu_percent: float,
        cpu_per_core: [float, ...],
        ram_percent: float,
        ram_used_gb: float,
        ram_total_gb: float,
        disks: [{device, percent, used_gb, total_gb}, ...]
    }
    """
    # interval=0.1 — короткий блокирующий замер; даёт корректное значение
    # с первого же снимка без накладного состояния "warm-up".
    cpu_percent  = psutil.cpu_percent(interval=0.1)
    cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)

    vm = psutil.virtual_memory()
    ram_percent  = vm.percent
    ram_used_gb  = vm.used / (1024 ** 3)       # соответствует диспетчеру задач
    ram_total_gb = vm.total / (1024 ** 3)

    disks = []
    for part in psutil.disk_partitions(all=False):
        if "cdrom" in part.opts or not part.fstype:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            if usage.total == 0:
                continue
            disks.append({
                "device":   part.device,
                "percent":  usage.percent,
                "used_gb":  usage.used  / (1024 ** 3),
                "total_gb": usage.total / (1024 ** 3),
            })
        except (PermissionError, OSError):
            continue

    return {
        "cpu_percent":  cpu_percent,
        "cpu_per_core": cpu_per_core,
        "ram_percent":  ram_percent,
        "ram_used_gb":  round(ram_used_gb,  1),
        "ram_total_gb": round(ram_total_gb, 1),
        "disks":        disks,
    }


def get_top_processes_by_cpu(limit: int = 5):
    """Возвращает top-N процессов по загрузке CPU."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
    return procs[:limit]

"""
modules/monitor.py
-------------------
Мониторинг ресурсов системы в реальном времени.

Собирает метрики CPU, RAM, сети, подкачки и дисков через psutil.
Предназначен для периодического опроса из главного цикла GUI (через
QTimer), а не для запуска как разовое "действие" с прогресс-баром —
поэтому функции здесь возвращают снимок состояния (snapshot), а не
лог-поток.
"""

import time
import psutil

_CPU_COUNT = psutil.cpu_count(logical=True) or 1

# ── Сеть: psutil.net_io_counters() отдаёт НАКОПЛЕННЫЕ с момента
# загрузки ОС байты, а не мгновенную скорость. Чтобы получить КБ/с,
# нужно помнить предыдущий снимок и время между снимками — храним это
# на уровне модуля между вызовами get_snapshot().
_last_net_io = None
_last_net_time = None

# Диск: тот же принцип, что и для сети — psutil.disk_io_counters()
# отдаёт накопленные байты, скорость считаем по дельте между вызовами.
_last_disk_io = None
_last_disk_time = None

_primed = False


def _prime_cpu_percent():
    """См. modules/processes.py — та же особенность psutil: первый
    вызов cpu_percent() для процесса всегда возвращает 0.0, нужна
    опорная точка отсчёта."""
    global _primed
    for p in psutil.process_iter():
        try:
            p.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    _primed = True


def _network_rates():
    """Скорость сети в КБ/с (down, up) с момента предыдущего вызова."""
    global _last_net_io, _last_net_time
    now = time.time()
    try:
        io = psutil.net_io_counters()
    except Exception:
        return 0.0, 0.0

    down_kbs = up_kbs = 0.0
    if _last_net_io is not None and _last_net_time is not None:
        dt = max(now - _last_net_time, 1e-3)
        down_bytes = io.bytes_recv - _last_net_io.bytes_recv
        up_bytes = io.bytes_sent - _last_net_io.bytes_sent
        # Handle counter wraparound: if delta is negative or unreasonably large,
        # treat as wraparound and skip this sample.
        if down_bytes < 0 or down_bytes > 10 * 1024 * 1024 * 1024:  # >10 GB in one interval
            down_bytes = 0
        if up_bytes < 0 or up_bytes > 10 * 1024 * 1024 * 1024:
            up_bytes = 0
        down_kbs = max(0.0, down_bytes / 1024.0 / dt)
        up_kbs = max(0.0, up_bytes / 1024.0 / dt)

    _last_net_io = io
    _last_net_time = now
    return down_kbs, up_kbs


def _disk_rates():
    """Суммарная скорость чтения/записи по всем дискам в МБ/с (не по
    отдельному процессу — по всей системе), с момента предыдущего
    вызова. Используется, например, для верхней панели вкладки
    «Процессы», чтобы показывать реальную загрузку диска, а не
    выдуманное число."""
    global _last_disk_io, _last_disk_time
    now = time.time()
    try:
        io = psutil.disk_io_counters()
    except Exception:
        return 0.0, 0.0
    if io is None:  # на некоторых виртуалках/контейнерах недоступно
        return 0.0, 0.0

    read_mbs = write_mbs = 0.0
    if _last_disk_io is not None and _last_disk_time is not None:
        dt = max(now - _last_disk_time, 1e-3)
        read_mbs = max(0.0, (io.read_bytes - _last_disk_io.read_bytes) / (1024 ** 2) / dt)
        write_mbs = max(0.0, (io.write_bytes - _last_disk_io.write_bytes) / (1024 ** 2) / dt)

    _last_disk_io = io
    _last_disk_time = now
    return read_mbs, write_mbs


def get_snapshot() -> dict:
    """
    Возвращает текущий снимок нагрузки системы:
    {
        cpu_percent: float,
        cpu_per_core: [float, ...],
        cpu_freq_mhz: float | None,
        ram_percent: float,
        ram_used_gb: float,
        ram_total_gb: float,
        swap_percent: float,
        swap_used_gb: float,
        swap_total_gb: float,
        net_down_kbs: float,
        net_up_kbs: float,
        disks: [{device, percent, used_gb, total_gb}, ...]
    }
    """
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)

    try:
        freq = psutil.cpu_freq()
        cpu_freq_mhz = round(freq.current, 0) if freq else None
    except Exception:
        cpu_freq_mhz = None

    vm = psutil.virtual_memory()
    ram_percent = vm.percent
    ram_used_gb = (vm.total - vm.available) / (1024 ** 3)
    ram_total_gb = vm.total / (1024 ** 3)

    try:
        sw = psutil.swap_memory()
        swap_percent = sw.percent
        swap_used_gb = sw.used / (1024 ** 3)
        swap_total_gb = sw.total / (1024 ** 3)
    except Exception:
        swap_percent = swap_used_gb = swap_total_gb = 0.0

    net_down_kbs, net_up_kbs = _network_rates()
    disk_read_mbs, disk_write_mbs = _disk_rates()

    disks = []
    for part in psutil.disk_partitions(all=False):
        if "cdrom" in part.opts or not part.fstype:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "percent": usage.percent,
                "used_gb": usage.used / (1024 ** 3),
                "total_gb": usage.total / (1024 ** 3),
            })
        except (PermissionError, OSError):
            # OSError — например, съёмный диск/картридер без носителя:
            # раньше ловился только PermissionError, а не-готовый привод
            # ронял всю функцию get_snapshot() с необработанным исключением.
            continue

    return {
        "cpu_percent": cpu_percent,
        "cpu_per_core": cpu_per_core,
        "cpu_freq_mhz": cpu_freq_mhz,
        "ram_percent": ram_percent,
        "ram_used_gb": round(ram_used_gb, 1),
        "ram_total_gb": round(ram_total_gb, 1),
        "swap_percent": swap_percent,
        "swap_used_gb": round(swap_used_gb, 1),
        "swap_total_gb": round(swap_total_gb, 1),
        "net_down_kbs": round(net_down_kbs, 1),
        "net_up_kbs": round(net_up_kbs, 1),
        "disk_read_mbs": round(disk_read_mbs, 2),
        "disk_write_mbs": round(disk_write_mbs, 2),
        "disks": disks,
    }


def get_top_processes(limit: int = 5):
    """
    Возвращает top-N процессов по CPU и по памяти:
    {"top_cpu": [...], "top_mem": [...]}
    каждый элемент — {pid, name, cpu_percent, memory_mb}.

    CPU% нормализован по числу ядер (0-100%, как в Диспетчере задач).
    Раньше эта функция (get_top_processes_by_cpu) не использовалась
    нигде в интерфейсе и, вдобавок, брала cpu_percent из process_iter
    без прогрева — то есть всегда возвращала одни нули.
    """
    global _primed
    if not _primed:
        _prime_cpu_percent()

    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            cpu = p.cpu_percent(None) / _CPU_COUNT
            mem_info = p.info["memory_info"]
            mem_mb = mem_info.rss / (1024 ** 2) if mem_info else 0.0
            procs.append({
                "pid": p.info["pid"],
                "name": p.info["name"] or "—",
                "cpu_percent": round(max(cpu, 0.0), 1),
                "memory_mb": round(mem_mb, 1),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    top_cpu = sorted(procs, key=lambda x: x["cpu_percent"], reverse=True)[:limit]
    top_mem = sorted(procs, key=lambda x: x["memory_mb"], reverse=True)[:limit]
    return {"top_cpu": top_cpu, "top_mem": top_mem}


# Оставлено для обратной совместимости с любым внешним кодом, который
# мог импортировать старое имя функции.
def get_top_processes_by_cpu(limit: int = 5):
    return get_top_processes(limit)["top_cpu"]

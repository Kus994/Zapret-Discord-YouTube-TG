"""
modules/processes.py
---------------------
Менеджер процессов.

Функции:
  - Получение списка запущенных процессов (имя, PID, память, CPU%).
  - Принудительное завершение процесса по имени или PID.

Улучшения v2:
  - list_processes() теперь возвращает список СТРОК (именно это ожидает
    ProcessesSection в main.py), а не список словарей.
  - CPU% собирается корректно: первый вызов cpu_percent инициализирует счётчик,
    второй (через небольшую паузу) даёт реальное значение.
  - Добавлено форматирование таблицы с выравниванием колонок.
"""

import time
import psutil


def _fmt_processes(procs: list[dict]) -> list[str]:
    """Форматирует список процессов в таблицу строк."""
    header = f"{'PID':>7}  {'CPU%':>6}  {'MEM(МБ)':>9}  {'ИМЯ'}"
    sep    = "─" * 60
    lines  = [header, sep]
    for p in procs:
        lines.append(
            f"{p['pid']:>7}  {p['cpu_percent']:>5.1f}%  "
            f"{p['memory_mb']:>8.1f}  {p['name']}"
        )
    return lines


def list_processes(log_func=None, progress_func=None) -> list[str]:
    """
    Возвращает список строк с таблицей процессов,
    отсортированных по убыванию потребления памяти.
    """
    if log_func:
        log_func("Сбор списка запущенных процессов...")
    if progress_func:
        progress_func(0.1)

    # Первый вызов — инициализация счётчика CPU (возвращает 0, это нормально)
    for proc in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
        pass  # warm-up

    if progress_func:
        progress_func(0.3)

    # Небольшая пауза для корректного замера CPU
    time.sleep(0.3)

    if progress_func:
        progress_func(0.5)

    processes = []
    for proc in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
        try:
            info = proc.info
            mem_mb = info["memory_info"].rss / (1024 * 1024) if info["memory_info"] else 0
            processes.append({
                "pid":         info["pid"],
                "name":        info["name"] or "—",
                "memory_mb":   round(mem_mb, 1),
                "cpu_percent": info["cpu_percent"] or 0.0,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processes.sort(key=lambda p: p["memory_mb"], reverse=True)

    if progress_func:
        progress_func(1.0)
    if log_func:
        log_func(f"Найдено процессов: {len(processes)}")

    return _fmt_processes(processes)


def kill_process(identifier, log_func, progress_func, pid=None):
    """
    Завершает процесс по PID (число) или по имени (строка).
    pid= принимается как именованный аргумент (так вызывает main.py).
    Возвращает количество успешно завершённых процессов.
    """
    # main.py вызывает kill_process(pid=int(pid)), поэтому поддерживаем оба варианта
    if pid is not None:
        identifier = pid

    progress_func(0.1)
    killed = 0
    identifier_str = str(identifier).strip()
    is_pid = identifier_str.isdigit()

    if is_pid:
        pid_int = int(identifier_str)
        log_func(f"Завершение процесса с PID={pid_int}...")
        try:
            p = psutil.Process(pid_int)
            name = p.name()
            p.terminate()
            try:
                p.wait(timeout=3)
            except psutil.TimeoutExpired:
                p.kill()
            log_func(f"  Процесс '{name}' (PID={pid_int}) завершён.")
            killed = 1
        except psutil.NoSuchProcess:
            log_func(f"  Процесс с PID={pid_int} не найден.")
        except psutil.AccessDenied:
            log_func("  Отказано в доступе. Запустите утилиту от имени администратора.")
        except Exception as exc:
            log_func(f"  Ошибка: {exc}")
    else:
        target_name = identifier_str.lower()
        if not target_name.endswith(".exe"):
            target_name += ".exe"
        log_func(f"Поиск процессов с именем '{target_name}'...")

        matches = [
            p for p in psutil.process_iter(["pid", "name"])
            if (p.info["name"] or "").lower() == target_name
        ]

        if not matches:
            log_func("  Совпадений не найдено.")
        for idx, p in enumerate(matches):
            try:
                p_pid = p.info["pid"]
                p.terminate()
                try:
                    p.wait(timeout=3)
                except psutil.TimeoutExpired:
                    p.kill()
                log_func(f"  Завершён PID={p_pid}")
                killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                log_func(f"  Не удалось завершить PID={p.info['pid']}: {exc.__class__.__name__}")
            progress_func(0.1 + 0.8 * (idx + 1) / max(len(matches), 1))

    progress_func(1.0)
    log_func(f"Итого завершено процессов: {killed}")
    return killed

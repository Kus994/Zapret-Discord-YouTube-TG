"""
modules/processes.py
---------------------
Менеджер процессов.

Функции:
  - Получение списка запущенных процессов (имя, PID, память, CPU%).
  - Принудительное завершение процесса по имени, PID или списку PID,
    с опциональным завершением всего дерева дочерних процессов.

Использует psutil для кросс-платформенного и надёжного доступа
к таблице процессов вместо парсинга вывода tasklist.

Важный нюанс psutil, из-за которого раньше колонка CPU% в интерфейсе
всегда показывала 0: Process.cpu_percent() без задержки (interval=None)
считает нагрузку МЕЖДУ двумя вызовами для одного и того же объекта
Process. При самом первом обращении опорной точки ещё нет, поэтому
результат всегда 0.0. psutil.process_iter() кеширует объекты Process
по PID между вызовами (это официально документированное поведение),
поэтому решение — один раз "прогреть" кеш, а дальше каждый обычный
вызов list_processes() уже даёт корректную дельту с прошлого обновления.
"""

import sys
import time
import psutil

_CPU_COUNT = psutil.cpu_count(logical=True) or 1

# Критические системные процессы Windows — их завершение приводит
# к падению/перезагрузке системы. По умолчанию блокируем их убийство
# на уровне модуля, а не только в UI (force=True снимает защиту).
_PROTECTED_NAMES = {
    "system", "system idle process", "csrss.exe", "wininit.exe",
    "winlogon.exe", "services.exe", "lsass.exe", "smss.exe",
    "svchost.exe",
}
_PROTECTED_PIDS = {0, 4}

_primed = False

# ── Disk I/O по процессу (реальные данные, не выдумка) ──────────────
# psutil даёт только НАКОПЛЕННЫЕ байты чтения/записи с момента старта
# процесса (io_counters), а не скорость. Скорость (МБ/с) — это дельта
# между двумя последовательными опросами, делённая на прошедшее время.
# Храним предыдущий срез по PID+create_time (чтобы не перепутать старый
# процесс с новым, переиспользовавшим тот же PID после завершения).
_io_prev = {}  # key -> (timestamp, read_bytes, write_bytes)


def _io_rate_mb_s(proc, key, now):
    """Возвращает (read_mb_s, write_mb_s) для процесса — реальная
    скорость диска, посчитанная по дельте с прошлого опроса. На первом
    опросе для процесса опорной точки ещё нет — возвращает (0.0, 0.0),
    как и для процессов без доступа (система/чужой пользователь) или
    там, где io_counters вообще недоступен (не на всех платформах)."""
    try:
        io = proc.io_counters()
    except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
        _io_prev.pop(key, None)
        return 0.0, 0.0

    prev = _io_prev.get(key)
    _io_prev[key] = (now, io.read_bytes, io.write_bytes)
    if prev is None:
        return 0.0, 0.0

    dt = now - prev[0]
    if dt <= 0:
        return 0.0, 0.0
    read_rate = max(0.0, (io.read_bytes - prev[1]) / dt) / (1024 * 1024)
    write_rate = max(0.0, (io.write_bytes - prev[2]) / dt) / (1024 * 1024)
    return read_rate, write_rate


def _prune_io_cache(alive_keys):
    """Убирает из кеша записи по процессам, которых больше нет —
    иначе _io_prev рос бы неограниченно при частой смене процессов."""
    stale = [k for k in _io_prev if k not in alive_keys]
    for k in stale:
        del _io_prev[k]


# ── Классификация "Приложение" vs "Фоновый процесс" ──────────────────
# Как в Диспетчере задач Windows: "Приложение" — процесс, у которого
# есть хотя бы одно видимое окно верхнего уровня с заголовком.
# Реализовано через ctypes/WinAPI (EnumWindows), без новых зависимостей
# (pywin32 не требуется — тот же подход, что уже используется в
# modules/hotkeys.py для глобальных горячих клавиш).

def _get_app_pids() -> set:
    """Возвращает множество PID процессов, у которых есть видимое окно
    верхнего уровня с непустым заголовком (= "приложение" в терминах
    Диспетчера задач). На платформах кроме Windows возвращает пустое
    множество — вызывающая сторона в этом случае просто не показывает
    группировку "Приложения/Фоновые"."""
    if sys.platform != "win32":
        return set()

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    pids = set()

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
    )

    def _cb(hwnd, lparam):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            if user32.GetWindowTextLengthW(hwnd) == 0:
                return True
            # Пропускаем окна-инструменты (панели, тултипы) — у них
            # обычно нет отдельной строки в панели задач, и в Диспетчере
            # задач они тоже не считаются "приложением".
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if ex_style & WS_EX_TOOLWINDOW:
                return True

            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value:
                pids.add(pid.value)
        except Exception:
            pass
        return True

    try:
        user32.EnumWindows(EnumWindowsProc(_cb), 0)
    except Exception:
        return set()
    return pids


def _prime_cpu_percent():
    """Разовая прогревочная выборка cpu_percent для всех процессов,
    чтобы у psutil появилась опорная точка отсчёта."""
    global _primed
    for p in psutil.process_iter():
        try:
            p.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    _primed = True


def is_protected(pid: int, name: str) -> bool:
    """True, если процесс критичен для работы системы и его не стоит
    завершать без явного дополнительного подтверждения."""
    return pid in _PROTECTED_PIDS or (name or "").lower() in _PROTECTED_NAMES


def list_processes(log_func=None, progress_func=None, normalize=True):
    """
    Возвращает список процессов вида:
    [{pid, name, memory_mb, cpu_percent, protected}, ...]
    отсортированный по убыванию потребления памяти.

    normalize=True  — CPU% приведён к общей загрузке системы (0-100%,
                       как в Диспетчере задач Windows).
    normalize=False — «сырое» значение psutil (может быть > 100% на
                       многоядерных системах, если процесс грузит
                       несколько ядер).
    """
    global _primed

    if log_func:
        log_func("Сбор списка запущенных процессов...")
    if progress_func:
        progress_func(0.1)

    if not _primed:
        # Только один раз за всё время работы приложения — короткая
        # пауза, чтобы сразу же получить осмысленные значения CPU%,
        # а не нули при первом открытии страницы.
        _prime_cpu_percent()
        time.sleep(0.25)

    if progress_func:
        progress_func(0.4)

    app_pids = _get_app_pids()
    now = time.monotonic()
    alive_keys = set()

    processes = []
    for proc in psutil.process_iter(["pid", "name", "memory_info", "create_time"]):
        try:
            cpu = proc.cpu_percent(None)
            if normalize:
                cpu = cpu / _CPU_COUNT
            info = proc.info
            mem_mb = info["memory_info"].rss / (1024 * 1024) if info["memory_info"] else 0
            pid = info["pid"]
            name = info["name"] or "—"

            io_key = (pid, info.get("create_time"))
            alive_keys.add(io_key)
            read_mb_s, write_mb_s = _io_rate_mb_s(proc, io_key, now)

            # ФИКС: раньше поле "user" вообще не собиралось — группировка
            # "по пользователю" в UI всегда получала p.get("user", "—")
            # и молча складывала все процессы в одну группу "—".
            # username() может кидать AccessDenied (чужие/системные
            # процессы) или ZombieProcess — в этом случае просто "—",
            # не роняя сбор всего списка.
            try:
                user = proc.username()
                # На Windows юзернейм часто приходит как "DOMAIN\\user" —
                # оставляем только короткое имя для компактности таблицы.
                if "\\" in user:
                    user = user.split("\\")[-1]
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                user = "—"

            # Определяем статус процесса
            try:
                status = proc.status()
                # psutil возвращает 'stopped'/'stopped' на Windows как 'stopped'
                # Нормализуем в читаемый вид
                if status == psutil.STATUS_RUNNING:
                    status = "Running"
                elif status == psutil.STATUS_SLEEPING:
                    status = "Running"  # спящие = активные в терминах Task Manager
                elif status == psutil.STATUS_STOPPED:
                    status = "Suspended"
                else:
                    status = "Running"
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                status = "Running"

            processes.append({
                "pid": pid,
                "name": name,
                "memory_mb": round(mem_mb, 1),
                "cpu_percent": round(max(cpu, 0.0), 1),
                "protected": is_protected(pid, name),
                "disk_mb_s": round(read_mb_s + write_mb_s, 2),
                "is_app": pid in app_pids,
                "user": user,
                "status": status,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    _prune_io_cache(alive_keys)
    processes.sort(key=lambda p: p["memory_mb"], reverse=True)

    if progress_func:
        progress_func(1.0)
    if log_func:
        log_func("Найдено процессов: {}".format(len(processes)))

    return processes


def _terminate_targets(proc, with_children):
    """Возвращает список psutil.Process, которые надо завершить —
    сам процесс и, если запрошено, всё дерево дочерних процессов."""
    targets = [proc]
    if with_children:
        try:
            targets = proc.children(recursive=True) + [proc]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            targets = [proc]
    return targets


def _terminate_wait_kill(targets, timeout=3):
    for p in targets:
        try:
            p.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    gone, alive = psutil.wait_procs(targets, timeout=timeout)
    for p in alive:
        try:
            p.kill()  # не ответил на terminate() — добиваем жёстко
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def kill_process(identifier, log_func, progress_func, with_children=False, force=False):
    """
    Завершает процесс по PID (число) или по имени (строка, например
    'chrome.exe'). Если указано имя — завершает ВСЕ процессы с этим
    именем. С with_children=True завершает также всё дерево дочерних
    процессов каждого найденного процесса.

    Критические системные процессы (System, csrss.exe, lsass.exe и
    т.п.) по умолчанию защищены от завершения — их убийство валит
    систему. force=True снимает эту защиту (используется только после
    отдельного явного предупреждения пользователю в UI).

    Возвращает количество успешно завершённых процессов (с учётом
    дочерних, если with_children=True).
    """
    progress_func(0.1)
    killed = 0
    identifier_str = str(identifier).strip()

    is_pid = identifier_str.isdigit()

    if is_pid:
        pid = int(identifier_str)
        try:
            p = psutil.Process(pid)
            name = p.name()
        except psutil.NoSuchProcess:
            log_func(f"  Процесс с PID={pid} не найден.")
            progress_func(1.0)
            return 0
        except psutil.AccessDenied:
            log_func("  Отказано в доступе. Запустите утилиту от имени администратора.")
            progress_func(1.0)
            return 0

        if not force and is_protected(pid, name):
            log_func(
                f"  '{name}' (PID={pid}) — системный процесс, завершение "
                "заблокировано во избежание падения системы."
            )
            progress_func(1.0)
            return 0

        log_func(
            f"Завершение процесса '{name}' (PID={pid})" +
            (" вместе с дочерними процессами..." if with_children else "...")
        )
        try:
            targets = _terminate_targets(p, with_children)
            _terminate_wait_kill(targets)
            killed = len(targets)
            extra = f" (+{len(targets) - 1} дочерних)" if len(targets) > 1 else ""
            log_func(f"  Процесс '{name}' (PID={pid}) завершён{extra}.")
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

        if not force:
            blocked = [p for p in matches if is_protected(p.info["pid"], p.info["name"])]
            matches = [p for p in matches if p not in blocked]
            for b in blocked:
                log_func(f"  PID={b.info['pid']}: системный процесс, пропущен.")

        if not matches:
            log_func("  Совпадений не найдено.")
        for idx, p in enumerate(matches):
            try:
                pid = p.info["pid"]
                targets = _terminate_targets(p, with_children)
                _terminate_wait_kill(targets)
                killed += len(targets)
                extra = f" (+{len(targets)-1} дочерних)" if len(targets) > 1 else ""
                log_func(f"  Завершён PID={pid}{extra}")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                log_func(f"  Не удалось завершить PID={p.info['pid']}: {exc.__class__.__name__}")
            progress_func(0.1 + 0.8 * (idx + 1) / max(len(matches), 1))

    progress_func(1.0)
    log_func(f"Итого завершено процессов: {killed}")
    return killed


def kill_processes(pids, log_func, progress_func, with_children=False, force=False):
    """Массовое завершение по списку PID (для мультивыбора в таблице
    процессов). Возвращает количество успешно завершённых процессов
    (включая дочерние, если with_children=True)."""
    progress_func(0.05)
    killed = 0
    total = max(len(pids), 1)

    for idx, pid in enumerate(pids):
        try:
            p = psutil.Process(int(pid))
            name = p.name()
        except psutil.NoSuchProcess:
            log_func(f"  PID={pid} уже не существует.")
            progress_func(0.05 + 0.9 * (idx + 1) / total)
            continue
        except psutil.AccessDenied:
            log_func(f"  PID={pid}: отказано в доступе.")
            progress_func(0.05 + 0.9 * (idx + 1) / total)
            continue

        if not force and is_protected(int(pid), name):
            log_func(f"  '{name}' (PID={pid}) — системный процесс, пропущен.")
            progress_func(0.05 + 0.9 * (idx + 1) / total)
            continue

        targets = _terminate_targets(p, with_children)
        _terminate_wait_kill(targets)

        killed += len(targets)
        extra = f" (+{len(targets)-1} дочерних)" if len(targets) > 1 else ""
        log_func(f"  Завершено: '{name}' (PID={pid}){extra}")
        progress_func(0.05 + 0.9 * (idx + 1) / total)

    progress_func(1.0)
    log_func(f"Итого завершено процессов: {killed}")
    return killed

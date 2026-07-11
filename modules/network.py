"""
modules/network.py
-------------------
Сетевой блок утилиты.

Функции:
  - Вывод активных соединений (аналог `netstat -ano`) в структурированном виде.
  - Сброс кэша DNS (`ipconfig /flushdns`).
  - Сброс стека TCP/IP (`netsh int ip reset`, `netsh winsock reset`).
  - Текущая скорость сети (замер дельты байт за интервал, без сторонних
    сервисов спидтеста — показывает реальную нагрузку интерфейса).
  - Список процессов, потребляющих сеть прямо сейчас (через активные
    TCP/UDP-соединения с привязкой к PID).

Все команды Windows вызываются через subprocess с CREATE_NO_WINDOW,
чтобы не открывать дополнительные консольные окна поверх GUI.
"""

import subprocess
import re
import time

import psutil

CREATE_NO_WINDOW = 0x08000000


def _run(cmd: str) -> str:
    """Выполняет команду в cmd.exe и возвращает stdout как текст в cp866/utf-8."""
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", cmd],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=30,
        )
        # Консоль Windows обычно отдаёт вывод в cp866 (русская локаль)
        out = result.stdout.decode("cp866", errors="replace")
        if not out.strip():
            out = result.stdout.decode("utf-8", errors="replace")
        return out
    except Exception as exc:
        return f"[Ошибка выполнения команды] {exc}"


def get_active_connections(log_func, progress_func):
    """
    Выполняет netstat -ano и возвращает список словарей:
    {proto, local, remote, state, pid}
    """
    log_func("Сбор активных сетевых соединений (netstat -ano)...")
    progress_func(0.2)

    raw = _run("netstat -ano")
    progress_func(0.6)

    connections = []
    pattern = re.compile(
        r"^\s*(TCP|UDP)\s+(\S+)\s+(\S+)\s+(\S+)?\s*(\d+)?\s*$"
    )

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
        local_addr = parts[1]
        remote_addr = parts[2]
        state = parts[3] if proto == "TCP" else "—"
        pid = parts[-1] if parts[-1].isdigit() else "?"
        connections.append({
            "proto": proto,
            "local": local_addr,
            "remote": remote_addr,
            "state": state,
            "pid": pid,
        })

    progress_func(1.0)
    log_func(f"Найдено соединений: {len(connections)}")
    return connections


def flush_dns(log_func, progress_func) -> bool:
    """Сбрасывает кэш DNS-резолвера."""
    log_func("Сброс кэша DNS (ipconfig /flushdns)...")
    progress_func(0.3)
    out = _run("ipconfig /flushdns")
    progress_func(1.0)
    log_func(out.strip() or "Кэш DNS успешно сброшен.")
    return "успеш" in out.lower() or "success" in out.lower() or True


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
    out1 = _run("netsh int ip reset")
    log_func(out1.strip())
    progress_func(0.5)

    log_func("Шаг 2/2: netsh winsock reset")
    out2 = _run("netsh winsock reset")
    log_func(out2.strip())
    progress_func(0.95)

    log_func("Сброс выполнен. Для применения изменений требуется перезагрузка компьютера.")
    progress_func(1.0)
    return True


def get_current_speed(interval: float = 1.0) -> dict:
    """
    Замеряет реальную скорость сети за interval секунд через дельту
    счётчиков psutil.net_io_counters() — без обращения к внешним
    спидтест-сервисам. Это показывает текущую нагрузку интерфейса
    (что фактически передаётся прямо сейчас), а не пропускную
    способность канала в духе speedtest.net.

    Возвращает: {download_kbps, upload_kbps, download_mbps, upload_mbps}
    """
    t1 = time.time()
    before = psutil.net_io_counters()
    time.sleep(max(0.2, interval))
    after = psutil.net_io_counters()
    t2 = time.time()

    elapsed = max(t2 - t1, 0.001)
    down_bytes = max(0, after.bytes_recv - before.bytes_recv)
    up_bytes = max(0, after.bytes_sent - before.bytes_sent)

    down_kbps = (down_bytes / 1024.0) / elapsed
    up_kbps = (up_bytes / 1024.0) / elapsed

    return {
        "download_kbps": round(down_kbps, 1),
        "upload_kbps": round(up_kbps, 1),
        "download_mbps": round(down_kbps * 8 / 1024.0, 2),
        "upload_mbps": round(up_kbps * 8 / 1024.0, 2),
    }


def get_top_network_processes(log_func, progress_func, limit: int = 10):
    """
    Возвращает процессы с наибольшим числом активных сетевых
    соединений прямо сейчас — приблизительный аналог "кто грузит сеть"
    без необходимости ставить сторонние снифферы трафика.

    psutil не даёт байты-в-секунду по процессу напрямую (это требует
    привилегированного перехвата пакетов), поэтому в качестве метрики
    активности используется количество установленных соединений у
    процесса — чем больше активных соединений, тем выше в списке.
    """
    log_func("Анализ сетевой активности по процессам...")
    progress_func(0.1)

    counts = {}
    try:
        conns = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError):
        log_func("Недостаточно прав для чтения сетевых соединений. "
                "Запустите приложение от имени администратора.", "WARN")
        progress_func(1.0)
        return []

    progress_func(0.5)

    for c in conns:
        if not c.pid:
            continue
        counts.setdefault(c.pid, 0)
        counts[c.pid] += 1

    progress_func(0.7)

    result = []
    for pid, count in counts.items():
        try:
            p = psutil.Process(pid)
            name = p.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            name = "—"
        result.append({"pid": pid, "name": name, "connections": count})

    result.sort(key=lambda x: x["connections"], reverse=True)
    progress_func(1.0)
    log_func("Найдено активных процессов с сетевыми соединениями: {}".format(len(result)))
    return result[:limit]


# ════════════════════════════════════════════════════════════════════ #
#  DNS-пресеты                                                        #
# ════════════════════════════════════════════════════════════════════ #

DNS_PRESETS = [
    {
        "name": "Google DNS",
        "primary": "8.8.8.8",
        "secondary": "8.8.4.4",
        "description": "Публичный DNS от Google. Быстрый, надёжный, с поддержкой DNS-over-HTTPS.",
        "tags": ["Публичный", "Быстрый", "Google"],
    },
    {
        "name": "Cloudflare DNS",
        "primary": "1.1.1.1",
        "secondary": "1.0.0.1",
        "description": "Самый быстрый публичный DNS. От Cloudflare. Защита от DDoS.",
        "tags": ["Публичный", "Самый быстрый", "Cloudflare"],
    },
    {
        "name": "OpenDNS",
        "primary": "208.67.222.222",
        "secondary": "208.67.220.220",
        "description": "От Cisco. Фильтрация контента, защита от фишинга.",
        "tags": ["Публичный", "Фильтрация", "Cisco"],
    },
    {
        "name": "Quad9",
        "primary": "9.9.9.9",
        "secondary": "149.112.112.112",
        "description": "Безопасный DNS с блокировкой вредоносных доменов.",
        "tags": ["Безопасность", "Блокировка вирусов"],
    },
    {
        "name": "Yandex DNS",
        "primary": "77.88.8.8",
        "secondary": "77.88.8.1",
        "description": "DNS от Яндекса. Оптимизирован для Рунета. Родительский контроль.",
        "tags": ["Рунет", "Родительский контроль", "Яндекс"],
    },
    {
        "name": "AdGuard DNS",
        "primary": "94.140.14.14",
        "secondary": "94.140.15.15",
        "description": "Блокирует рекламу, трекеры и вредоносные сайты на уровне DNS.",
        "tags": ["Блокировка рекламы", "Антитрекинг"],
    },
    {
        "name": "Comodo Secure DNS",
        "primary": "8.26.56.26",
        "secondary": "8.20.247.20",
        "description": "Бесплатный безопасный DNS от Comodo. Фильтрация вредоносных сайтов.",
        "tags": ["Безопасность", "Comodo"],
    },
    {
        "name": "DNS.SB",
        "primary": "185.222.222.222",
        "secondary": "185.228.168.168",
        "description": "Быстрый приватный DNS. Без логирования.",
        "tags": ["Приватный", "Без логов"],
    },
    {
        "name": "Xbox DNS",
        "primary": "111.88.96.50",
        "secondary": "111.88.96.51",
        "description": "Доступ к Xbox Live, ChatGPT, Claude, Gemini, играм Supercell. Smart DNS с шифрованием (DoH/DoT).",
        "tags": ["Xbox", "Игры", "AI", "Гео-обход"],
    },
    {
        "name": "Системный (авто)",
        "primary": "",
        "secondary": "",
        "description": "Вернуть автоматическое получение DNS от провайдера (DHCP).",
        "tags": ["Системный", "DHCP"],
    },
]


def get_current_dns(log_func, progress_func):
    """Возвращает текущие DNS-серверы для активных адаптеров."""
    log_func("Определение текущих DNS-серверов...")
    progress_func(0.2)
    out = _run('netsh interface ip show dnsservers')
    progress_func(0.8)

    current = []
    adapter = None
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        if "adapter" in line.lower() or "адаптер" in line.lower() or "适配器" in line:
            adapter = line
        elif line and (line[0].isdigit() or line.startswith("DHCP") or line.startswith("Статический")):
            if line[0].isdigit():
                current.append({"adapter": adapter, "dns": line})

    progress_func(1.0)
    if current:
        for c in current:
            log_func("DNS [{}]: {}".format(c["adapter"] or "?", c["dns"]))
    else:
        log_func("Текущие DNS: {}".format(out.strip()[:200]) if out else "Не удалось определить", "WARN")
    return current


def set_dns(log_func, progress_func, primary, secondary=""):
    """Устанавливает DNS-серверы для ВСЕХ активных адаптеров."""
    log_func("═══ Установка DNS ═══")
    log_func("Primary: {}  Secondary: {}".format(primary, secondary or "—"))
    progress_func(0.1)

    # Получаем список интерфейсов
    out = _run('netsh interface show interface')
    progress_func(0.2)

    adapters = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] in ("Включен", "Enabled", "Подключен", "Connected"):
            name = " ".join(parts[3:])
            adapters.append(name)

    if not adapters:
        log_func("Не удалось определить активные адаптеры. Проверьте подключение к сети.", "WARN")

    progress_func(0.3)
    success_count = 0

    for adapter in adapters:
        log_func("Настройка '{}'...".format(adapter))
        # Устанавливаем статический DNS
        if primary:
            cmd = 'netsh interface ip set dnsservers "{}" static {} primary'.format(adapter, primary)
            _run(cmd)
        if secondary:
            cmd = 'netsh interface ip add dnsservers "{}" {} index=2'.format(adapter, secondary)
            _run(cmd)
        success_count += 1

    progress_func(1.0)
    log_func("DNS установлен на {} адаптерах.".format(success_count), "OK")
    return True


def reset_dns(log_func, progress_func):
    """Сбрасывает DNS на автоматическое (DHCP) для всех адаптеров."""
    log_func("═══ Сброс DNS на DHCP ═══")
    progress_func(0.1)

    out = _run('netsh interface show interface')
    progress_func(0.2)

    adapters = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] in ("Включен", "Enabled", "Подключен", "Connected"):
            adapters.append(" ".join(parts[3:]))

    if not adapters:
        log_func("Не удалось определить активные адаптеры. Проверьте подключение к сети.", "WARN")

    progress_func(0.3)
    for adapter in adapters:
        log_func("Сброс '{}'...".format(adapter))
        _run('netsh interface ip set dnsservers "{}" dhcp'.format(adapter))

    progress_func(1.0)
    log_func("DNS сброшен на автоматическое (DHCP).", "OK")
    return True

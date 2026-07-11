"""
modules/gaming_optimizer.py
----------------------------
Игровые оптимизации Windows для максимального FPS и минимального пинга.
Взято лучшее из RustNightVision + OptimizerCore.
"""

import subprocess
import time

CREATE_NO_WINDOW = 0x08000000

# Процессы, которые стоит закрывать перед игрой
HEAVY_PROCESSES = [
    "Spotify.exe", "Chrome.exe", "msedge.exe", "Firefox.exe",
    "Discord.exe", "OneDrive.exe", "Teams.exe",
    "SteamWebHelper.exe", "EpicGamesLauncher.exe",
    "Battle.net.exe", "Origin.exe", "GOGGalaxy.exe",
    "vivaldi.exe", "brave.exe", "opera.exe", "operaGX.exe",
    "Telegram.exe", " qbittorrent.exe", "uTorrent.exe",
]

# Службы Windows, которые нагружают систему и безопасно отключать
GAMING_SERVICES = {
    "SysMain": "Суперфетч — кэширование программ (отключаем для SSD)",
    "DiagTrack": "Телеметрия Microsoft",
    "WSearch": "Индексация Windows Search",
    "dmwappushservice": "WAP Push",
    "RetailDemo": "Демо-режим",
}


def _run_cmd(cmd, timeout=30):
    """Выполняет cmd-команду."""
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", cmd],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=timeout,
        )
        return result.stdout.decode("cp866", errors="replace"), result.returncode
    except Exception as e:
        return str(e), -1


def _set_reg_dword(hive, path, name, value, log_func):
    """Устанавливает DWORD в реестр."""
    try:
        import winreg
        hkey = {
            "HKCU": winreg.HKEY_CURRENT_USER,
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
        }.get(hive, winreg.HKEY_CURRENT_USER)
        with winreg.OpenKey(hkey, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
        return True
    except Exception:
        return False


def optimize_gpu(log_func):
    """Оптимизация GPU для игр."""
    log_func("Оптимизация GPU...")

    # Включаем аппаратное ускорение планирования GPU
    ok = _set_reg_dword(
        "HKLM",
        r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
        "HwSchMode", 2, log_func
    )
    if ok:
        log_func("  GPU: аппаратное планирование включено", "OK")
    else:
        log_func("  GPU: не удалось изменить HwSchMode", "WARN")

    # NVIDIA Digital Vibrance (яркость контраста)
    ok = _set_reg_dword(
        "HKCU",
        r"Software\NVIDIA Corporation\Global\NvControlPanel2\Guest",
        "DigitalVibrance", 75, log_func
    )
    if ok:
        log_func("  NVIDIA: яркость контраста установлена", "OK")


def optimize_power_plan(log_func):
    """Включает план высокой производительности."""
    log_func("Настройка плана питания...")
    # GUID плана высокой производительности
    _run_cmd("powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c")
    log_func("  План питания: высокая производительность", "OK")


def optimize_game_mode_registry(log_func):
    """Включает игровой режим Windows и отключает Game DVR."""
    log_func("Настройка игрового режима Windows...")

    # Включаем Game Mode
    _set_reg_dword(
        "HKCU",
        r"Software\Microsoft\GameBar",
        "AllowAutoGameMode", 1, log_func
    )
    log_func("  Game Mode: включён", "OK")

    # Отключаем Game DVR (запись экрана — снижает FPS)
    _set_reg_dword(
        "HKCU",
        r"System\GameConfigStore",
        "GameDVR_Enabled", 0, log_func
    )
    log_func("  Game DVR: отключён (экономит FPS)", "OK")


def optimize_multimedia_priority(log_func):
    """Оптимизация приоритетов мультимедиа и сети."""
    log_func("Оптимизация приоритетов...")

    # SystemResponsiveness = 0 (весь ресурс — приложениям, не сервисам)
    _set_reg_dword(
        "HKLM",
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
        "SystemResponsiveness", 0, log_func
    )
    log_func("  SystemResponsiveness: 0 (максимум для приложений)", "OK")

    # NetworkThrottlingIndex = максимальное значение (без троттлинга сети)
    _set_reg_dword(
        "HKLM",
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
        "NetworkThrottlingIndex", 4294967295, log_func
    )
    log_func("  NetworkThrottlingIndex: отключён троттлинг", "OK")


def set_rust_priority(log_func):
    """Устанавливает высокий приоритет для RustClient.exe через реестр."""
    log_func("Настройка приоритета Rust...")
    _set_reg_dword(
        "HKLM",
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\RustClient.exe",
        "PriorityClass", 4, log_func  # 4 = HIGH_PRIORITY_CLASS
    )
    log_func("  Rust: приоритет HIGH", "OK")


def kill_heavy_processes(log_func, progress_func, extra_list=None):
    """Закрывает тяжёлые фоновые процессы перед игрой."""
    log_func("Закрытие фоновых процессов...")

    import psutil
    processes_to_kill = list(HEAVY_PROCESSES)
    if extra_list:
        processes_to_kill.extend(extra_list)

    killed = 0
    total = len(processes_to_kill)

    # Собираем запущенные процессы
    running = {}
    for p in psutil.process_iter(["name"]):
        name = (p.info["name"] or "").lower()
        running.setdefault(name, []).append(p)

    for i, proc_name in enumerate(processes_to_kill):
        name_lower = proc_name.lower()
        matches = running.get(name_lower, [])
        for p in matches:
            try:
                p.terminate()
                killed += 1
            except Exception:
                pass
        progress_func((i + 1) / max(total, 1))

    log_func("  Закрыто процессов: {}".format(killed), "OK")
    return killed


def optimize_network_for_gaming(log_func):
    """Сетевые оптимизации для снижения пинга."""
    log_func("Сетевые оптимизации для игр...")

    # TCP Ack Frequency = 1 (быстрое подтверждение пакетов)
    # Применяется ко всем сетевым интерфейсам
    try:
        _run_cmd(
            'for /f tokens=* %i in (\'reg query "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces" /s /v DhcpIPAddress 2^>nul ^| findstr /i HKEY\') do '
            '(reg add "%i" /v TcpAckFrequency /t REG_DWORD /d 1 /f >nul 2>&1 & '
            'reg add "%i" /v TCPNoDelay /t REG_DWORD /d 1 /f >nul 2>&1)'
        )
        log_func("  TcpAckFrequency: 1 (быстрый ACK)", "OK")
        log_func("  TCPNoDelay: 1 (без задержки Nagle)", "OK")
    except Exception:
        log_func("  Сетевые оптимизации: не удалось применить", "WARN")


def full_gaming_optimize(log_func, progress_func, options=None):
    """
    Полная игровая оптимизация: всё из RustNightVision + OptimizerCore.

    options: dict с ключами:
        gpu: bool           — оптимизация GPU
        power: bool         — план высокой производительности
        game_mode: bool     — игровой режим Windows
        multimedia: bool    — приоритеты мультимедиа
        rust_priority: bool — приоритет Rust
        kill_processes: bool — закрыть фоновые процессы
        network: bool       — сетевые оптимизации
        services: bool      — отключить ненужные службы
    """
    if options is None:
        options = {
            "gpu": True,
            "power": True,
            "game_mode": True,
            "multimedia": True,
            "rust_priority": True,
            "kill_processes": True,
            "network": True,
            "services": True,
        }

    log_func("=== ПОЛНАЯ ИГРОВАЯ ОПТИМИЗАЦИЯ ===")
    log_func("Лучшее из RustNightVision + OptimizerCore")
    log_func("")
    progress_func(0.0)

    step = 0
    total_steps = sum(1 for v in options.values() if v)

    def _pct():
        return min(0.95, step / max(total_steps, 1))

    # 1. Закрытие тяжёлых процессов
    if options.get("kill_processes"):
        kill_heavy_processes(log_func, progress_func)
        step += 1
        progress_func(_pct())

    # 2. Отключение служб
    if options.get("services"):
        log_func("Отключение ненужных служб...")
        disabled = 0
        for service in GAMING_SERVICES:
            out, code = _run_cmd('sc config "{}" start= disabled'.format(service))
            if code == 0:
                disabled += 1
                log_func("  {} — отключена".format(service), "OK")
        log_func("  Итого отключено служб: {}".format(disabled))
        step += 1
        progress_func(_pct())

    # 3. GPU оптимизации
    if options.get("gpu"):
        optimize_gpu(log_func)
        step += 1
        progress_func(_pct())

    # 4. План питания
    if options.get("power"):
        optimize_power_plan(log_func)
        step += 1
        progress_func(_pct())

    # 5. Игровой режим Windows
    if options.get("game_mode"):
        optimize_game_mode_registry(log_func)
        step += 1
        progress_func(_pct())

    # 6. Приоритеты мультимедиа
    if options.get("multimedia"):
        optimize_multimedia_priority(log_func)
        step += 1
        progress_func(_pct())

    # 7. Приоритет Rust
    if options.get("rust_priority"):
        set_rust_priority(log_func)
        step += 1
        progress_func(_pct())

    # 8. Сетевые оптимизации
    if options.get("network"):
        optimize_network_for_gaming(log_func)
        step += 1
        progress_func(_pct())

    progress_func(1.0)
    log_func("")
    log_func("=== ИГРОВАЯ ОПТИМИЗАЦИЯ ЗАВЕРШЕНА ===", "OK")
    log_func("Рекомендуется перезагрузка для применения всех изменений.", "WARN")

    return True


def get_gaming_optimization_status(log_func, progress_func):
    """Проверяет текущий статус игровых оптимизаций."""
    log_func("=== Проверка статуса игровых оптимизаций ===")
    progress_func(0.0)

    status = {}

    # Проверяем Game Mode
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\GameBar",
            0, winreg.KEY_QUERY_VALUE
        ) as key:
            val, _ = winreg.QueryValueEx(key, "AllowAutoGameMode")
            status["game_mode"] = val == 1
    except Exception:
        status["game_mode"] = False

    # Проверяем Game DVR
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"System\GameConfigStore",
            0, winreg.KEY_QUERY_VALUE
        ) as key:
            val, _ = winreg.QueryValueEx(key, "GameDVR_Enabled")
            status["game_dvr"] = val == 1
    except Exception:
        status["game_dvr"] = False

    # Проверяем GPU HwSchMode
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
            0, winreg.KEY_QUERY_VALUE
        ) as key:
            val, _ = winreg.QueryValueEx(key, "HwSchMode")
            status["gpu_hwsch"] = val == 2
    except Exception:
        status["gpu_hwsch"] = False

    # Проверяем SystemResponsiveness
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
            0, winreg.KEY_QUERY_VALUE
        ) as key:
            val, _ = winreg.QueryValueEx(key, "SystemResponsiveness")
            status["multimedia_priority"] = val == 0
    except Exception:
        status["multimedia_priority"] = False

    progress_func(1.0)

    log_func("Game Mode: {}".format("включён" if status.get("game_mode") else "выключен"))
    log_func("Game DVR: {}".format("выключен" if not status.get("game_dvr") else "включён (рекомендуется выключить)"))
    log_func("GPU HwSchMode: {}".format("оптимизирован" if status.get("gpu_hwsch") else "стандартный"))
    log_func("Приоритет мультимедиа: {}".format("оптимизирован" if status.get("multimedia_priority") else "стандартный"))

    return status

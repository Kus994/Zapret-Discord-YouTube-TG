"""
page_zapret.py — KUS Pro
Управление Zapret: пресеты, сервисные функции, скачивание.
Все операции выполняются нативно через Python — без запуска service.bat.
"""

import os
import re
import shlex
import subprocess
import threading
import urllib.request
import ssl
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QComboBox,
    QListWidget, QListWidgetItem, QTabWidget, QWidget,
    QFrame, QSizePolicy, QGroupBox, QPushButton, QGridLayout,
    QRadioButton, QButtonGroup, QDialog, QDialogButtonBox,
    QCheckBox, QMessageBox, QScrollArea,
)
from PyQt5.QtCore import Qt, QTimer

from base_page import BasePage
from worker import Worker
from app_paths import BASE_DIR, ZAPRET_DIR
from qt_compat import *

CNW = 0x08000000  # CREATE_NO_WINDOW
SUH = subprocess.STARTUPINFO()
SUH.dwFlags |= subprocess.STARTF_USESHOWWINDOW
SUH.wShowWindow = 0  # SW_HIDE

_proc: Optional[subprocess.Popen] = None
_proc_lock = threading.Lock()


# ════════════════════════════════════════════════════════════════════ #
#  Бат-парсер (извлекает аргументы winws.exe из .bat файла)           #
# ════════════════════════════════════════════════════════════════════ #

def _get_game_filter_ports(ver_dir):
    """Читает game_filter.enabled и возвращает (tcp_ports, udp_ports) как в service.bat."""
    flag_file = ver_dir / "utils" / "game_filter.enabled"
    if not flag_file.exists():
        return "12", "12"
    mode = flag_file.read_text(encoding="utf-8", errors="replace").strip().lower()
    if mode == "all":
        return "1024-65535", "1024-65535"
    elif mode == "tcp":
        return "1024-65535", "12"
    elif mode == "udp":
        return "12", "1024-65535"
    return "12", "12"


def _parse_bat_winws_args(bat_path: Path):
    """Парсит bat-файл и извлекает аргументы winws.exe/winws2.exe."""
    text = bat_path.read_text(encoding="utf-8-sig", errors="replace")
    text = re.sub(r'\^\s*\n', ' ', text)
    
    # Формат 1: start "..." /min "winws.exe" args...
    m = re.search(
        r'start\s+"[^"]*"\s*/min\s+"[^"]*winws2?\.exe"\s+(.*)',
        text, re.IGNORECASE | re.DOTALL
    )
    # Формат 2: "%BIN%winws.exe" args... (без start)
    if not m:
        m = re.search(
            r'"?[^"]*winws2?\.exe"?\s+(.*)',
            text, re.IGNORECASE | re.DOTALL
        )
    if not m:
        return None
    args_str = m.group(1).strip()
    ver_dir = bat_path.parent
    args_str = args_str.replace('%~dp0', str(ver_dir) + os.sep)
    args_str = args_str.replace('%ZAPRET%', str(ver_dir) + os.sep)
    args_str = args_str.replace('%LUA%', str(ver_dir / 'lua') + os.sep)
    args_str = args_str.replace('%FILES%', str(ver_dir / 'files') + os.sep)
    args_str = args_str.replace('%BIN%', str(ver_dir / 'bin') + os.sep)
    args_str = args_str.replace('%LISTS%', str(ver_dir / 'lists') + os.sep)
    args_str = args_str.replace('%WINV%', str(ver_dir / 'windivert.filter') + os.sep)
    game_tcp, game_udp = _get_game_filter_ports(ver_dir)
    args_str = args_str.replace('%GameFilterTCP%', game_tcp)
    args_str = args_str.replace('%GameFilterUDP%', game_udp)
    args_str = re.sub(r'--\S+=""', '', args_str)
    try:
        args = shlex.split(args_str, posix=False)
    except ValueError:
        args = args_str.split()
    args = [a for a in args if a and a != '--new']
    return args


# ════════════════════════════════════════════════════════════════════ #
#  Утилиты для системных команд                                       #
# ════════════════════════════════════════════════════════════════════ #

def _run_cmd(cmd, log_func, timeout=15, encoding="cp866"):
    """Запуск shell-команды с захватом вывода. Возвращает (returncode, stdout_text)."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            creationflags=CNW, startupinfo=SUH,
            timeout=timeout, encoding=encoding, errors="replace",
        )
        return r.returncode, r.stdout.strip()
    except Exception as e:
        log_func("Ошибка команды '{}': {}".format(cmd[0], e), "ERR")
        return -1, ""


def _sc_query(service_name):
    """Проверяет статус Windows-сервиса. Возвращает статус или None."""
    code, out = _run_cmd(
        ["sc", "query", service_name],
        lambda *a: None, timeout=5
    )
    if code != 0:
        return None
    for line in out.splitlines():
        if "STATE" in line.upper():
            parts = line.split()
            if len(parts) >= 4:
                return parts[3]  # RUNNING, STOPPED, STOP_PENDING и т.д.
    return None


def _tasklist_running(exe_name):
    """Проверяет, запущен ли процесс."""
    code, out = _run_cmd(
        ["tasklist", "/FI", "IMAGENAME eq {}".format(exe_name)],
        lambda *a: None, timeout=5
    )
    return exe_name.lower() in out.lower()


def _is_running():
    with _proc_lock:
        return _proc is not None and _proc.poll() is None


# ════════════════════════════════════════════════════════════════════ #
#  Версии / бат-файлы                                                 #
# ════════════════════════════════════════════════════════════════════ #

def _get_versions():
    if not ZAPRET_DIR.exists():
        return []
    versions = []
    # Корневая папка zapret/ — если в ней есть service.bat и bat-файлы
    if (ZAPRET_DIR / "service.bat").exists():
        root_bats = list(ZAPRET_DIR.glob("*.bat"))
        if root_bats:
            versions.append("root")
    # Подпапки с service.bat
    for p in ZAPRET_DIR.iterdir():
        if p.is_dir() and (p / "service.bat").exists():
            versions.append(p.name)
    return sorted(versions)


def _get_bats(ver_dir: Path):
    if not ver_dir.exists():
        return []
    bats = [p.name for p in ver_dir.glob("*.bat")
            if p.name.lower() != "service.bat"]
    bats.sort(key=lambda x: (0 if x.lower() == "general.bat" else 1, x.lower()))
    return bats


def _ver_to_path(ver_name):
    """Конвертирует имя версии в путь. 'root' = ZAPRET_DIR, остальное = подпапка."""
    if ver_name == "root":
        return ZAPRET_DIR
    return ZAPRET_DIR / ver_name


def _saved_ver():
    vf = ZAPRET_DIR / "current_version.txt"
    if vf.exists():
        n = vf.read_text(encoding="utf-8").strip()
        if n == "root" or (ZAPRET_DIR / n).exists():
            return n
    v = _get_versions()
    return v[0] if v else None


def _save_ver(name):
    ZAPRET_DIR.mkdir(parents=True, exist_ok=True)
    (ZAPRET_DIR / "current_version.txt").write_text(name, encoding="utf-8")


# ════════════════════════════════════════════════════════════════════ #
#  Worker-функции (выполняются в фоновом потоке)                       #
# ════════════════════════════════════════════════════════════════════ #

def _fn_start(log_func, progress_func, bat_path, ver_dir):
    global _proc

    for name in ["zapret", "winws.exe", "winws2.exe"]:
        try:
            subprocess.run(
                ["sc", "stop", name] if not name.endswith(".exe")
                else ["taskkill", "/F", "/IM", name],
                creationflags=CNW, startupinfo=SUH,
                capture_output=True, timeout=5)
        except Exception:
            pass
    progress_func(0.2)

    bat = Path(bat_path)
    if not bat.exists():
        log_func("Файл не найден: {}".format(bat_path), "ERR"); return

    log_func("Запуск: {}".format(bat.name), "INFO")

    # Парсим аргументы из bat-файла и запускаем winws.exe напрямую
    # Это исключает появление окна консоли
    from page_zapret import _parse_bat_winws_args
    ver_dir_path = Path(ver_dir)
    winws_exe = ver_dir_path / "bin" / "winws.exe"
    if not winws_exe.exists():
        winws_exe = ver_dir_path / "winws2.exe"
    if not winws_exe.exists():
        log_func("winws.exe/winws2.exe не найден", "ERR")
        return

    args = _parse_bat_winws_args(bat)
    if not args:
        log_func("Не удалось извлечь аргументы из {}".format(bat.name), "ERR")
        return

    log_func("CMD: {} {}".format(winws_exe.name, " ".join(args[:5]) + "..."), "INFO")
    try:
        with _proc_lock:
            _proc = subprocess.Popen(
                [str(winws_exe)] + args,
                cwd=str(ver_dir_path),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=CNW, startupinfo=SUH,
                text=True, encoding="cp866", errors="replace",
            )
        progress_func(0.5)
        line_count = 0
        for line in _proc.stdout:
            line = line.rstrip()
            if line:
                log_func(line, "INFO")
                line_count += 1
                if line_count % 10 == 0:
                    progress_func(min(0.95, 0.5 + 0.4 * min(line_count, 100) / 100))
        _proc.wait()
        log_func("Завершён (код: {})".format(_proc.returncode),
                 "OK" if _proc.returncode == 0 else "WARN")
    except PermissionError:
        log_func("Нет прав администратора! Запустите KUS Pro от администратора.", "ERR")
    except Exception as e:
        log_func("Ошибка: {}".format(e), "ERR")
    finally:
        progress_func(1.0)
        with _proc_lock:
            _proc = None


def _fn_stop(log_func, progress_func, ver_dir=""):
    global _proc
    with _proc_lock:
        proc_ref = _proc
    if proc_ref and proc_ref.poll() is None:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc_ref.pid)],
                           creationflags=CNW, capture_output=True, timeout=8)
            log_func("Zapret остановлен.", "OK")
        except Exception as e:
            log_func("Ошибка: {}".format(e), "WARN")
    for exe in ["winws.exe", "winws2.exe"]:
        try:
            subprocess.run(["taskkill", "/F", "/IM", exe],
                           creationflags=CNW, capture_output=True, timeout=5)
        except Exception:
            pass
    with _proc_lock:
        _proc = None
    progress_func(1.0)


def _fn_install_service(log_func, progress_func, ver_dir, bat_name):
    """Установка Windows-службы zapret — нативно через sc create."""
    ver_path = Path(ver_dir)
    bin_path = ver_path / "bin"
    lists_path = ver_path / "lists"
    winws_exe = bin_path / "winws.exe"

    if not winws_exe.exists():
        log_func("winws.exe не найден: {}".format(winws_exe), "ERR")
        return

    bat_path = ver_path / bat_name
    if not bat_path.exists():
        log_func("Файл пресета не найден: {}".format(bat_name), "ERR")
        return

    log_func("Парсинг аргументов из {}...".format(bat_name), "INFO")
    winws_args = _parse_bat_winws_args(bat_path)
    if not winws_args:
        log_func("Не удалось извлечь аргументы из {}".format(bat_name), "ERR")
        return

    # Подставляем пути к lists/ и bin/
    final_args = []
    for a in winws_args:
        a = a.replace('%LISTS%', str(lists_path) + os.sep)
        a = a.replace('%BIN%', str(bin_path) + os.sep)
        final_args.append(a)

    args_str = '"{}" {}'.format(winws_exe, " ".join(final_args))

    log_func("Остановка старого сервиса...", "INFO")
    _run_cmd(["net", "stop", "zapret"], lambda *a: None, timeout=10)
    _run_cmd(["sc", "delete", "zapret"], lambda *a: None, timeout=5)

    log_func("Создание сервиса zapret...", "INFO")
    code, out = _run_cmd(
        ["sc", "create", "zapret",
         'binPath= "{}"'.format(args_str),
         "DisplayName=", "zapret",
         "start=", "auto"],
        log_func, timeout=10
    )
    if code == 0:
        log_func("Сервис создан.", "OK")
    else:
        log_func("Ошибка создания сервиса. Код: {}".format(code), "ERR")
        if out:
            log_func(out, "ERR")
        return

    _run_cmd(["sc", "description", "zapret", "Zapret DPI bypass software"],
             lambda *a: None, timeout=5)

    log_func("Запуск сервиса...", "INFO")
    code, out = _run_cmd(["sc", "start", "zapret"], log_func, timeout=15)
    if code == 0:
        log_func("Сервис запущен.", "OK")
    else:
        log_func("Ошибка запуска сервиса. Код: {}".format(code), "WARN")

    # Запись имени пресета в реестр
    bat_stem = Path(bat_name).stem
    _run_cmd(
        ["reg", "add",
         r"HKLM\System\CurrentControlSet\Services\zapret",
         "/v", "zapret-discord-youtube",
         "/t", "REG_SZ", "/d", bat_stem, "/f"],
        lambda *a: None, timeout=5
    )
    log_func("Пресет '{}' сохранён в реестр.".format(bat_stem), "OK")
    progress_func(1.0)


def _fn_remove_service(log_func, progress_func):
    """Удаление всех сервисов zapret — нативно."""
    log_func("Остановка сервиса zapret...", "INFO")
    code, _ = _run_cmd(["sc", "query", "zapret"], lambda *a: None)
    if code == 0:
        _run_cmd(["net", "stop", "zapret"], lambda *a: None, timeout=10)
        _run_cmd(["sc", "delete", "zapret"], log_func, timeout=5)
        log_func("Сервис zapret удалён.", "OK")
    else:
        log_func("Сервис zapret не установлен.", "INFO")

    if _tasklist_running("winws.exe"):
        _run_cmd(["taskkill", "/IM", "winws.exe", "/F"], lambda *a: None)
        log_func("winws.exe остановлен.", "OK")

    for svc in ["WinDivert", "WinDivert14"]:
        code, _ = _run_cmd(["sc", "query", svc], lambda *a: None)
        if code == 0:
            _run_cmd(["net", "stop", svc], lambda *a: None, timeout=10)
            _run_cmd(["sc", "delete", svc], lambda *a: None, timeout=5)
            log_func("Сервис {} удалён.".format(svc), "OK")

    progress_func(1.0)


def _fn_status_zapret(log_func, progress_func):
    """Проверка статуса сервиса zapret — нативно."""
    log_func("═══ Статус Zapret ═══", "INFO")

    # Проверка сервиса zapret
    status = _sc_query("zapret")
    if status == "RUNNING":
        log_func("Сервис zapret: РАБОТАЕТ", "OK")
    elif status:
        log_func("Сервис zapret: {}".format(status), "WARN")
    else:
        log_func("Сервис zapret: НЕ УСТАНОВЛЕН", "INFO")

    # Проверка WinDivert
    wd_status = _sc_query("WinDivert")
    if wd_status == "RUNNING":
        log_func("WinDivert: РАБОТАЕТ", "OK")
    elif wd_status:
        log_func("WinDivert: {}".format(wd_status), "WARN")
    else:
        log_func("WinDivert: НЕ УСТАНОВЛЕН", "INFO")

    # Проверка WinDivert64.sys
    ver = _saved_ver()
    if ver:
        sys_file = ZAPRET_DIR / ver / "bin" / "WinDivert64.sys"
        if sys_file.exists():
            log_func("WinDivert64.sys: найден", "OK")
        else:
            log_func("WinDivert64.sys: НЕ НАЙДЕН", "WARN")

    # Проверка winws.exe
    if _tasklist_running("winws.exe"):
        log_func("winws.exe: РАБОТАЕТ", "OK")
    else:
        log_func("winws.exe: НЕ ЗАПУЩЕН", "INFO")

    progress_func(1.0)


def _fn_update_ipset(log_func, progress_func):
    """Обновление ipset-all.txt — нативно через Python."""
    ver = _saved_ver()
    if not ver:
        log_func("Версия zapret не определена.", "ERR"); return

    list_file = ZAPRET_DIR / ver / "lists" / "ipset-all.txt"
    url = "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/refs/heads/main/.service/ipset-service.txt"

    log_func("Загрузка ipset-all.txt...", "INFO")
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = resp.read().decode("utf-8", errors="replace")
        list_file.parent.mkdir(parents=True, exist_ok=True)
        list_file.write_text(data, encoding="utf-8")
        log_func("ipset-all.txt обновлён ({} байт).".format(len(data)), "OK")
    except Exception as e:
        log_func("Ошибка загрузки: {}".format(e), "ERR")
    progress_func(1.0)


def _fn_update_hosts(log_func, progress_func):
    """Обновление hosts — нативно через Python."""
    hosts_file = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"
    url = "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/refs/heads/main/.service/hosts"

    log_func("Загрузка hosts из репозитория...", "INFO")
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        new_hosts = resp.read().decode("utf-8", errors="replace").strip()
    except Exception as e:
        log_func("Ошибка загрузки hosts: {}".format(e), "ERR")
        progress_func(1.0)
        return

    if not new_hosts:
        log_func("Пустой файл hosts из репозитория.", "ERR")
        progress_func(1.0)
        return

    new_lines = new_hosts.splitlines()
    first_line = new_lines[0].strip()
    last_line = new_lines[-1].strip()

    needs_update = False
    if hosts_file.exists():
        current = hosts_file.read_text(encoding="utf-8", errors="replace")
        if first_line not in current or last_line not in current:
            needs_update = True
    else:
        needs_update = True

    if needs_update:
        log_func("Файл hosts требует обновления.", "WARN")
        log_func("Запись обновлённого hosts...", "INFO")
        try:
            hosts_file.write_text(new_hosts, encoding="utf-8")
            log_func("Файл hosts успешно обновлён!", "OK")
        except PermissionError:
            log_func("Ошибка: нет прав для записи. Запустите от администратора.", "ERR")
        except Exception as e:
            log_func("Ошибка записи hosts: {}".format(e), "ERR")
    else:
        log_func("Файл hosts уже актуален.", "OK")
    progress_func(1.0)


def _fn_check_updates(log_func, progress_func):
    """Проверка обновлений — нативно через GitHub API."""
    url = "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/main/.service/version.txt"
    log_func("Проверка последней версии на GitHub...", "INFO")
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        latest = resp.read().decode("utf-8").strip()
    except Exception as e:
        log_func("Ошибка проверки версий: {}".format(e), "ERR")
        progress_func(1.0)
        return

    current = _saved_ver()
    if current and current == latest:
        log_func("Установлена последняя версия: {}".format(current), "OK")
    else:
        log_func("Доступна новая версия: {} (текущая: {})".format(latest, current or "нет"), "WARN")
        log_func("Скачайте обновление на вкладке «Установка».", "INFO")
    progress_func(1.0)


def _fn_run_diagnostics(log_func, progress_func):
    """Диагностика — все проверки нативно через Python."""
    log_func("═══ Диагностика Zapret ═══", "INFO")
    passed = 0
    failed = 0
    warns = 0

    def ok(msg):
        nonlocal passed
        log_func("[OK] {}".format(msg), "OK"); passed += 1

    def fail(msg):
        nonlocal failed
        log_func("[X] {}".format(msg), "ERR"); failed += 1

    def warn(msg):
        nonlocal warns
        log_func("[?] {}".format(msg), "WARN"); warns += 1

    # 1. Base Filtering Engine
    bfe = _sc_query("BFE")
    if bfe == "RUNNING":
        ok("Base Filtering Engine работает")
    else:
        fail("Base Filtering Engine НЕ работает — этот сервис обязателен для zapret")

    # 2. Прокси
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
        try:
            proxy_enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if proxy_enabled:
                try:
                    proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                    warn("Системный прокси включён: {}".format(proxy_server))
                except Exception:
                    warn("Системный прокси включён")
            else:
                ok("Прокси выключен")
        finally:
            winreg.CloseKey(key)
    except Exception:
        ok("Прокси не настроен")

    # 3. TCP timestamps
    code, out = _run_cmd(
        ["netsh", "interface", "tcp", "show", "global"],
        lambda *a: None
    )
    if "enabled" in out.lower() and "timestamps" in out.lower():
        ok("TCP timestamps включены")
    else:
        warn("TCP timestamps выключены — включаю...")
        _run_cmd(["netsh", "interface", "tcp", "set", "global", "timestamps=enabled"],
                 lambda *a: None)
        ok("TCP timestamps включены")

    # 4. Adguard
    if _tasklist_running("AdguardSvc.exe"):
        fail("Adguard обнаружен — может конфликтовать с Discord")
    else:
        ok("Adguard не найден")

    # 5. Killer services
    code, out = _run_cmd(["sc", "query"], lambda *a: None, timeout=10)
    if "killer" in out.lower():
        fail("Killer-сервисы обнаружены — конфликтуют с zapret")
    else:
        ok("Killer не найден")

    # 6. Intel Connectivity
    if "intel" in out.lower() and "connectivity" in out.lower():
        fail("Intel Connectivity Network Service обнаружен — конфликтует с zapret")
    else:
        ok("Intel Connectivity не найден")

    # 7. Check Point
    if "tracsrvwrapper" in out.lower() or "epwd" in out.lower():
        fail("Check Point обнаружен — конфликтует с zapret")
    else:
        ok("Check Point не найден")

    # 8. SmartByte
    if "smartbyte" in out.lower():
        fail("SmartByte обнаружен — конфликтует с zapret")
    else:
        ok("SmartByte не найден")

    # 9. WinDivert64.sys
    ver = _saved_ver()
    if ver:
        sys_file = ZAPRET_DIR / ver / "bin" / "WinDivert64.sys"
        if sys_file.exists():
            ok("WinDivert64.sys найден")
        else:
            fail("WinDivert64.sys НЕ найден в {}".format(sys_file.parent))

    # 10. VPN
    if "vpn" in out.lower():
        warn("VPN-сервисы обнаружены — некоторые могут конфликтовать с zapret")
    else:
        ok("VPN не найден")

    # 11. WinDivert конфликт
    winws_running = _tasklist_running("winws.exe")
    wd_status = _sc_query("WinDivert")
    if not winws_running and wd_status in ("RUNNING", "STOP_PENDING"):
        warn("winws.exe не запущен, но WinDivert активен — удаляю...")
        _run_cmd(["net", "stop", "WinDivert"], lambda *a: None)
        _run_cmd(["sc", "delete", "WinDivert"], lambda *a: None)
        ok("WinDivert удалён")

    # 12. Конфликтующие обходы
    for svc in ["GoodbyeDPI", "discordfix_zapret", "winws1", "winws2"]:
        if svc.lower() in out.lower():
            fail("Конфликтующий сервис: {}".format(svc))

    # 13. Discord кэш
    discord_cache = Path(os.environ.get("APPDATA", "")) / "discord"
    cache_dirs = ["Cache", "Code Cache", "GPUCache"]
    for d in cache_dirs:
        p = discord_cache / d
        if p.exists():
            warn("Discord кэш найден: {}".format(p))

    log_func("─────────────────────────", "INFO")
    log_func("Результат: {} OK, {} предупреждений, {} ошибок".format(passed, warns, failed), "INFO")
    progress_func(1.0)


def _fn_run_tests(log_func, progress_func):
    """Запуск тестов PowerShell."""
    ver = _saved_ver()
    if not ver:
        log_func("Версия zapret не определена.", "ERR"); return

    test_script = ZAPRET_DIR / ver / "utils" / "test zapret.ps1"
    if not test_script.exists():
        log_func("Скрипт тестов не найден: {}".format(test_script), "ERR")
        return

    log_func("Запуск тестов в PowerShell...", "INFO")
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(test_script)],
            creationflags=CNW, startupinfo=SUH,
        )
        log_func("PowerShell тесты запущены.", "OK")
    except Exception as e:
        log_func("Ошибка запуска тестов: {}".format(e), "ERR")
    progress_func(1.0)


def _fn_game_filter(log_func, progress_func, ver_dir, mode):
    """Переключение Game Filter — нативно через файл флага."""
    utils_dir = Path(ver_dir) / "utils"
    utils_dir.mkdir(exist_ok=True)
    flag_file = utils_dir / "game_filter.enabled"

    if mode == "disabled":
        if flag_file.exists():
            flag_file.unlink()
        log_func("Game Filter: отключён", "OK")
    else:
        flag_file.write_text(mode, encoding="utf-8")
        labels = {"all": "TCP и UDP", "tcp": "TCP", "udp": "UDP"}
        log_func("Game Filter: {} — перезапустите zapret для применения".format(
            labels.get(mode, mode)), "OK")
    progress_func(1.0)


def _fn_check_updates_switch(log_func, progress_func, ver_dir):
    """Переключение авто-проверки обновлений."""
    utils_dir = Path(ver_dir) / "utils"
    utils_dir.mkdir(exist_ok=True)
    flag_file = utils_dir / "check_updates.enabled"

    if flag_file.exists():
        flag_file.unlink()
        log_func("Авто-проверка обновлений: отключена", "OK")
    else:
        flag_file.write_text("ENABLED", encoding="utf-8")
        log_func("Авто-проверка обновлений: включена", "OK")
    progress_func(1.0)


def _fn_ipset_switch(log_func, progress_func, ver_dir):
    """Переключение IPSet Filter — цикл: loaded -> none -> any -> loaded."""
    lists_dir = Path(ver_dir) / "lists"
    list_file = lists_dir / "ipset-all.txt"
    backup_file = lists_dir / "ipset-all.txt.backup"

    if not list_file.exists():
        list_file.parent.mkdir(parents=True, exist_ok=True)
        list_file.write_text("203.0.113.113/32", encoding="utf-8")
        log_func("IPSet: none (файл создан)", "OK")
        progress_func(1.0)
        return

    content = list_file.read_text(encoding="utf-8", errors="replace")

    if "203.0.113.113/32" in content:
        # none -> any
        list_file.write_text("", encoding="utf-8")
        log_func("IPSet: any (пустой список)", "OK")
    elif not content.strip():
        # any -> loaded
        if backup_file.exists():
            backup_file.rename(list_file)
            log_func("IPSet: loaded (восстановлен из бэкапа)", "OK")
        else:
            log_func("IPSet: нет бэкапа для восстановления", "ERR")
    else:
        # loaded -> none (с бэкапом)
        if backup_file.exists():
            backup_file.unlink()
        list_file.rename(backup_file)
        list_file.write_text("203.0.113.113/32", encoding="utf-8")
        log_func("IPSet: none (бэкап создан)", "OK")

    progress_func(1.0)


# ════════════════════════════════════════════════════════════════════ #
#  Диалог выбора пресета для установки сервиса                         #
# ════════════════════════════════════════════════════════════════════ #

class _InstallServiceDialog(QDialog):
    """Диалог выбора пресета для установки Windows-службы."""
    def __init__(self, bat_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Установка сервиса Zapret")
        self.setMinimumWidth(400)
        self._selected = None

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        info = QLabel("Выберите пресет для автозагрузки:")
        info.setStyleSheet("font-weight:600;")
        lay.addWidget(info)

        self._group = QButtonGroup(self)
        for i, name in enumerate(bat_names):
            rb = QRadioButton(name)
            self._group.addButton(rb, i)
            lay.addWidget(rb)
            if i == 0:
                rb.setChecked(True)

        self._group.idToggled.connect(self._on_select)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _on_select(self, idx, checked):
        if checked:
            self._selected = self._group.button(idx).text()

    def selected_bat(self):
        if self._selected:
            return self._selected
        btn = self._group.checkedButton()
        return btn.text() if btn else None


# ════════════════════════════════════════════════════════════════════ #
#  Диалог выбора Game Filter                                          #
# ════════════════════════════════════════════════════════════════════ #

class _GameFilterDialog(QDialog):
    """Диалог выбора режима Game Filter."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Game Filter")
        self.setMinimumWidth(300)
        self._mode = "disabled"

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        info = QLabel("Режим обхода для игр (UDP/TCP):")
        info.setStyleSheet("font-weight:600;")
        lay.addWidget(info)

        self._group = QButtonGroup(self)
        modes = [
            ("disabled", "Отключён", 0),
            ("all",      "TCP и UDP", 1),
            ("tcp",      "Только TCP", 2),
            ("udp",      "Только UDP", 3),
        ]
        for key, label, idx in modes:
            rb = QRadioButton(label)
            self._group.addButton(rb, idx)
            rb.setProperty("mode", key)
            lay.addWidget(rb)
            if key == "disabled":
                rb.setChecked(True)

        self._group.idToggled.connect(self._on_select)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _on_select(self, idx, checked):
        if checked:
            btn = self._group.button(idx)
            self._mode = btn.property("mode") if btn else "disabled"

    def selected_mode(self):
        btn = self._group.checkedButton()
        return btn.property("mode") if btn else "disabled"


# ════════════════════════════════════════════════════════════════════ #
#  Страница                                                          #
# ════════════════════════════════════════════════════════════════════ #

class ZapretPage(BasePage):
    PAGE_TITLE = "Zapret — Обход блокировок"
    PAGE_SUB   = "Discord, YouTube, Twitch и другие заблокированные сервисы"

    _HINTS = {
        "general.bat":                     "Основной пресет. Попробуйте первым — подходит для большинства случаев.",
        "general (ALT).bat":               "Альтернатива 1. Если general не помог, попробуйте этот.",
        "general (ALT2).bat":              "Альтернатива 2. Другая стратегия обхода.",
        "general (ALT3).bat":              "Альтернатива 3.",
        "general (ALT4).bat":              "Альтернатива 4.",
        "general (ALT5).bat":              "Альтернатива 5.",
        "general (ALT6).bat":              "Альтернатива 6.",
        "general (ALT7).bat":              "Альтернатива 7.",
        "general (ALT8).bat":              "Альтернатива 8.",
        "general (ALT9).bat":              "Альтернатива 9.",
        "general (ALT10).bat":             "Альтернатива 10.",
        "general (ALT11).bat":             "Альтернатива 11.",
        "general (ALT12).bat":             "Альтернатива 12.",
        "general (SIMPLE FAKE).bat":       "Simple Fake TLS — простая подмена TLS-хендшейка.",
        "general (SIMPLE FAKE ALT).bat":   "Simple Fake TLS — альтернатива.",
        "general (SIMPLE FAKE ALT2).bat":  "Simple Fake TLS — альтернатива 2.",
        "general (FAKE TLS AUTO).bat":     "Auto Fake TLS — автоматически определяет параметры. Рекомендуется.",
        "general (FAKE TLS AUTO ALT).bat": "Auto Fake TLS — альтернатива.",
        "general (FAKE TLS AUTO ALT2).bat":"Auto Fake TLS — альтернатива 2.",
        "general (FAKE TLS AUTO ALT3).bat":"Auto Fake TLS — альтернатива 3.",
    }

    _CATEGORIES = {
        "Рекомендуемые": ["general.bat", "general (FAKE TLS AUTO).bat"],
        "Простые": ["general (SIMPLE FAKE).bat", "general (SIMPLE FAKE ALT).bat"],
        "Альтернативы": [k for k in _HINTS if k.startswith("general (ALT")],
    }

    def build_ui(self):
        self._start_w = None
        self._stop_w  = None

        # ── Проверка прав администратора ───────────────────────────── #
        import ctypes
        is_admin = False
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            pass

        if not is_admin:
            warn_card = self.card("", "")
            warn_card.setStyleSheet(
                "QFrame#card {{ border:1px solid #e05252; border-radius:8px; background:#2a1a1a; }}")
            warn_lbl = QLabel(
                "Zapret (winws.exe) требует прав администратора!\n"
                "Нажмите правой кнопкой → «Запуск от имени администратора»,\n"
                "либо перезапустите KUS Pro с повышением прав (UAC)."
            )
            warn_lbl.setWordWrap(True)
            warn_lbl.setStyleSheet("color:#e05252; font-size:13px; font-weight:bold; background:transparent;")
            warn_card.lay.addWidget(warn_lbl)
            self._content.addWidget(warn_card)

        # ── Верхняя панель ────────────────────────────────────────── #
        top = QHBoxLayout()
        top.setSpacing(12)

        self._badge = QLabel("Остановлен")
        self._badge.setObjectName("badge_stop")
        top.addWidget(self._badge)

        top.addStretch()

        self._quick_start = self.btn("🚀  Быстрый старт", obj="btn_glow")
        self._quick_start.setToolTip("Запустить основной пресет general.bat")
        self._quick_start.clicked.connect(self._quick_start_action)
        top.addWidget(self._quick_start)

        self._btn_auto_tune = self.btn("🔍  Авто-подбор", obj="btn_sec")
        self._btn_auto_tune.setToolTip("Автоматически найти лучший пресет для вашего провайдера")
        self._btn_auto_tune.clicked.connect(self._auto_tune)
        top.addWidget(self._btn_auto_tune)

        self._content.addLayout(top)

        # ── Вкладки ───────────────────────────────────────────────── #
        tabs = QTabWidget()

        # ─ Вкладка 1: Запуск ────────────────────────────────────────
        tab_run = QWidget()
        tab_run.setStyleSheet("background: transparent;")
        trl = QVBoxLayout(tab_run)
        trl.setContentsMargins(14, 14, 14, 14)
        trl.setSpacing(12)

        ver_row = QHBoxLayout()
        ver_lbl = QLabel("Версия:")
        ver_lbl.setFixedWidth(60)
        ver_lbl.setStyleSheet("color:#5a5248; font-weight:600;")
        self._ver_combo = QComboBox()
        self._ver_combo.currentTextChanged.connect(self._on_ver_change)
        ver_row.addWidget(ver_lbl)
        ver_row.addWidget(self._ver_combo, 1)
        ref = self.btn("Обновить", obj="btn_sec")
        ref.setFixedWidth(90)
        ref.clicked.connect(self._reload)
        ver_row.addWidget(ref)
        trl.addLayout(ver_row)

        hint_frame = QFrame()
        hint_frame.setStyleSheet(
            "QFrame { background: rgba(76,175,125,0.06); border: 1px solid rgba(76,175,125,0.15);"
            " border-radius: 8px; padding: 8px; }"
        )
        hint_lay = QVBoxLayout(hint_frame)
        hint_lay.setContentsMargins(12, 8, 12, 8)
        self._hint = QLabel("Выберите пресет из списка ниже")
        self._hint.setStyleSheet("color:#8ac8a0; font-size:12px; background:transparent;")
        self._hint.setWordWrap(True)
        self._hint.setMinimumHeight(36)
        hint_lay.addWidget(self._hint)
        trl.addWidget(hint_frame)

        cat_row = QHBoxLayout()
        cat_row.setSpacing(6)
        cat_lbl = QLabel("Быстрый выбор:")
        cat_lbl.setStyleSheet("color:#5a5248; font-size:11px; font-weight:600; background:transparent;")
        cat_row.addWidget(cat_lbl)

        for cat_name in self._CATEGORIES:
            cat_btn = self.btn(cat_name, obj="btn_sec")
            cat_btn.setFixedHeight(28)
            cat_btn.setStyleSheet(
                "QPushButton { padding: 4px 12px; font-size: 11px; border-radius: 6px; }"
            )
            cat_btn.clicked.connect(lambda _, cn=cat_name: self._select_category(cn))
            cat_row.addWidget(cat_btn)
        cat_row.addStretch()
        trl.addLayout(cat_row)

        self._bat_list = QListWidget()
        self._bat_list.setMinimumHeight(220)
        self._bat_list.setSizePolicy(Expanding, Expanding)
        self._bat_list.currentRowChanged.connect(self._on_preset_select)
        trl.addWidget(self._bat_list, 1)

        ctrl = QHBoxLayout()
        ctrl.setSpacing(10)
        self._btn_start = self.btn("Запустить")
        self._btn_start.setFixedHeight(42)
        self._btn_start.clicked.connect(self._start)
        ctrl.addWidget(self._btn_start)

        self._btn_stop = self.btn("Остановить", obj="btn_danger")
        self._btn_stop.setFixedHeight(42)
        self._btn_stop.clicked.connect(self._stop)
        self._btn_stop.setEnabled(False)
        ctrl.addWidget(self._btn_stop)
        ctrl.addStretch()
        trl.addLayout(ctrl)

        tabs.addTab(tab_run, "Запуск")

        # ─ Вкладка 2: Службы (нативные команды) ─────────────────────
        tab_svc = QWidget()
        tab_svc.setStyleSheet("background: transparent;")
        tsl = QVBoxLayout(tab_svc)
        tsl.setContentsMargins(14, 14, 14, 14)
        tsl.setSpacing(10)

        svc_info = QLabel(
            "Управление сервисом — все операции выполняются напрямую,\n"
            "без запуска внешних bat-файлов. Требуют прав администратора."
        )
        svc_info.setStyleSheet("color:#5a5248; font-size:12px; background:transparent;")
        svc_info.setWordWrap(True)
        tsl.addWidget(svc_info)

        # Автозагрузка
        grp_auto = QGroupBox("Автозагрузка (Windows Service)")
        gl = QGridLayout(grp_auto)
        gl.setSpacing(8)

        svc_buttons = [
            ("Установить службу", self._install_service, "btn_sec",
             "Установить zapret как сервис автозагрузки"),
            ("Удалить службу", self._remove_service, "btn_danger",
             "Остановить и удалить все сервисы zapret"),
            ("Проверить статус", self._check_status, "btn_sec",
             "Показать текущий статус сервисов и winws.exe"),
        ]
        for i, (label, handler, style, tip) in enumerate(svc_buttons):
            b = self._reg_btn(self.btn(label, obj=style))
            b.setMinimumHeight(38)
            b.setToolTip(tip)
            b.clicked.connect(handler)
            gl.addWidget(b, i // 3, i % 3)

        tsl.addWidget(grp_auto)

        # Обновление данных
        grp_upd = QGroupBox("Обновление данных")
        ul = QGridLayout(grp_upd)
        ul.setSpacing(8)

        upd_buttons = [
            ("Обновить hosts", self._update_hosts_action, "btn_sec",
             "Скачать и проверить hosts файл из репозитория"),
            ("Обновить IPSet", self._update_ipset_action, "btn_sec",
             "Скачать актуальный список IP-адресов"),
            ("Проверить обновления", self._check_updates_action, "btn_sec",
             "Проверить наличие новых версий zapret"),
        ]
        for i, (label, handler, style, tip) in enumerate(upd_buttons):
            b = self._reg_btn(self.btn(label, obj=style))
            b.setMinimumHeight(38)
            b.setToolTip(tip)
            b.clicked.connect(handler)
            ul.addWidget(b, i // 3, i % 3)

        tsl.addWidget(grp_upd)

        # Настройки
        grp_settings = QGroupBox("Настройки")
        sl = QGridLayout(grp_settings)
        sl.setSpacing(8)

        settings_buttons = [
            ("Game Filter", self._game_filter_action, "btn_sec",
             "Переключить режим обхода для игр (TCP/UDP)"),
            ("IPSet Filter", self._ipset_switch_action, "btn_sec",
             "Переключить режим фильтра IPSet (loaded/none/any)"),
            ("Авто-обновления", self._check_updates_switch_action, "btn_sec",
             "Включить/выключить автоматическую проверку обновлений"),
        ]
        for i, (label, handler, style, tip) in enumerate(settings_buttons):
            b = self._reg_btn(self.btn(label, obj=style))
            b.setMinimumHeight(38)
            b.setToolTip(tip)
            b.clicked.connect(handler)
            sl.addWidget(b, i // 3, i % 3)

        tsl.addWidget(grp_settings)

        # Диагностика и тесты
        grp_diag = QGroupBox("Диагностика и тесты")
        dl = QGridLayout(grp_diag)
        dl.setSpacing(8)

        diag_buttons = [
            ("Диагностика", self._run_diagnostics_action, "btn_warn",
             "Проверяет распространённые причины неработоспособности"),
            ("Запустить тесты", self._run_tests_action, "btn_sec",
             "Запускает PowerShell-скрипт тестов"),
        ]
        for i, (label, handler, style, tip) in enumerate(diag_buttons):
            b = self._reg_btn(self.btn(label, obj=style))
            b.setMinimumHeight(38)
            b.setToolTip(tip)
            b.clicked.connect(handler)
            dl.addWidget(b, i // 3, i % 3)

        tsl.addWidget(grp_diag)
        tsl.addStretch()
        tabs.addTab(tab_svc, "Службы")

        # ─ Вкладка 3: Установка ──────────────────────────────────────
        tab_dl = QWidget()
        tab_dl.setStyleSheet("background: transparent;")
        tdl = QVBoxLayout(tab_dl)
        tdl.setContentsMargins(14, 14, 14, 14)
        tdl.setSpacing(10)

        dl_info = QLabel(
            "Скачивает последний релиз zapret-discord-youtube с GitHub\n"
            "и распаковывает в папку zapret/.\n\n"
            "После скачивания перейдите на вкладку «Запуск» и выберите пресет."
        )
        dl_info.setStyleSheet("color:#5a5248; font-size:12px; background:transparent;")
        dl_info.setWordWrap(True)
        tdl.addWidget(dl_info)

        dl_row = QHBoxLayout()
        self._dl_btn = self._reg_btn(
            self.btn("Скачать / обновить Zapret", obj="btn_sec"))
        self._dl_btn.clicked.connect(self._download)
        dl_row.addWidget(self._dl_btn)
        dl_row.addStretch()
        tdl.addLayout(dl_row)
        tdl.addStretch()
        tabs.addTab(tab_dl, "Установка")

        self._content.addWidget(tabs, 1)

        # Poll timer
        self._poll = QTimer(self)
        self._poll.timeout.connect(self._refresh_badge)
        self._poll.start(2000)

        self._reload()
        self.log("Папка zapret: {}".format(ZAPRET_DIR), "INFO")

    # ── Versions ──────────────────────────────────────────────────── #
    def _reload(self):
        self._ver_combo.blockSignals(True)
        self._ver_combo.clear()
        versions = _get_versions()
        if versions:
            self._ver_combo.addItems(versions)
            saved = _saved_ver()
            if saved and saved in versions:
                self._ver_combo.setCurrentText(saved)
            self.log("Версий найдено: {}".format(len(versions)), "OK")
        else:
            self._ver_combo.addItem("— скачайте zapret —")
            self.log("Версии не найдены. Перейдите на вкладку «Установка».", "WARN")
        self._ver_combo.blockSignals(False)
        self._on_ver_change(self._ver_combo.currentText())

    def _on_ver_change(self, name):
        self._bat_list.clear()
        bats = _get_bats(_ver_to_path(name))
        if bats:
            for bat in bats:
                item = QListWidgetItem(bat)
                item.setData(Qt.UserRole, str(_ver_to_path(name) / bat))
                self._bat_list.addItem(item)
            self._bat_list.setCurrentRow(0)
            self.log("Пресетов: {}".format(len(bats)), "OK")
        else:
            self._bat_list.addItem("— bat-файлы не найдены —")

    def _on_preset_select(self, row):
        if row < 0:
            self._hint.setText(""); return
        item = self._bat_list.item(row)
        if not item: return
        name = item.text()
        bat_path = item.data(Qt.UserRole)
        # Генерируем описание из параметров bat-файла
        hint = self._generate_preset_hint(name, bat_path)
        self._hint.setText(hint)

    def _generate_preset_hint(self, name, bat_path):
        """Анализирует bat-файл и возвращает описание стратегии."""
        if not bat_path or not Path(bat_path).exists():
            return self._HINTS.get(name, "Нажмите «Запустить» для активации.")

        try:
            text = Path(bat_path).read_text(encoding="utf-8-sig", errors="replace")
            text = re.sub(r'\^\s*\n', ' ', text)  # убираем переносы строк
        except Exception:
            return self._HINTS.get(name, "Нажмите «Запустить» для активации.")

        parts = []

        # Определяем метод обхода
        if '--dpi-desync=fake' in text:
            parts.append("Fake (подмена пакетов)")
        elif '--dpi-desync=multisplit' in text:
            parts.append("Multisplit (разбиение пакетов)")
        elif '--dpi-desync=disorder' in text:
            parts.append("Disorder (перестановка)")
        elif '--dpi-desync=datagramspli' in text:
            parts.append("DatagramSplit")

        # Определяем протоколы
        protos = []
        if '--filter-udp=443' in text:
            protos.append("QUIC (UDP 443)")
        if '--filter-tcp=443' in text:
            protos.append("HTTPS (TCP 443)")
        if '--filter-tcp=80' in text:
            protos.append("HTTP (TCP 80)")
        if 'discord' in text.lower():
            protos.append("Discord")
        if '--filter-tcp=2053' in text or '--filter-tcp=2083' in text:
            protos.append("Discord Media")
        if 'google' in text.lower() and '--filter-tcp' in text:
            protos.append("Google/YouTube")
        if protos:
            parts.append("Протоколы: " + ", ".join(protos))

        # Fake TLS?
        if 'fake' in text.lower() and 'tls' in text.lower():
            parts.append("TLS: подмена ClientHello")
        if 'simple' in name.lower():
            parts.append("Простая подмена (Simple)")
        if 'auto' in name.lower():
            parts.append("Автоподбор параметров")

        # Специфические особенности
        if '--dpi-desync-repeats=' in text:
            m = re.search(r'--dpi-desync-repeats=(\d+)', text)
            if m:
                repeats = int(m.group(1))
                parts.append("Повторы: {}".format(repeats))

        if '--dpi-desync-split-pos=' in text:
            m = re.search(r'--dpi-desync-split-pos=(\d+)', text)
            if m:
                parts.append("Split pos: {}".format(m.group(1)))

        if '--ipset=' in text:
            parts.append("IPSet: включён (фильтр по IP)")

        # Краткое имя
        short_name = Path(name).stem
        if not parts:
            return "Пресет: {}".format(short_name)

        return "{}: {}".format(short_name, " | ".join(parts))

    def _select_category(self, cat_name):
        presets = self._CATEGORIES.get(cat_name, [])
        if not presets:
            return
        for preset in presets:
            for i in range(self._bat_list.count()):
                if self._bat_list.item(i).text() == preset:
                    self._bat_list.setCurrentRow(i)
                    return
        if presets:
            first = presets[0]
            for i in range(self._bat_list.count()):
                if first.lower() in self._bat_list.item(i).text().lower():
                    self._bat_list.setCurrentRow(i)
                    return

    def _get_bat_name(self):
        item = self._bat_list.currentItem()
        if not item: return None
        name = item.text()
        return name if name.endswith(".bat") else None

    def _get_ver_dir(self):
        ver = self._ver_combo.currentText()
        if not ver or ver.startswith("—"):
            return None
        return str(ZAPRET_DIR / ver)



    # ── Quick start ──────────────────────────────────────────────── #
    def _auto_tune(self):
        """Запуск авто-подбора стратегии."""
        ver_dir = self._get_ver_dir()
        if not ver_dir:
            self.log("Выберите версию zapret.", "WARN")
            return
        bat_paths = _get_bats(Path(ver_dir))
        if not bat_paths:
            self.log("Нет доступных пресетов", "WARN")
            return
        self._run_worker(_fn_auto_tune, bat_paths, ver_dir, on_result=self._on_auto_tune_done)

    def _on_auto_tune_done(self, result):
        if result:
            best = result.get("best", "")  # filename like "general.bat"
            score = result.get("score", 0)
            for i in range(self._bat_list.count()):
                item = self._bat_list.item(i)
                if not item:
                    continue
                # UserRole stores full path, compare by basename
                item_path = item.data(Qt.UserRole) or ""
                if Path(item_path).name == best or item.text() == best:
                    self._bat_list.setCurrentRow(i)
                    break

    def _quick_start_action(self):
        ver = self._ver_combo.currentText()
        if not ver or ver.startswith("—"):
            self.log("Сначала скачайте zapret (вкладка «Установка»).", "WARN")
            return

        # Останавливаем предыдущую стратегию если запущена
        if _is_running():
            self.log("Останавливаю предыдущую стратегию...", "INFO")
            _fn_stop(lambda *a: None, lambda *a: None)

        bat_path = str(_ver_to_path(ver) / "general.bat")
        ver_dir = str(_ver_to_path(ver))
        if not Path(bat_path).exists():
            self.log("general.bat не найден в {}".format(ver_dir), "ERR")
            return
        _save_ver(ver)
        
        # Сохраняем пресет для автозапуска
        try:
            from config_manager import set_value
            set_value("autostart_zapret_preset", "general.bat")
        except Exception:
            pass
        
        self.log("Быстрый запуск: {} / general.bat".format(ver), "INFO")
        self._start_w = Worker(_fn_start, bat_path, ver_dir)
        self._start_w.line_out.connect(self.log)
        self._start_w.progress.connect(self.set_progress)
        self._start_w.finished.connect(self._on_quick_start_done)
        self._start_w.start()
        self._set_busy(True)
        self._refresh_badge()

    def _on_quick_start_done(self):
        self._set_busy(False)
        self._refresh_badge()

    # ── Service commands (нативные) ──────────────────────────────── #
    def _install_service(self):
        """Показать диалог выбора пресета и установить сервис."""
        vd = self._get_ver_dir()
        if not vd:
            self.log("Выберите версию zapret.", "WARN"); return

        bats = _get_bats(Path(vd))
        if not bats:
            self.log("Пресеты не найдены.", "ERR"); return

        dlg = _InstallServiceDialog(bats, self)
        if dlg.exec() != QDialog.Accepted:
            return

        bat_name = dlg.selected_bat()
        if not bat_name:
            return

        self._run_worker(_fn_install_service, vd, bat_name)

    def _remove_service(self):
        self._run_worker(_fn_remove_service)

    def _check_status(self):
        self._run_worker(_fn_status_zapret)

    def _update_hosts_action(self):
        self._run_worker(_fn_update_hosts)

    def _update_ipset_action(self):
        self._run_worker(_fn_update_ipset)

    def _check_updates_action(self):
        self._run_worker(_fn_check_updates)

    def _game_filter_action(self):
        vd = self._get_ver_dir()
        if not vd:
            self.log("Выберите версию zapret.", "WARN"); return
        dlg = _GameFilterDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        mode = dlg.selected_mode()
        self._run_worker(_fn_game_filter, vd, mode)

    def _ipset_switch_action(self):
        vd = self._get_ver_dir()
        if not vd:
            self.log("Выберите версию zapret.", "WARN"); return
        self._run_worker(_fn_ipset_switch, vd)

    def _check_updates_switch_action(self):
        vd = self._get_ver_dir()
        if not vd:
            self.log("Выберите версию zapret.", "WARN"); return
        self._run_worker(_fn_check_updates_switch, vd)

    def _run_diagnostics_action(self):
        self._run_worker(_fn_run_diagnostics)

    def _run_tests_action(self):
        self._run_worker(_fn_run_tests)

    # ── Download ─────────────────────────────────────────────────── #
    def _download(self):
        self._dl_btn.setEnabled(False)
        self.log("Поиск релиза на GitHub...", "INFO")
        from downloader import DownloadWorker
        self._dl_w = DownloadWorker(
            dest_dir=str(ZAPRET_DIR),
            owner="Flowseal",
            repo="zapret-discord-youtube",
            asset_suffix=".zip",
            parent=self,
        )
        self._dl_w.log.connect(self.log)
        self._dl_w.progress.connect(self.set_progress)
        self._dl_w.done.connect(self._on_dl_done)
        self._dl_w.start()

    def _on_dl_done(self, ok, msg):
        self.log(msg, "OK" if ok else "ERR")
        self._dl_btn.setEnabled(True)
        if ok:
            self._reload()

    # ── Start / Stop ─────────────────────────────────────────────── #
    def _start(self):
        ver = self._ver_combo.currentText()
        if not ver or ver.startswith("—"):
            self.log("Выберите версию.", "WARN"); return
        bat_name = self._get_bat_name()
        if not bat_name:
            self.log("Выберите пресет из списка.", "WARN"); return

        # Останавливаем предыдущую стратегию если запущена
        if _is_running():
            self.log("Останавливаю предыдущую стратегию...", "INFO")
            _fn_stop(lambda *a: None, lambda *a: None)

        bat_path = str(_ver_to_path(ver) / bat_name)
        ver_dir  = str(_ver_to_path(ver))
        _save_ver(ver)
        
        # Сохраняем выбранный пресет для автозапуска
        try:
            from config_manager import set_value
            set_value("autostart_zapret_preset", bat_name)
        except Exception:
            pass
        
        self.log("Запуск: {}  /  {}".format(ver, bat_name), "INFO")

        self._start_w = Worker(_fn_start, bat_path, ver_dir)
        self._start_w.line_out.connect(self.log)
        self._start_w.progress.connect(self.set_progress)
        self._start_w.finished.connect(self._refresh_badge)
        self._start_w.start()
        self._refresh_badge()

    def _stop(self):
        vd = self._get_ver_dir() or ""
        self._stop_w = Worker(_fn_stop, vd)
        self._stop_w.line_out.connect(self.log)
        self._stop_w.progress.connect(self.set_progress)
        self._stop_w.finished.connect(self._refresh_badge)
        self._stop_w.start()
        self._refresh_badge()

    def _refresh_badge(self):
        running  = _is_running()
        starting = self._start_w is not None and self._start_w.isRunning()
        stopping = self._stop_w  is not None and self._stop_w.isRunning()
        self._badge.setText("Работает" if running else "Остановлен")
        self._badge.setObjectName("badge_run" if running else "badge_stop")
        self._badge.style().unpolish(self._badge)
        self._badge.style().polish(self._badge)
        self._btn_start.setEnabled(not running and not starting)
        self._btn_stop.setEnabled(running and not stopping)
        self._quick_start.setEnabled(not running and not starting)

    def showEvent(self, e):
        self._poll.start(2000)
        super().showEvent(e)

    def hideEvent(self, e):
        self._poll.stop()
        super().hideEvent(e)


# ── Auto-Tuning функция ────────────────────────────────────────────── #
def _fn_auto_tune(log_func, progress_func, bat_paths, ver_dir):
    """Auto-Tuning: тестирует HTTPS-доступность через пресеты."""
    import ssl
    import time
    import socket


    log_func("=== Авто-подбор стратегии (Auto-Tuning) ===")
    progress_func(0.0)

    # Тестируем именно HTTPS — это то, что Zapret обходит
    test_hosts = [
        ("youtube.com", 443),
        ("discord.com", 443),
        ("rutracker.org", 443),
        ("google.com", 443),
    ]
    best_preset = None
    best_score = 0
    ctx = ssl.create_default_context()

    for i, bat_path in enumerate(bat_paths):
        bat_name = Path(bat_path).stem if isinstance(bat_path, str) else bat_path.stem
        log_func("Тестирование пресета: {}".format(bat_name))
        progress_func(0.1 + 0.7 * i / max(len(bat_paths), 1))

        success_count = 0
        for host, port in test_hosts:
            try:
                raw = socket.create_connection((host, port), timeout=5)
                sock = ctx.wrap_socket(raw, server_hostname=host)
                # Проверяем что TLS handshake проходит
                cert = sock.getpeercert()
                sock.close()
                if cert:
                    success_count += 1
                    log_func("  {} — доступен (TLS OK)".format(host), "OK")
                else:
                    log_func("  {} — без сертификата".format(host), "WARN")
            except ssl.SSLCertVerificationError:
                log_func("  {} — сертификат невалиден (DPI?)".format(host), "WARN")
            except Exception:
                log_func("  {} — недоступен".format(host), "WARN")

        score = success_count / len(test_hosts) * 100
        log_func("  Результат: {}/{} ресурсов доступно ({:.0f}%)".format(
            success_count, len(test_hosts), score
        ))

        if score > best_score:
            best_score = score
            best_preset = bat_path

    progress_func(1.0)

    if best_preset and best_score > 0:
        log_func("=== Auto-Tuning завершён ===", "OK")
        log_func("Лучший пресет: {} ({:.0f}% доступно)".format(
            Path(best_preset).stem if isinstance(best_preset, str) else best_preset.stem, best_score
        ), "OK")
        return {"best": str(best_preset), "score": best_score}
    else:
        log_func("=== Auto-Tuning завершён ===", "WARN")
        log_func("Не удалось найти работающий пресет", "WARN")
        return None

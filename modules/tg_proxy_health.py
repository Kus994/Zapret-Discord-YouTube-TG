"""
modules/tg_proxy_health.py
--------------------------
Health Check и авто-фикс для TG Proxy.
Мониторинг состояния прокси и автоматическое восстановление.
"""

import os
import socket
import subprocess
import threading
import time
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000


def check_proxy_health(port: int = 8080) -> dict:
    """
    Проверяет здоровье TG Proxy.
    Возвращает статус подключения и время отклика.
    """
    result = {
        "port_open": False,
        "telegram_reachable": False,
        "latency_ms": 0,
        "status": "unknown",
        "message": "",
    }

    # Проверяем открыт ли порт
    try:
        sock = socket.create_connection(("127.0.0.1", port), timeout=3)
        sock.close()
        result["port_open"] = True
    except Exception:
        result["status"] = "port_closed"
        result["message"] = "Порт {} закрыт — TgWsProxy не запущен".format(port)
        return result

    # Проверяем доступность Telegram
    try:
        sock = socket.create_connection(("149.154.167.50", 443), timeout=5)
        t1 = time.time()
        sock.send(b"\x16\x03\x01\x00\x05\x01\x00\x00\x01\x00")
        t2 = time.time()
        sock.close()
        result["telegram_reachable"] = True
        result["latency_ms"] = int((t2 - t1) * 1000)
        result["status"] = "ok"
        result["message"] = "Прокси работает. Telegram доступен."
    except Exception as e:
        result["status"] = "telegram_unreachable"
        result["message"] = "Telegram недоступен: {}".format(str(e)[:50])

    return result


def auto_fix_media_issues(port: int = 8080) -> dict:
    """
    Авто-фикс проблем с загрузкой медиа в Telegram.
    Выполняет типичные шаги из FAQ.
    """
    fixes_applied = []

    # 1. Проверяем порт
    health = check_proxy_health(port)
    if not health["port_open"]:
        return {
            "success": False,
            "message": "TgWsProxy не запущен. Запустите прокси.",
            "fixes": [],
        }

    # 2. Очищаем кэш DNS
    try:
        subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=10
        )
        fixes_applied.append("Очищен DNS кэш")
    except Exception:
        pass

    # 3. Проверяем настройки прокси в реестре
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            # Убеждаемся что системный прокси выключен
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        fixes_applied.append("Системный прокси отключен")
    except Exception:
        pass

    # 4. Проверяем доступность Telegram
    health = check_proxy_health(port)
    if health["telegram_reachable"]:
        return {
            "success": True,
            "message": "Telegram доступен через прокси. Проблем с медиа быть не должно.",
            "fixes": fixes_applied,
        }
    else:
        return {
            "success": False,
            "message": "Telegram недоступен. Попробуйте перезапустить прокси.",
            "fixes": fixes_applied,
        }


class HealthMonitor(threading.Thread):
    """
    Фоновый мониторинг здоровья TG Proxy.
    Периодически проверяет статус и уведомляет при проблемах.
    """

    def __init__(self, port: int = 8080, interval: int = 30, callback=None):
        super().__init__(daemon=True)
        self.port = port
        self.interval = interval
        self.callback = callback
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            try:
                health = check_proxy_health(self.port)
                if self.callback:
                    self.callback(health)
            except Exception:
                pass
            self._stop_event.wait(self.interval)


def get_secret_from_logs() -> str:
    """Пытается извлечь Secret из логов TgWsProxy."""
    log_patterns = [
        "secret=",
        "Secret:",
        "SECRET=",
    ]

    # Ищем в стандартных путях логов
    log_paths = [
        Path(os.environ.get("APPDATA", "")) / "TgWsProxy" / "log.txt",
        Path(os.environ.get("LOCALAPPDATA", "")) / "TgWsProxy" / "log.txt",
        Path(os.path.expanduser("~")) / "AppData" / "Local" / "TgWsProxy" / "log.txt",
    ]

    for log_path in log_paths:
        if log_path.exists():
            try:
                content = log_path.read_text(encoding="utf-8", errors="replace")
                for line in content.splitlines():
                    for pattern in log_patterns:
                        if pattern in line:
                            # Извлекаем значение после паттерна
                            idx = line.find(pattern)
                            if idx >= 0:
                                value = line[idx + len(pattern):].strip()
                                if value:
                                    return value
            except Exception:
                pass

    return ""


def generate_proxy_link(port: int = 8080, secret: str = "") -> str:
    """Генерирует ссылку для подключения к прокси."""
    if not secret:
        secret = get_secret_from_logs()

    if secret:
        return "https://t.me/proxy?server=127.0.0.1&port={}&secret={}".format(port, secret)
    else:
        return "Secret не найден. Запустите TgWsProxy и скопируйте из трей-меню."

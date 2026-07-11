"""
config_manager.py — KUS Pro
Единый менеджер конфигурации с файловым lock.

Все страницы используют load_config() / save_config() вместо
независимых json.load/dump — это гарантирует целостность данных
при одновременном доступе из разных страниц.
"""

import json
import threading
from app_paths import CONFIG_FILE

_lock = threading.Lock()

DEFAULTS = {
    "game_mode": {
        "apps": [],
        "disable_transparency": True,
        "enable_taskbar_autohide": True,
        "auto_return_enabled": False,
        "auto_return_minutes": 60,
        "hotkey": "",
    },
    "autostart_zapret": False,
    "autostart_zapret_preset": "",
    "autostart_tg_proxy": False,
    "tg_proxy_port": 8080,
    "start_minimized": False,
    "auto_update_enabled": True,
    "auto_update_zapret": True,
    "auto_update_tg_proxy": True,
    "tg_bot_token": "",
    "tg_bot_chat_id": "",
}


def load_config() -> dict:
    """Загружает конфигурацию. Возвращает копию — безопасно модифицировать."""
    with _lock:
        if CONFIG_FILE.exists():
            try:
                with CONFIG_FILE.open(encoding="utf-8") as f:
                    data = json.load(f)
                # Гарантируем наличие всех ключей верхнего уровня
                for k, v in DEFAULTS.items():
                    if k not in data:
                        data[k] = v if not isinstance(v, dict) else dict(v)
                    elif isinstance(v, dict):
                        for sk, sv in v.items():
                            data[k].setdefault(sk, sv)
                return data
            except Exception:
                pass
        return json.loads(json.dumps(DEFAULTS))


def save_config(data: dict):
    """Сохраняет конфигурацию. Атомарная запись через temp-файл."""
    with _lock:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CONFIG_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(CONFIG_FILE)


def get_section(section: str):
    """Возвращает секцию конфига (например 'game_mode')."""
    with _lock:
        if CONFIG_FILE.exists():
            try:
                with CONFIG_FILE.open(encoding="utf-8") as f:
                    data = json.load(f)
                return data.get(section, {})
            except Exception:
                pass
        return {}


def set_section(section: str, value):
    """Обновляет секцию конфига."""
    with _lock:
        data = {}
        if CONFIG_FILE.exists():
            try:
                with CONFIG_FILE.open(encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        data[section] = value
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CONFIG_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(CONFIG_FILE)


def get_value(key, default=None):
    """Возвращает значение верхнего уровня."""
    with _lock:
        if CONFIG_FILE.exists():
            try:
                with CONFIG_FILE.open(encoding="utf-8") as f:
                    data = json.load(f)
                return data.get(key, default)
            except Exception:
                pass
        return DEFAULTS.get(key, default)


def set_value(key, value):
    """Устанавливает значение верхнего уровня."""
    with _lock:
        data = {}
        if CONFIG_FILE.exists():
            try:
                with CONFIG_FILE.open(encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        data[key] = value
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CONFIG_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(CONFIG_FILE)

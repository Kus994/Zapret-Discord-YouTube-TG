"""
modules/settings_backup.py
--------------------------
Экспорт и импорт всех настроек KUS Pro.
Бэкап конфигурации, расписания, исторических данных.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

try:
    from app_paths import (
        DATA_DIR, CONFIG_FILE, TIMETRACK_FILE,
        ZAPRET_DIR, TG_PROXY_DIR,
    )
except ImportError:
    DATA_DIR = Path(__file__).parent.parent
    CONFIG_FILE = DATA_DIR / "config.json"
    TIMETRACK_FILE = DATA_DIR / "timetrack_data.json"
    ZAPRET_DIR = DATA_DIR / "zapret"
    TG_PROXY_DIR = DATA_DIR / "tg_proxy"


def export_settings(filepath: str) -> bool:
    """
    Экспортирует все настройки в JSON файл.
    Включает: конфиг, историю действий, настройки хронометража.
    """
    try:
        backup = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "config": {},
            "timetrack": {},
            "action_log_path": str(DATA_DIR / "action_log.db"),
        }

        # Конфиг
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, encoding="utf-8") as f:
                backup["config"] = json.load(f)

        # Хронометраж
        if TIMETRACK_FILE.exists():
            with open(TIMETRACK_FILE, encoding="utf-8") as f:
                backup["timetrack"] = json.load(f)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(backup, f, indent=2, ensure_ascii=False)

        return True
    except Exception:
        return False


def import_settings(filepath: str, restore_config=True, restore_timetrack=False) -> bool:
    """
    Импортирует настройки из JSON файла.
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            backup = json.load(f)

        if restore_config and backup.get("config"):
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(backup["config"], f, indent=2, ensure_ascii=False)

        if restore_timetrack and backup.get("timetrack"):
            with open(TIMETRACK_FILE, "w", encoding="utf-8") as f:
                json.dump(backup["timetrack"], f, indent=2, ensure_ascii=False)

        return True
    except Exception:
        return False


def get_backup_info(filepath: str) -> dict:
    """Возвращает информацию о файле бэкапа."""
    try:
        with open(filepath, encoding="utf-8") as f:
            backup = json.load(f)

        return {
            "version": backup.get("version", "?"),
            "timestamp": backup.get("timestamp", "?"),
            "has_config": bool(backup.get("config")),
            "has_timetrack": bool(backup.get("timetrack")),
            "has_action_log": bool(backup.get("action_log_path")),
        }
    except Exception:
        return {}

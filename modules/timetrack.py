"""
modules/timetrack.py
---------------------
Хронометраж рабочего времени — по методике «сначала фиксируем реальную
картину, потом ищем пожирателей времени»: несколько дней подряд
записывается, на что уходит время, а потом это анализируется.

Два источника данных:
  1. Автоматический — какое окно/приложение было активно и сколько
     секунд. Работает ТОЛЬКО после явного согласия пользователя
     (has_consent() == True) и ничего не отправляет наружу — всё
     хранится локально, в JSON-файле рядом с приложением.
     Фиксируется только имя процесса и заголовок окна, НЕ содержимое
     экрана, НЕ нажатия клавиш и НЕ текст из окон.
  2. Ручной — пользователь сам записывает бытовые/рабочие дела
     (например «Работа: созвон с клиентом», «Быт: готовка ужина»).

Согласие хранится персистентно (consent=False по умолчанию при первом
запуске) — включение автослежения требует явного действия пользователя
в UI, это не переключатель "по умолчанию включено".
"""

import os
import sys
import json
import uuid
import threading
import datetime as dt
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

# Используем app_paths для определения пути к файлу данных
# чтобы корректно работать и в dev-режиме, и в frozen .exe
try:
    from app_paths import TIMETRACK_FILE as DATA_FILE
except ImportError:
    DATA_FILE = Path(os.path.dirname(os.path.abspath(__file__))).parent / "timetrack_data.json"

_lock = threading.Lock()

DEFAULT_DATA = {
    "consent": False,          # согласие на автослежение за активным окном
    "app_categories": {},      # {"chrome.exe": "distracting", ...}
    "days": {},                # {"2026-07-01": {"auto": {...}, "manual": [...]}}
}

CATEGORIES = ["Работа", "Быт", "Учёба", "Отдых", "Другое"]

# Категории приложений для авто-слежения (используются, чтобы отметить
# «пожирателей времени» — то, что обычно отвлекает).
APP_CATEGORY_LABELS = {
    "productive": "Продуктивно",
    "distracting": "Отвлекает",
    "neutral": "Нейтрально",
}


def _today_key() -> str:
    return dt.date.today().isoformat()


def load_data() -> dict:
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open(encoding="utf-8") as f:
                data = json.load(f)
            merged = json.loads(json.dumps(DEFAULT_DATA))
            merged.update(data)
            # гарантируем наличие всех ключей верхнего уровня, даже если
            # файл был создан более старой версией модуля
            for k, v in DEFAULT_DATA.items():
                merged.setdefault(k, v)
            return merged
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_DATA))


def save_data(data: dict):
    with _lock:
        tmp = DATA_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(DATA_FILE)  # атомарная замена — не оставит битый файл при сбое посреди записи


# ── Согласие ─────────────────────────────────────────────────────── #
def has_consent() -> bool:
    return bool(load_data().get("consent", False))


def set_consent(value: bool):
    data = load_data()
    data["consent"] = bool(value)
    save_data(data)


# ── Активное окно (только Windows) ──────────────────────────────── #
def get_active_window():
    """Возвращает (имя_процесса, заголовок_окна) активного сейчас окна.
    (None, None), если недоступно (не Windows / нет прав / нет psutil)."""
    if sys.platform != "win32":
        return None, None
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None, None

        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or "(без заголовка)"

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        name = "unknown"
        if psutil is not None and pid.value:
            try:
                name = psutil.Process(pid.value).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return name, title
    except Exception:
        return None, None


# ── Тики автослежения (дергает QTimer страницы) ─────────────────── #
def tick(seconds: int):
    """Фиксирует, что последние `seconds` секунд активным было текущее
    окно. Ничего не делает, если пользователь не давал согласия —
    это защита на уровне модуля, а не только UI-переключатель."""
    if not has_consent():
        return None
    name, title = get_active_window()
    if not name:
        return None

    data = load_data()
    day = data["days"].setdefault(_today_key(), {"auto": {}, "manual": []})
    entry = day["auto"].setdefault(name, {"seconds": 0, "last_title": ""})
    entry["seconds"] += int(seconds)
    entry["last_title"] = title
    save_data(data)
    return {"app": name, "title": title, "total_seconds": entry["seconds"]}


# ── Ручные записи ─────────────────────────────────────────────────── #
def add_manual_entry(category: str, name: str, minutes: float, note: str = "") -> dict:
    if minutes <= 0:
        raise ValueError("Длительность должна быть больше нуля.")
    if not name.strip():
        raise ValueError("Укажите название дела.")

    data = load_data()
    day = data["days"].setdefault(_today_key(), {"auto": {}, "manual": []})
    entry = {
        "id": uuid.uuid4().hex[:8],
        "time": dt.datetime.now().strftime("%H:%M"),
        "category": category if category in CATEGORIES else "Другое",
        "name": name.strip(),
        "minutes": float(minutes),
        "note": note.strip(),
    }
    day["manual"].append(entry)
    save_data(data)
    return entry


def delete_manual_entry(entry_id: str, day_key: str = None) -> bool:
    data = load_data()
    day_key = day_key or _today_key()
    day = data["days"].get(day_key)
    if not day:
        return False
    before = len(day.get("manual", []))
    day["manual"] = [e for e in day.get("manual", []) if e["id"] != entry_id]
    save_data(data)
    return len(day["manual"]) < before


# ── Категоризация приложений ────────────────────────────────────── #
def set_app_category(app_name: str, category: str):
    """category: 'productive' | 'distracting' | 'neutral'"""
    data = load_data()
    data["app_categories"][app_name] = category
    save_data(data)


def get_app_category(app_name: str, data: dict = None) -> str:
    data = data or load_data()
    return data.get("app_categories", {}).get(app_name, "neutral")


# ── Сводки / анализ ──────────────────────────────────────────────── #
def get_day_summary(day_key: str = None) -> dict:
    """Сводка за день: список авто-записей (app, seconds, category),
    список ручных записей, итоговые суммы и «топ пожирателей времени»
    (самые долгие непродуктивные/нейтральные окна)."""
    data = load_data()
    day_key = day_key or _today_key()
    day = data["days"].get(day_key, {"auto": {}, "manual": []})

    auto_rows = []
    for app, info in day.get("auto", {}).items():
        auto_rows.append({
            "app": app,
            "seconds": info.get("seconds", 0),
            "last_title": info.get("last_title", ""),
            "category": get_app_category(app, data),
        })
    auto_rows.sort(key=lambda r: r["seconds"], reverse=True)

    manual_rows = sorted(day.get("manual", []), key=lambda e: e.get("time", ""))

    total_auto = sum(r["seconds"] for r in auto_rows)
    total_manual_min = sum(e["minutes"] for e in manual_rows)
    distracting_seconds = sum(r["seconds"] for r in auto_rows if r["category"] == "distracting")

    return {
        "date": day_key,
        "auto": auto_rows,
        "manual": manual_rows,
        "total_auto_seconds": total_auto,
        "total_manual_minutes": total_manual_min,
        "distracting_seconds": distracting_seconds,
        "top_eaters": auto_rows[:5],
    }


def get_recent_days(n: int = 7):
    """Список дат (YYYY-MM-DD) за последние n дней, для которых есть
    хоть какие-то записи — для простого недельного обзора."""
    data = load_data()
    all_days = sorted(data.get("days", {}).keys(), reverse=True)
    return all_days[:n]


def format_hms(seconds) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} ч {m:02d} мин"
    if m:
        return f"{m} мин {s:02d} с"
    return f"{s} с"


def format_minutes(minutes) -> str:
    return format_hms(int(minutes * 60))

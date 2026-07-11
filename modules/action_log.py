"""
modules/action_log.py
---------------------
Журнал всех выполненных действий в KUS Pro.
Хранит историю операций для возможности отслеживания и отката.

Использует SQLite для лёгковесного хранения без внешних зависимостей.
"""

import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

try:
    from app_paths import DATA_DIR
    DB_PATH = DATA_DIR / "action_log.db"
except ImportError:
    DB_PATH = Path(__file__).parent.parent / "action_log.db"

_lock = threading.RLock()
_initialized = False
_conn = None  # Persistent connection


def _get_conn():
    """Возвращает постоянное соединение с БД (создаёт при необходимости)."""
    global _conn, _initialized

    with _lock:
        if _conn is not None:
            return _conn

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)

        if not _initialized:
            _conn.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    details TEXT,
                    status TEXT DEFAULT 'ok',
                    undoable INTEGER DEFAULT 0
                )
            """)
            _conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_type ON actions(type)")
            _conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON actions(timestamp DESC)")
            _conn.commit()
            _initialized = True

        return _conn


def log_action(action_type: str, description: str, details: str = "",
               status: str = "ok", undoable: bool = False):
    """
    Записывает действие в журнал.

    action_type: "cleanup", "kill_process", "dns_change", "service_change",
                 "game_mode", "settings_change", "export", "speed_test", и т.д.
    description: человекочитаемое описание
    details: JSON-строка с доп. данными (необязательно)
    status: "ok", "error", "warning"
    undoable: можно ли отменить действие
    """
    with _lock:
        try:
            conn = _get_conn()
            conn.execute(
                "INSERT INTO actions (timestamp, type, description, details, status, undoable) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now().isoformat(),
                    action_type,
                    description,
                    details,
                    status,
                    1 if undoable else 0,
                )
            )
            conn.commit()
        except Exception:
            pass


def get_actions(action_type: str = None, limit: int = 100, days: int = None) -> list:
    """
    Возвращает список действий из журнала.

    action_type: фильтр по типу (None = все)
    limit: максимальное количество записей
    days: только за последние N дней (None = все)
    """
    query = "SELECT id, timestamp, type, description, details, status, undoable FROM actions"
    params = []

    conditions = []
    if action_type:
        conditions.append("type = ?")
        params.append(action_type)
    if days:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        conditions.append("timestamp >= ?")
        params.append(since)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    with _lock:
        try:
            conn = _get_conn()
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "type": row[2],
                    "description": row[3],
                    "details": row[4],
                    "status": row[5],
                    "undoable": bool(row[6]),
                }
                for row in rows
            ]
        except Exception:
            return []


def get_action_count(action_type: str = None) -> int:
    """Возвращает количество действий (опционально по типу)."""
    query = "SELECT COUNT(*) FROM actions"
    params = []
    if action_type:
        query += " WHERE type = ?"
        params.append(action_type)

    with _lock:
        try:
            conn = _get_conn()
            return conn.execute(query, params).fetchone()[0]
        except Exception:
            return 0


def clear_old_actions(days: int = 30):
    """Удаляет действия старше N дней."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with _lock:
        try:
            conn = _get_conn()
            conn.execute("DELETE FROM actions WHERE timestamp < ?", (cutoff,))
            conn.commit()
        except Exception:
            pass


def get_stats() -> dict:
    """Возвращает статистику по действиям."""
    with _lock:
        try:
            conn = _get_conn()

            total = conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0]

            by_type = {}
            rows = conn.execute("SELECT type, COUNT(*) FROM actions GROUP BY type").fetchall()
            for row in rows:
                by_type[row[0]] = row[1]

            by_status = {}
            rows = conn.execute("SELECT status, COUNT(*) FROM actions GROUP BY status").fetchall()
            for row in rows:
                by_status[row[0]] = row[1]

            today = datetime.now().date().isoformat()
            today_count = conn.execute(
                "SELECT COUNT(*) FROM actions WHERE timestamp >= ?", (today,)
            ).fetchone()[0]

            return {
                "total": total,
                "by_type": by_type,
                "by_status": by_status,
                "today": today_count,
            }
        except Exception:
            return {"total": 0, "by_type": {}, "by_status": {}, "today": 0}

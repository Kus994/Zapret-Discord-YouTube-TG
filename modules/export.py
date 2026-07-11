"""
modules/export.py
-----------------
Экспорт данных KUS Pro в различные форматы.

Функции:
  - Экспорт отчётов в CSV, JSON, HTML
  - Экспорт списка процессов
  - Экспорт истории действий
  - Экспорт настроек
"""

import csv
import json
import html
from datetime import datetime
from pathlib import Path


def export_processes_csv(processes: list, filepath: str) -> bool:
    """Экспортирует список процессов в CSV."""
    try:
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["PID", "Имя", "Память (МБ)", "CPU %", "Диск (МБ/с)", "Пользователь", "Статус", "Тип"])
            for p in processes:
                writer.writerow([
                    p.get("pid", ""),
                    p.get("name", ""),
                    p.get("memory_mb", 0),
                    p.get("cpu_percent", 0),
                    p.get("disk_mb_s", 0),
                    p.get("user", "—"),
                    p.get("status", "—"),
                    "Приложение" if p.get("is_app") else "Фоновый",
                ])
        return True
    except Exception:
        return False


def export_processes_json(processes: list, filepath: str) -> bool:
    """Экспортирует список процессов в JSON."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(processes, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def export_processes_html(processes: list, filepath: str) -> bool:
    """Экспортирует список процессов в HTML-таблицу."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>KUS Pro — Список процессов</title>
<style>
body { font-family: 'Segoe UI', sans-serif; background: #0a0e1a; color: #e8ddd0; padding: 20px; }
h1 { color: #00ff88; }
table { border-collapse: collapse; width: 100%; margin-top: 20px; }
th { background: #1a1e2e; color: #00ff88; padding: 10px; text-align: left; border-bottom: 2px solid #00ff88; }
td { padding: 8px 10px; border-bottom: 1px solid #1a1e2e; }
tr:hover { background: #1a1e2e; }
.app { color: #00ff88; }
.bg { color: #a8a098; }
</style>
</head>
<body>
<h1>KUS Pro — Список процессов</h1>
<p>Экспортировано: {}</p>
<p>Всего процессов: {}</p>
<table>
<tr><th>PID</th><th>Имя</th><th>Память (МБ)</th><th>CPU %</th><th>Диск (МБ/с)</th><th>Пользователь</th><th>Статус</th></tr>
""".format(datetime.now().strftime("%d.%m.%Y %H:%M:%S"), len(processes)))

            for p in processes:
                cls = "app" if p.get("is_app") else "bg"
                f.write('<tr class="{}"><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>\n'.format(
                    cls,
                    p.get("pid", ""),
                    html.escape(str(p.get("name", ""))),
                    p.get("memory_mb", 0),
                    p.get("cpu_percent", 0),
                    p.get("disk_mb_s", 0),
                    html.escape(str(p.get("user", "—"))),
                    p.get("status", "—"),
                ))

            f.write("</table>\n</body>\n</html>")
        return True
    except Exception:
        return False


def export_timetrack_csv(day_summary: dict, filepath: str) -> bool:
    """Экспортирует сводку хронометража в CSV."""
    try:
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Тип", "Приложение/Дело", "Категория", "Время", "Заголовок"])

            for entry in day_summary.get("auto", []):
                seconds = entry.get("seconds", 0)
                h, rem = divmod(seconds, 3600)
                m, s = divmod(rem, 60)
                time_str = "{}ч {}мин {}с".format(h, m, s) if h else "{}мин {}с".format(m, s)
                writer.writerow(["Авто", entry.get("app", ""), entry.get("category", ""), time_str, entry.get("last_title", "")])

            for entry in day_summary.get("manual", []):
                writer.writerow(["Ручная", entry.get("name", ""), entry.get("category", ""), "{} мин".format(entry.get("minutes", 0)), entry.get("note", "")])

        return True
    except Exception:
        return False


def export_timetrack_html(day_summary: dict, filepath: str) -> bool:
    """Экспортирует сводку хронометража в HTML."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>KUS Pro — Отчёт за {}</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; background: #0a0e1a; color: #e8ddd0; padding: 20px; }}
h1 {{ color: #00ff88; }}
h2 {{ color: #f5a623; margin-top: 30px; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
th {{ background: #1a1e2e; color: #00ff88; padding: 10px; text-align: left; }}
td {{ padding: 8px 10px; border-bottom: 1px solid #1a1e2e; }}
.total {{ font-size: 18px; color: #f5a623; margin: 10px 0; }}
</style>
</head>
<body>
<h1>Отчёт KUS Pro — {}</h1>
""".format(day_summary.get("date", ""), day_summary.get("date", "")))

            total_auto = day_summary.get("total_auto_seconds", 0)
            total_manual = day_summary.get("total_manual_minutes", 0)
            distracting = day_summary.get("distracting_seconds", 0)

            f.write('<p class="total">Время за ПК: <b>{} сек</b></p>\n'.format(total_auto))
            f.write('<p class="total">Ручные записи: <b>{} мин</b></p>\n'.format(total_manual))
            f.write('<p class="total">Отвлекающие: <b>{} сек</b></p>\n'.format(distracting))

            # Авто-записи
            auto = day_summary.get("auto", [])
            if auto:
                f.write("<h2>Приложения</h2>\n<table>\n<tr><th>Приложение</th><th>Время (сек)</th><th>Категория</th></tr>\n")
                for entry in auto:
                    f.write("<tr><td>{}</td><td>{}</td><td>{}</td></tr>\n".format(
                        html.escape(str(entry.get("app", ""))),
                        entry.get("seconds", 0),
                        entry.get("category", "—"),
                    ))
                f.write("</table>\n")

            # Ручные записи
            manual = day_summary.get("manual", [])
            if manual:
                f.write("<h2>Ручные записи</h2>\n<table>\n<tr><th>Дело</th><th>Категория</th><th>Время (мин)</th><th>Заметка</th></tr>\n")
                for entry in manual:
                    f.write("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>\n".format(
                        html.escape(str(entry.get("name", ""))),
                        entry.get("category", ""),
                        entry.get("minutes", 0),
                        html.escape(str(entry.get("note", ""))),
                    ))
                f.write("</table>\n")

            f.write("</body>\n</html>")
        return True
    except Exception:
        return False


def export_settings_json(config: dict, filepath: str) -> bool:
    """Экспортирует настройки в JSON."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def export_action_log_csv(actions: list, filepath: str) -> bool:
    """Экспортирует историю действий в CSV."""
    try:
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Дата/Время", "Тип", "Описание", "Статус"])
            for a in actions:
                writer.writerow([
                    a.get("timestamp", ""),
                    a.get("type", ""),
                    a.get("description", ""),
                    a.get("status", ""),
                ])
        return True
    except Exception:
        return False

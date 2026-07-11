"""
tg_bot.py — KUS Pro
Модуль для отправки отчётов хронометража в Telegram.
Использует Telegram Bot API (https://core.telegram.org/bots/api).

Как настроить:
  1. Создайте бота через @BotFather в Telegram
  2. Получите токен бота
  3. Узнайте ваш chat_id (напишите боту /start, затем
     откройте https://api.telegram.org/bot<TOKEN>/getUpdates)
  4. Вставьте токен и chat_id в настройки
"""

import json
import datetime
import urllib.request
import urllib.error
from typing import Optional


def send_message(token: str, chat_id: str, text: str,
                 parse_mode: str = "HTML") -> dict:
    """Отправляет текстовое сообщение в Telegram."""
    url = "https://api.telegram.org/bot{}/sendMessage".format(token)
    data = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def test_connection(token: str, chat_id: str) -> tuple:
    """Проверяет подключение к Telegram. Возвращает (ok, message)."""
    try:
        result = send_message(token, chat_id,
                              "<b>KUS Pro</b>\nТестовое сообщение отправлено успешно!")
        if result.get("ok"):
            return True, "Соединение установлено! Сообщение отправлено."
        return False, "Ошибка: {}".format(result.get("description", "неизвестная"))
    except urllib.error.URLError as e:
        return False, "Ошибка сети: {}".format(getattr(e, "reason", e))
    except Exception as e:
        return False, "Ошибка: {}".format(e)


def format_daily_report(summary: dict) -> str:
    """Форматирует отчёт за день для Telegram (HTML)."""
    lines = []
    lines.append("<b>Отчёт за {}</b>".format(
        datetime.date.today().strftime("%d.%m.%Y")))

    total_auto = summary.get("total_auto_seconds", 0)
    total_manual = summary.get("total_manual_minutes", 0)
    distracting = summary.get("distracting_seconds", 0)

    lines.append("")
    lines.append("Время за ПК: <b>{}</b>".format(_fmt_hms(total_auto)))
    lines.append("Ручные записи: <b>{}</b>".format(_fmt_min(total_manual)))
    lines.append("Отвлекающие: <b>{}</b>".format(_fmt_hms(distracting)))

    # Топ приложений
    auto = summary.get("auto", [])
    if auto:
        lines.append("")
        lines.append("<b>Топ приложений:</b>")
        for i, entry in enumerate(sorted(auto, key=lambda x: -x["seconds"])[:8], 1):
            lines.append("{}. {} — {}".format(
                i, entry["app"], _fmt_hms(entry["seconds"])))

    # Ручные записи
    manual = summary.get("manual", [])
    if manual:
        lines.append("")
        lines.append("<b>Ручные записи:</b>")
        for entry in manual:
            lines.append("• {} ({}) — {} мин".format(
                entry["name"], entry["category"],
                int(entry["minutes"])))

    return "\n".join(lines)


def format_weekly_report(daily_summaries: list) -> str:
    """Форматирует недельный отчёт для Telegram (HTML)."""
    lines = []
    lines.append("<b>Недельный отчёт KUS Pro</b>")
    lines.append("")

    total_auto = sum(d.get("total_auto_seconds", 0) for d in daily_summaries)
    total_manual = sum(d.get("total_manual_minutes", 0) for d in daily_summaries)

    lines.append("Общее время за ПК: <b>{}</b>".format(_fmt_hms(total_auto)))
    lines.append("Все ручные записи: <b>{}</b>".format(_fmt_min(total_manual)))

    # Среднее в день
    days = len(daily_summaries) or 1
    lines.append("Среднее в день: <b>{}</b>".format(_fmt_hms(total_auto // days)))

    # Топ приложений за неделю
    app_totals = {}
    for d in daily_summaries:
        for entry in d.get("auto", []):
            app = entry["app"]
            app_totals[app] = app_totals.get(app, 0) + entry["seconds"]

    if app_totals:
        lines.append("")
        lines.append("<b>Топ за неделю:</b>")
        top = sorted(app_totals.items(), key=lambda x: -x[1])[:8]
        for i, (app, secs) in enumerate(top, 1):
            lines.append("{}. {} — {}".format(i, app, _fmt_hms(secs)))

    return "\n".join(lines)


def _fmt_hms(total_seconds: int) -> str:
    """Форматирует секунды в часы:минуты:секунды."""
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    if h > 0:
        return "{}ч {}мин".format(h, m)
    if m > 0:
        return "{}мин {}с".format(m, s)
    return "{}с".format(s)


def _fmt_min(minutes: float) -> str:
    """Форматирует минуты."""
    m = int(minutes)
    if m >= 60:
        return "{}ч {}мин".format(m // 60, m % 60)
    return "{}мин".format(m)

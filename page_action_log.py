"""
page_action_log.py — Страница истории действий KUS Pro.
"""

from PyQt5.QtWidgets import (
    QLabel, QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QPushButton,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush

from base_page import BasePage
from theme import TEXT_MAIN, TEXT_DIM, ACCENT, SUCCESS, WARNING, DANGER
from qt_compat import *


class ActionLogPage(BasePage):
    """Страница истории действий с фильтрацией и статистикой."""
    PAGE_TITLE = "История действий"
    PAGE_SUB = "Журнал всех операций KUS Pro"

    def build_ui(self):

        # Фильтры
        filter_row = QHBoxLayout()

        self._filter_type = QComboBox()
        self._filter_type.addItems(["Все типы", "Очистка", "Процессы", "DNS", "Службы", "Игровой режим", "Экспорт", "Настройки"])
        self._filter_type.currentTextChanged.connect(self._load_actions)
        filter_row.addWidget(self._filter_type, 1)

        self._filter_period = QComboBox()
        self._filter_period.addItems(["Все время", "Сегодня", "За неделю", "За месяц"])
        self._filter_period.currentTextChanged.connect(self._load_actions)
        filter_row.addWidget(self._filter_period, 1)

        btn_refresh = self.btn("Обновить", ":refresh")
        btn_refresh.clicked.connect(self._load_actions)
        filter_row.addWidget(btn_refresh)

        self._content.addLayout(filter_row)

        # Статистика
        self._stats_label = QLabel()
        self._stats_label.setStyleSheet("color:{}; font-size:12px; margin: 8px 0;".format(TEXT_DIM))
        self._content.addWidget(self._stats_label)

        # Таблица
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["Дата/Время", "Тип", "Описание", "Статус", ""])
        self._table.horizontalHeader().setSectionResizeMode(2, Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._content.addWidget(self._table)

        self._content.addWidget(self._log_box)

        self._load_actions()

    def _load_actions(self):
        """Загружает и отображает действия."""
        from modules.action_log import get_actions, get_stats


        type_filter = self._filter_type.currentText()
        period_filter = self._filter_period.currentText()

        # Маппинг типов
        type_map = {
            "Очистка": "cleanup",
            "Процессы": "kill_process",
            "DNS": "dns_change",
            "Службы": "service_change",
            "Игровой режим": "game_mode",
            "Экспорт": "export",
            "Настройки": "settings_change",
        }
        action_type = type_map.get(type_filter)

        # Маппинг периодов
        days_map = {
            "Сегодня": 1,
            "За неделю": 7,
            "За месяц": 30,
        }
        days = days_map.get(period_filter)

        actions = get_actions(action_type=action_type, limit=500, days=days)

        # Статистика
        stats = get_stats()
        self._stats_label.setText(
            "Всего действий: {} | Сегодня: {}".format(stats["total"], stats["today"])
        )

        # Заполняем таблицу
        self._table.setRowCount(len(actions))

        status_colors = {
            "ok": SUCCESS,
            "error": DANGER,
            "warning": WARNING,
        }

        type_labels = {
            "cleanup": "Очистка",
            "kill_process": "Процессы",
            "dns_change": "DNS",
            "service_change": "Службы",
            "game_mode": "Игровой режим",
            "export": "Экспорт",
            "settings_change": "Настройки",
        }

        for i, action in enumerate(actions):
            # Дата/время
            ts = action.get("timestamp", "")
            if "T" in ts:
                ts = ts.replace("T", " ")[:19]
            date_item = QTableWidgetItem(ts)
            date_item.setFlags(date_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(i, 0, date_item)

            # Тип
            type_item = QTableWidgetItem(type_labels.get(action.get("type", ""), action.get("type", "")))
            type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(i, 1, type_item)

            # Описание
            desc_item = QTableWidgetItem(action.get("description", ""))
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(i, 2, desc_item)

            # Статус
            status = action.get("status", "ok")
            status_item = QTableWidgetItem("OK" if status == "ok" else "Ошибка" if status == "error" else "Предупреждение")
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            status_color = status_colors.get(status, TEXT_DIM)
            status_item.setForeground(QBrush(QColor(status_color)))
            self._table.setItem(i, 3, status_item)

            # Действие (пустая колонка для будущего undo)
            action_item = QTableWidgetItem("")
            action_item.setFlags(action_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(i, 4, action_item)

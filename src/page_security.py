"""
page_security.py — KUS Pro
Страница «Безопасность»: аудит автозагрузки Windows (реестр Run +
папка автозагрузки) с простыми эвристическими предупреждениями.

Это НЕ замена антивирусу — модуль не определяет вредоносность,
только показывает, что и откуда стартует автоматически, и явно
помечает потенциально подозрительные признаки (несуществующий файл,
запуск из Temp, закодированный PowerShell), чтобы пользователь мог
сам разобраться, нужна ли эта запись.
"""

from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from qt_compat import *

from base_page import BasePage
from theme import TABLE_QSS


def _fn_scan(log_func, progress_func):
    from modules.security import get_all_autostart_entries
    return get_all_autostart_entries(log_func, progress_func)


def _fn_remove(log_func, progress_func, entry):
    from modules.security import remove_autostart_entry

    return remove_autostart_entry(log_func, progress_func, entry)


class SecurityPage(BasePage):
    PAGE_TITLE = "🛡️  Безопасность"
    PAGE_SUB   = "Аудит автозагрузки Windows: что и откуда стартует вместе с системой"

    def build_ui(self):
        info = QLabel(
            "Показывает программы, которые запускаются автоматически при входе в "
            "Windows (реестр Run + папка автозагрузки). Это не антивирусная проверка — "
            "предупреждения (⚠) лишь обращают внимание на признаки, которые стоит "
            "проверить самостоятельно: отсутствующий файл, запуск из Temp и т.п."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#6a6258; font-size:11px; background:transparent;")
        self._content.addWidget(info)

        row = QHBoxLayout()
        b_scan = self._reg_btn(self.btn("🔍  Сканировать автозагрузку"))
        b_scan.clicked.connect(self._scan)
        row.addWidget(b_scan)

        self._b_remove = self._reg_btn(self.btn("🗑  Удалить выбранное", obj="btn_danger"))
        self._b_remove.clicked.connect(self._remove_selected)
        self._b_remove.setEnabled(False)
        row.addWidget(self._b_remove)
        row.addStretch()
        self._content.addLayout(row)

        self._summary = QLabel("Нажмите «Сканировать автозагрузку», чтобы увидеть список.")
        self._summary.setStyleSheet("color:#a8a098; font-size:11px; background:transparent;")
        self._content.addWidget(self._summary)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["ИМЯ", "ИСТОЧНИК", "ПУТЬ", "СТАТУС"])
        self._table.setStyleSheet(TABLE_QSS)
        self._table.setShowGrid(False)
        self._table.setSelectionBehavior(SelectRows)
        self._table.setEditTriggers(NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(32)
        self._table.setFrameShape(NoFrame)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Fixed); hdr.resizeSection(0, 140)
        hdr.setSectionResizeMode(1, QHeaderView.Fixed); hdr.resizeSection(1, 130)
        hdr.setSectionResizeMode(2, Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.Fixed); hdr.resizeSection(3, 200)
        self._content.addWidget(self._table)
        self._content.addStretch()

        self._entries = []

    def _scan(self):
        self._table.setRowCount(0)
        self._b_remove.setEnabled(False)
        self._run_worker(_fn_scan, on_result=self._fill_table)

    def _fill_table(self, entries):
        self._entries = entries

        if not entries:
            self._summary.setText("Записи автозагрузки не найдены.")
            self._table.setRowCount(0)
            return

        warn_count = sum(1 for e in entries if e["warnings"])
        self._summary.setText(
            "Найдено записей: {}. С предупреждениями: {}.".format(len(entries), warn_count)
        )

        self._table.setRowCount(len(entries))
        bold = QFont(); bold.setBold(True)

        for r, e in enumerate(entries):
            name_item = QTableWidgetItem(e["name"])
            if e["warnings"]:
                name_item.setForeground(QColor("#f5c842"))
                name_item.setFont(bold)
            else:
                name_item.setForeground(QColor("#ddd8d0"))
            self._table.setItem(r, 0, name_item)

            src_item = QTableWidgetItem(e["source"])
            src_item.setForeground(QColor("#7a7068"))
            self._table.setItem(r, 1, src_item)

            path_item = QTableWidgetItem(e.get("exe_path") or e["command"])
            path_item.setForeground(QColor("#a8a098"))
            self._table.setItem(r, 2, path_item)

            if e["warnings"]:
                status_text = "⚠  " + "; ".join(e["warnings"])
                status_color = "#f5c842"
            else:
                status_text = "✓  В норме"
                status_color = "#4caf7d"
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(status_color))
            self._table.setItem(r, 3, status_item)

        self._b_remove.setEnabled(True)

    def _remove_selected(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._entries):
            self.log("Выберите запись в таблице перед удалением.", "WARN")
            return

        entry = self._entries[row]
        if QMessageBox.question(
            self, "Удаление записи автозагрузки",
            "Удалить «{}» из автозагрузки?\n\nИсточник: {}\n"
            "Это не удаляет саму программу — только запись о её "
            "автоматическом запуске.".format(entry["name"], entry["source"]),
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return

        self._run_worker(_fn_remove, entry, on_result=lambda ok: self._after_remove(ok, row))

    def _after_remove(self, success, row):
        if success and 0 <= row < len(self._entries):
            self._entries.pop(row)
            self._fill_table(self._entries)

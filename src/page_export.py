"""
page_export.py — Страница экспорта данных KUS Pro.
"""

import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QLabel, QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt

from base_page import BasePage
from theme import TEXT_MAIN, TEXT_DIM, ACCENT
from qt_compat import *


class ExportPage(BasePage):
    """Страница экспорта данных в различные форматы."""

    PAGE_TITLE = "📤  Экспорт данных"
    PAGE_SUB = "Экспорт отчётов, процессов и настроек"

    def build_ui(self):
        # Экспорт процессов
        self._content.addWidget(self._section_label("Процессы"))

        row1 = QHBoxLayout()
        btn_csv = self._reg_btn(self.btn("📄  Экспорт в CSV", "btn_sec"))
        btn_csv.setFixedHeight(38)
        btn_csv.clicked.connect(lambda: self._export_processes("csv"))
        row1.addWidget(btn_csv)

        btn_json = self._reg_btn(self.btn("📋  Экспорт в JSON", "btn_sec"))
        btn_json.setFixedHeight(38)
        btn_json.clicked.connect(lambda: self._export_processes("json"))
        row1.addWidget(btn_json)

        btn_html = self._reg_btn(self.btn("🌐  Экспорт в HTML", "btn_sec"))
        btn_html.setFixedHeight(38)
        btn_html.clicked.connect(lambda: self._export_processes("html"))
        row1.addWidget(btn_html)

        self._content.addLayout(row1)

        # Экспорт хронометража
        self._content.addWidget(self._section_label("Хронометраж"))

        row2 = QHBoxLayout()
        btn_tt_csv = self._reg_btn(self.btn("📊  Сводка за день (CSV)", "btn_sec"))
        btn_tt_csv.setFixedHeight(38)
        btn_tt_csv.clicked.connect(lambda: self._export_timetrack("csv"))
        row2.addWidget(btn_tt_csv)

        btn_tt_html = self._reg_btn(self.btn("📈  Сводка за день (HTML)", "btn_sec"))
        btn_tt_html.setFixedHeight(38)
        btn_tt_html.clicked.connect(lambda: self._export_timetrack("html"))
        row2.addWidget(btn_tt_html)

        self._content.addLayout(row2)

        # Экспорт истории действий
        self._content.addWidget(self._section_label("История действий"))

        row3 = QHBoxLayout()
        btn_log_csv = self._reg_btn(self.btn("📝  История (CSV)", "btn_sec"))
        btn_log_csv.setFixedHeight(38)
        btn_log_csv.clicked.connect(lambda: self._export_action_log("csv"))
        row3.addWidget(btn_log_csv)

        btn_log_json = self._reg_btn(self.btn("📑  История (JSON)", "btn_sec"))
        btn_log_json.setFixedHeight(38)
        btn_log_json.clicked.connect(lambda: self._export_action_log("json"))
        row3.addWidget(btn_log_json)

        self._content.addLayout(row3)

        # Экспорт настроек
        self._content.addWidget(self._section_label("Настройки"))

        row4 = QHBoxLayout()
        btn_settings = self._reg_btn(self.btn("⚙️  Экспорт настроек (JSON)", "btn_sec"))
        btn_settings.setFixedHeight(38)
        btn_settings.clicked.connect(self._export_settings)
        row4.addWidget(btn_settings)
        row4.addStretch()
        self._content.addLayout(row4)

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color:{}; font-size:14px; font-weight:700; margin-top:16px;".format(ACCENT))
        return lbl

    def _export_processes(self, fmt):
        """Экспортирует текущий список процессов."""
        from modules.processes import list_processes
        from modules.export import export_processes_csv, export_processes_json, export_processes_html
        from modules.action_log import log_action

        processes = list_processes(log_func=self.log, progress_func=self.set_progress)

        filters = {"csv": "CSV (*.csv)", "json": "JSON (*.json)", "html": "HTML (*.html)"}
        ext = {"csv": ".csv", "json": ".json", "html": ".html"}

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить список процессов",
            str(Path.home() / "Desktop" / "processes{}".format(ext[fmt])),
            filters[fmt],
        )
        if not path:
            return

        exporters = {"csv": export_processes_csv, "json": export_processes_json, "html": export_processes_html}
        success = exporters[fmt](processes, path)

        if success:
            self.log("Процессы экспортированы: {}".format(path), "OK")
            log_action("export", "Экспорт списка процессов в {}".format(fmt.upper()), path)
        else:
            self.log("Ошибка экспорта", "ERR")

    def _export_timetrack(self, fmt):
        """Экспортирует сводку хронометража за сегодня."""
        from modules.timetrack import get_day_summary
        from modules.export import export_timetrack_csv, export_timetrack_html
        from modules.action_log import log_action

        summary = get_day_summary()

        filters = {"csv": "CSV (*.csv)", "html": "HTML (*.html)"}
        ext = {"csv": ".csv", "html": ".html"}

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить сводку хронометража",
            str(Path.home() / "Desktop" / "timetrack{}{}".format(summary.get("date", ""), ext[fmt])),
            filters[fmt],
        )
        if not path:
            return

        exporters = {"csv": export_timetrack_csv, "html": export_timetrack_html}
        success = exporters[fmt](summary, path)

        if success:
            self.log("Хронометраж экспортирован: {}".format(path), "OK")
            log_action("export", "Экспорт хронометража в {}".format(fmt.upper()), path)
        else:
            self.log("Ошибка экспорта", "ERR")

    def _export_action_log(self, fmt):
        """Экспортирует историю действий."""
        from modules.action_log import get_actions, log_action as log_act

        actions = get_actions(limit=1000)

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить историю действий",
            str(Path.home() / "Desktop" / "action_log.csv"),
            "CSV (*.csv)" if fmt == "csv" else "JSON (*.json)",
        )
        if not path:
            return

        if fmt == "csv":
            from modules.export import export_action_log_csv
            success = export_action_log_csv(actions, path)
        else:
            import json
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(actions, f, indent=2, ensure_ascii=False)
                success = True
            except Exception:
                success = False

        if success:
            self.log("История действий экспортирована: {}".format(path), "OK")
            log_act("export", "Экспорт истории действий", path)
        else:
            self.log("Ошибка экспорта", "ERR")

    def _export_settings(self):
        """Экспортирует настройки."""
        from config_manager import load_config
        from modules.export import export_settings_json
        from modules.action_log import log_action


        config = load_config()

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить настройки",
            str(Path.home() / "Desktop" / "kus_pro_settings.json"),
            "JSON (*.json)",
        )
        if not path:
            return

        success = export_settings_json(config, path)

        if success:
            self.log("Настройки экспортированы: {}".format(path), "OK")
            log_action("export", "Экспорт настроек", path)
        else:
            self.log("Ошибка экспорта", "ERR")

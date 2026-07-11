"""
page_services.py — Страница управления службами Windows KUS Pro.
"""

from PyQt5.QtWidgets import (
    QLabel, QHBoxLayout, QVBoxLayout, QFrame, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu,
    QMessageBox, QComboBox, QAction,
)
from PyQt5.QtGui import QFont, QColor, QBrush
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from base_page import BasePage
from theme import TEXT_MAIN, TEXT_DIM, ACCENT, SUCCESS, WARNING, DANGER, BG_CARD
from qt_compat import *


class _ServicesWorker(QThread):
    """Фоновый поток для загрузки списка служб."""
    log = pyqtSignal(str, str)
    progress = pyqtSignal(float)
    result = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        from modules.services import list_services
        services = list_services(
            log_func=lambda msg, lvl="INFO": self.log.emit(msg, lvl),
            progress_func=lambda p: self.progress.emit(p),
        )
        self.result.emit(services)


class ServicesPage(BasePage):
    """Страница управления службами Windows."""
    PAGE_TITLE = "Службы Windows"
    PAGE_SUB = "Управление системными службами"

    def build_ui(self):

        # Поиск и фильтры
        filter_row = QHBoxLayout()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Поиск служб...")
        self._search.textChanged.connect(self._filter_services)
        filter_row.addWidget(self._search, 2)

        self._filter_status = QComboBox()
        self._filter_status.addItems(["Все", "Запущены", "Остановлены"])
        self._filter_status.currentTextChanged.connect(self._filter_services)
        filter_row.addWidget(self._filter_status, 1)

        self._filter_start = QComboBox()
        self._filter_start.addItems(["Все", "Авто", "Вручную", "Отключена"])
        self._filter_start.currentTextChanged.connect(self._filter_services)
        filter_row.addWidget(self._filter_start, 1)

        self._btn_refresh = self.btn("Обновить", ":refresh")
        self._btn_refresh.clicked.connect(self._load_services)
        filter_row.addWidget(self._btn_refresh)

        self._content.addLayout(filter_row)

        # Таблица служб
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["Имя", "Отображаемое имя", "Статус", "Тип запуска", "PID"])
        self._table.horizontalHeader().setSectionResizeMode(1, Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._context_menu)
        self._table.doubleClicked.connect(self._toggle_service)
        self._content.addWidget(self._table)

        # Статус бар
        self._status_label = QLabel("Загрузка...")
        self._status_label.setStyleSheet("color:{}; font-size:12px;".format(TEXT_DIM))
        self._content.addWidget(self._status_label)

        self._services = []
        self._load_services()

    def _load_services(self):
        """Загружает список служб в фоновом потоке."""
        self._btn_refresh.setEnabled(False)
        self._set_busy(True)
        self._status_label.setText("Загрузка списка служб...")

        self._worker = _ServicesWorker(self)
        self._worker.log.connect(self.log)
        self._worker.progress.connect(self.set_progress)
        self._worker.result.connect(self._on_services_loaded)
        self._worker.finished.connect(lambda: self._set_busy(False))
        self._worker.start()

    def _on_services_loaded(self, services):
        """Обработчик загрузки служб."""
        self._services = services
        self._btn_refresh.setEnabled(True)
        self._populate_table(services)
        self._status_label.setText("Загружено служб: {}".format(len(services)))

    def _populate_table(self, services):
        """Заполняет таблицу службами."""
        self._table.setRowCount(len(services))

        status_colors = {
            "Running": SUCCESS,
            "Stopped": TEXT_DIM,
            "Paused": WARNING,
            "StartPending": ACCENT,
        }

        for i, svc in enumerate(services):
            # Имя
            name_item = QTableWidgetItem(svc.get("name", ""))
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(i, 0, name_item)

            # Отображаемое имя
            display_item = QTableWidgetItem(svc.get("display_name", ""))
            display_item.setFlags(display_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(i, 1, display_item)

            # Статус
            status = svc.get("status", "Unknown")
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            status_color = status_colors.get(status, TEXT_DIM)
            status_item.setForeground(QBrush(QColor(status_color)))
            self._table.setItem(i, 2, status_item)

            # Тип запуска
            start_item = QTableWidgetItem(svc.get("start_type", "Unknown"))
            start_item.setFlags(start_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(i, 3, start_item)

            # PID
            pid = svc.get("pid")
            pid_item = QTableWidgetItem(str(pid) if pid else "—")
            pid_item.setFlags(pid_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(i, 4, pid_item)

    def _filter_services(self):
        """Фильтрует таблицу по поиску и фильтрам."""
        query = self._search.text().lower()
        status_filter = self._filter_status.currentText()
        start_filter = self._filter_start.currentText()

        filtered = []
        for svc in self._services:
            # Поиск
            if query and query not in svc.get("name", "").lower() and query not in svc.get("display_name", "").lower():
                continue

            # Фильтр по статусу
            if status_filter == "Запущены" and svc.get("status") != "Running":
                continue
            if status_filter == "Остановлены" and svc.get("status") != "Stopped":
                continue

            # Фильтр по типу запуска
            start_type = svc.get("start_type", "")
            if start_filter == "Авто" and start_type != "Auto":
                continue
            if start_filter == "Вручную" and start_type != "Manual":
                continue
            if start_filter == "Отключена" and start_type != "Disabled":
                continue

            filtered.append(svc)

        self._populate_table(filtered)

    def _context_menu(self, position):
        """Контекстное меню для службы."""
        row = self._table.rowAt(position.y())
        if row < 0:
            return

        name_item = self._table.item(row, 0)
        if not name_item:
            return

        service_name = name_item.text()
        svc = next((s for s in self._services if s.get("name") == service_name), None)
        if not svc:
            return

        menu = QMenu(self)

        if svc.get("status") == "Running":
            stop_action = menu.addAction("Остановить")
            stop_action.triggered.connect(lambda: self._stop_service(service_name))
            restart_action = menu.addAction("Перезапустить")
            restart_action.triggered.connect(lambda: self._restart_service(service_name))
        else:
            start_action = menu.addAction("Запустить")
            start_action.triggered.connect(lambda: self._start_service(service_name))

        menu.addSeparator()

        auto_action = menu.addAction("Авто-запуск")
        auto_action.triggered.connect(lambda: self._set_start_type(service_name, "auto"))
        manual_action = menu.addAction("Вручную")
        manual_action.triggered.connect(lambda: self._set_start_type(service_name, "manual"))
        disabled_action = menu.addAction("Отключена")
        disabled_action.triggered.connect(lambda: self._set_start_type(service_name, "disabled"))

        menu.exec_(self._table.viewport().mapToGlobal(position))

    def _toggle_service(self):
        """Переключает состояние службы (двойной клик)."""
        row = self._table.currentRow()
        if row < 0:
            return

        name_item = self._table.item(row, 0)
        status_item = self._table.item(row, 2)
        if not name_item or not status_item:
            return

        service_name = name_item.text()
        if status_item.text() == "Running":
            self._stop_service(service_name)
        else:
            self._start_service(service_name)

    def _start_service(self, name):
        def _do():
            from modules.services import start_service
            return start_service(name, log_func=self.log)
        self._run_worker(_do, on_done=lambda: self._load_services())

    def _stop_service(self, name):
        def _do():
            from modules.services import stop_service
            return stop_service(name, log_func=self.log)
        self._run_worker(_do, on_done=lambda: self._load_services())

    def _restart_service(self, name):
        def _do():
            from modules.services import restart_service
            return restart_service(name, log_func=self.log)
        self._run_worker(_do, on_done=lambda: self._load_services())

    def _set_start_type(self, name, start_type):
        def _do():
            from modules.services import set_start_type

            return set_start_type(name, start_type, log_func=self.log)
        self._run_worker(_do, on_done=lambda: self._load_services())

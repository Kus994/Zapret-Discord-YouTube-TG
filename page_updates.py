"""
page_updates.py — KUS Pro
Страница обновлений: KUS Pro, Windows, компоненты.
"""

import os
import json
import webbrowser
from pathlib import Path

from qt_compat import *

from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QTextEdit, QTabWidget, QWidget,
    QFrame, QProgressBar, QFileDialog, QMessageBox,
    QCheckBox, QComboBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from base_page import BasePage
from app_paths import ZAPRET_DIR


class _UpdateCheckThread(QThread):
    result = pyqtSignal(bool, str, str, str)

    def run(self):
        try:
            from auto_updater import check_kus_pro_update
            has, cur, lat, url = check_kus_pro_update()
            self.result.emit(has, cur, lat, url)
        except Exception as e:
            from theme import VERSION
            self.result.emit(False, VERSION, "", str(e))


def _fn_windows_updates(log_func, progress_func, auto_install):
    from modules.updates import search_and_install_windows_updates
    search_and_install_windows_updates(log_func, progress_func,
                                       auto_install=auto_install)


def _fn_drivers(log_func, progress_func):
    from modules.updates import search_driver_updates
    search_driver_updates(log_func, progress_func)


def _fn_register_task(log_func, progress_func, schedule, time_str):
    from modules.updates import register_scheduled_task
    return register_scheduled_task(log_func, progress_func,
                                   schedule=schedule, time_str=time_str)


def _fn_unregister_task(log_func, progress_func):
    from modules.updates import unregister_scheduled_task
    return unregister_scheduled_task(log_func, progress_func)


class UpdatesPage(BasePage):
    PAGE_TITLE = "🔄 Обновления"
    PAGE_SUB = "KUS Pro, Windows, компоненты"

    def build_ui(self):
        tabs = QTabWidget()

        # ══════════════════════════════════════════════════════════════
        #  Вкладка 1: KUS Pro
        # ══════════════════════════════════════════════════════════════
        tab_kus = QWidget()
        tab_kus.setStyleSheet("background: transparent;")
        kl = QVBoxLayout(tab_kus)
        kl.setContentsMargins(14, 14, 14, 14)
        kl.setSpacing(12)

        grp_ver = QGroupBox("Текущая версия")
        vl = QGridLayout(grp_ver)
        vl.setSpacing(8)

        try:
            from theme import VERSION
            ver_text = "KUS Pro v{}".format(VERSION)
        except Exception:
            ver_text = "KUS Pro"

        self._cur_version = QLabel(ver_text)
        self._cur_version.setStyleSheet("color:#00ff88; font-size:18px; font-weight:bold; background:transparent;")
        vl.addWidget(self._cur_version, 0, 0, 1, 2)

        self._update_status = QLabel("Нажмите «Проверить обновления»")
        self._update_status.setStyleSheet("color:#5a5248; font-size:12px; background:transparent;")
        vl.addWidget(self._update_status, 1, 0, 1, 2)

        btn_check = self._reg_btn(self.btn("Проверить обновления", obj="btn_glow"))
        btn_check.setFixedHeight(40)
        btn_check.clicked.connect(self._check_kus_update)
        vl.addWidget(btn_check, 2, 0)

        self._btn_download = QPushButton("Скачать обновление")
        self._btn_download.setFixedHeight(40)
        self._btn_download.setStyleSheet(
            "QPushButton { color:#fff; background:#2d8a4e; border:none; "
            "border-radius:8px; padding:0 24px; font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#38a85c; }"
            "QPushButton:disabled { background:#3a3430; color:#555; }"
        )
        self._btn_download.setEnabled(False)
        self._btn_download.clicked.connect(self._download_kus_update)
        vl.addWidget(self._btn_download, 2, 1)

        kl.addWidget(grp_ver)

        # Changelog
        grp_log = QGroupBox("История изменений")
        ll = QVBoxLayout(grp_log)
        self._changelog = QTextEdit()
        self._changelog.setReadOnly(True)
        self._changelog.setFont(QFont("Consolas", 10))
        self._changelog.setMaximumHeight(250)
        self._changelog.setPlainText(self._get_changelog())
        ll.addWidget(self._changelog)
        kl.addWidget(grp_log)

        kl.addStretch()
        tabs.addTab(tab_kus, "KUS Pro")

        # ══════════════════════════════════════════════════════════════
        #  Вкладка 2: Windows
        # ══════════════════════════════════════════════════════════════
        tab_win = QWidget()
        tab_win.setStyleSheet("background: transparent;")
        wl = QVBoxLayout(tab_win)
        wl.setContentsMargins(14, 14, 14, 14)
        wl.setSpacing(10)

        grp_auto = QGroupBox("Настройки")
        al = QHBoxLayout(grp_auto)
        self._auto = QCheckBox("Устанавливать обновления автоматически")
        self._auto.setChecked(True)
        al.addWidget(self._auto)
        al.addStretch()
        wl.addWidget(grp_auto)

        hint = QLabel(
            "При первом запуске устанавливается PSWindowsUpdate."
        )
        hint.setStyleSheet("color:#5a5248; font-size:11px; background:transparent;")
        wl.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_upd = self._reg_btn(self.btn("Обновления Windows"))
        btn_upd.setFixedHeight(36)
        btn_upd.clicked.connect(self._run_windows_updates)
        btn_row.addWidget(btn_upd)

        btn_drv = self._reg_btn(self.btn("Драйверы"))
        btn_drv.setFixedHeight(36)
        btn_drv.clicked.connect(self._run_drivers)
        btn_row.addWidget(btn_drv)

        btn_row.addStretch()
        wl.addLayout(btn_row)

        # Планировщик
        grp_sched = QGroupBox("Автопроверка")
        sl = QHBoxLayout(grp_sched)
        sl.addWidget(QLabel("Периодичность:"))
        self._schedule = QComboBox()
        self._schedule.setFixedWidth(160)
        self._schedule.addItem("Ежедневно", "DAILY")
        self._schedule.addItem("Еженедельно", "WEEKLY")
        self._schedule.addItem("При входе", "ONLOGON")
        sl.addWidget(self._schedule)
        sl.addWidget(QLabel("Время:"))
        self._sched_time = QComboBox()
        self._sched_time.setFixedWidth(100)
        for h in ("02:00", "03:00", "04:00", "06:00", "09:00", "18:00"):
            self._sched_time.addItem(h)
        sl.addWidget(self._sched_time)
        sl.addStretch()

        btn_reg = QPushButton("Включить")
        btn_reg.setFixedHeight(32)
        btn_reg.clicked.connect(self._register_task)
        sl.addWidget(btn_reg)

        btn_unreg = QPushButton("Отключить")
        btn_unreg.setFixedHeight(32)
        btn_unreg.clicked.connect(self._unregister_task)
        sl.addWidget(btn_unreg)

        wl.addWidget(grp_sched)
        wl.addStretch()
        tabs.addTab(tab_win, "Windows")

        # ══════════════════════════════════════════════════════════════
        #  Вкладка 3: Компоненты
        # ══════════════════════════════════════════════════════════════
        tab_comp = QWidget()
        tab_comp.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(tab_comp)
        cl.setContentsMargins(14, 14, 14, 14)
        cl.setSpacing(10)

        comp_info = QLabel(
            "Внешние компоненты KUS Pro.\n"
            "Обновляются отдельно от основного приложения."
        )
        comp_info.setStyleSheet("color:#5a5248; font-size:12px; background:transparent;")
        comp_info.setWordWrap(True)
        cl.addWidget(comp_info)

        # Таблица компонентов
        self._comp_table = QGridLayout()
        self._comp_table.setSpacing(8)

        for i, txt in enumerate(["Компонент", "Версия", "Действие"]):
            lbl = QLabel(txt)
            lbl.setStyleSheet("color:#5a5248; font-size:11px; font-weight:600; background:transparent;")
            self._comp_table.addWidget(lbl, 0, i)

        self._comp_zapret_ver = QLabel("—")
        self._comp_zapret_ver.setStyleSheet("color:#5a5248; font-size:11px; background:transparent;")
        self._comp_table.addWidget(QLabel("Zapret"), 1, 0)
        self._comp_table.addWidget(self._comp_zapret_ver, 1, 1)
        btn_z = self._reg_btn(self.btn("Обновить"))
        btn_z.setFixedHeight(28)
        btn_z.clicked.connect(lambda: self._update_component("zapret"))
        self._comp_table.addWidget(btn_z, 1, 2)

        self._comp_tg_ver = QLabel("—")
        self._comp_tg_ver.setStyleSheet("color:#5a5248; font-size:11px; background:transparent;")
        self._comp_table.addWidget(QLabel("Telegram Proxy"), 2, 0)
        self._comp_table.addWidget(self._comp_tg_ver, 2, 1)
        btn_t = self._reg_btn(self.btn("Обновить"))
        btn_t.setFixedHeight(28)
        btn_t.clicked.connect(lambda: self._update_component("tg_proxy"))
        self._comp_table.addWidget(btn_t, 2, 2)

        cl.addLayout(self._comp_table)

        self._comp_progress = QProgressBar()
        self._comp_progress.setValue(0)
        self._comp_progress.setVisible(False)
        cl.addWidget(self._comp_progress)

        btn_refresh = self._reg_btn(self.btn("Обновить список"))
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self._refresh_components)
        cl.addWidget(btn_refresh)

        cl.addStretch()
        tabs.addTab(tab_comp, "Компоненты")

        self._content.addWidget(tabs, 1)

        self._check_kus_update()
        self._refresh_components()

    # ── KUS Pro ──────────────────────────────────────────────────────

    def _check_kus_update(self):
        self._update_status.setText("Проверка...")
        self._check_thread = _UpdateCheckThread()
        self._check_thread.result.connect(self._on_kus_result)
        self._check_thread.start()

    def _on_kus_result(self, has, cur, lat, url_or_err):
        if has and lat:
            self._update_status.setText("Доступна версия {} (текущая: {})".format(lat, cur))
            self._update_status.setStyleSheet("color:#00ff88; font-size:12px; font-weight:bold; background:transparent;")
            self._btn_download.setEnabled(bool(url_or_err))
            self._pending_url = url_or_err
        elif lat == "":
            self._update_status.setText("Ошибка: {}".format(url_or_err))
            self._update_status.setStyleSheet("color:#ff4444; font-size:12px; background:transparent;")
            self._btn_download.setEnabled(False)
        else:
            self._update_status.setText("Актуально (v{})".format(cur))
            self._update_status.setStyleSheet("color:#5a5248; font-size:12px; background:transparent;")
            self._btn_download.setEnabled(False)

    def _download_kus_update(self):
        url = getattr(self, '_pending_url', '')
        if url:
            webbrowser.open(url)
            self.log("Открыта страница скачивания", "OK")

    # ── Windows ──────────────────────────────────────────────────────

    def _run_windows_updates(self):
        if QMessageBox.question(
            self, "Обновления Windows",
            "Запустить проверку обновлений?\nМожет занять несколько минут.",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        self._run_worker(_fn_windows_updates, auto_install=self._auto.isChecked())

    def _run_drivers(self):
        if QMessageBox.question(
            self, "Драйверы",
            "Поиск обновлений драйверов?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        self._run_worker(_fn_drivers)

    def _register_task(self):
        self._run_worker(_fn_register_task,
                         self._schedule.currentData(),
                         self._sched_time.currentText())

    def _unregister_task(self):
        self._run_worker(_fn_unregister_task)

    # ── Компоненты ───────────────────────────────────────────────────

    def _refresh_components(self):
        vf = ZAPRET_DIR / "current_version.txt"
        self._comp_zapret_ver.setText(
            vf.read_text(encoding="utf-8").strip() if vf.exists() else "Не установлен")
        tg = ZAPRET_DIR.parent / "tg_proxy" / "TgWsProxy_windows.exe"
        self._comp_tg_ver.setText("Установлен" if tg.exists() else "Не установлен")

    def _update_component(self, name):
        self.log("Обновление {}...".format(name), "INFO")
        self._comp_progress.setVisible(True)
        self._comp_progress.setValue(30)

        def _worker(log_func, progress_func):
            if name == "zapret":
                from auto_updater import update_zapret
                return update_zapret(log_func, progress_func)
            elif name == "tg_proxy":
                from auto_updater import update_tg_proxy
                return update_tg_proxy(log_func, progress_func)

        from worker import Worker
        w = Worker(_worker)
        w.line_out.connect(self.log)
        w.progress.connect(lambda p: self._comp_progress.setValue(int(p * 100)))
        w.finished.connect(self._on_comp_updated)
        w.start()

    def _on_comp_updated(self, result):
        self._comp_progress.setValue(100)
        self._comp_progress.setVisible(False)
        self._refresh_components()
        self.log("Компонент обновлён" if result else "Ошибка",
                 "OK" if result else "ERR")

    # ── Changelog ────────────────────────────────────────────────────

    def _get_changelog(self):
        return """KUS Pro — История изменений

v3.1.0
• Страница Zapret: Lua-стратегии (zapret2)
• Страница настроек: расширенная конфигурация
• Страница логов: мониторинг и live-лог
• Страница обновлений: компоненты и донаты
• Обновлены бинарники zapret2 (winws2.exe v1.0.2)
• Загружены Lua-скрипты из zapret2
• Исправлены ошибки импортов PyQt5/PyQt6

v3.0.1
• Добавлена страница Zapret
• Добавлена страница История действий
• Исправлены ошибки с импортами QAction

v3.0.0
• Полная переработка UI
• Тема Dark с glow-эффектами
• Страницы: Мониторинг, Батарея, Сеть, Безопасность
• Game Mode, Оптимизация, Telegram Proxy

v2.0.0
• Базовый функционал: процессы, службы, очистка
• Настройка DNS, экспорт данных

v1.0.0
• Первая версия KUS Pro
"""

"""
page_settings.py — KUS Pro
Страница настроек, логов и поддержки.
"""

import os
import json
import webbrowser
from pathlib import Path

from qt_compat import *

from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QCheckBox, QSpinBox,
    QPushButton, QGroupBox, QGridLayout, QLineEdit,
    QTabWidget, QWidget, QTextEdit, QComboBox, QFileDialog,
    QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor

from base_page import BasePage
from config_manager import load_config, save_config
from app_paths import ZAPRET_DIR, CONFIG_FILE
from widgets import GalahhadToggle


class SettingsPage(BasePage):
    PAGE_TITLE = "⚙ Настройки"
    PAGE_SUB = "Конфигурация, логи, поддержка"

    def build_ui(self):
        cfg = load_config()

        tabs = QTabWidget()

        # ══════════════════════════════════════════════════════════════
        #  Вкладка 1: Основные
        # ══════════════════════════════════════════════════════════════
        tab_main = QWidget()
        tab_main.setStyleSheet("background: transparent;")
        ml = QVBoxLayout(tab_main)
        ml.setContentsMargins(14, 14, 14, 14)
        ml.setSpacing(10)

        # Автозапуск Windows
        grp_win = QGroupBox("Автозапуск Windows")
        wl = QVBoxLayout(grp_win)
        from modules.autostart import is_autostart_enabled
        self._cb_win = GalahhadToggle("Автозапуск KUS Pro при входе в Windows")
        self._cb_win.setChecked(is_autostart_enabled())
        self._cb_win.toggled.connect(self._toggle_win_autostart)
        wl.addWidget(self._cb_win)
        ml.addWidget(grp_win)

        # Автозапуск модулей
        grp_mod = QGroupBox("Автозапуск модулей")
        modl = QVBoxLayout(grp_mod)
        self._cb_z = GalahhadToggle("Запускать Zapret при старте")
        self._cb_z.setChecked(cfg.get("autostart_zapret", False))
        modl.addWidget(self._cb_z)
        self._cb_t = GalahhadToggle("Запускать Telegram Proxy при старте")
        self._cb_t.setChecked(cfg.get("autostart_tg_proxy", False))
        modl.addWidget(self._cb_t)
        self._cb_min = GalahhadToggle("Запускать свёрнутым в трей")
        self._cb_min.setChecked(cfg.get("start_minimized", False))
        modl.addWidget(self._cb_min)
        ml.addWidget(grp_mod)

        # Тема
        grp_theme = QGroupBox("Тема")
        tl = QVBoxLayout(grp_theme)
        from theme import ThemeManager
        self._cb_theme = GalahhadToggle("Светлая тема")
        self._cb_theme.setChecked(ThemeManager.is_light())
        self._cb_theme.toggled.connect(self._toggle_theme)
        tl.addWidget(self._cb_theme)
        ml.addWidget(grp_theme)

        # Сеть
        grp_net = QGroupBox("Сеть")
        nl = QHBoxLayout(grp_net)
        nl.addWidget(QLabel("Порт Telegram Proxy:"))
        self._port = QSpinBox()
        self._port.setRange(1024, 65535)
        self._port.setValue(cfg.get("tg_proxy_port", 8080))
        nl.addWidget(self._port)
        nl.addStretch()
        ml.addWidget(grp_net)

        # Автообновления
        grp_upd = QGroupBox("Автообновления")
        ul = QVBoxLayout(grp_upd)
        self._cb_auto_upd = GalahhadToggle("Проверять обновления при старте")
        self._cb_auto_upd.setChecked(cfg.get("auto_update_enabled", True))
        ul.addWidget(self._cb_auto_upd)
        self._cb_upd_z = GalahhadToggle("Обновлять Zapret")
        self._cb_upd_z.setChecked(cfg.get("auto_update_zapret", True))
        ul.addWidget(self._cb_upd_z)
        self._cb_upd_t = GalahhadToggle("Обновлять Telegram Proxy")
        self._cb_upd_t.setChecked(cfg.get("auto_update_tg_proxy", True))
        ul.addWidget(self._cb_upd_t)
        ml.addWidget(grp_upd)

        ml.addStretch()
        tabs.addTab(tab_main, "Основные")

        # ══════════════════════════════════════════════════════════════
        #  Вкладка 2: Логи
        # ══════════════════════════════════════════════════════════════
        tab_logs = QWidget()
        tab_logs.setStyleSheet("background: transparent;")
        logl = QVBoxLayout(tab_logs)
        logl.setContentsMargins(14, 14, 14, 14)
        logl.setSpacing(10)

        # Выбор лога
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Файл:"))
        self._log_combo = QComboBox()
        self._log_combo.addItems(["run_log.txt", "crash_log.txt"])
        self._log_combo.currentTextChanged.connect(self._load_log)
        sel_row.addWidget(self._log_combo, 1)

        btn_refresh = QPushButton("Обновить")
        btn_refresh.setFixedHeight(32)
        btn_refresh.clicked.connect(self._load_log)
        sel_row.addWidget(btn_refresh)

        btn_clear = QPushButton("Очистить")
        btn_clear.setFixedHeight(32)
        btn_clear.clicked.connect(self._clear_log)
        sel_row.addWidget(btn_clear)

        btn_export = QPushButton("Экспорт")
        btn_export.setFixedHeight(32)
        btn_export.clicked.connect(self._export_log)
        sel_row.addWidget(btn_export)

        logl.addLayout(sel_row)

        # Поиск
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Поиск:"))
        self._log_search = QLineEdit()
        self._log_search.setPlaceholderText("Введите текст...")
        self._log_search.returnPressed.connect(self._search_log)
        search_row.addWidget(self._log_search, 1)
        btn_search = QPushButton("Найти")
        btn_search.setFixedHeight(32)
        btn_search.clicked.connect(self._search_log)
        search_row.addWidget(btn_search)
        logl.addLayout(search_row)

        # Просмотрщик лога
        self._log_viewer = QTextEdit()
        self._log_viewer.setReadOnly(True)
        self._log_viewer.setFont(QFont("Consolas", 10))
        self._log_viewer.setStyleSheet(
            "background:#0a0e14; border:1px solid rgba(255,255,255,0.06); border-radius:8px;")
        logl.addWidget(self._log_viewer, 1)

        # Статистика
        self._log_stats = QLabel("Строк: 0 | Размер: 0")
        self._log_stats.setStyleSheet("color:#5a5248; font-size:11px; background:transparent;")
        logl.addWidget(self._log_stats)

        tabs.addTab(tab_logs, "Логи")

        # ══════════════════════════════════════════════════════════════
        #  Вкладка 3: Поддержка
        # ══════════════════════════════════════════════════════════════
        tab_donate = QWidget()
        tab_donate.setStyleSheet("background: transparent;")
        dl = QVBoxLayout(tab_donate)
        dl.setContentsMargins(14, 14, 14, 14)
        dl.setSpacing(12)

        don_title = QLabel("Поддержать проект")
        don_title.setStyleSheet("color:#00ff88; font-size:18px; font-weight:bold; background:transparent;")
        dl.addWidget(don_title)

        don_desc = QLabel(
            "KUS Pro — бесплатный open-source проект.\n"
            "Если приложение вам помогает, поддержите разработку!"
        )
        don_desc.setStyleSheet("color:#5a5248; font-size:12px; background:transparent;")
        don_desc.setWordWrap(True)
        dl.addWidget(don_desc)

        # DonationAlerts
        grp_da = QGroupBox("Поддержка автора")
        da_lay = QVBoxLayout(grp_da)

        da_info = QLabel(
            "Быстрый способ поддержать — DonationAlerts.\n"
            "Принимает карты, ЮMoney, Qiwi и другие способы."
        )
        da_info.setStyleSheet("color:#5a5248; font-size:12px; background:transparent;")
        da_info.setWordWrap(True)
        da_lay.addWidget(da_info)

        btn_donate = QPushButton("Открыть DonationAlerts")
        btn_donate.setFixedHeight(42)
        btn_donate.setStyleSheet(
            "QPushButton { color:#fff; background:#ff6b35; border:none; "
            "border-radius:8px; padding:0 24px; font-size:14px; font-weight:bold; }"
            "QPushButton:hover { background:#ff8c5a; }"
        )
        btn_donate.clicked.connect(
            lambda: webbrowser.open("https://www.donationalerts.com/r/kus_777"))
        da_lay.addWidget(btn_donate)

        dl.addWidget(grp_da)

        # Криптокошельки
        grp_crypto = QGroupBox("Криптокошельки")
        crypto_lay = QGridLayout(grp_crypto)
        crypto_lay.setSpacing(8)

        wallets = [
            ("BTC", "bc1qhqew3mrvp47uk2vevt5sctp7p2x9m7m5kkchve", "#f7931a"),
            ("ETH", "0x3d52Ce15B7Be734c53fc9526ECbAB8267b63d66E", "#627eea"),
            ("USDT ERC-20", "0x3d52Ce15B7Be734c53fc9526ECbAB8267b63d66E", "#26a17b"),
            ("USDT TRC-20", "TEzAAtn4VhndqEaAyuCM78xh5W2gCjwWEo", "#ff0013"),
        ]

        for i, (name, addr, color) in enumerate(wallets):
            icon = QLabel("●")
            icon.setStyleSheet("color:{}; font-size:20px; background:transparent;".format(color))
            crypto_lay.addWidget(icon, i, 0)

            info = QVBoxLayout()
            info.setSpacing(1)
            n = QLabel(name)
            n.setStyleSheet("color:{}; font-size:13px; font-weight:bold; background:transparent;".format(color))
            info.addWidget(n)
            a = QLabel(addr)
            a.setStyleSheet("color:#a09080; font-size:10px; font-family:Consolas; background:transparent;")
            a.setTextInteractionFlags(Qt.TextSelectableByMouse)
            crypto_lay.addLayout(info, i, 1)

            btn_copy = QPushButton("📋")
            btn_copy.setFixedSize(28, 28)
            btn_copy.setStyleSheet("border:none; font-size:14px;")
            a_addr = addr
            btn_copy.clicked.connect(lambda _, a=a_addr: self._copy_addr(a))
            crypto_lay.addWidget(btn_copy, i, 2)

        dl.addWidget(grp_crypto)

        # Автор
        grp_author = QGroupBox("Автор")
        auth_lay = QVBoxLayout(grp_author)

        author_row = QHBoxLayout()
        author_row.addWidget(QLabel("Автор:"))
        link = QLabel('<a href="https://github.com/Kus993" style="color:#00ff88; text-decoration:none;">Kus993</a>')
        link.setOpenExternalLinks(True)
        author_row.addWidget(link)
        author_row.addStretch()
        auth_lay.addLayout(author_row)

        btn_github = QPushButton("GitHub")
        btn_github.setFixedHeight(36)
        btn_github.clicked.connect(
            lambda: webbrowser.open("https://github.com/Kus993/Zapret Discord YouTube TG"))
        auth_lay.addWidget(btn_github)

        dl.addWidget(grp_author)
        dl.addStretch()
        tabs.addTab(tab_donate, "Поддержка")

        # ══════════════════════════════════════════════════════════════
        #  Вкладка 4: О приложении
        # ══════════════════════════════════════════════════════════════
        tab_about = QWidget()
        tab_about.setStyleSheet("background: transparent;")
        al = QVBoxLayout(tab_about)
        al.setContentsMargins(14, 14, 14, 14)
        al.setSpacing(10)

        grp_about = QGroupBox("О приложении")
        abl = QVBoxLayout(grp_about)

        try:
            from theme import VERSION
            ver_text = "KUS Pro v{}".format(VERSION)
        except Exception:
            ver_text = "KUS Pro"
        ver_label = QLabel(ver_text)
        ver_label.setStyleSheet("color:#00ff88; font-size:16px; font-weight:bold; background:transparent;")
        abl.addWidget(ver_label)

        desc = QLabel("Универсальная системная утилита для Windows.")
        desc.setStyleSheet("color:#5a5248; font-size:12px; background:transparent;")
        desc.setWordWrap(True)
        abl.addWidget(desc)

        # Версии
        grp_ver = QGroupBox("Компоненты")
        vgl = QGridLayout(grp_ver)
        vgl.setSpacing(6)

        components = [
            ("KUS Pro", ver_text),
            ("Python", self._get_python_version()),
            ("PyQt5", self._get_pyqt_version()),
        ]
        for i, (name, ver) in enumerate(components):
            nl = QLabel(name)
            nl.setStyleSheet("color:#5a5248; font-size:12px; background:transparent;")
            vl = QLabel(ver)
            vl.setStyleSheet("color:#00ff88; font-size:12px; font-weight:600; background:transparent;")
            vgl.addWidget(nl, i, 0)
            vgl.addWidget(vl, i, 1)

        abl.addWidget(grp_ver)

        al.addWidget(grp_about)
        al.addStretch()
        tabs.addTab(tab_about, "О приложении")

        self._content.addWidget(tabs, 1)

        # Кнопка сохранения
        save_row = QHBoxLayout()
        self._save_status = QLabel("")
        self._save_status.setStyleSheet("color:#4caf7d; font-size:12px; font-weight:600; background:transparent;")
        save_row.addWidget(self._save_status)
        save_row.addStretch()
        b = self.btn("💾 Сохранить настройки", obj="btn_glow")
        b.setFixedHeight(42)
        b.clicked.connect(self._save)
        save_row.addWidget(b)
        self._content.addLayout(save_row)

    # ── Методы ────────────────────────────────────────────────────

    def _toggle_win_autostart(self, checked):
        from modules.autostart import enable_autostart, disable_autostart
        ok, msg = (enable_autostart() if checked else disable_autostart())
        self.log(msg, "OK" if ok else "WARN")

    def _toggle_theme(self, checked):
        from theme import ThemeManager
        from PyQt5.QtWidgets import QApplication
        theme = "light" if checked else "dark"
        ThemeManager.switch_to(theme)
        qss = ThemeManager.get_qss()
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)
        w = self.window()
        if w:
            w.setStyleSheet(qss)
        self.log("Тема: {}".format(theme), "OK")

    # ── Логи ─────────────────────────────────────────────────────────

    def _get_log_path(self, name):
        if name == "run_log.txt":
            for p in [Path("run_log.txt"), ZAPRET_DIR / "run_log.txt",
                      Path.cwd() / "run_log.txt"]:
                if p.exists():
                    return p
            return Path("run_log.txt")
        elif name == "crash_log.txt":
            for p in [Path("crash_log.txt"), ZAPRET_DIR / "crash_log.txt",
                      Path.cwd() / "crash_log.txt"]:
                if p.exists():
                    return p
            return Path("crash_log.txt")
        return Path(name)

    def _load_log(self):
        name = self._log_combo.currentText()
        path = self._get_log_path(name)
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                if len(content) > 100000:
                    content = "...\n" + content[-100000:]
                self._log_viewer.setPlainText(content)
                cursor = self._log_viewer.textCursor()
                cursor.movePosition(QTextCursor.End)
                self._log_viewer.setTextCursor(cursor)
                lines = content.count('\n') + 1
                size = path.stat().st_size
                size_str = "{:.1f} КБ".format(size / 1024) if size > 1024 else "{} байт".format(size)
                self._log_stats.setText("Строк: {} | Размер: {}".format(lines, size_str))
            except Exception as e:
                self._log_viewer.setPlainText("Ошибка: {}".format(e))
        else:
            self._log_viewer.setPlainText("Файл не найден: {}".format(path))

    def _clear_log(self):
        name = self._log_combo.currentText()
        path = self._get_log_path(name)
        reply = QMessageBox.question(
            self, "Очистка", "Очистить {}?".format(name),
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                path.write_text("", encoding="utf-8")
                self._log_viewer.clear()
                self._log_stats.setText("Очищен")
            except Exception as e:
                self.log("Ошибка: {}".format(e), "ERR")

    def _export_log(self):
        name = self._log_combo.currentText()
        path = self._get_log_path(name)
        if not path.exists():
            self.log("Файл не найден", "ERR")
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт", str(Path.home() / "Desktop" / name), "Text (*.txt)")
        if save_path:
            import shutil
            shutil.copy2(str(path), save_path)
            self.log("Экспортирован: {}".format(save_path), "OK")

    def _search_log(self):
        text = self._log_search.text().strip()
        if not text:
            return
        content = self._log_viewer.toPlainText()
        lines = content.split('\n')
        found = ["Строка {}: {}".format(i, l.strip())
                 for i, l in enumerate(lines, 1) if text.lower() in l.lower()]
        if found:
            result = "Найдено {}:\n\n{}".format(len(found), '\n'.join(found[:100]))
            self._log_viewer.setPlainText(result)
            self._log_stats.setText("Найдено: {}".format(len(found)))
        else:
            self._log_stats.setText("Ничего не найдено")

    def _copy_addr(self, addr):
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.clipboard().setText(addr)
            self.log("Скопировано: {}...".format(addr[:20]), "OK")

    # ── Сохранение ──────────────────────────────────────────────────

    def _save(self):
        cfg = load_config()
        cfg["autostart_zapret"] = self._cb_z.isChecked()
        cfg["autostart_tg_proxy"] = self._cb_t.isChecked()
        cfg["start_minimized"] = self._cb_min.isChecked()
        cfg["tg_proxy_port"] = self._port.value()
        cfg["auto_update_enabled"] = self._cb_auto_upd.isChecked()
        cfg["auto_update_zapret"] = self._cb_upd_z.isChecked()
        cfg["auto_update_tg_proxy"] = self._cb_upd_t.isChecked()
        save_config(cfg)
        self._save_status.setText("✓ Сохранено")
        self.log("Настройки сохранены", "OK")

    def _get_python_version(self):
        import sys
        return "{}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro)

    def _get_pyqt_version(self):
        try:
            from PyQt5.QtCore import PYQT_VERSION_STR
            return PYQT_VERSION_STR
        except Exception:
            return "?"

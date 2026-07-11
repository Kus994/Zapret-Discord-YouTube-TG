"""
main_window.py — KUS Pro
Главное окно с фоном, сайдбаром, стеком страниц и системным треем.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict

from qt_compat import *

# Автовыбор PyQt5 (первый) или PyQt6
try:
    from PyQt5.QtWidgets import (
        QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
        QLabel, QPushButton, QSizePolicy,
        QFrame, QSystemTrayIcon, QMenu, QApplication,
    )
    from PyQt5.QtGui import (
        QPixmap, QPainter, QColor, QLinearGradient,
        QBrush, QRadialGradient, QIcon, QFont,
    )
    from PyQt5.QtCore import Qt, QSettings, QTimer
    QT6 = False
except ImportError:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
        QLabel, QPushButton, QSizePolicy,
        QFrame, QSystemTrayIcon, QMenu, QApplication,
    )
    from PyQt6.QtGui import (
        QPixmap, QPainter, QColor, QLinearGradient,
        QBrush, QRadialGradient, QIcon, QFont,
    )
    from PyQt6.QtCore import Qt, QSettings, QTimer
    QT6 = True

from theme import QSS
from app_paths import BASE_DIR, BG_FILE, ICON_FILE


class _BgWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._px = None  # Загружаем лениво при первом paint

    def paintEvent(self, event):
        if self._px is None:
            self._px = QPixmap(str(BG_FILE)) if BG_FILE.exists() else QPixmap()
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if not self._px.isNull():
            scaled = self._px.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            ox = (scaled.width()  - self.width())  // 2
            oy = (scaled.height() - self.height()) // 2
            p.drawPixmap(-ox, -oy, scaled)
        else:
            g = QLinearGradient(0, 0, self.width(), self.height())
            g.setColorAt(0, QColor(4, 5, 10))
            g.setColorAt(1, QColor(8, 10, 20))
            p.fillRect(self.rect(), QBrush(g))
            glow = QRadialGradient(self.width()*.75, self.height()*.25, self.width()*.5)
            glow.setColorAt(0, QColor(245, 166, 35, 35))
            glow.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), QBrush(glow))
        ov = QLinearGradient(0, 0, self.width(), self.height())
        ov.setColorAt(0.0, QColor(9, 11, 15, 220))
        ov.setColorAt(0.5, QColor(9, 11, 15, 196))
        ov.setColorAt(1.0, QColor(9, 11, 15, 212))
        p.fillRect(self.rect(), QBrush(ov))
        p.end()


class _NavBtn(QPushButton):
    def __init__(self, label, parent=None):
        super().__init__(label, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(46)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._nav_color = "#5a5248"
        self._nav_icon = ""
        self._active = False
        self._set(False)

    def _set(self, active):
        self._active = active
        self._update_style()

    def _update_style(self):
        color = self._nav_color if self._active else "#5a5248"
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)

        if self._active:
            self.setStyleSheet(
                "text-align:left; padding:12px 20px 12px 18px; border:none;"
                "border-left:3px solid {c}; background:rgba({r},{g},{b},0.10);"
                "color:{c}; font-size:13px; font-weight:700; border-radius:10px; margin:3px 8px;".format(
                    c=color, r=r, g=g, b=b
                )
            )
        else:
            self.setStyleSheet(
                "text-align:left; padding:12px 20px; border:none;"
                "background:transparent; color:#5a5248; font-size:13px;"
                "font-weight:500; border-radius:10px; margin:3px 8px; border-left:3px solid transparent;"
            )
        self.setObjectName("nav_active" if self._active else "nav_idle")

    def enterEvent(self, event):
        if not self._active:
            self.setStyleSheet(
                "text-align:left; padding:12px 20px; border:none;"
                "background:rgba(255,255,255,0.05); color:#94a3b8; font-size:13px;"
                "font-weight:600; border-radius:10px; margin:3px 8px; border-left:3px solid rgba(0,255,136,0.2);"
            )
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._active:
            self._update_style()
        super().leaveEvent(event)

    def set_active(self, v): self._set(v)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ФИКС (уточнение предыдущего фикса): это должно быть САМОЙ
        # ПЕРВОЙ строкой сразу после super().__init__() — без единого
        # вызова между ними. setWindowTitle/setStyleSheet/resize/
        # restoreGeometry ниже могут форсировать создание нативного
        # HWND (например, restoreGeometry затрагивает менеджер окон),
        # а как только HWND существует, Windows может прислать
        # nativeEvent() ДО того, как выполнение дойдёт до конца
        # __init__. Раньше атрибут выставлялся после этих вызовов —
        # ошибка воспроизводилась стабильно именно из-за них.
        self._hotkey_registered = False

        self.setWindowTitle("KUS Pro — Системная утилита")
        self.setMinimumSize(900, 600)
        self.setStyleSheet(QSS)

        # Устанавливаем иконку окна
        ico_path = str(BASE_DIR / "assets" / "icon.ico")
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))

        # Заголовок с версией
        try:
            from theme import VERSION
            self.setWindowTitle("KUS Pro v{} — Системная утилита".format(VERSION))
        except Exception:
            self.setWindowTitle("KUS Pro — Системная утилита")

        s = QSettings("KUS", "Pro")
        geo = s.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(1140, 720)

        # Всегда показываем развёрнутым
        QTimer.singleShot(0, self.showMaximized)

        self._nav_btns: List[tuple] = []  # [(page_id, _NavBtn), ...]
        self._pg_cache: Dict[str, QWidget] = {}
        self._pages_def = []
        self._build()
        self._setup_tray()
        self._register_game_mode_hotkey()
        self._auto_update_w = None
        # Запускаем автообновление через 3 сек после старта (не блокируя UI)
        QTimer.singleShot(3000, self._check_auto_update)
        # Autostart zapret/tg_proxy if enabled in settings
        QTimer.singleShot(4000, self._autostart_modules)

    def _build(self):
        # Страницы импортируются лениво при первом переходе
        # Формат: (id, label, module_name, class_name)

        self._pages_def = [
            ("cleanup",    "Очистка",          "page_cleanup",   "CleanupPage"),
            ("optimizer",  "Оптимизация",      "page_optimizer", "OptimizerPage"),
            ("network",    "Сеть",             "page_network",   "NetworkPage"),
            ("processes",  "Процессы",          "page_processes", "ProcessesPage"),
            ("monitor",    "Мониторинг",       "page_monitor",   "MonitorPage"),
            ("battery",    "Батарея",          "page_battery",   "BatteryPage"),
            ("services",   "Службы",           "page_services",  "ServicesPage"),
            ("timetrack",  "Хронометраж",      "page_timetrack", "TimeTrackPage"),
            ("game_mode",  "Игровой режим",    "page_game_mode", "GameModePage"),
            ("security",   "Безопасность",     "page_security",  "SecurityPage"),
            ("updates",    "Обновления",       "page_updates",   "UpdatesPage"),
            ("zapret",     "Zapret",            "page_zapret",    "ZapretPage"),
            ("tg_proxy",   "Telegram Proxy",   "page_tg_proxy",  "TgProxyPage"),
            ("export",     "Экспорт",          "page_export",    "ExportPage"),
            ("action_log", "История",          "page_action_log","ActionLogPage"),
            ("settings",   "Настройки",        "page_settings",  "SettingsPage"),
        ]

        # Цветовые метки для каждой страницы
        self._nav_colors = {
            "cleanup":   ("🧹", "#4caf7d"),
            "optimizer": ("🚀", "#f59e0b"),
            "network":   ("🌐", "#5b9df0"),
            "processes": ("⚙",  "#f5a623"),
            "monitor":   ("📊", "#a070e0"),
            "battery":   ("🔋", "#fbbf24"),
            "services":  ("🔧", "#22d3ee"),
            "timetrack": ("⏱",  "#4ac9c9"),
            "game_mode": ("🎮", "#e070a0"),
            "security":  ("🛡",  "#4caf7d"),
            "updates":   ("🔄", "#f5c842"),
            "zapret":    ("🛡",  "#e05252"),
            "tg_proxy":  ("✈",  "#5b9df0"),
            "export":    ("📤", "#a78bfa"),
            "action_log":("📋", "#f472b6"),
            "settings":  ("⚙",  "#7a7068"),
        }

        bg = _BgWidget(self)
        self.setCentralWidget(bg)
        root = QHBoxLayout(bg)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ─────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(0, 0, 0, 0)
        sb.setSpacing(0)

        title = QLabel("KUS"); title.setObjectName("app_title"); sb.addWidget(title)
        sub   = QLabel("PRO EDITION"); sub.setObjectName("app_sub"); sb.addWidget(sub)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: rgba(245,166,35,0.18);"); sb.addWidget(sep)
        sb.addSpacing(4)

        # ── Глобальный поиск ── #
        from PyQt5.QtWidgets import QLineEdit
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("🔍 Поиск...")
        self._search_box.setFixedHeight(32)
        self._search_box.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
                padding: 4px 10px;
                color: #e2e8f0;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(0,255,136,0.3);
            }
        """)
        self._search_box.textChanged.connect(self._on_search)
        sb.addWidget(self._search_box)
        sb.addSpacing(4)

        # Результаты поиска (скрыты по умолчанию)
        self._search_results = QFrame()
        self._search_results.setVisible(False)
        self._search_results_lay = QVBoxLayout(self._search_results)
        self._search_results_lay.setContentsMargins(8, 4, 8, 4)
        self._search_results_lay.setSpacing(2)
        sb.addWidget(self._search_results)

        for pid, label, _, __ in self._pages_def:
            icon, color = self._nav_colors.get(pid, ("", "#5a5248"))
            btn = _NavBtn("  {} {}".format(icon, label))
            btn._nav_color = color
            btn._nav_icon = icon
            btn.clicked.connect(lambda _, p=pid: self._go(p))
            sb.addWidget(btn)
            self._nav_btns.append((pid, btn))

        sb.addStretch()

        try:
            from modules.elevation import is_admin
            admin = is_admin()
        except Exception:
            admin = False
        adm = QLabel("🛡 Администратор" if admin else "⚠ Без прав адм.")
        adm.setObjectName("admin_badge")
        if not admin:
            adm.setStyleSheet("color:#e05252;font-size:10px;padding:8px 18px 4px 18px;")
        sb.addWidget(adm)

        tray_btn = QPushButton("⬇  В трей")
        tray_btn.setObjectName("tray_btn")
        tray_btn.clicked.connect(self._hide_to_tray)
        sb.addWidget(tray_btn)

        try:
            from theme import VERSION
            ver = QLabel("v{}".format(VERSION))
        except ImportError:
            ver = QLabel("")
        ver.setStyleSheet("color:#3a3830; font-size:9px; padding:6px 18px 4px 18px; background:transparent;")
        sb.addWidget(ver)

        root.addWidget(sidebar)

        # ── Content stack (с анимацией переходов) ───────────────────
        from widgets import AnimatedStackedWidget
        self._stack = AnimatedStackedWidget()
        root.addWidget(self._stack, 1)
        # Первая страница загружается после показа окна (deferred)
        QTimer.singleShot(100, lambda: self._go(self._pages_def[0][0]))

        # Если пользователь уже давал согласие на хронометраж в прошлом
        # запуске — создаём страницу сразу, чтобы слежение началось с
        # запуска приложения, а не только когда он сам зайдёт на неё.
        try:
            from modules.timetrack import has_consent
            if has_consent() and "timetrack" not in self._pg_cache:
                import importlib
                mod = importlib.import_module("page_timetrack")
                page = mod.TimeTrackPage()
                self._stack.addWidget(page)
                self._pg_cache["timetrack"] = page
        except Exception:
            pass

    def _on_search(self, text):
        """Обработчик глобального поиска."""
        # Убираем старые результаты
        while self._search_results_lay.count():
            child = self._search_results_lay.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not text or len(text) < 2:
            self._search_results.setVisible(False)
            return

        from modules.search import search
        results = search(text)

        if not results:
            self._search_results.setVisible(False)
            return

        self._search_results.setVisible(True)

        for r in results[:8]:  # Показываем максимум 8 результатов
            btn = QPushButton("  {} → {}".format(r["page"], r["action"]))
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 6px 10px;
                    border: none;
                    border-radius: 4px;
                    background: rgba(255,255,255,0.05);
                    color: #e2e8f0;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: rgba(0,255,136,0.1);
                }
            """)
            btn.setFixedHeight(28)
            module = r.get("module", "")
            page_id = module.replace("page_", "") if module.startswith("page_") else r["page"].lower()
            btn.clicked.connect(lambda _, p=page_id: self._go(p))
            self._search_results_lay.addWidget(btn)

    def _go(self, pid):
        old_page = self._stack.currentWidget()

        if pid not in self._pg_cache:
            for p, label, mod_name, cls_name in self._pages_def:
                if p == pid:
                    try:
                        import importlib
                        mod = importlib.import_module(mod_name)
                        factory = getattr(mod, cls_name)
                        page = factory()
                    except Exception as exc:
                        page = self._build_error_page(label, exc)
                    self._stack.addWidget(page)
                    self._pg_cache[pid] = page
                    break
        page = self._pg_cache.get(pid)
        if page:
            # Плавный переход между страницами (только при смене)
            if old_page and old_page != page and old_page.isVisible():
                try:
                    from PyQt5.QtWidgets import QGraphicsOpacityEffect
                    from PyQt5.QtCore import QPropertyAnimation, QEasingCurve

                    # Плавное исчезновение старой страницы
                    old_effect = QGraphicsOpacityEffect(old_page)
                    old_page.setGraphicsEffect(old_effect)
                    self._old_fade = QPropertyAnimation(old_effect, b"opacity")
                    self._old_fade.setDuration(150)
                    self._old_fade.setStartValue(1.0)
                    self._old_fade.setEndValue(0.0)
                    self._old_fade.setEasingCurve(QEasingCurve.InCubic)
                    self._old_fade.start()
                except Exception:
                    pass

            self._stack.setCurrentWidget(page)

            # Плавное появление новой страницы
            try:
                from PyQt5.QtWidgets import QGraphicsOpacityEffect
                from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QTimer

                new_effect = QGraphicsOpacityEffect(page)
                page.setGraphicsEffect(new_effect)
                new_effect.setOpacity(0.0)

                def _fade_in():
                    anim = QPropertyAnimation(new_effect, b"opacity")
                    anim.setDuration(200)
                    anim.setStartValue(0.0)
                    anim.setEndValue(1.0)
                    anim.setEasingCurve(QEasingCurve.OutCubic)
                    anim.start()
                    page._fade_anim = anim  # Сохраняем ссылку

                QTimer.singleShot(50, _fade_in)
            except Exception:
                pass

        for btn_pid, btn in self._nav_btns:
            btn.set_active(btn_pid == pid)

    def _build_error_page(self, label, exc):
        import traceback
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 24, 24, 24)
        title = QLabel("⚠  Не удалось открыть страницу «{}»".format(label))
        title.setStyleSheet("color:#f5c842; font-size:15px; font-weight:700; background:transparent;")
        lay.addWidget(title)
        detail = QLabel(
            "Произошла ошибка при построении страницы:\n\n{}\n\n"
            "Остальные страницы приложения продолжают работать.".format(
                "".join(traceback.format_exception_only(type(exc), exc)).strip()
            )
        )
        detail.setWordWrap(True)
        detail.setStyleSheet("color:#a8a098; font-size:12px; background:transparent;")
        lay.addWidget(detail)
        lay.addStretch()
        return w

    # ── Tray ─────────────────────────────────────────────────────── #
    @staticmethod
    def _make_tray_icon():
        """Загружает .ico или создаёт программную иконку трея."""
        ico_path = str(BASE_DIR / "assets" / "icon.ico")
        if os.path.exists(ico_path):
            return QIcon(ico_path)
        # Fallback: рисуем программно
        from PyQt5.QtGui import QFont, QLinearGradient
        px = QPixmap(64, 64)
        px.fill(Qt.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, 64, 64)
        grad.setColorAt(0, QColor(245, 166, 35))
        grad.setColorAt(1, QColor(200, 120, 10))
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(2, 2, 60, 60, 14, 14)
        p.setPen(QColor(10, 12, 18))
        f = QFont("Segoe UI", 30, QFont.Bold)
        p.setFont(f)
        p.drawText(px.rect(), Qt.AlignCenter, "K")
        p.end()
        return QIcon(px)

    def _setup_tray(self):
        icon = self._make_tray_icon()

        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("KUS Pro — двойной клик для открытия")

        menu = QMenu()
        act_show = menu.addAction("📂  Показать")
        act_show.triggered.connect(self.show_window)
        menu.addSeparator()

        # Быстрые действия
        act_zapret = menu.addAction("🛡  Zapret: статус")
        act_zapret.triggered.connect(self._tray_zapret_status)
        menu.addSeparator()

        act_quit = menu.addAction("✖  Выход")
        act_quit.triggered.connect(self._quit_app)
        self._tray.setContextMenu(menu)

        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _tray_zapret_status(self):
        """Показать статус zapret в трее."""
        try:
            from page_zapret import _is_running, _saved_ver
            running = _is_running()
            ver = _saved_ver() or "нет"
            status = "РАБОТАЕТ" if running else "остановлен"
            self._tray.showMessage(
                "Zapret",
                "Статус: {}\nВерсия: {}".format(status, ver),
                QSystemTrayIcon.Information if running else QSystemTrayIcon.Warning,
                3000,
            )
        except Exception:
            pass

    def _on_tray_activated(self, reason):
        """Обработчик клика по иконке трея."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()
        elif reason == QSystemTrayIcon.Trigger:
            # Одиночный клик — тоже показываем
            self.show_window()

    def show_window(self):
        """Показать и поднять окно поверх остальных."""
        # Восстанавливаем флаги окна для отображения в панели задач
        self.setWindowFlags(Qt.Window)
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        self.setWindowState(
            (self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive
        )

    def _hide_to_tray(self):
        """Полное скрытие в трей — окно невидимо, видно только в диспетчере задач."""
        self.hide()
        # Дополнительно скрываем из панели задач
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.showMinimized()
        self.hide()
        self._tray.showMessage(
            "KUS Pro",
            "Приложение свёрнуто в трей. Двойной клик для открытия.",
            QSystemTrayIcon.Information,
            2000,
        )

    def _quit_app(self):
        """Полный выход из приложения (в отличие от закрытия окна,
        которое только сворачивает его в трей) — здесь нужно снять
        регистрацию глобального хоткея, иначе он останется висеть до
        перезагрузки или вызовет конфликт при повторном запуске."""
        self._unregister_game_mode_hotkey()
        QApplication.quit()

    # ── Глобальный хоткей игрового режима ──────────────────────────── #
    def _hotkey_combo_from_settings(self):
        try:
            from config_manager import get_section
            return get_section("game_mode").get("hotkey", "")
        except Exception:
            return ""

    def _register_game_mode_hotkey(self):
        """Регистрирует глобальный хоткей переключения игрового режима,
        если он задан в настройках. Не вызывает ошибку, если платформа
        не Windows или хоткей уже занят другой программой — просто не
        регистрируется, приложение продолжает работать как обычно."""
        if sys.platform != "win32":
            return
        combo = self._hotkey_combo_from_settings()
        if not combo:
            return
        try:
            from modules.hotkeys import register_hotkey
            hwnd = int(self.winId())
            self._hotkey_registered = register_hotkey(hwnd, combo)
        except Exception:
            self._hotkey_registered = False

    def _unregister_game_mode_hotkey(self):
        if not self._hotkey_registered or sys.platform != "win32":
            return
        try:
            from modules.hotkeys import unregister_hotkey
            hwnd = int(self.winId())
            unregister_hotkey(hwnd)
        except Exception:
            pass
        self._hotkey_registered = False

    def nativeEvent(self, eventType, message):
        """Перехватывает нативные сообщения Windows для обработки
        WM_HOTKEY — глобальный хоткей игрового режима срабатывает,
        даже если окно свёрнуто или не в фокусе.

        nativeEvent вызывается на КАЖДОЕ нативное Windows-сообщение
        (движение мыши, ресайз и т.д.) — счёт идёт на сотни/тысячи
        раз в секунду при активном использовании, поэтому здесь
        критично не делать ничего медленного и не бросать исключений:
        исключение, вылетевшее из этого callback'а, проходит через
        границу Qt C++/Python и может привести к падению всего
        приложения, а не просто к тихому pass в Python."""
        # getattr(..., False) вместо self._hotkey_registered напрямую —
        # это не просто косметика: nativeEvent может быть вызван Qt/OS
        # в узком окне между super().__init__() и присвоением этого
        # атрибута (см. комментарий в __init__), и любое такое
        # необработанное исключение здесь роняет всё приложение.
        # getattr с дефолтом делает эту защиту гарантированной, а не
        # зависящей от точного порядка строк в __init__.
        if sys.platform == "win32" and getattr(self, "_hotkey_registered", False):
            try:
                import ctypes
                from ctypes import wintypes
                from modules.hotkeys import is_hotkey_message, HOTKEY_ID_GAME_MODE
                msg = wintypes.MSG.from_address(int(message))
                if is_hotkey_message(msg, HOTKEY_ID_GAME_MODE):
                    self._toggle_game_mode_via_hotkey()
                    return True, 0
            except Exception:
                pass
        return super().nativeEvent(eventType, message)

    def _toggle_game_mode_via_hotkey(self):
        """Переключает игровой режим по глобальному хоткею. Открывает
        страницу «Игровой режим», чтобы пользователь сразу видел лог
        выполнения, и переключает состояние на противоположное текущему.
        Вызывает _do_activate/_do_deactivate (без диалога подтверждения) —
        модальное окно посреди хоткея было бы хуже, чем пользователю
        самому отменить действие через UI, если он промахнулся."""
        self._go("game_mode")
        page = self._pg_cache.get("game_mode")
        if not page:
            return
        if getattr(page, "_is_active", False):
            page._do_deactivate()
        else:
            page._do_activate()

    # ── Auto-update ──────────────────────────────────────────────── #
    def _check_auto_update(self):
        """Фоновая проверка обновлений KUS Pro, Zapret и TgProxy при старте."""
        try:
            from config_manager import get_value
            if not get_value("auto_update_enabled", True):
                return

            # Проверяем KUS Pro саму
            QTimer.singleShot(1000, self._check_kus_pro_update)

            do_zapret = get_value("auto_update_zapret", True)
            do_tg = get_value("auto_update_tg_proxy", True)
            if not do_zapret and not do_tg:
                return
        except Exception:
            return

        from auto_updater import AutoUpdateWorker
        self._auto_update_w = AutoUpdateWorker(
            update_zapret=do_zapret,
            update_tg_proxy=do_tg,
            parent=self,
        )
        self._auto_update_w.done.connect(self._on_auto_update_done)
        self._auto_update_w.start()

    def _check_kus_pro_update(self):
        """Проверяет обновление KUS Pro и показывает уведомление."""
        try:
            from auto_updater import check_kus_pro_update
            has_update, current, latest, url = check_kus_pro_update()
            if has_update and latest:
                self._tray.showMessage(
                    "KUS Pro — Доступно обновление",
                    "Версия {} → {}\nОткройте Настройки для скачивания.".format(current, latest),
                    QSystemTrayIcon.Information,
                    8000,
                )
                # Сохраняем URL для страницы настроек
                from config_manager import load_config, save_config
                cfg = load_config()
                cfg["kus_pro_update_url"] = url
                cfg["kus_pro_update_version"] = latest
                save_config(cfg)
        except Exception:
            pass

    def _autostart_modules(self):
        """Start zapret/tg_proxy automatically if enabled in settings."""
        try:
            from config_manager import get_value
            if get_value("autostart_zapret", False):
                page = self._pg_cache.get("zapret")
                if page and hasattr(page, '_quick_start_action'):
                    page._quick_start_action()
            if get_value("autostart_tg_proxy", False):
                page = self._pg_cache.get("tg_proxy")
                if page and hasattr(page, '_start'):
                    page._start()
        except Exception:
            pass

    def _on_auto_update_done(self, summary):
        """Показывает уведомление о результате автообновления."""
        if "Обновлены" in summary:
            self._tray.showMessage(
                "KUS Pro — Обновления",
                summary,
                QSystemTrayIcon.Information,
                5000,
            )

    # ── Close ────────────────────────────────────────────────────── #
    def closeEvent(self, event):
        QSettings("KUS", "Pro").setValue("geometry", self.saveGeometry())
        for page in self._pg_cache.values():
            w = getattr(page, "_worker", None)
            if w and hasattr(w, "isRunning") and w.isRunning():
                # Сначала просим воркер остановиться сам (кооперативно) —
                # это даёт ему шанс закрыть файлы/сокеты корректно.
                if hasattr(w, "request_cancel"):
                    w.request_cancel()
                if not w.wait(3000):
                    # Не успел за 3 сек — это уже нештатная ситуация,
                    # terminate() остаётся последним резервом, а не нормой.
                    w.terminate()
                    w.wait(1500)
        # Скрываем в трей вместо закрытия
        event.ignore()
        self._hide_to_tray()

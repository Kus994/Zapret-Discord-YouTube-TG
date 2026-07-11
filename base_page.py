"""
base_page.py — KUS Pro
Базовый класс всех страниц.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame,
    QPlainTextEdit, QPushButton, QSizePolicy, QScrollArea,
)
from PyQt5.QtCore import QDateTime
from theme import TEXT_DIM, TEXT_MAIN
from qt_compat import *


class BasePage(QWidget):
    PAGE_TITLE = ""
    PAGE_SUB = ""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._action_btns = []  # Кнопки, блокируемые во время работы worker
        self._worker = None  # Текущий фоновый воркер

        # Scroll area для адаптивности
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(1)  # Qt.ScrollBarAlwaysOff
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setFrameShape(NoFrame)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._root = QVBoxLayout(container)
        self._root.setContentsMargins(24, 20, 24, 12)
        self._root.setSpacing(12)

        # ── Header ──
        if self.PAGE_TITLE:
            t = QLabel(self.PAGE_TITLE)
            t.setObjectName("page_title")
            self._root.addWidget(t)
        if self.PAGE_SUB:
            s = QLabel(self.PAGE_SUB)
            s.setObjectName("page_sub")
            self._root.addWidget(s)
        if self.PAGE_TITLE:
            sep = QFrame()
            sep.setFrameShape(HLine)
            self._root.addWidget(sep)
            self._root.addSpacing(2)

        # ── Content (subclass fills _content) ──
        self._content = QVBoxLayout()
        self._content.setSpacing(12)
        self._root.addLayout(self._content, 1)

        scroll.setWidget(container)

        # Основной layout страницы
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(scroll)

        # ── Log console (вне скролла, внизу) ──
        self._log_box = QPlainTextEdit()
        self._log_box.setReadOnly(True)
        self._log_box.setMaximumBlockCount(800)
        self._log_box.setFixedHeight(120)
        self._log_box.setPlaceholderText("Лог операций появится здесь...")
        main_layout.addWidget(self._log_box)

        # ── Progress bar ──
        from widgets import LiquidProgressBar
        self._progress = LiquidProgressBar()
        self._progress.setValue(0)
        main_layout.addWidget(self._progress)

        self.build_ui()

    # ── Override in subclass ──────────────────────────────────────── #
    def build_ui(self):
        pass

    # ── Widget factories ─────────────────────────────────────────── #
    def card(self, title="", sub=""):
        """Возвращает карточку-фрейм. Дочерние виджеты добавлять в .lay"""
        f = QFrame()
        f.setObjectName("card")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)
        if title:
            lbl = QLabel(title)
            lbl.setObjectName("card_title")
            lay.addWidget(lbl)
        if sub:
            d = QLabel(sub)
            d.setObjectName("card_sub")
            d.setWordWrap(True)
            lay.addWidget(d)
        f.lay = lay
        return f

    def btn(self, label, obj="", tip=""):
        b = QPushButton(label)
        if obj:
            b.setObjectName(obj)
        if tip:
            b.setToolTip(tip)
        return b

    def _reg_btn(self, b):
        """Зарегистрировать кнопку — блокируется пока worker работает."""
        self._action_btns.append(b)
        return b

    # ── Logging ───────────────────────────────────────────────────── #
    def log(self, text, level="INFO"):
        ts = QDateTime.currentDateTime().toString("hh:mm:ss")
        colors = {
            "INFO":    "#a0c8a0",
            "OK":      "#4caf7d",
            "WARN":    "#f5c842",
            "WARNING": "#f5c842",
            "ERR":     "#e05252",
            "ERROR":   "#e05252",
        }
        c = colors.get(level.upper(), TEXT_MAIN)
        self._log_box.appendHtml(
            '<span style="color:{d}">[{ts}]</span> '
            '<span style="color:{c}">[{lvl}]</span> '
            '<span style="color:{m}">{txt}</span>'.format(
                d=TEXT_DIM, ts=ts, c=c, lvl=level,
                m=TEXT_MAIN, txt=str(text).replace("<", "&lt;").replace(">", "&gt;")
            )
        )
        sb = self._log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_progress(self, val):
        v = min(1.0, max(0.0, float(val)))
        self._progress.setValue(v)

    # ── Worker runner ─────────────────────────────────────────────── #
    def _run_worker(self, func, *args, on_result=None, on_done=None, **kwargs):
        """
        Запускает func(log_func, progress_func, *args, **kwargs) в фоновом потоке.
        Сигнатура func ДОЛЖНА принимать log_func и progress_func первыми.
        """
        from worker import Worker

        if self._worker and self._worker.isRunning():
            self.log("Задача уже выполняется — подождите.", "WARN")
            return

        # Отключаем сигналы старого воркера перед созданием нового
        if self._worker:
            try:
                self._worker.line_out.disconnect()
                self._worker.progress.disconnect()
                self._worker.finished.disconnect()
            except (TypeError, RuntimeError):
                pass
            self._worker.deleteLater()
            self._worker = None

        self._set_busy(True)
        self.set_progress(0)

        w = Worker(func, *args, **kwargs)
        w.line_out.connect(self.log)
        w.progress.connect(self.set_progress)
        w.finished.connect(lambda: self._set_busy(False))
        if on_result:
            w.result.connect(on_result)
        if on_done:
            w.finished.connect(on_done)

        self._worker = w
        w.start()

    def _set_busy(self, busy):
        for b in self._action_btns:
            b.setEnabled(not busy)

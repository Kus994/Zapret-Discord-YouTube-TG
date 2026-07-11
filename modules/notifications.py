"""
modules/notifications.py
------------------------
Система уведомлений KUS Pro.
Toast-уведомления в стиле Windows 10/11.
"""

from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame

from qt_compat import *

from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QRadialGradient


class ToastNotification(QWidget):
    """Toast-уведомление в стиле Windows 10/11."""

    closed = pyqtSignal()

    def __init__(self, title, message, level="info", duration=3000, parent=None):
        super().__init__(parent)
        self.setWindowFlags(FramelessWindowHint | WindowStaysOnTopHint | Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(380)

        # Цвета по уровню
        colors = {
            "info": ("#22d3ee", "#0891b2"),
            "success": ("#00ff88", "#00aa6a"),
            "warning": ("#fbbf24", "#d97706"),
            "error": ("#ef4444", "#dc2626"),
        }
        self._accent, self._accent_dark = colors.get(level, colors["info"])

        # UI
        self._build_ui(title, message)

        # Анимация появления
        self._fade_in = QPropertyAnimation(self, b"windowOpacity")
        self._fade_in.setDuration(300)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)

        # Автозакрытие
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._close)

    def _build_ui(self, title, message):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Карточка
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: rgba(15, 17, 23, 240);
                border: 1px solid {};
                border-radius: 12px;
                border-left: 4px solid {};
            }
        """.format(self._accent, self._accent))

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(4)

        # Заголовок
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: {}; font-size: 14px; font-weight: bold; background: transparent;".format(self._accent))
        card_layout.addWidget(title_lbl)

        # Сообщение
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #e2e8f0; font-size: 12px; background: transparent;")
        card_layout.addWidget(msg_lbl)

        layout.addWidget(card)

    def show_at(self, x, y):
        """Показывает уведомление в указанной позиции."""
        self.move(x, y)
        self.show()
        self.raise_()
        self._fade_in.start()
        self._timer.start(3000)

    def _close(self):
        self._fade_out = QPropertyAnimation(self, b"windowOpacity")
        self._fade_out.setDuration(300)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(self._on_closed)
        self._fade_out.start()

    def _on_closed(self):
        self.closed.emit()
        self.deleteLater()


class NotificationManager:
    """Менеджер уведомлений — показывает toast-уведомления."""

    _instance = None
    _notifications = []

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def show(self, title, message, level="info", duration=3000, parent=None):
        """Показывает toast-уведомление."""
        toast = ToastNotification(title, message, level, duration, parent)

        # Позиционируем в правом верхнем углу
        if parent:
            geo = parent.geometry()
            x = geo.right() - 400
            y = geo.top() + 20
        else:
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.primaryScreen().geometry()
            x = screen.width() - 400
            y = 50

        # Сдвигаем вниз для каждой новой нотификации
        offset = len(self._notifications) * 80
        toast.show_at(x, y + offset)

        self._notifications.append(toast)
        toast.closed.connect(lambda: self._on_closed(toast))

    def _on_closed(self, toast):
        if toast in self._notifications:
            self._notifications.remove(toast)

    def info(self, title, message, parent=None):
        self.show(title, message, "info", parent=parent)

    def success(self, title, message, parent=None):
        self.show(title, message, "success", parent=parent)

    def warning(self, title, message, parent=None):
        self.show(title, message, "warning", parent=parent)

    def error(self, title, message, parent=None):
        self.show(title, message, "error", parent=parent)

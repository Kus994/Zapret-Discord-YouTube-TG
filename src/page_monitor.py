"""
page_monitor.py — KUS Pro
Premium system monitor dashboard with glow gauges, smooth sparklines,
disk cards with gradient bars, styled process table, and system info.
"""

import math

from qt_compat import *

import os
import time
import threading
from collections import deque

from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QWidget, QSizePolicy, QFrame,
)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, QThread, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QLinearGradient, QFont, QPainterPath,
    QRadialGradient,
)

from base_page import BasePage
from theme import (
    ACCENT as _ACCENT_HEX, SUCCESS as _SUCCESS_HEX, WARNING as _WARNING_HEX,
    DANGER as _DANGER_HEX, TEXT_MAIN as _TEXT_MAIN_HEX, TEXT_DIM as _TEXT_DIM_HEX,
)

ACCENT    = QColor(_ACCENT_HEX)
SUCCESS   = QColor(_SUCCESS_HEX)
WARNING   = QColor(_WARNING_HEX)
DANGER    = QColor(_DANGER_HEX)
NET_DOWN  = QColor(_SUCCESS_HEX)
NET_UP    = QColor(_ACCENT_HEX)
TEXT_MAIN  = QColor(_TEXT_MAIN_HEX)
TEXT_DIM   = QColor(_TEXT_DIM_HEX)
TEXT_MUTED = QColor("#5a5248")
TRACK      = QColor(255, 255, 255, 16)
CARD_BG    = QColor(18, 19, 26, 242)
CARD_BORDER = QColor(0, 255, 136, 51)
ROW_ALT     = QColor(255, 255, 255, 8)
ROW_HOVER   = QColor(255, 255, 255, 14)


def _level_color(pct: float) -> QColor:
    if pct >= 90:
        return DANGER
    if pct >= 70:
        return WARNING
    return SUCCESS


# ──────────────────────────────────────────────────────────────────────
# Card frame
# ──────────────────────────────────────────────────────────────────────

class _CardFrame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        # Subtle gradient background
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(28, 29, 38))
        grad.setColorAt(1.0, QColor(16, 17, 24))
        p.setBrush(grad)
        p.setPen(QPen(CARD_BORDER, 1))
        p.drawRoundedRect(rect, 12, 12)
        p.end()


def _card_title(text):
    lbl = QLabel(text)
    lbl.setObjectName("card_sub")
    lbl.setStyleSheet(
        "color:#5a5248; font-size:10px; font-weight:800; "
        "letter-spacing:1.5px; text-transform:uppercase; background:transparent;"
    )
    return lbl


# ──────────────────────────────────────────────────────────────────────
# GaugeRing — 100×100 with glow
# ──────────────────────────────────────────────────────────────────────

class GaugeRing(QWidget):
    """100×100 ring gauge with outer glow effect on the arc.

    УЛУЧШЕНИЕ («более динамичный дизайн»): раньше set_value() сразу
    перескакивал на новое значение — визуально дуга «дёргалась» каждые
    1.5 сек, когда приходил новый снапшот. Теперь текущее отображаемое
    значение (_pct) плавно едет к целевому (_target_pct) на отдельном
    таймере ~60 FPS с ease-out — между тиками данных дуга не стоит на
    месте, а всё время что-то делает, как в живом дашборде. Таймер сам
    останавливается, когда анимация "доехала" до цели, чтобы не грузить
    CPU перерисовкой в состоянии покоя.
    """

    def __init__(self, label, parent=None):
        super().__init__(parent)
        self._label = label
        self._pct = 0.0
        self._target_pct = 0.0
        self._value_text = "—"
        self._color = SUCCESS
        self.setFixedSize(100, 100)

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60 FPS
        self._anim_timer.timeout.connect(self._animate_step)

    def set_value(self, pct, value_text):
        self._target_pct = max(0.0, min(100.0, pct))
        self._value_text = value_text
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _animate_step(self):
        diff = self._target_pct - self._pct
        if abs(diff) < 0.05:
            self._pct = self._target_pct
            self._anim_timer.stop()
        else:
            self._pct += diff * 0.22  # ease-out — быстрее вначале, плавно замедляется
        self._color = _level_color(self._pct)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.width() / 2.0, self.height() / 2.0
        outer_r = 44.0
        pen_w = 10.0
        inner_r = outer_r - pen_w

        rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)

        # Track ring
        p.setPen(QPen(QColor(255, 255, 255, 14), pen_w, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect.adjusted(pen_w / 2, pen_w / 2, -pen_w / 2, -pen_w / 2),
                  0, 360 * 16)

        # Glow layers (drawn behind the arc)
        glow_color = QColor(self._color)
        for alpha, blur in [(12, 6), (8, 10), (5, 14)]:
            gc = QColor(glow_color)
            gc.setAlpha(alpha)
            p.setPen(QPen(gc, pen_w + blur, Qt.SolidLine, Qt.RoundCap))
            span = int(self._pct / 100.0 * 360 * 16)
            p.drawArc(rect, 90 * 16, -span)

        # Main arc
        pen_color = QColor(self._color)
        p.setPen(QPen(pen_color, pen_w, Qt.SolidLine, Qt.RoundCap))
        span = int(self._pct / 100.0 * 360 * 16)
        p.drawArc(rect, 90 * 16, -span)

        # Bright tip glow at the end of the arc
        if self._pct > 1.0:
            end_angle_deg = 90 - self._pct / 100.0 * 360
            end_angle_rad = math.radians(end_angle_deg)
            mid_r = outer_r - pen_w / 2
            tip_x = cx + mid_r * math.cos(end_angle_rad)
            tip_y = cy - mid_r * math.sin(end_angle_rad)
            tip_glow = QRadialGradient(tip_x, tip_y, 8)
            tc = QColor(self._color)
            tc.setAlpha(90)
            tip_glow.setColorAt(0.0, tc)
            tc2 = QColor(self._color)
            tc2.setAlpha(0)
            tip_glow.setColorAt(1.0, tc2)
            p.setPen(Qt.NoPen)
            p.setBrush(tip_glow)
            p.drawEllipse(QPointF(tip_x, tip_y), 8, 8)

        # Center text
        p.setPen(TEXT_MAIN)
        f = QFont("Segoe UI", 16, QFont.Bold)
        p.setFont(f)
        p.drawText(self.rect().adjusted(0, -8, 0, -8), AlignCenter, self._value_text)

        # Label below
        p.setPen(TEXT_DIM)
        f2 = QFont("Segoe UI", 7, QFont.Bold)
        p.setFont(f2)
        p.drawText(self.rect().adjusted(0, 18, 0, 18), AlignCenter, self._label)
        p.end()


# ──────────────────────────────────────────────────────────────────────
# CoreBars — mini bar-chart per core with glow
# ──────────────────────────────────────────────────────────────────────

class CoreBars(QWidget):
    """УЛУЧШЕНИЕ: те же соображения, что в GaugeRing — полоски по ядрам
    плавно едут к новому значению вместо рывка каждые 1.5 сек."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = []
        self._targets = []
        self.setMinimumHeight(36)
        self.setMinimumWidth(80)
        self.setSizePolicy(Expanding, Fixed)

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._animate_step)

    def set_values(self, values):
        self._targets = list(values)
        # Число ядер не меняется в рантайме — но на всякий случай
        # синхронизируем длину без анимации, чтобы не индексировать
        # мимо списка.
        if len(self._values) != len(self._targets):
            self._values = list(self._targets)
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _animate_step(self):
        moving = False
        for i, target in enumerate(self._targets):
            diff = target - self._values[i]
            if abs(diff) < 0.1:
                self._values[i] = target
            else:
                self._values[i] += diff * 0.22
                moving = True
        if not moving:
            self._anim_timer.stop()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self._values:
            p.end()
            return

        n = len(self._values)
        gap = 2
        w = max(2.5, (self.width() - gap * (n - 1)) / n)
        h = self.height()

        for i, v in enumerate(self._values):
            v = max(0.0, min(100.0, v))
            bar_h = max(2.0, h * (v / 100.0))
            x = i * (w + gap)
            y = h - bar_h
            color = _level_color(v)

            # Glow under bar
            gc = QColor(color)
            gc.setAlpha(25)
            p.setPen(Qt.NoPen)
            p.setBrush(gc)
            p.drawRoundedRect(QRectF(x - 1, y + 1, w + 2, bar_h), 2, 2)

            # Main bar
            p.setBrush(color)
            p.drawRoundedRect(QRectF(x, y, w, bar_h), 1.5, 1.5)
        p.end()


# ──────────────────────────────────────────────────────────────────────
# Sparkline — smooth bezier curves
# ──────────────────────────────────────────────────────────────────────

class Sparkline(QWidget):
    """Smooth sparkline with bezier interpolation and gradient fill."""

    def __init__(self, maxlen=60, color=None, parent=None):
        super().__init__(parent)
        self._data = deque(maxlen=maxlen)
        self._color = color or ACCENT
        self.setMinimumHeight(52)
        self.setSizePolicy(Expanding, Fixed)

    def push(self, value):
        self._data.append(max(0.0, min(100.0, value)))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        if len(self._data) < 2:
            p.end()
            return

        n = len(self._data)
        step = w / max(1, n - 1)

        pts = [
            QPointF(i * step, h - (val / 100.0) * (h - 6) - 3)
            for i, val in enumerate(self._data)
        ]

        # Area fill
        area = QPainterPath()
        area.moveTo(pts[0].x(), h)
        area.lineTo(pts[0].x(), pts[0].y())
        for i in range(1, len(pts)):
            area.lineTo(pts[i].x(), pts[i].y())
        area.lineTo(pts[-1].x(), h)
        area.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        fill_color = QColor(self._color)
        fill_color.setAlpha(50)
        grad.setColorAt(0.0, fill_color)
        transparent = QColor(self._color)
        transparent.setAlpha(0)
        grad.setColorAt(1.0, transparent)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawPath(area)

        # Smooth line
        line = QPainterPath()
        line.moveTo(pts[0])
        for i in range(1, len(pts)):
            # Bezier smoothing between consecutive points
            prev = pts[i - 1]
            curr = pts[i]
            cpx = (prev.x() + curr.x()) / 2.0
            line.cubicTo(QPointF(cpx, prev.y()), QPointF(cpx, curr.y()), curr)

        p.setPen(QPen(self._color, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(line)
        p.end()


# ──────────────────────────────────────────────────────────────────────
# Process table widget
# ──────────────────────────────────────────────────────────────────────

class _ProcessTable(QWidget):
    """Styled table with column headers and alternating row backgrounds."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        # Column headers
        hdr = QHBoxLayout()
        hdr.setContentsMargins(12, 8, 12, 8)
        for text, w in [("Process", 0), ("CPU %", 70), ("RAM (MB)", 70)]:
            lbl = QLabel(text)
            lbl.setStyleSheet(
                "color:#5a5248; font-size:10px; font-weight:800; "
                "letter-spacing:1px; background:transparent;"
            )
            if w:
                lbl.setFixedWidth(w)
            lbl.setAlignment(AlignRight if w else AlignLeft | AlignVCenter)
            hdr.addWidget(lbl)
        self._root.addLayout(hdr)

        self._rows_lay = QVBoxLayout()
        self._rows_lay.setSpacing(0)
        self._root.addLayout(self._rows_lay)

    def set_items(self, items):
        """Update table with items list. Each item: {name, cpu_percent, memory_mb}."""
        # Remove excess rows if we have fewer items than existing rows
        while len(self._rows) > len(items):
            row = self._rows.pop()
            self._rows_lay.removeWidget(row)
            row.setParent(None)
            row.deleteLater()

        while len(self._rows) < len(items):
            row = _ProcessRow()
            self._rows_lay.addWidget(row)
            self._rows.append(row)

        for i, row in enumerate(self._rows):
            row.setVisible(i < len(items))
            if i < len(items):
                row.set_data(i, items[i])


class _ProcessRow(QWidget):
    """Single row with alternating background, name, cpu%, mem mb."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_alt = False
        self._root = QHBoxLayout(self)
        self._root.setContentsMargins(12, 6, 12, 6)
        self._root.setSpacing(0)

        self._name = QLabel("—")
        self._name.setStyleSheet("color:#ddd8d0; font-size:12px; background:transparent;")
        self._name.setSizePolicy(Expanding, Fixed)
        self._root.addWidget(self._name, 1)

        self._cpu = QLabel("—")
        self._cpu.setAlignment(AlignRight | AlignVCenter)
        self._cpu.setFixedWidth(70)
        self._root.addWidget(self._cpu)

        self._mem = QLabel("—")
        self._mem.setAlignment(AlignRight | AlignVCenter)
        self._mem.setFixedWidth(70)
        self._root.addWidget(self._mem)

    def set_data(self, index, item):
        self._is_alt = index % 2 == 0
        self._name.setText(item["name"])
        self._name.setToolTip(item["name"])
        cpu_val = item.get("cpu_percent", 0.0)
        mem_val = item.get("memory_mb", 0.0)
        self._cpu.setText("{:.1f}".format(cpu_val))
        self._cpu.setStyleSheet(
            "color:{}; font-size:12px; font-weight:700; background:transparent;".format(
                "#f5a623" if cpu_val > 20 else "#e8ddd0"
            )
        )
        self._mem.setText("{:.0f}".format(mem_val))
        self._mem.setStyleSheet(
            "color:{}; font-size:12px; font-weight:700; background:transparent;".format(
                "#f5a623" if mem_val > 200 else "#e8ddd0"
            )
        )

    def paintEvent(self, event):
        # Draw alternating background
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg = ROW_ALT if self._is_alt else QColor(0, 0, 0, 0)
        p.fillRect(self.rect(), bg)
        p.end()

        # Chain to parent for children
        super().paintEvent(event)


# ──────────────────────────────────────────────────────────────────────
# Disk card — individual mini card with gradient bar
# ──────────────────────────────────────────────────────────────────────

class _DiskCard(QWidget):
    """Single disk card: drive letter, progress bar, used/total, percentage."""

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self._pct = 0.0
        self._name = name
        self.setFixedHeight(72)
        self.setSizePolicy(Expanding, Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        # Top row: drive name + percentage
        top = QHBoxLayout()
        top.setContentsMargins(14, 10, 14, 0)
        self._lbl_name = QLabel(name)
        self._lbl_name.setStyleSheet(
            "color:#e8ddd0; font-size:13px; font-weight:700; background:transparent;"
        )
        top.addWidget(self._lbl_name)
        top.addStretch()
        self._lbl_pct = QLabel("—")
        self._lbl_pct.setStyleSheet(
            "color:#f5a623; font-size:12px; font-weight:700; background:transparent;"
        )
        top.addWidget(self._lbl_pct)
        root.addLayout(top)

        # Bottom row: progress bar + space info
        bot = QHBoxLayout()
        bot.setContentsMargins(14, 0, 14, 10)
        self._bar = _DiskBar()
        bot.addWidget(self._bar, 1)
        self._lbl_info = QLabel("—")
        self._lbl_info.setStyleSheet(
            "color:#7a7068; font-size:11px; background:transparent;"
        )
        self._lbl_info.setFixedWidth(120)
        self._lbl_info.setAlignment(AlignRight | AlignVCenter)
        bot.addWidget(self._lbl_info)
        root.addLayout(bot)

    def update_values(self, pct, text):
        self._pct = pct
        self._lbl_pct.setText("{:.0f}%".format(pct))
        self._lbl_info.setText(text)

        color = _level_color(pct)
        self._lbl_pct.setStyleSheet(
            "color:{}; font-size:12px; font-weight:700; background:transparent;".format(
                color.name()
            )
        )
        self._bar.set_pct(pct)


class _DiskBar(QWidget):
    """Gradient fill bar with rounded corners."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pct = 0.0
        self.setFixedHeight(6)
        self.setSizePolicy(Expanding, Fixed)

    def set_pct(self, pct):
        self._pct = max(0.0, min(100.0, pct))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())

        # Track
        p.setPen(Qt.NoPen)
        p.setBrush(TRACK)
        p.drawRoundedRect(rect, 3, 3)

        fill_w = rect.width() * (self._pct / 100.0)
        if fill_w <= 0:
            p.end()
            return

        fill_rect = QRectF(rect.x(), rect.y(), fill_w, rect.height())
        color = _level_color(self._pct)

        # Gradient fill
        grad = QLinearGradient(fill_rect.left(), 0, fill_rect.right(), 0)
        dark = QColor(color).darker(130)
        grad.setColorAt(0.0, dark)
        grad.setColorAt(0.7, color)
        bright = QColor(color).lighter(130)
        grad.setColorAt(1.0, bright)

        p.setBrush(grad)
        p.drawRoundedRect(fill_rect, 3, 3)

        # Subtle glow at the tip
        if fill_w > 4:
            tip_glow = QRadialGradient(fill_rect.right(), rect.center().y(), 6)
            gc = QColor(color)
            gc.setAlpha(40)
            tip_glow.setColorAt(0.0, gc)
            gc2 = QColor(color)
            gc2.setAlpha(0)
            tip_glow.setColorAt(1.0, gc2)
            p.setBrush(tip_glow)
            p.drawEllipse(QPointF(fill_rect.right(), rect.center().y()), 6, 6)
        p.end()


# ──────────────────────────────────────────────────────────────────────
# Network sparkline (color-aware)
# ──────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────
# FanCurve — temperature-to-fan-speed mapping visualization
# ──────────────────────────────────────────────────────────────────────




class DiskRow(QWidget):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self._pct = 0.0
        self._name = name
        self.setMinimumHeight(22)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self._lbl_name = QLabel(name)
        self._lbl_name.setFixedWidth(56)
        self._lbl_name.setStyleSheet(
            "color:#e8ddd0; font-size:12px; font-weight:700; background:transparent;"
        )
        lay.addWidget(self._lbl_name)

        self._bar = _DiskBar()
        lay.addWidget(self._bar, 1)

        self._lbl_val = QLabel("—")
        self._lbl_val.setFixedWidth(130)
        self._lbl_val.setAlignment(AlignRight | AlignVCenter)
        self._lbl_val.setStyleSheet(
            "color:#a8a098; font-size:11px; background:transparent;"
        )
        lay.addWidget(self._lbl_val)

    def update_values(self, pct, text):
        self._bar.set_pct(pct)
        self._lbl_val.setText(text)


class FanCurveWidget(QWidget):
    """Draws a temperature (X) vs fan speed % (Y) graph with a curved line
    and fills the area below.  Accepts a list of (temp, speed%) tuples for
    the curve and a current operating point (temp, speed%) shown as a dot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._curve_points = []  # [(temp, speed%), ...]
        self._current = None     # (temp, speed%)
        self.setMinimumHeight(110)
        self.setSizePolicy(Expanding, Fixed)

    def set_curve(self, points):
        """points: list of (temp_celsius, fan_speed_percent)"""
        self._curve_points = list(points)
        self.update()

    def set_current(self, temp, speed):
        """Mark the current operating point on the curve."""
        self._current = (temp, speed)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 36, 12, 8, 22
        gw = w - pad_l - pad_r
        gh = h - pad_t - pad_b

        # Background grid area
        grid_rect = QRectF(pad_l, pad_t, gw, gh)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 6))
        p.drawRoundedRect(grid_rect, 4, 4)

        # Axes labels
        p.setPen(TEXT_DIM)
        f = QFont("Segoe UI", 7)
        p.setFont(f)
        # X-axis: 0°C .. 100°C
        for temp_val in (0, 25, 50, 75, 100):
            x = pad_l + (temp_val / 100.0) * gw
            p.drawText(QRectF(x - 12, h - 16, 24, 14), AlignCenter, "{}°".format(temp_val))
            # Vertical grid line
            p.setPen(QPen(QColor(255, 255, 255, 10), 1, Qt.DotLine))
            p.drawLine(QPointF(x, pad_t), QPointF(x, pad_t + gh))
            p.setPen(Qt.NoPen)
        # Y-axis: 0% .. 100%
        for pct_val in (0, 25, 50, 75, 100):
            y = pad_t + gh - (pct_val / 100.0) * gh
            p.setPen(TEXT_DIM)
            p.drawText(QRectF(0, y - 7, pad_l - 4, 14), AlignRight | AlignVCenter, "{}%".format(pct_val))
            # Horizontal grid line
            p.setPen(QPen(QColor(255, 255, 255, 10), 1, Qt.DotLine))
            p.drawLine(QPointF(pad_l, y), QPointF(pad_l + gw, y))
            p.setPen(Qt.NoPen)

        if len(self._curve_points) < 2:
            p.setPen(TEXT_MUTED)
            p.setFont(QFont("Segoe UI", 9))
            p.drawText(self.rect(), AlignCenter, "Нет данных кривой вентилятора")
            p.end()
            return

        # Map curve points to widget coordinates
        def _map(temp, speed):
            x = pad_l + (max(0, min(100, temp)) / 100.0) * gw
            y = pad_t + gh - (max(0, min(100, speed)) / 100.0) * gh
            return QPointF(x, y)

        pts = [_map(t, s) for t, s in self._curve_points]

        # Area fill under curve
        area = QPainterPath()
        area.moveTo(pts[0].x(), pad_t + gh)
        area.lineTo(pts[0].x(), pts[0].y())
        for i in range(1, len(pts)):
            prev, curr = pts[i - 1], pts[i]
            cpx = (prev.x() + curr.x()) / 2.0
            area.cubicTo(QPointF(cpx, prev.y()), QPointF(cpx, curr.y()), curr)
        area.lineTo(pts[-1].x(), pad_t + gh)
        area.closeSubpath()

        grad = QLinearGradient(0, pad_t, 0, pad_t + gh)
        fc = QColor(ACCENT)
        fc.setAlpha(35)
        grad.setColorAt(0.0, fc)
        tr = QColor(ACCENT)
        tr.setAlpha(0)
        grad.setColorAt(1.0, tr)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawPath(area)

        # Curve line
        line = QPainterPath()
        line.moveTo(pts[0])
        for i in range(1, len(pts)):
            prev, curr = pts[i - 1], pts[i]
            cpx = (prev.x() + curr.x()) / 2.0
            line.cubicTo(QPointF(cpx, prev.y()), QPointF(cpx, curr.y()), curr)

        p.setPen(QPen(ACCENT, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(line)

        # Glow on curve
        for alpha, blur in [(18, 4), (10, 8)]:
            gc = QColor(ACCENT)
            gc.setAlpha(alpha)
            p.setPen(QPen(gc, 2.0 + blur, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(line)

        # Current operating point
        if self._current:
            cx, cy = _map(self._current[0], self._current[1])
            # Outer glow
            for r, alpha in [(10, 20), (6, 45)]:
                glow = QRadialGradient(cx, cy, r)
                gc = QColor(SUCCESS)
                gc.setAlpha(alpha)
                glow.setColorAt(0.0, gc)
                gc2 = QColor(SUCCESS)
                gc2.setAlpha(0)
                glow.setColorAt(1.0, gc2)
                p.setPen(Qt.NoPen)
                p.setBrush(glow)
                p.drawEllipse(cx, cy, r, r)
            # Dot
            p.setPen(QPen(SUCCESS, 2))
            p.setBrush(SUCCESS)
            p.drawEllipse(cx, cy, 4, 4)

        p.end()


class _NetSparkline(Sparkline):
    """Sparkline that supports custom colors and tracks absolute values."""

    def __init__(self, color=ACCENT, parent=None):
        super().__init__(maxlen=120, color=color, parent=parent)

    def paintEvent(self, event):
        # Remap: net speed can exceed 100, so we auto-scale
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        if len(self._data) < 2:
            p.end()
            return

        n = len(self._data)
        step = w / max(1, n - 1)
        max_val = max(self._data) if self._data else 1.0
        max_val = max(max_val, 1.0)

        pts = [
            QPointF(i * step, h - (val / max_val) * (h - 6) - 3)
            for i, val in enumerate(self._data)
        ]

        # Area
        area = QPainterPath()
        area.moveTo(pts[0].x(), h)
        area.lineTo(pts[0].x(), pts[0].y())
        for i in range(1, len(pts)):
            area.lineTo(pts[i].x(), pts[i].y())
        area.lineTo(pts[-1].x(), h)
        area.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        fc = QColor(self._color)
        fc.setAlpha(45)
        grad.setColorAt(0.0, fc)
        tr = QColor(self._color)
        tr.setAlpha(0)
        grad.setColorAt(1.0, tr)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawPath(area)

        # Line
        line = QPainterPath()
        line.moveTo(pts[0])
        for i in range(1, len(pts)):
            prev, curr = pts[i - 1], pts[i]
            cpx = (prev.x() + curr.x()) / 2.0
            line.cubicTo(QPointF(cpx, prev.y()), QPointF(cpx, curr.y()), curr)

        p.setPen(QPen(self._color, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(line)
        p.end()



# ──────────────────────────────────────────────────────────────────────
# _HardwareThread — background sensor reading
# ──────────────────────────────────────────────────────────────────────

class _HardwareThread(QThread):
    """Reads hardware sensors in a background thread to avoid blocking the UI."""
    hw_ready = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        from modules.hardware import get_hardware_sensors
        while not self._stop_event.is_set():
            try:
                hw = get_hardware_sensors()
                if not self._stop_event.is_set():
                    self.hw_ready.emit(hw)
            except Exception:
                pass
            self.msleep(2000)


# ──────────────────────────────────────────────────────────────────────
# MonitorPage
# ──────────────────────────────────────────────────────────────────────

class MonitorPage(BasePage):
    PAGE_TITLE = "📊  Мониторинг ресурсов"
    PAGE_SUB   = "CPU, RAM и диски в реальном времени"

    def build_ui(self):
        self._log_box.setFixedHeight(0)
        self._log_box.setVisible(False)
        self._progress.setVisible(False)

        self._disk_cards = {}

        # ════════════════════════════════════════════════════════════════
        # TOP ROW: CPU + RAM cards
        # ════════════════════════════════════════════════════════════════
        top = QHBoxLayout()
        top.setSpacing(14)

        # CPU card
        cpu_card, cpu_lay = self._gauge_card()
        cpu_left = QVBoxLayout()
        cpu_left.setSpacing(4)
        cpu_label = QLabel("CPU")
        cpu_label.setStyleSheet(
            "color:#00ff88; font-size:10px; font-weight:800; "
            "letter-spacing:1.5px; background:transparent;"
        )
        cpu_left.addWidget(cpu_label)
        self._cpu_ring = GaugeRing("load")
        cpu_left.addWidget(self._cpu_ring)
        cpu_left.addStretch()
        cpu_lay.addLayout(cpu_left)

        cpu_right = QVBoxLayout()
        cpu_right.setSpacing(6)
        self._cpu_sub = QLabel("—")
        self._cpu_sub.setStyleSheet("color:#f0f4f8; font-size:13px; font-weight:600; background:transparent;")
        cpu_right.addWidget(self._cpu_sub)
        self._cpu_freq = QLabel("—")
        self._cpu_freq.setStyleSheet("color:#8899aa; font-size:11px; background:transparent;")
        cpu_right.addWidget(self._cpu_freq)
        self._core_bars = CoreBars()
        cpu_right.addWidget(self._core_bars)
        cpu_lay.addLayout(cpu_right, 1)
        top.addWidget(cpu_card, 1)

        # RAM card
        ram_card, ram_lay = self._gauge_card()
        ram_left = QVBoxLayout()
        ram_left.setSpacing(4)
        ram_label = QLabel("RAM")
        ram_label.setStyleSheet(
            "color:#00ff88; font-size:10px; font-weight:800; "
            "letter-spacing:1.5px; background:transparent;"
        )
        ram_left.addWidget(ram_label)
        self._ram_ring = GaugeRing("usage")
        ram_left.addWidget(self._ram_ring)
        ram_left.addStretch()
        ram_lay.addLayout(ram_left)

        ram_right = QVBoxLayout()
        ram_right.setSpacing(6)
        self._ram_sub = QLabel("—")
        self._ram_sub.setStyleSheet("color:#f0f4f8; font-size:13px; font-weight:600; background:transparent;")
        ram_right.addWidget(self._ram_sub)
        self._ram_free = QLabel("—")
        self._ram_free.setStyleSheet("color:#8899aa; font-size:11px; background:transparent;")
        ram_right.addWidget(self._ram_free)
        self._ram_total = QLabel("—")
        self._ram_total.setStyleSheet("color:#6a7a8a; font-size:11px; background:transparent;")
        ram_right.addWidget(self._ram_total)
        ram_right.addStretch()
        ram_lay.addLayout(ram_right, 1)
        top.addWidget(ram_card, 1)

        self._content.addLayout(top)

        # ════════════════════════════════════════════════════════════════
        # NETWORK card — full width with sparklines + totals
        # ════════════════════════════════════════════════════════════════
        net_card = _CardFrame()
        net_lay = QVBoxLayout(net_card)
        net_lay.setContentsMargins(18, 14, 18, 14)
        net_lay.setSpacing(10)
        net_lay.addWidget(_card_title("СЕТЬ"))

        # Download row
        dl_row = QHBoxLayout()
        dl_row.setSpacing(10)
        dl_label = QLabel("↓ Download")
        dl_label.setStyleSheet(
            "color:#4caf7d; font-size:12px; font-weight:700; background:transparent;"
        )
        dl_row.addWidget(dl_label)
        self._net_down_val = QLabel("— КБ/с")
        self._net_down_val.setStyleSheet(
            "color:#4caf7d; font-size:14px; font-weight:700; background:transparent;"
        )
        dl_row.addWidget(self._net_down_val)
        self._net_down_total = QLabel("—")
        self._net_down_total.setStyleSheet(
            "color:#8899aa; font-size:11px; background:transparent;"
        )
        dl_row.addWidget(self._net_down_total)
        dl_row.addStretch()
        net_lay.addLayout(dl_row)

        self._net_down_spark = _NetSparkline(color=NET_DOWN)
        net_lay.addWidget(self._net_down_spark)

        # Upload row
        ul_row = QHBoxLayout()
        ul_row.setSpacing(10)
        ul_label = QLabel("↑ Upload")
        ul_label.setStyleSheet(
            "color:#f5a623; font-size:12px; font-weight:700; background:transparent;"
        )
        ul_row.addWidget(ul_label)
        self._net_up_val = QLabel("— КБ/с")
        self._net_up_val.setStyleSheet(
            "color:#f5a623; font-size:14px; font-weight:700; background:transparent;"
        )
        ul_row.addWidget(self._net_up_val)
        self._net_up_total = QLabel("—")
        self._net_up_total.setStyleSheet(
            "color:#8899aa; font-size:11px; background:transparent;"
        )
        ul_row.addWidget(self._net_up_total)
        ul_row.addStretch()
        net_lay.addLayout(ul_row)

        self._net_up_spark = _NetSparkline(color=NET_UP)
        net_lay.addWidget(self._net_up_spark)

        self._content.addWidget(net_card)

        # ════════════════════════════════════════════════════════════════
        # HARDWARE — temperatures, fans, voltages, fan curve
        # ════════════════════════════════════════════════════════════════
        hw_card = _CardFrame()
        hw_lay = QVBoxLayout(hw_card)
        hw_lay.setContentsMargins(18, 14, 18, 14)
        hw_lay.setSpacing(10)
        hw_lay.addWidget(_card_title("АППАРАТНЫЕ ДАТЧИКИ"))

        hw_body = QHBoxLayout()
        hw_body.setSpacing(20)

        # — Temperatures column —
        hw_temps_col = QVBoxLayout()
        hw_temps_col.setSpacing(4)
        hw_temps_hdr = QLabel("ТЕМПЕРАТУРА")
        hw_temps_hdr.setStyleSheet(
            "color:#5a5248; font-size:10px; font-weight:800; "
            "letter-spacing:1px; background:transparent;"
        )
        hw_temps_col.addWidget(hw_temps_hdr)
        self._hw_temps_rows = QVBoxLayout()
        self._hw_temps_rows.setSpacing(3)
        hw_temps_col.addLayout(self._hw_temps_rows)
        hw_temps_col.addStretch()
        hw_body.addLayout(hw_temps_col, 2)

        # — Fan speeds + curve column —
        hw_fans_col = QVBoxLayout()
        hw_fans_col.setSpacing(4)
        hw_fans_hdr = QLabel("ВЕНТИЛЯТОРЫ")
        hw_fans_hdr.setStyleSheet(
            "color:#5a5248; font-size:10px; font-weight:800; "
            "letter-spacing:1px; background:transparent;"
        )
        hw_fans_col.addWidget(hw_fans_hdr)
        self._hw_fans_rows = QVBoxLayout()
        self._hw_fans_rows.setSpacing(3)
        hw_fans_col.addLayout(self._hw_fans_rows)

        self._hw_fan_curve = FanCurveWidget()
        hw_fans_col.addWidget(self._hw_fan_curve)
        hw_body.addLayout(hw_fans_col, 3)

        # — Voltages column —
        hw_volts_col = QVBoxLayout()
        hw_volts_col.setSpacing(4)
        hw_volts_hdr = QLabel("НАПРЯЖЕНИЕ")
        hw_volts_hdr.setStyleSheet(
            "color:#5a5248; font-size:10px; font-weight:800; "
            "letter-spacing:1px; background:transparent;"
        )
        hw_volts_col.addWidget(hw_volts_hdr)
        self._hw_volts_rows = QVBoxLayout()
        self._hw_volts_rows.setSpacing(3)
        hw_volts_col.addLayout(self._hw_volts_rows)
        hw_volts_col.addStretch()
        hw_body.addLayout(hw_volts_col, 2)

        hw_lay.addLayout(hw_body)

        self._hw_label_pool = []
        self._hw_last_temps = []
        self._hw_last_fans = []

        # Background hardware sensor thread - started in showEvent
        self._hw_thread = None

        self._content.addWidget(hw_card)

        # ════════════════════════════════════════════════════════════════
        # DISK CARDS — grid layout, each disk gets own mini card
        # ════════════════════════════════════════════════════════════════
        self._disk_container = _CardFrame()
        disk_container_lay = QVBoxLayout(self._disk_container)
        disk_container_lay.setContentsMargins(18, 14, 18, 14)
        disk_container_lay.setSpacing(10)
        disk_container_lay.addWidget(_card_title("ДИСКИ"))
        self._disk_rows_lay = QVBoxLayout()
        self._disk_rows_lay.setSpacing(6)
        disk_container_lay.addLayout(self._disk_rows_lay)
        self._content.addWidget(self._disk_container)

        # ════════════════════════════════════════════════════════════════
        # PROCESSES — styled table with columns
        # ════════════════════════════════════════════════════════════════
        proc_card = _CardFrame()
        proc_lay = QVBoxLayout(proc_card)
        proc_lay.setContentsMargins(0, 14, 0, 14)
        proc_lay.setSpacing(0)
        proc_lay.addWidget(_card_title("  ПРОЦЕССЫ"))

        proc_container = QWidget()
        proc_container.setStyleSheet("background:transparent;")
        proc_inner = QHBoxLayout(proc_container)
        proc_inner.setContentsMargins(14, 10, 14, 0)
        proc_inner.setSpacing(20)

        # CPU column
        cpu_proc = QVBoxLayout()
        cpu_proc.setSpacing(4)
        cpu_proc_head = QLabel("TOP BY CPU")
        cpu_proc_head.setStyleSheet(
            "color:#5a5248; font-size:10px; font-weight:800; "
            "letter-spacing:1px; background:transparent;"
        )
        cpu_proc.addWidget(cpu_proc_head)
        self._top_cpu_table = _ProcessTable()
        cpu_proc.addWidget(self._top_cpu_table)
        proc_inner.addLayout(cpu_proc, 1)

        # Mem column
        mem_proc = QVBoxLayout()
        mem_proc.setSpacing(4)
        mem_proc_head = QLabel("TOP BY MEMORY")
        mem_proc_head.setStyleSheet(
            "color:#5a5248; font-size:10px; font-weight:800; "
            "letter-spacing:1px; background:transparent;"
        )
        mem_proc.addWidget(mem_proc_head)
        self._top_mem_table = _ProcessTable()
        mem_proc.addWidget(self._top_mem_table)
        proc_inner.addLayout(mem_proc, 1)

        proc_lay.addWidget(proc_container)
        self._content.addWidget(proc_card)

        # ════════════════════════════════════════════════════════════════
        # SYSTEM INFO card — uptime + boot time + swap
        # ════════════════════════════════════════════════════════════════
        info_row = QHBoxLayout()
        info_row.setSpacing(14)

        self._info_card = _CardFrame()
        info_lay = QVBoxLayout(self._info_card)
        info_lay.setContentsMargins(18, 14, 18, 14)
        info_lay.setSpacing(8)
        info_lay.addWidget(_card_title("ИНФОРМАЦИЯ О СИСТЕМЕ"))
        self._uptime_lbl = QLabel("—")
        self._uptime_lbl.setStyleSheet(
            "color:#f0f4f8; font-size:13px; font-weight:600; background:transparent;"
        )
        info_lay.addWidget(self._uptime_lbl)
        self._boot_lbl = QLabel("—")
        self._boot_lbl.setStyleSheet(
            "color:#8899aa; font-size:11px; background:transparent;"
        )
        info_lay.addWidget(self._boot_lbl)
        info_lay.addStretch()
        info_row.addWidget(self._info_card, 1)

        self._swap_card = _CardFrame()
        swap_lay = QVBoxLayout(self._swap_card)
        swap_lay.setContentsMargins(18, 14, 18, 14)
        swap_lay.setSpacing(8)
        swap_lay.addWidget(_card_title("ПОДКАЧКА (SWAP)"))
        self._swap_row = DiskRow("SWAP")
        swap_lay.addWidget(self._swap_row)
        info_row.addWidget(self._swap_card, 1)

        self._content.addLayout(info_row)

        # ── CPU sparkline (below processes) ───────────────────────────────
        self._spark_card = _CardFrame()
        spark_lay = QVBoxLayout(self._spark_card)
        spark_lay.setContentsMargins(18, 14, 18, 10)
        spark_lay.setSpacing(6)
        spark_lay.addWidget(_card_title("ИСТОРИЯ НАГРУЗКИ CPU"))
        self._sparkline = Sparkline(maxlen=120)
        spark_lay.addWidget(self._sparkline)
        self._content.addWidget(self._spark_card)

        self._content.addStretch()

        # ── Timer ────────────────────────────────────────────────────────
        import psutil
        self._psutil = psutil
        psutil.cpu_percent(interval=None)

        self._boot_time = None
        self._tick_count = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

    def _gauge_card(self):
        card = _CardFrame()
        lay = QHBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(14)
        return card, lay

    def _ensure_disk_card(self, dev):
        if dev in self._disk_cards:
            return self._disk_cards[dev]
        short = dev[:2].rstrip("\\/") or dev[:4]
        card = _DiskCard(short)
        self._disk_rows_lay.addWidget(card)
        self._disk_cards[dev] = card
        return card

    def _hw_make_row(self, parent_layout):
        """Create a label pair (name + value) inside a horizontal layout and add to parent."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        name_lbl = QLabel("—")
        name_lbl.setStyleSheet("color:#c8d2dc; font-size:12px; background:transparent;")
        name_lbl.setSizePolicy(Expanding, Fixed)
        val_lbl = QLabel("—")
        val_lbl.setAlignment(AlignRight | AlignVCenter)
        val_lbl.setStyleSheet("color:#00ff88; font-size:12px; font-weight:700; background:transparent;")
        val_lbl.setFixedWidth(80)
        row.addWidget(name_lbl)
        row.addWidget(val_lbl)
        parent_layout.addLayout(row)
        return name_lbl, val_lbl

    def _on_hw_data(self, hw):
        """Slot called when the hardware thread has new sensor data."""
        self._apply_hw_data(hw)

    def _apply_hw_data(self, hw):
        temps = hw.get("temperatures", [])
        fans = hw.get("fans", [])
        voltages = hw.get("voltages", [])

        # ── Temperatures ──
        # Ensure enough label rows exist
        while len(self._hw_temps_rows) > len(temps):
            item = self._hw_temps_rows.takeAt(self._hw_temps_rows.count() - 1)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        for i, t in enumerate(temps):
            if i >= self._hw_temps_rows.count():
                self._hw_make_row(self._hw_temps_rows)
            row_item = self._hw_temps_rows.itemAt(i)
            if not row_item:
                continue
            row_lay = row_item.layout()
            if not row_lay:
                continue
            name_lbl = row_lay.itemAt(0).widget()
            val_lbl = row_lay.itemAt(1).widget()
            if not name_lbl or not val_lbl:
                continue

            label = t["label"]
            current = t.get("current")
            if current is not None:
                val_text = "{:.1f}°C".format(current)
            else:
                val_text = "N/A"

            name_lbl.setText(label)
            name_lbl.setToolTip(label)

            # Color based on temperature thresholds
            if current is not None:
                if current >= 80:
                    val_color = QColor("#e05252")
                elif current >= 65:
                    val_color = QColor("#f5c842")
                else:
                    val_color = QColor("#4caf7d")
            else:
                val_color = QColor("#7a7068")

            val_lbl.setText(val_text)
            val_lbl.setStyleSheet("color:{}; font-size:12px; font-weight:700; background:transparent;".format(val_color.name()))

        self._hw_last_temps = temps

        # ── Fans ──
        while len(self._hw_fans_rows) > len(fans):
            item = self._hw_fans_rows.takeAt(self._hw_fans_rows.count() - 1)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        for i, f in enumerate(fans):
            if i >= self._hw_fans_rows.count():
                self._hw_make_row(self._hw_fans_rows)
            row_item = self._hw_fans_rows.itemAt(i)
            if not row_item:
                continue
            row_lay = row_item.layout()
            if not row_lay:
                continue
            name_lbl = row_lay.itemAt(0).widget()
            val_lbl = row_lay.itemAt(1).widget()
            if not name_lbl or not val_lbl:
                continue

            label = f["label"]
            current = f.get("current", 0)
            name_lbl.setText(label)
            name_lbl.setToolTip(label)
            val_lbl.setText("{:.0f} RPM".format(current))
            val_lbl.setStyleSheet("color:#4ac9c9; font-size:12px; font-weight:700; background:transparent;")

        self._hw_last_fans = fans

        # ── Voltages ──
        while len(self._hw_volts_rows) > len(voltages):
            item = self._hw_volts_rows.takeAt(self._hw_volts_rows.count() - 1)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        for i, v in enumerate(voltages):
            if i >= self._hw_volts_rows.count():
                self._hw_make_row(self._hw_volts_rows)
            row_item = self._hw_volts_rows.itemAt(i)
            if not row_item:
                continue
            row_lay = row_item.layout()
            if not row_lay:
                continue
            name_lbl = row_lay.itemAt(0).widget()
            val_lbl = row_lay.itemAt(1).widget()
            if not name_lbl or not val_lbl:
                continue

            label = v["label"]
            current = v.get("current")
            name_lbl.setText(label)
            name_lbl.setToolTip(label)
            if current is not None:
                val_lbl.setText("{:.3f} V".format(current))
            else:
                val_lbl.setText("N/A")
            val_lbl.setStyleSheet("color:#a070e0; font-size:12px; font-weight:700; background:transparent;")

        # ── Fan curve ──
        # Build a default fan curve based on available temp data
        cpu_temp = None
        for t in temps:
            if "core" in t["label"].lower() or "cpu" in t["sensor"].lower():
                cpu_temp = t.get("current")
                break
        if cpu_temp is None and temps:
            cpu_temp = temps[0].get("current")

        cpu_fan_speed = None
        for f in fans:
            cpu_fan_speed = f.get("current", 0)
            break

        # Default fan curve points (temp°C -> fan%)
        default_curve = [
            (0, 0), (30, 0), (40, 20), (50, 40),
            (60, 60), (70, 75), (80, 90), (90, 100), (100, 100),
        ]

        # Normalize fan speed to 0-100% (assume max ~3000 RPM)
        fan_pct = None
        if cpu_fan_speed is not None:
            fan_pct = min(100.0, max(0.0, cpu_fan_speed / 30.0))

        self._hw_fan_curve.set_curve(default_curve)
        if cpu_temp is not None and fan_pct is not None:
            self._hw_fan_curve.set_current(cpu_temp, fan_pct)

        # If no data at all, show N/A placeholder
        if not temps and not fans and not voltages:
            if self._hw_temps_rows.count() == 0:
                self._hw_make_row(self._hw_temps_rows)
                row_item = self._hw_temps_rows.itemAt(0)
                if row_item and row_item.layout():
                    nl = row_item.layout().itemAt(0).widget()
                    vl = row_item.layout().itemAt(1).widget()
                    if nl:
                        nl.setText("Датчики не обнаружены")
                    if vl:
                        vl.setText("N/A")
                        vl.setStyleSheet("color:#7a7068; font-size:12px; font-weight:700; background:transparent;")

    def _format_uptime(self, seconds):
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        mins = int((seconds % 3600) // 60)
        parts = []
        if days:
            parts.append("{} д".format(days))
        if hours:
            parts.append("{} ч".format(hours))
        parts.append("{} мин".format(mins))
        return ", ".join(parts)

    def _tick(self):
        try:
            from modules.monitor import get_snapshot
            snap = get_snapshot()
            self._tick_count += 1

            # CPU
            cpu = snap["cpu_percent"]
            self._cpu_ring.set_value(cpu, "{:.0f}%".format(cpu))
            cores = snap.get("cpu_per_core") or []
            freq = snap.get("cpu_freq_mhz")
            freq_txt = "  ·  {:.1f} ГГц".format(freq / 1000.0) if freq else ""
            self._cpu_sub.setText(
                ("{} ядер".format(len(cores)) if cores else "—") + freq_txt
            )
            self._cpu_freq.setText("")
            try:
                load = os.getloadavg()
                self._cpu_freq.setText(
                    "load avg: {:.1f} / {:.1f} / {:.1f}".format(*load)
                )
            except (AttributeError, OSError, NotImplementedError):
                self._cpu_freq.setText("load avg: N/A")
            self._core_bars.set_values(cores)
            self._sparkline.push(cpu)

            # RAM
            ram = snap["ram_percent"]
            self._ram_ring.set_value(ram, "{:.0f}%".format(ram))
            self._ram_sub.setText(
                "{:.1f} / {:.1f} ГБ".format(snap["ram_used_gb"], snap["ram_total_gb"])
            )
            free_gb = max(0.0, snap["ram_total_gb"] - snap["ram_used_gb"])
            self._ram_free.setText("Свободно: {:.1f} ГБ".format(free_gb))
            self._ram_total.setText("Всего: {:.1f} ГБ".format(snap["ram_total_gb"]))

            # Network
            down = snap.get("net_down_kbs", 0.0)
            up = snap.get("net_up_kbs", 0.0)
            self._net_down_val.setText("↓ {:.0f} КБ/с".format(down))
            self._net_up_val.setText("↑ {:.0f} КБ/с".format(up))
            self._net_down_spark.push(down)
            self._net_up_spark.push(up)

            # Total bytes (from psutil)
            try:
                import psutil as _ps
                io = _ps.net_io_counters()
                down_gb = io.bytes_recv / (1024 ** 3)
                up_gb = io.bytes_sent / (1024 ** 3)
                self._net_down_total.setText("Всего: {:.2f} ГБ".format(down_gb))
                self._net_up_total.setText("Всего: {:.2f} ГБ".format(up_gb))
            except Exception:
                pass

            # Swap
            self._swap_row.update_values(
                snap.get("swap_percent", 0.0),
                "{:.1f} / {:.1f} ГБ".format(
                    snap.get("swap_used_gb", 0.0),
                    snap.get("swap_total_gb", 0.0)
                ),
            )

            # Disks
            seen = set()
            for disk in snap["disks"]:
                dev = disk["device"]
                seen.add(dev)
                card = self._ensure_disk_card(dev)
                card.update_values(
                    disk["percent"],
                    "{:.0f} / {:.0f} ГБ".format(disk["used_gb"], disk["total_gb"]),
                )
            for dev, card in self._disk_cards.items():
                card.setVisible(dev in seen)

            # System info
            if self._boot_time is None:
                try:
                    self._boot_time = snap.get("boot_time") or self._psutil.boot_time()
                except Exception:
                    self._boot_time = None

            if self._boot_time:
                uptime_sec = time.time() - self._boot_time
                self._uptime_lbl.setText("Аптайм: {}".format(self._format_uptime(uptime_sec)))
                boot_dt = time.strftime("%d.%m.%Y %H:%M", time.localtime(self._boot_time))
                self._boot_lbl.setText("Загрузка: {}".format(boot_dt))

            # Processes — обновляем каждые 5 секунд, а не каждую, чтобы не грузить CPU
            if self._tick_count % 5 == 0:
                from modules.monitor import get_top_processes
                top = get_top_processes(limit=5)
                self._top_cpu_table.set_items(top["top_cpu"])
                self._top_mem_table.set_items(top["top_mem"])

        except Exception as exc:
            print("[Monitor] tick error:", exc)

    def showEvent(self, e):
        self._timer.start(1000)
        # Create and start hardware thread if not running
        if self._hw_thread is None or self._hw_thread.isFinished():
            try:
                self._hw_thread = _HardwareThread(self)
                self._hw_thread.hw_ready.connect(self._on_hw_data)
                self._hw_thread.start()
            except Exception:
                pass
        super().showEvent(e)

    def hideEvent(self, e):
        self._timer.stop()
        if self._hw_thread is not None:
            try:
                self._hw_thread.stop()
                self._hw_thread.wait(1000)
            except Exception:
                pass
        super().hideEvent(e)

"""
widgets.py — Uiverse.io стилизованные виджеты для KUS Pro.

UiverseToggle — QCheckBox с анимированным переключателем в стиле
uiverse.io (Shoh2008 checkbox-wrapper-5), адаптированный под
тёмную тему KUS Pro.
"""

from PyQt5.QtWidgets import QCheckBox, QWidget

from qt_compat import *

from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRectF, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QRadialGradient


class UiverseToggle(QCheckBox):
    """QCheckBox с кастомной отрисовкой toggle-переключателя.

    Вдохновлён checkbox-wrapper-5 с uiverse.io (Shoh2008):
    - Скруглённый трек с градиентом
    - Кружок-переключатель с тенью
    - Плавная анимация скольжения
    - 3D-эффект при нажатии
    """

    def __init__(self, text="", parent=None, accent=None):
        super().__init__(text, parent)
        self._accent = accent or "#f5a623"
        self._track_off = QColor(35, 38, 45)
        self._track_on = QColor(30, 33, 40)
        self._knob_pos = 0.0
        self._knob_scale = 1.0
        self._press_scale = 1.0

        self._track_h = 26
        self._track_w = 50
        self._knob_r = 10
        self._knob_margin = 3

        self.setFixedWidth(self._track_w + 8)
        self.setFixedHeight(self._track_h + 8)
        self.setCursor(PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"knobPos")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    @pyqtProperty(float)
    def knobPos(self):
        return self._knob_pos

    @knobPos.setter
    def knobPos(self, val):
        self._knob_pos = val
        self.update()

    def _target_pos(self):
        return 1.0 if self.isChecked() else 0.0

    def nextCheckState(self):
        super().nextCheckState()
        self._anim.stop()
        self._anim.setStartValue(self._knob_pos)
        self._anim.setEndValue(self._target_pos())
        self._anim.start()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient
        from PyQt5.QtCore import QPointF, QRectF

        p = QPainter(self)
        if not p.isActive(): return
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w = self.width()
        h = self.height()
        cy = h / 2.0
        cx = w / 2.0

        track_left = (w - self._track_w) / 2.0
        track_top = (h - self._track_h) / 2.0
        half = self._track_h / 2.0

        # ── Трек ──
        if self.isChecked():
            # Включён: тёмный фон с оранжевым свечением
            track_fill = QColor(25, 28, 35)
            border = QColor(self._accent)
            border.setAlpha(180)
            # Внутреннее свечение
            glow = QColor(self._accent)
            glow.setAlpha(20)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(glow))
            p.drawRoundedRect(QRectF(track_left - 1, track_top - 1,
                                     self._track_w + 2, self._track_h + 2),
                              half + 1, half + 1)
        else:
            track_fill = QColor(40, 43, 50)
            border = QColor(70, 73, 80)

        p.setPen(QPen(border, 1.5))
        p.setBrush(QBrush(track_fill))
        p.drawRoundedRect(QRectF(track_left, track_top, self._track_w, self._track_h),
                          half, half)

        # ── Точки "· ·" на выключенном треке ──
        if not self.isChecked():
            dot_color = QColor(80, 83, 90)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(dot_color))
            p.drawEllipse(QPointF(track_left + 14, cy), 1.5, 1.5)
            p.drawEllipse(QPointF(track_left + 22, cy), 1.5, 1.5)

        # ── Кружок-переключатель ──
        max_travel = self._track_w - 2 * self._knob_margin - 2 * self._knob_r
        knob_x = track_left + self._knob_margin + self._knob_pos * max_travel
        knob_r = self._knob_r * self._press_scale
        knob_cx = knob_x + self._knob_r
        knob_cy = cy

        # Тень кружка
        shadow = QRadialGradient(knob_cx, knob_cy + 2, knob_r * 1.3)
        shadow.setColorAt(0, QColor(0, 0, 0, 60))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(shadow))
        p.drawEllipse(QPointF(knob_cx, knob_cy + 2), knob_r * 1.3, knob_r * 1.3)

        # Градиент кружка
        if self.isChecked():
            knob_grad = QRadialGradient(knob_cx - knob_r * 0.25, knob_cy - knob_r * 0.25, knob_r * 1.1)
            knob_grad.setColorAt(0, QColor("#fff8e8"))
            knob_grad.setColorAt(0.4, QColor("#f5a623"))
            knob_grad.setColorAt(1, QColor("#c07a10"))
        else:
            knob_grad = QRadialGradient(knob_cx - knob_r * 0.25, knob_cy - knob_r * 0.25, knob_r * 1.1)
            knob_grad.setColorAt(0, QColor("#ffffff"))
            knob_grad.setColorAt(0.5, QColor("#d8d8d8"))
            knob_grad.setColorAt(1, QColor("#a0a0a0"))

        p.setPen(QPen(QColor(255, 255, 255, 25), 0.5))
        p.setBrush(QBrush(knob_grad))
        p.drawEllipse(QPointF(knob_cx, knob_cy), knob_r, knob_r)

        # ── Текст ──
        if self.text():
            p.setPen(QColor(232, 221, 208))
            p.setFont(self.font())
            text_x = track_left + self._track_w + 12
            p.drawText(
                int(text_x), int(cy - self.fontMetrics().height() / 2 + self.fontMetrics().ascent()),
                self.text(),
            )

        p.end()

    def mousePressEvent(self, event):
        self._press_scale = 0.88
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_scale = 1.0
        self.update()
        super().mouseReleaseEvent(event)

    def sizeHint(self):
        from PyQt5.QtCore import QSize
        text_w = self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0
        return QSize(self._track_w + 14 + text_w + 8, self._track_h + 8)


class LiquidProgressBar(QWidget):
    """Жидкий прогресс-бар в стиле uiverse.io (ShaikhWahid99).

    Анимированный градиент с переливом цветов, подходит для
    отображения прогресса очистки, обновлений и других операций.
    """

    def __init__(self, parent=None, accent=None):
        super().__init__(parent)
        self._value = 0.0
        self._accent = accent or "#f5a623"
        self._accent2 = "#4ac9c9"
        self._accent3 = "#a070e0"
        self._track_h = 28
        self.setFixedHeight(self._track_h + 16)
        self.setMinimumWidth(200)

        # Анимация градиента
        self._hue_offset = 0.0
        self._anim_hue = QPropertyAnimation(self, b"hueOffset")
        self._anim_hue.setDuration(3000)
        self._anim_hue.setLoopCount(-1)
        self._anim_hue.setStartValue(0.0)
        self._anim_hue.setEndValue(1.0)
        self._anim_hue.setEasingCurve(QEasingCurve.Linear)
        self._anim_hue.start()

    @pyqtProperty(float)
    def hueOffset(self):
        return self._hue_offset

    @hueOffset.setter
    def hueOffset(self, val):
        self._hue_offset = val
        self.update()

    def setValue(self, val):
        self._value = max(0.0, min(1.0, val))
        self.update()

    def value(self):
        return self._value

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QRadialGradient, QPen, QFont
        from PyQt5.QtCore import QRectF
        p = QPainter(self)
        if not p.isActive(): return
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w = self.width()
        h = self.height()
        cy = h / 2.0

        # ── Трек ──
        track_left = 4
        track_top = (h - self._track_h) / 2.0
        track_w = w - 8
        half = self._track_h / 2.0

        # Внутренняя тень трека
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 30))
        p.drawRoundedRect(QRectF(track_left, track_top + 1, track_w, self._track_h),
                          half, half)

        p.setPen(QPen(QColor(40, 43, 50), 1.5))
        p.setBrush(QColor(18, 20, 28))
        p.drawRoundedRect(QRectF(track_left, track_top, track_w, self._track_h),
                          half, half)

        # ── Заливка ──
        if self._value > 0.001:
            fill_w = max(12, (track_w - 4) * self._value)
            fill_rect = QRectF(track_left + 2, track_top + 2, fill_w, self._track_h - 4)

            # Градиент с анимацией
            grad = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight())
            offset = self._hue_offset

            colors = [
                (QColor(self._accent), 0.0),
                (QColor(self._accent2), 0.33 + offset * 0.3),
                (QColor(self._accent3), 0.66 + offset * 0.2),
                (QColor(self._accent), 1.0),
            ]
            for color, pos in colors:
                grad.setColorAt(min(1.0, max(0.0, pos)), color)

            p.setPen(Qt.NoPen)
            p.setBrush(grad)
            p.drawRoundedRect(fill_rect, (self._track_h - 4) / 2, (self._track_h - 4) / 2)

            # Свечение сверху
            glow = QLinearGradient(fill_rect.topLeft(), fill_rect.bottomLeft())
            glow.setColorAt(0, QColor(255, 255, 255, 20))
            glow.setColorAt(0.5, QColor(255, 255, 255, 5))
            glow.setColorAt(1, QColor(255, 255, 255, 0))
            p.setBrush(glow)
            p.drawRoundedRect(fill_rect, (self._track_h - 4) / 2, (self._track_h - 4) / 2)

        # ── Процент ──
        if self._value > 0.001:
            p.setPen(QColor(232, 221, 208))
            font = QFont("Segoe UI", 10, QFont.Bold)
            p.setFont(font)
            pct = "{}%".format(int(self._value * 100))
            p.drawText(QRectF(track_left, track_top, track_w, self._track_h),
                       AlignCenter, pct)

        p.end()

    def sizeHint(self):
        from PyQt5.QtCore import QSize
        return QSize(260, self._track_h + 16)


class NeonCheckbox(QCheckBox):
    """Неоновый чекбокс в стиле uiverse.io (00Kubi).

    Анимированные эффекты:
    - Свечение неонового цвета при наведении
    - Рисование галочки с анимацией stroke
    - Вспышка частиц при включении
    - Пульсирующие кольца
    - Бегущие полоски по рамке
    """

    def __init__(self, text="", parent=None, accent=None):
        super().__init__(text, parent)
        self._accent = accent or "#00ffaa"
        self._accent_dark = self._accent
        self._size = 30
        self._check_progress = 0.0
        self._glow_opacity = 0.0
        self._particles = []
        self._rings = []
        self._hover_scale = 1.0

        self.setFixedWidth(self._size + 12)
        self.setFixedHeight(self._size + 12)
        self.setCursor(PointingHandCursor)

        # Анимация галочки
        self._anim_check = QPropertyAnimation(self, b"checkProgress")
        self._anim_check.setDuration(350)
        self._anim_check.setEasingCurve(QEasingCurve.OutCubic)

        # Анимация свечения
        self._anim_glow = QPropertyAnimation(self, b"glowOpacity")
        self._anim_glow.setDuration(300)
        self._anim_glow.setEasingCurve(QEasingCurve.OutCubic)

        # Анимация частиц
        self._anim_timer = None
        self._particle_phase = 0.0

    @pyqtProperty(float)
    def checkProgress(self):
        return self._check_progress

    @checkProgress.setter
    def checkProgress(self, val):
        self._check_progress = val
        self.update()

    @pyqtProperty(float)
    def glowOpacity(self):
        return self._glow_opacity

    @glowOpacity.setter
    def glowOpacity(self, val):
        self._glow_opacity = val
        self.update()

    def nextCheckState(self):
        super().nextCheckState()

        # Анимация галочки
        self._anim_check.stop()
        if self.isChecked():
            self._anim_check.setStartValue(0.0)
            self._anim_check.setEndValue(1.0)
        else:
            self._anim_check.setStartValue(1.0)
            self._anim_check.setEndValue(0.0)
        self._anim_check.start()

        # Анимация свечения
        self._anim_glow.stop()
        self._anim_glow.setStartValue(self._glow_opacity)
        self._anim_glow.setEndValue(0.3 if self.isChecked() else 0.0)
        self._anim_glow.start()

        # Запуск частиц при включении
        if self.isChecked():
            self._spawn_particles()
            self._spawn_rings()

    def _spawn_particles(self):
        import math
        import random
        self._particles = []
        cx = self._size / 2 + 6
        cy = self._size / 2 + 6
        for i in range(12):
            angle = (i / 12) * 2 * math.pi + random.uniform(-0.3, 0.3)
            dist = random.uniform(18, 32)
            self._particles.append({
                "x": cx, "y": cy,
                "tx": cx + math.cos(angle) * dist,
                "ty": cy + math.sin(angle) * dist,
                "life": 1.0,
                "speed": random.uniform(0.02, 0.04),
            })
        self._particle_phase = 0.0
        if self._anim_timer is None:
            from PyQt5.QtCore import QTimer
            self._anim_timer = QTimer(self)
            self._anim_timer.timeout.connect(self._animate_particles)
        self._anim_timer.start(16)

    def _spawn_rings(self):
        self._rings = [{"scale": 0.0, "opacity": 1.0} for _ in range(3)]

    def _animate_particles(self):
        alive = False
        for p in self._particles:
            if p["life"] > 0:
                p["life"] -= p["speed"]
                alive = True
        for r in self._rings:
            if r["opacity"] > 0:
                r["scale"] += 0.08
                r["opacity"] -= 0.04
                alive = True
        if alive:
            self.update()
        else:
            self._particles = []
            self._rings = []
            self._anim_timer.stop()
            self.update()

    def enterEvent(self, event):
        self._hover_scale = 1.08
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_scale = 1.0
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QPolygonF
        from PyQt5.QtCore import QPointF
        import math

        p = QPainter(self)
        if not p.isActive(): return
        p.setRenderHint(QPainter.Antialiasing)

        cx = self._size / 2 + 6
        cy = self._size / 2 + 6
        half = self._size / 2 * self._hover_scale

        accent = QColor(self._accent)

        # ── Свечение (glow) ──
        if self._glow_opacity > 0.01:
            glow_grad = QRadialGradient(cx, cy, half * 1.5)
            glow_color = QColor(accent)
            glow_color.setAlphaF(self._glow_opacity)
            glow_grad.setColorAt(0, glow_color)
            glow_color2 = QColor(accent)
            glow_color2.setAlphaF(0)
            glow_grad.setColorAt(1, glow_color2)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(glow_grad))
            p.drawEllipse(QPointF(cx, cy), half * 1.5, half * 1.5)

        # ── Кольца (rings) ──
        for r in self._rings:
            if r["opacity"] > 0.01:
                ring_color = QColor(accent)
                ring_color.setAlphaF(r["opacity"])
                p.setPen(QPen(ring_color, 1))
                p.setBrush(Qt.NoBrush)
                r_size = half * (1.0 + r["scale"])
                p.drawEllipse(QPointF(cx, cy), r_size, r_size)

        # ── Фон бокса ──
        box_rect_x = cx - half
        box_rect_y = cy - half
        box_size = half * 2

        if self.isChecked():
            bg = QColor(accent)
            bg.setAlphaF(0.1)
            p.setBrush(QBrush(bg))
        else:
            p.setBrush(QColor(20, 22, 30))

        border_color = accent if (self.isChecked() or self._hover_scale > 1.0) else QColor(60, 65, 75)
        if self._hover_scale > 1.0 and not self.isChecked():
            border_color.setAlphaF(0.8)
        p.setPen(QPen(border_color, 2))
        p.drawRoundedRect(box_rect_x, box_rect_y, box_size, box_size, 4, 4)

        # ── Галочка (checkmark) ──
        if self._check_progress > 0.01:
            p.setPen(QPen(accent, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)

            # Точки галочки (относительно центра)
            pts = [
                QPointF(cx - half * 0.4, cy),
                QPointF(cx - half * 0.1, cy + half * 0.35),
                QPointF(cx + half * 0.4, cy - half * 0.3),
            ]

            # Анимация рисования — интерполяция вдоль пути
            total_len = 0
            segs = []
            for i in range(len(pts) - 1):
                dx = pts[i + 1].x() - pts[i].x()
                dy = pts[i + 1].y() - pts[i].y()
                seg_len = math.sqrt(dx * dx + dy * dy)
                segs.append(seg_len)
                total_len += seg_len

            target_len = total_len * self._check_progress
            drawn = 0
            poly = QPolygonF()
            poly.append(pts[0])

            for i, seg_len in enumerate(segs):
                if drawn + seg_len <= target_len:
                    poly.append(pts[i + 1])
                    drawn += seg_len
                else:
                    remaining = target_len - drawn
                    t = remaining / seg_len if seg_len > 0 else 0
                    px = pts[i].x() + (pts[i + 1].x() - pts[i].x()) * t
                    py = pts[i].y() + (pts[i + 1].y() - pts[i].y()) * t
                    poly.append(QPointF(px, py))
                    break

            if len(poly) >= 2:
                p.drawPolyline(poly)

        # ── Частицы (particles) ──
        for part in self._particles:
            if part["life"] > 0:
                t = 1.0 - part["life"]
                px = part["x"] + (part["tx"] - part["x"]) * t
                py = part["y"] + (part["ty"] - part["y"]) * t
                particle_color = QColor(accent)
                particle_color.setAlphaF(part["life"] * 0.8)
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(particle_color))
                p.drawEllipse(QPointF(px, py), 2.5 * part["life"], 2.5 * part["life"])

        # ── Текст ──
        if self.text():
            p.setPen(QColor(232, 221, 208))
            p.setFont(self.font())
            text_x = cx + half + 12
            p.drawText(
                int(text_x), int(cy - self.fontMetrics().height() / 2 + self.fontMetrics().ascent()),
                self.text(),
            )

        p.end()

    def sizeHint(self):
        from PyQt5.QtCore import QSize
        text_w = self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0
        return QSize(self._size + 12 + 12 + text_w + 8, self._size + 12)


# ═══════════════════════════════════════════════════════════════════════
#  AnimatedStackedWidget — fade-анимация при переключении страниц
# ═══════════════════════════════════════════════════════════════════════

from PyQt5.QtWidgets import QStackedWidget
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty


class AnimatedStackedWidget(QStackedWidget):
    """QStackedWidget с анимированными переходами между страницами.

    Вдохновлён CSS View Transitions API:
    - Crossfade (стандартный) — плавное затухание
    - Slide — горизонтальное скольжение
    - Easing: cubic-bezier для естественных переходов
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fade_duration = 300
        self._current_opacity = 1.0
        self._fading = False
        self._slide_x = 0.0
        self._slide_mode = "fade"  # "fade" или "slide"

    @pyqtProperty(float)
    def currentOpacity(self):
        return self._current_opacity

    @currentOpacity.setter
    def currentOpacity(self, val):
        self._current_opacity = val
        self.update()

    @pyqtProperty(float)
    def slideX(self):
        return self._slide_x

    @slideX.setter
    def slideX(self, val):
        self._slide_x = val
        self.update()

    def setCurrentWidget(self, widget):
        if self.currentWidget() == widget:
            return
        if self._fading:
            return
        self._fading = True

        # Определяем направление слайда (вправо или влево)
        old_idx = self.indexOf(self.currentWidget()) if self.currentWidget() else 0
        new_idx = self.indexOf(widget)
        self._slide_mode = "slide" if abs(new_idx - old_idx) == 1 else "fade"

        self._fade_out(widget)

    def _fade_out(self, new_widget):
        old_widget = self.currentWidget()
        if old_widget is None:
            super().setCurrentWidget(new_widget)
            self._fading = False
            return

        # Fade out текущей страницы
        self._anim = QPropertyAnimation(self, b"currentOpacity")
        self._anim.setDuration(self._fade_duration // 2)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(lambda: self._switch_and_fade_in(new_widget))
        self._anim.start()

    def _switch_and_fade_in(self, new_widget):
        super().setCurrentWidget(new_widget)

        # Fade in новой страницы
        self._anim2 = QPropertyAnimation(self, b"currentOpacity")
        self._anim2.setDuration(self._fade_duration // 2)
        self._anim2.setStartValue(0.0)
        self._anim2.setEndValue(1.0)
        self._anim2.setEasingCurve(QEasingCurve.OutCubic)
        self._anim2.finished.connect(lambda: setattr(self, '_fading', False))
        self._anim2.start()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QPaintEvent
        if self._fading and self._current_opacity < 1.0:
            p = QPainter(self)
            p.setOpacity(self._current_opacity)
            super().paintEvent(event)
            p.end()
        else:
            super().paintEvent(event)


# ═══════════════════════════════════════════════════════════════════════
#  BellToggle (Javierrocadev) — toggle с иконкой колокольчика
# ═══════════════════════════════════════════════════════════════════════

class BellToggle(QCheckBox):
    """Toggle-переключатель с SVG иконкой колокольчика.

    Вдохновлён uiverse.io (Javierrocadev):
    - Круглый трек с градиентом
    - Кружок-переключатель с SVG иконками (колокольчик вкл/выкл)
    - Плавная анимация скольжения
    """

    def __init__(self, text="", parent=None, accent_on="#4caf7d", accent_off="#e05252"):
        super().__init__(text, parent)
        self._accent_on = accent_on
        self._accent_off = accent_off
        self._track_w = 96
        self._track_h = 44
        self._knob_r = 18
        self._knob_margin = 4
        self._knob_pos = 0.0
        self._press_scale = 1.0

        self.setFixedWidth(self._track_w + 8)
        self.setFixedHeight(self._track_h + 8)
        self.setCursor(PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"knobPos")
        self._anim.setDuration(350)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    @pyqtProperty(float)
    def knobPos(self):
        return self._knob_pos

    @knobPos.setter
    def knobPos(self, val):
        self._knob_pos = val
        self.update()

    def nextCheckState(self):
        super().nextCheckState()
        self._anim.stop()
        self._anim.setStartValue(self._knob_pos)
        self._anim.setEndValue(1.0 if self.isChecked() else 0.0)
        self._anim.start()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QPolygonF
        from PyQt5.QtCore import QPointF, QRectF
        import math

        p = QPainter(self)
        if not p.isActive(): return
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cy = h / 2.0
        track_left = (w - self._track_w) / 2.0
        track_top = (h - self._track_h) / 2.0

        # ── Трек ──
        if self.isChecked():
            track_color = QColor(self._accent_on)
            track_color.setAlpha(40)
            border_color = QColor(self._accent_on)
            border_color.setAlpha(120)
        else:
            track_color = QColor(50, 52, 60)
            border_color = QColor(80, 82, 90)

        p.setPen(QPen(border_color, 2))
        p.setBrush(QBrush(track_color))
        p.drawRoundedRect(track_left, track_top, self._track_w, self._track_h,
                          self._track_h / 2, self._track_h / 2)

        # ── Кружок-переключатель ──
        max_travel = self._track_w - 2 * self._knob_margin - 2 * self._knob_r
        knob_x = track_left + self._knob_margin + self._knob_pos * max_travel
        knob_r = self._knob_r * self._press_scale
        knob_cx = knob_x + self._knob_r
        knob_cy = cy

        # Тень
        shadow = QRadialGradient(knob_cx, knob_cy + 2, knob_r * 1.2)
        shadow.setColorAt(0, QColor(0, 0, 0, 50))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(shadow))
        p.drawEllipse(QPointF(knob_cx, knob_cy + 2), knob_r * 1.2, knob_r * 1.2)

        # Градиент кружка
        if self.isChecked():
            knob_grad = QRadialGradient(knob_cx - knob_r * 0.3, knob_cy - knob_r * 0.3, knob_r * 1.2)
            knob_grad.setColorAt(0, QColor("#e8f5e9"))
            knob_grad.setColorAt(0.5, QColor(self._accent_on))
            knob_grad.setColorAt(1, QColor("#2e7d32"))
        else:
            knob_grad = QRadialGradient(knob_cx - knob_r * 0.3, knob_cy - knob_r * 0.3, knob_r * 1.2)
            knob_grad.setColorAt(0, QColor("#ffebee"))
            knob_grad.setColorAt(0.5, QColor(self._accent_off))
            knob_grad.setColorAt(1, QColor("#c62828"))

        p.setPen(QPen(QColor(255, 255, 255, 20), 0.5))
        p.setBrush(QBrush(knob_grad))
        p.drawEllipse(QPointF(knob_cx, knob_cy), knob_r, knob_r)

        # ── SVG-иконки колокольчика ──
        icon_size = 16
        icon_color = QColor("#090b0f")
        p.setPen(QPen(icon_color, 2))
        p.setBrush(Qt.NoBrush)

        if self._knob_pos > 0.5:
            # Колокольчик ВКЛ (с точкой)
            bx, by = knob_cx, knob_cy
            # Тело колокольчика
            bell = QPolygonF([
                QPointF(bx, by - 8),
                QPointF(bx - 7, by + 2),
                QPointF(bx + 7, by + 2),
            ])
            p.drawPolygon(bell)
            # Дуга снизу
            p.drawArc(QRectF(bx - 8, by + 1, 16, 8), 0, 180 * 16)
            # Точка
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(icon_color))
            p.drawEllipse(QPointF(bx, by + 10), 1.5, 1.5)
        else:
            # Колокольчик ВЫКЛ (с крестиком)
            bx, by = knob_cx, knob_cy
            bell = QPolygonF([
                QPointF(bx, by - 8),
                QPointF(bx - 7, by + 2),
                QPointF(bx + 7, by + 2),
            ])
            p.setPen(QPen(QColor(100, 100, 100), 2))
            p.drawPolygon(bell)
            p.drawArc(QRectF(bx - 8, by + 1, 16, 8), 0, 180 * 16)
            # Крестик
            p.setPen(QPen(QColor(self._accent_off), 2, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(bx - 3, by - 3), QPointF(bx + 3, by + 3))
            p.drawLine(QPointF(bx + 3, by - 3), QPointF(bx - 3, by + 3))

        # ── Текст ──
        if self.text():
            p.setPen(QColor(232, 221, 208))
            p.setFont(self.font())
            text_x = track_left + self._track_w + 14
            p.drawText(
                int(text_x), int(cy - self.fontMetrics().height() / 2 + self.fontMetrics().ascent()),
                self.text(),
            )

        p.end()

    def mousePressEvent(self, event):
        self._press_scale = 0.9
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_scale = 1.0
        self.update()
        super().mouseReleaseEvent(event)

    def sizeHint(self):
        from PyQt5.QtCore import QSize
        text_w = self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0
        return QSize(self._track_w + 14 + text_w + 8, self._track_h + 8)


# ═══════════════════════════════════════════════════════════════════════
#  Uiverse.io Button Styles — QSS Constants
# ═══════════════════════════════════════════════════════════════════════

# Glow Button
UIVERSE_GLOW_QSS = """
QPushButton {
    padding: 12px 28px; font-size: 13px; font-weight: 700; color: #090b0f;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #f5a623, stop:1 #d89018);
    border: none; border-radius: 10px;
}
QPushButton:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #ffc145, stop:1 #f5a623);
}
QPushButton:pressed {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #b87010, stop:1 #a06008);
}
"""

# Neon Button
UIVERSE_NEON_QSS = """
QPushButton {
    padding: 12px 28px; font-size: 13px; font-weight: 700; color: #f5a623;
    background: transparent; border: 2px solid #f5a623; border-radius: 10px;
}
QPushButton:hover { color: #090b0f; background: #f5a623; }
"""

# Slide Button
UIVERSE_SLIDE_QSS = """
QPushButton {
    padding: 12px 28px; font-size: 13px; font-weight: 700; color: #e8ddd0;
    background: rgba(245,166,35,0.05); border: 1px solid rgba(245,166,35,0.12);
    border-radius: 10px;
}
QPushButton:hover { color: #090b0f; background: #f5a623; border-color: transparent; }
"""

# Pulse (Danger)
UIVERSE_PULSE_QSS = """
QPushButton {
    padding: 12px 28px; font-size: 13px; font-weight: 700; color: #fff;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #e05252, stop:1 #c03030);
    border: none; border-radius: 10px;
}
QPushButton:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #ff6b6b, stop:1 #e05252);
}
"""

# Glass Button
UIVERSE_GLASS_QSS = """
QPushButton {
    padding: 12px 28px; font-size: 13px; font-weight: 700; color: #e8ddd0;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
}
QPushButton:hover {
    background: rgba(255,255,255,0.08); border-color: rgba(245,166,35,0.2); color: #f5a623;
}
"""

# Spin Button
UIVERSE_SPIN_QSS = """
QPushButton {
    padding: 8px 18px; height: 38px; border: none;
    background: rgba(245,166,35,0.12); border-radius: 20px;
    color: #f5a623; font-weight: 700; font-size: 13px; letter-spacing: 0.5px;
}
QPushButton:hover { background: rgba(245,166,35,0.2); }
"""

# Invert Button
UIVERSE_INVERT_QSS = """
QPushButton {
    padding: 10px 20px; background: #1a1b1e; border: none;
    border-radius: 8px; color: #e8ddd0; font-weight: 700; font-size: 13px;
}
QPushButton:hover { background: transparent; color: #f5a623; }
"""


# ═══════════════════════════════════════════════════════════════════════
#  FlowerSplashScreen — сплеш-скрин с анимированным цветком
#  Вдохновлён uiverse.io (tako143 flower + dovatgabriel line-wobble)
# ═══════════════════════════════════════════════════════════════════════

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QTimer, QRectF
from PyQt5.QtGui import QPainter, QColor, QRadialGradient, QPen, QBrush, QFont, QLinearGradient
import math


class FlowerWidget(QWidget):
    """Анимированный цветок из лепестков (tako143 style)."""

    def __init__(self, parent=None, size=120, accent="#f5a623"):
        super().__init__(parent)
        self._size = size
        self._accent = accent
        self._rotation = 0.0
        self._scale = 1.0
        self._petal_colors = [
            ("#fcdbdf", "#fd688d"),
            ("#fcd2e3", "#fa6094"),
            ("#fabefc", "#c34ec7"),
            ("#f7d6d6", "#fd6a6a"),
        ]
        self.setFixedSize(size, size)

        # Анимация вращения
        self._anim_rot = QPropertyAnimation(self, b"rotation")
        self._anim_rot.setDuration(8000)
        self._anim_rot.setLoopCount(-1)
        self._anim_rot.setStartValue(0.0)
        self._anim_rot.setEndValue(360.0)
        self._anim_rot.setEasingCurve(QEasingCurve.Linear)
        self._anim_rot.start()

        # Анимация масштаба
        self._anim_scale = QPropertyAnimation(self, b"scale")
        self._anim_scale.setDuration(4000)
        self._anim_scale.setLoopCount(-1)
        self._anim_scale.setStartValue(1.0)
        self._anim_scale.setKeyValueAt(0.5, 1.15)
        self._anim_scale.setEndValue(1.0)
        self._anim_scale.setEasingCurve(QEasingCurve.InOutSine)
        self._anim_scale.start()

    @pyqtProperty(float)
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, val):
        self._rotation = val
        self.update()

    @pyqtProperty(float)
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, val):
        self._scale = val
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        if not p.isActive(): return
        p.setRenderHint(QPainter.Antialiasing)

        cx = self._size / 2
        cy = self._size / 2
        petal_len = self._size * 0.35
        petal_w = self._size * 0.12
        num_petals = 8

        # Применяем трансформации
        p.translate(cx, cy)
        p.rotate(self._rotation)
        p.scale(self._scale, self._scale)
        p.translate(-cx, -cy)

        # Рисуем лепестки
        for i in range(num_petals):
            angle = (i / num_petals) * 360
            color_idx = i % len(self._petal_colors)
            c1, c2 = self._petal_colors[color_idx]

            p.save()
            p.translate(cx, cy)
            p.rotate(angle)

            # Градиент лепестка
            grad = QLinearGradient(0, -petal_len, 0, 0)
            grad.setColorAt(0, QColor(c1))
            grad.setColorAt(1, QColor(c2))

            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(grad))

            # Лепесток — эллипс
            petal_rect = QRectF(-petal_w / 2, -petal_len, petal_w, petal_len)
            p.drawEllipse(petal_rect)

            p.restore()

        # Центр цветка
        center_r = self._size * 0.08
        center_grad = QRadialGradient(cx, cy, center_r)
        center_grad.setColorAt(0, QColor("#fff0f0"))
        center_grad.setColorAt(1, QColor("#f1d2d2"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(center_grad))
        p.drawEllipse(QPointF(cx, cy), center_r, center_r)

        p.end()


class LineWobble(QWidget):
    """Анимированная линия загрузки (dovatgabriel style)."""

    def __init__(self, parent=None, width=200, color="#f5a623"):
        super().__init__(parent)
        self._w = width
        self._h = 6
        self._color = color
        self._pos = -0.9

        self.setFixedWidth(width)
        self.setFixedHeight(20)

        self._anim = QPropertyAnimation(self, b"linePos")
        self._anim.setDuration(1550)
        self._anim.setLoopCount(-1)
        self._anim.setStartValue(-0.9)
        self._anim.setKeyValueAt(0.5, 0.9)
        self._anim.setEndValue(-0.9)
        self._anim.setEasingCurve(QEasingCurve.InOutSine)
        self._anim.start()

    @pyqtProperty(float)
    def linePos(self):
        return self._pos

    @linePos.setter
    def linePos(self, val):
        self._pos = val
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient
        p = QPainter(self)
        if not p.isActive(): return
        p.setRenderHint(QPainter.Antialiasing)

        w = self._w
        h = self._h
        y = (self.height() - h) / 2
        r = h / 2

        # Фоновая полоса
        bg_color = QColor(self._color)
        bg_color.setAlpha(25)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(bg_color))
        p.drawRoundedRect(0, y, w, h, r, r)

        # Анимированная полоса
        bar_w = w * 0.4
        bar_x = (w - bar_w) / 2 + self._pos * (w - bar_w) / 2

        grad = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
        grad.setColorAt(0, QColor(self._color))
        grad.setColorAt(0.5, QColor("#ffc145"))
        grad.setColorAt(1, QColor(self._color))

        p.setBrush(QBrush(grad))
        p.drawRoundedRect(bar_x, y, bar_w, h, r, r)

        # Свечение
        glow_color = QColor(self._color)
        glow_color.setAlpha(40)
        p.setBrush(QBrush(glow_color))
        p.drawRoundedRect(bar_x - 2, y - 2, bar_w + 4, h + 4, r + 2, r + 2)

        p.end()


class FlowerSplashScreen(QWidget):
    """Сплеш-скрин с анимированным цветком и Line Wobble."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            SplashScreen | FramelessWindowHint | WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 380)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 30, 0, 20)
        lay.setSpacing(10)

        # Цветок
        self._flower = FlowerWidget(size=140)
        flower_row = QHBoxLayout()
        flower_row.addStretch()
        flower_row.addWidget(self._flower)
        flower_row.addStretch()
        lay.addLayout(flower_row)

        # Заголовок
        title = QLabel("KUS PRO")
        title.setAlignment(AlignCenter)
        title.setStyleSheet(
            "color: #f5a623; font-size: 28px; font-weight: 800; "
            "background: transparent; letter-spacing: 6px;"
        )
        lay.addWidget(title)

        # Подзаголовок
        sub = QLabel("SYSTEM UTILITY")
        sub.setAlignment(AlignCenter)
        sub.setStyleSheet(
            "color: #5a5248; font-size: 10px; font-weight: 600; "
            "background: transparent; letter-spacing: 3px;"
        )
        lay.addWidget(sub)

        # Версия
        try:
            from theme import VERSION
            ver_text = "v{}".format(VERSION)
        except Exception:
            ver_text = ""
        if ver_text:
            ver = QLabel(ver_text)
            ver.setAlignment(AlignCenter)
            ver.setStyleSheet("color: #3a3530; font-size: 10px; background: transparent;")
            lay.addWidget(ver)

        # Line Wobble
        wobble_row = QHBoxLayout()
        wobble_row.addStretch()
        self._wobble = LineWobble(width=160, color="#f5a623")
        wobble_row.addWidget(self._wobble)
        wobble_row.addStretch()
        lay.addLayout(wobble_row)

        # Текст загрузки
        self._load_text = QLabel("Загрузка компонентов...")
        self._load_text.setAlignment(AlignCenter)
        self._load_text.setStyleSheet(
            "color: #5a5248; font-size: 11px; background: transparent;"
        )
        lay.addWidget(self._load_text)

        self._step = 0
        self._messages = [
            "Загрузка компонентов...",
            "Инициализация модулей...",
            "Проверка зависимостей...",
            "Подготовка интерфейса...",
            "Готово!",
        ]

        # Таймер смены текста
        self._text_timer = QTimer(self)
        self._text_timer.timeout.connect(self._next_message)
        self._text_timer.start(400)

    def _next_message(self):
        if self._step < len(self._messages):
            self._load_text.setText(self._messages[self._step])
            self._step += 1
        else:
            self._text_timer.stop()

    def finish(self, main_window):
        self._text_timer.stop()
        super().finish(main_window)


# ═══════════════════════════════════════════════════════════════════════
#  GlitchToggle (tutel_6585) — toggle с glitch-эффектом
# ═══════════════════════════════════════════════════════════════════════

class GlitchToggle(QCheckBox):
    """Toggle-переключатель с glitch-эффектом и эмодзи.

    Вдохновлён uiverse.io (tutel_6585):
    - Круглый трек с ползунком-эмодзи
    - Анимация тряски при включении
    - Смена эмодзи (:P → >:(
    - Красный фон при активации
    """

    def __init__(self, text="", parent=None, accent=None):
        super().__init__(text, parent)
        self._knob_pos = 0.0
        self._glitch_offset_x = 0.0
        self._glitch_offset_y = 0.0
        self._glitch_phase = 0.0
        self._accent = accent or "#14b8a6"

        self._track_w = 56
        self._track_h = 30
        self._knob_r = 12
        self._knob_margin = 3

        self.setFixedHeight(self._track_h + 8)
        self.setCursor(PointingHandCursor)

        # Анимация позиции кружка
        self._anim = QPropertyAnimation(self, b"knobPos")
        self._anim.setDuration(350)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        # Анимация glitch
        self._glitch_timer = QTimer(self)
        self._glitch_timer.timeout.connect(self._glitch_tick)

    @pyqtProperty(float)
    def knobPos(self):
        return self._knob_pos

    @knobPos.setter
    def knobPos(self, val):
        self._knob_pos = val
        self.update()

    @pyqtProperty(float)
    def glitchX(self):
        return self._glitch_offset_x

    @glitchX.setter
    def glitchX(self, val):
        self._glitch_offset_x = val
        self.update()

    @pyqtProperty(float)
    def glitchY(self):
        return self._glitch_offset_y

    @glitchY.setter
    def glitchY(self, val):
        self._glitch_offset_y = val
        self.update()

    def _glitch_tick(self):
        import random
        if self.isChecked():
            self._glitch_offset_x = random.uniform(-2, 2)
            self._glitch_offset_y = random.uniform(-2, 2)
            self.update()
        else:
            self._glitch_offset_x = 0
            self._glitch_offset_y = 0
            self._glitch_timer.stop()
            self.update()

    def nextCheckState(self):
        super().nextCheckState()
        self._anim.stop()
        self._anim.setStartValue(self._knob_pos)
        self._anim.setEndValue(1.0 if self.isChecked() else 0.0)
        self._anim.start()

        if self.isChecked():
            self._glitch_timer.start(50)
        else:
            self._glitch_offset_x = 0
            self._glitch_offset_y = 0
            self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QFont
        from PyQt5.QtCore import QPointF, QRectF

        p = QPainter(self)
        if not p.isActive(): return
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w = self.width()
        h = self.height()
        cy = h / 2.0

        track_left = 4
        track_top = (h - self._track_h) / 2.0
        half = self._track_h / 2.0

        gx = self._glitch_offset_x
        gy = self._glitch_offset_y

        # ── Трек ──
        if self.isChecked():
            track_color = QColor(self._accent)
        else:
            track_color = QColor(60, 65, 75)

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(track_color))
        p.drawRoundedRect(QRectF(track_left + gx, track_top + gy,
                                  self._track_w, self._track_h),
                          half, half)

        # ── Кружок-переключатель ──
        max_travel = self._track_w - 2 * self._knob_margin - 2 * self._knob_r
        knob_x = track_left + self._knob_margin + self._knob_pos * max_travel
        knob_cx = knob_x + self._knob_r + gx
        knob_cy = cy + gy

        # Тень
        shadow = QRadialGradient(knob_cx, knob_cy + 2, self._knob_r * 1.2)
        shadow.setColorAt(0, QColor(0, 0, 0, 40))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(shadow))
        p.drawEllipse(QPointF(knob_cx, knob_cy + 2), self._knob_r * 1.2, self._knob_r * 1.2)

        # Белый кружок
        knob_grad = QRadialGradient(knob_cx - 2, knob_cy - 2, self._knob_r)
        knob_grad.setColorAt(0, QColor("#ffffff"))
        knob_grad.setColorAt(0.7, QColor("#f0f0f0"))
        knob_grad.setColorAt(1, QColor("#d0d0d0"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(knob_grad))
        p.drawEllipse(QPointF(knob_cx, knob_cy), self._knob_r, self._knob_r)

        # ── Эмодзи ──
        font = QFont("Segoe UI Emoji", 10, QFont.Bold)
        p.setFont(font)
        p.setPen(QColor(0, 0, 0))
        emoji_rect = QRectF(knob_cx - self._knob_r, knob_cy - self._knob_r,
                            self._knob_r * 2, self._knob_r * 2)
        if self.isChecked():
            p.drawText(emoji_rect, AlignCenter, ">:(")
        else:
            p.drawText(emoji_rect, AlignCenter, ":P")

        # ── Текст (цветной) ──
        if self.text():
            p.setPen(QColor(self._accent))
            p.setFont(QFont("Segoe UI", 11, QFont.Bold))
            text_x = track_left + self._track_w + 10
            p.drawText(
                int(text_x), int(cy + 4),
                self.text(),
            )

        p.end()

    def sizeHint(self):
        from PyQt5.QtCore import QSize
        text_w = self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0
        return QSize(self._track_w + 14 + text_w + 8, self._track_h + 8)

    def minimumSizeHint(self):
        from PyQt5.QtCore import QSize
        return QSize(self._track_w + 14, self._track_h + 8)


# ═══════════════════════════════════════════════════════════════════════
#  GalahhadToggle (Galahhad) — чистый toggle с галочкой/крестиком
# ═══════════════════════════════════════════════════════════════════════

class GalahhadToggle(QCheckBox):
    """Чистый toggle-переключатель с галочкой и крестиком.

    Вдохновлён uiverse.io (Galahhad):
    - Плавная анимация без тряски
    - Галочка при включении, крестик при выключении
    - Зелёный фон при активации
    - Эффект линии при переключении
    """

    def __init__(self, text="", parent=None, accent=None):
        super().__init__(text, parent)
        self._knob_pos = 0.0
        self._accent = accent or "#00da50"
        self._accent_off = "#838383"

        self._track_w = 46
        self._track_h = 24
        self._knob_r = 9
        self._knob_margin = 3

        self.setFixedHeight(self._track_h + 8)
        self.setCursor(PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"knobPos")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    @pyqtProperty(float)
    def knobPos(self):
        return self._knob_pos

    @knobPos.setter
    def knobPos(self, val):
        self._knob_pos = val
        self.update()

    def nextCheckState(self):
        super().nextCheckState()
        self._anim.stop()
        self._anim.setStartValue(self._knob_pos)
        self._anim.setEndValue(1.0 if self.isChecked() else 0.0)
        self._anim.start()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QFont, QPolygonF
        from PyQt5.QtCore import QPointF, QRectF
        import math

        p = QPainter(self)
        if not p.isActive(): return
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w = self.width()
        h = self.height()
        cy = h / 2.0

        track_left = 4
        track_top = (h - self._track_h) / 2.0
        half = self._track_h / 2.0

        # ── Трек ──
        if self.isChecked():
            track_color = QColor(self._accent)
        else:
            track_color = QColor(self._accent_off)

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(track_color))
        p.drawRoundedRect(QRectF(track_left, track_top, self._track_w, self._track_h),
                          half, half)

        # ── Кружок-переключатель ──
        max_travel = self._track_w - 2 * self._knob_margin - 2 * self._knob_r
        knob_x = track_left + self._knob_margin + self._knob_pos * max_travel
        knob_cx = knob_x + self._knob_r
        knob_cy = cy

        # Тень
        shadow = QRadialGradient(knob_cx, knob_cy + 1, self._knob_r * 1.1)
        shadow.setColorAt(0, QColor(0, 0, 0, 30))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(shadow))
        p.drawEllipse(QPointF(knob_cx, knob_cy + 1), self._knob_r * 1.1, self._knob_r * 1.1)

        # Белый кружок
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawEllipse(QPointF(knob_cx, knob_cy), self._knob_r, self._knob_r)

        # ── Иконка (галочка или крестик) ──
        icon_color = QColor(self._accent) if self.isChecked() else QColor(self._accent_off)
        p.setPen(QPen(icon_color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

        if self.isChecked():
            # Галочка
            cx, cy_icon = knob_cx, knob_cy
            p.drawLine(QPointF(cx - 3, cy_icon), QPointF(cx - 1, cy_icon + 3))
            p.drawLine(QPointF(cx - 1, cy_icon + 3), QPointF(cx + 4, cy_icon - 3))
        else:
            # Крестик
            cx, cy_icon = knob_cx, knob_cy
            p.drawLine(QPointF(cx - 3, cy_icon - 3), QPointF(cx + 3, cy_icon + 3))
            p.drawLine(QPointF(cx + 3, cy_icon - 3), QPointF(cx - 3, cy_icon + 3))

        # ── Эффект-линия при переключении ──
        if 0.1 < self._knob_pos < 0.9:
            effect_alpha = int(40 * (1 - abs(self._knob_pos - 0.5) * 2))
            effect_color = QColor(self._accent)
            effect_color.setAlpha(effect_alpha)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(effect_color))
            effect_x = track_left + self._track_w / 2
            p.drawEllipse(QPointF(effect_x, cy), 8, 8)

        # ── Текст (цветной) ──
        if self.text():
            p.setPen(QColor(self._accent) if self.isChecked() else QColor(200, 210, 220))
            p.setFont(QFont("Segoe UI", 11, QFont.Bold))
            text_x = track_left + self._track_w + 10
            p.drawText(
                int(text_x), int(cy + 4),
                self.text(),
            )

        p.end()

    def sizeHint(self):
        from PyQt5.QtCore import QSize
        text_w = self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0
        return QSize(self._track_w + 14 + text_w + 8, self._track_h + 8)

    def minimumSizeHint(self):
        from PyQt5.QtCore import QSize
        return QSize(self._track_w + 14, self._track_h + 8)


# ═══════════════════════════════════════════════════════════════════════
#  WavingHand (Pradeepsaranbishnoi) — волшая рука
# ═══════════════════════════════════════════════════════════════════════

class WavingHand(QWidget):
    """Анимированная волшую рука (Pradeepsaranbishnoi style)."""

    def __init__(self, parent=None, size=60, accent="#f5a623"):
        super().__init__(parent)
        self._size = size
        self._accent = accent
        self._phase = 0.0

        self.setFixedSize(size, int(size * 0.75))

        self._anim = QPropertyAnimation(self, b"phase")
        self._anim.setDuration(1200)
        self._anim.setLoopCount(-1)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.InOutSine)
        self._anim.start()

    @pyqtProperty(float)
    def phase(self):
        return self._phase

    @phase.setter
    def phase(self, val):
        self._phase = val
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
        from PyQt5.QtCore import QPointF, QRectF
        import math

        p = QPainter(self)
        if not p.isActive(): return
        p.setRenderHint(QPainter.Antialiasing, True)

        s = self._size
        cx = s / 2
        cy = s / 2
        skin = QColor(self._accent)

        # Ладонь
        palm_w = s * 0.45
        palm_h = s * 0.5
        palm_x = cx - palm_w / 2 + 5
        palm_y = cy - palm_h / 2

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(skin))
        p.drawRoundedRect(QRectF(palm_x, palm_y, palm_w, palm_h), 8, 20)

        # Большой палец
        thumb_angle = math.sin(self._phase * math.pi * 4) * 15
        p.save()
        p.translate(palm_x + palm_w - 5, palm_y + palm_h * 0.6)
        p.rotate(-20 + thumb_angle)
        p.setBrush(QBrush(skin))
        p.drawRoundedRect(QRectF(-4, -20, 14, 24), 6, 6)
        p.restore()

        # 4 пальца (анимация по очереди)
        for i in range(4):
            finger_phase = (self._phase + i * 0.1) % 1.0
            finger_angle = math.sin(finger_phase * math.pi * 4) * (10 + i * 5)
            finger_x = palm_x + 5 + i * (palm_w / 5)
            finger_y = palm_y - 2

            p.save()
            p.translate(finger_x, finger_y)
            p.rotate(finger_angle)

            brightness = 70 + i * 10
            finger_color = QColor(skin)
            finger_color.setHsvF(finger_color.hueF(), finger_color.saturationF(),
                                  min(1.0, brightness / 100.0))
            p.setBrush(QBrush(finger_color))

            finger_h = 16 + i * 2
            p.drawRoundedRect(QRectF(-3, -finger_h, 8, finger_h), 4, 4)
            p.restore()

        # Тень
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 20)))
        p.drawEllipse(QPointF(cx + 5, cy + palm_h / 2 + 8), palm_w / 2, 4)

        p.end()

class LoadingText(QWidget):
    """Анимированный текст загрузки с прыгающим кружком (alexruix style)."""

    def __init__(self, text="LOADING", parent=None, accent="#f5a623"):
        super().__init__(parent)
        self._text = text
        self._accent = accent
        self._ball_x = 0.0
        self._letter_spacing = 1.0

        self.setFixedHeight(40)
        self.setMinimumWidth(120)

        self._anim_ball = QPropertyAnimation(self, b"ballX")
        self._anim_ball.setDuration(3500)
        self._anim_ball.setLoopCount(-1)
        self._anim_ball.setStartValue(0.0)
        self._anim_ball.setKeyValueAt(0.4, 1.0)
        self._anim_ball.setKeyValueAt(0.8, 0.0)
        self._anim_ball.setEndValue(0.0)
        self._anim_ball.setEasingCurve(QEasingCurve.InOutSine)
        self._anim_ball.start()

        self._anim_space = QPropertyAnimation(self, b"letterSpacing")
        self._anim_space.setDuration(3500)
        self._anim_space.setLoopCount(-1)
        self._anim_space.setStartValue(1.0)
        self._anim_space.setKeyValueAt(0.4, 2.0)
        self._anim_space.setKeyValueAt(0.8, 1.0)
        self._anim_space.setEndValue(1.0)
        self._anim_space.setEasingCurve(QEasingCurve.InOutSine)
        self._anim_space.start()

    @pyqtProperty(float)
    def ballX(self):
        return self._ball_x

    @ballX.setter
    def ballX(self, val):
        self._ball_x = val
        self.update()

    @pyqtProperty(float)
    def letterSpacing(self):
        return self._letter_spacing

    @letterSpacing.setter
    def letterSpacing(self, val):
        self._letter_spacing = val
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics, QRadialGradient
        from PyQt5.QtCore import QPointF
        p = QPainter(self)
        if not p.isActive(): return
        p.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()
        cy = h / 2.0

        font = QFont("Segoe UI", 14, QFont.Bold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, self._letter_spacing)
        p.setFont(font)
        p.setPen(QColor(self._accent))

        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self._text)
        text_x = (w - text_w) / 2
        p.drawText(int(text_x), int(cy + fm.height() / 4), self._text)

        ball_r = 6
        ball_x = text_x + self._ball_x * text_w
        ball_y = cy + 14

        ball_grad = QRadialGradient(ball_x - 1, ball_y - 1, ball_r)
        ball_grad.setColorAt(0, QColor("#ffc145"))
        ball_grad.setColorAt(1, QColor(self._accent))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(ball_grad))
        p.drawEllipse(QPointF(ball_x, ball_y), ball_r, ball_r)

        p.end()


# ═══════════════════════════════════════════════════════════════════════
#  HourglassWidget (SouravBandyopadhyay) — песочные часы
# ═══════════════════════════════════════════════════════════════════════

class HourglassWidget(QWidget):
    """Анимированные песочные часы (SouravBandyopadhyay style)."""

    def __init__(self, parent=None, size=100, accent="#f5a623"):
        super().__init__(parent)
        self._size = size
        self._accent = accent
        self._rotation = 0.0
        self._sand_top_h = 0.0
        self._sand_bottom_h = 14.0
        self._stream_h = 0.0

        self.setFixedSize(size, size)

        self._anim_rot = QPropertyAnimation(self, b"rotation")
        self._anim_rot.setDuration(2000)
        self._anim_rot.setLoopCount(-1)
        self._anim_rot.setStartValue(0.0)
        self._anim_rot.setKeyValueAt(0.5, 180.0)
        self._anim_rot.setEndValue(180.0)
        self._anim_rot.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim_rot.start()

        self._anim_sand = QTimer(self)
        self._anim_sand.timeout.connect(self._update_sand)
        self._anim_sand.start(50)
        self._sand_tick = 0

    @pyqtProperty(float)
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, val):
        self._rotation = val
        self.update()

    def _update_sand(self):
        self._sand_tick += 1
        phase = (self._sand_tick % 200) / 200.0
        if phase < 0.5:
            self._sand_top_h = max(0, 14 - phase * 2 * 14)
            self._sand_bottom_h = min(14, phase * 2 * 14)
            self._stream_h = 20 if phase < 0.4 else max(0, 20 - (phase - 0.4) * 100)
        else:
            rev_phase = (phase - 0.5) * 2
            self._sand_top_h = min(14, rev_phase * 14)
            self._sand_bottom_h = max(0, 14 - rev_phase * 14)
            self._stream_h = 0
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
        from PyQt5.QtCore import QPointF, QRectF

        p = QPainter(self)
        if not p.isActive(): return
        p.setRenderHint(QPainter.Antialiasing, True)

        s = self._size
        cx = s / 2
        cy = s / 2
        accent = QColor(self._accent)

        bg = QColor(18, 19, 26)
        p.setPen(QPen(QColor(40, 43, 50), 1.5))
        p.setBrush(QBrush(bg))
        p.drawEllipse(QPointF(cx, cy), s / 2 - 2, s / 2 - 2)

        p.translate(cx, cy)
        p.rotate(self._rotation)
        p.translate(-cx, -cy)

        cap_w = s * 0.35
        cap_h = 4
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(accent))
        p.drawRoundedRect(QRectF(cx - cap_w / 2, cy - s * 0.32, cap_w, cap_h), 2, 2)
        p.drawRoundedRect(QRectF(cx - cap_w / 2, cy + s * 0.32 - cap_h, cap_w, cap_h), 2, 2)

        glass_color = QColor(self._accent)
        glass_color.setAlpha(60)
        p.setPen(QPen(accent, 1.5))
        p.setBrush(QBrush(glass_color))

        top_pts = [
            QPointF(cx - cap_w / 2, cy - s * 0.32 + cap_h),
            QPointF(cx + cap_w / 2, cy - s * 0.32 + cap_h),
            QPointF(cx + 4, cy - 2),
            QPointF(cx - 4, cy - 2),
        ]
        p.drawPolygon(top_pts)

        bot_pts = [
            QPointF(cx - 4, cy + 2),
            QPointF(cx + 4, cy + 2),
            QPointF(cx + cap_w / 2, cy + s * 0.32 - cap_h),
            QPointF(cx - cap_w / 2, cy + s * 0.32 - cap_h),
        ]
        p.drawPolygon(bot_pts)

        if self._sand_top_h > 0.5:
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor("#ffc145")))
            p.drawRect(QRectF(cx - cap_w / 2 + 2, cy - s * 0.32 + cap_h, cap_w - 4, self._sand_top_h))

        if self._sand_bottom_h > 0.5:
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor("#ffc145")))
            p.drawRect(QRectF(cx - cap_w / 2 + 2, cy + s * 0.32 - cap_h - self._sand_bottom_h, cap_w - 4, self._sand_bottom_h))

        if self._stream_h > 1:
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor("#ffc145")))
            p.drawRect(QRectF(cx - 1.5, cy - self._stream_h / 2, 3, self._stream_h))

        p.end()


# ═══════════════════════════════════════════════════════════════════════
#  InstallButton (Na3ar-17) — кнопка установки с анимацией
# ═══════════════════════════════════════════════════════════════════════

class InstallButton(QWidget):
    """Кнопка установки с анимацией прогресса (Na3ar-17 style)."""
    clicked = pyqtSignal()

    def __init__(self, text="Установить", parent=None, accent="#f5a623"):
        super().__init__(parent)
        self._text = text
        self._done_text = "Готово!"
        self._accent = accent
        self._state = "idle"
        self._progress = 0.0
        self._circle_scale = 1.0

        self.setFixedWidth(180)
        self.setFixedHeight(48)
        self.setCursor(PointingHandCursor)

        self._anim_progress = QPropertyAnimation(self, b"progress")
        self._anim_progress.setDuration(3000)
        self._anim_progress.setStartValue(0.0)
        self._anim_progress.setEndValue(1.0)
        self._anim_progress.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_progress.finished.connect(self._on_install_done)

        self._anim_scale = QPropertyAnimation(self, b"circleScale")
        self._anim_scale.setDuration(400)
        self._anim_scale.setEasingCurve(QEasingCurve.OutBack)

    @pyqtProperty(float)
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, val):
        self._progress = val
        self.update()

    @pyqtProperty(float)
    def circleScale(self):
        return self._circle_scale

    @circleScale.setter
    def circleScale(self, val):
        self._circle_scale = val
        self.update()

    def _on_install_done(self):
        self._state = "done"
        self._anim_scale.setStartValue(0.5)
        self._anim_scale.setEndValue(1.0)
        self._anim_scale.start()
        self.update()

    def mousePressEvent(self, event):
        if self._state == "idle":
            self._state = "installing"
            self._progress = 0.0
            self._anim_progress.start()
            self.clicked.emit()
            self.update()
        elif self._state == "done":
            self._state = "idle"
            self._progress = 0.0
            self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QFont
        from PyQt5.QtCore import QPointF, QRectF

        p = QPainter(self)
        if not p.isActive(): return
        p.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()
        cy = h / 2.0

        border_color = QColor("#10b981") if self._state == "done" else QColor(self._accent)
        p.setPen(QPen(border_color, 2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(2, 2, w - 4, h - 4, h / 2 - 2, h / 2 - 2)

        if self._state == "installing" and self._progress > 0.001:
            fill_w = (w - 8) * self._progress
            fill_color = QColor(self._accent)
            fill_color.setAlpha(30)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(fill_color))
            p.drawRoundedRect(4, 4, fill_w, h - 8, h / 2 - 4, h / 2 - 4)

        circle_r = 14 * self._circle_scale
        circle_cx = 28
        circle_cy = cy

        if self._state == "idle":
            grad = QRadialGradient(circle_cx - 2, circle_cy - 2, circle_r)
            grad.setColorAt(0, QColor("#fff8e8"))
            grad.setColorAt(0.5, QColor(self._accent))
            grad.setColorAt(1, QColor("#c07a10"))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(grad))
            p.drawEllipse(QPointF(circle_cx, circle_cy), circle_r, circle_r)

            p.setPen(QPen(QColor("#0a0e1a"), 2.5, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(circle_cx, circle_cy - 5), QPointF(circle_cx, circle_cy + 4))
            p.drawLine(QPointF(circle_cx - 4, circle_cy + 1), QPointF(circle_cx, circle_cy + 5))
            p.drawLine(QPointF(circle_cx + 4, circle_cy + 1), QPointF(circle_cx, circle_cy + 5))

        elif self._state == "installing":
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(30, 33, 40)))
            p.drawEllipse(QPointF(circle_cx, circle_cy), circle_r, circle_r)

            pen = QPen(QColor(self._accent), 3)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            start_angle = 90 * 16
            span_angle = -int(self._progress * 360 * 16)
            p.drawArc(QRectF(circle_cx - circle_r, circle_cy - circle_r,
                              circle_r * 2, circle_r * 2), start_angle, span_angle)

        elif self._state == "done":
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor("#10b981")))
            p.drawEllipse(QPointF(circle_cx, circle_cy), circle_r, circle_r)

            p.setPen(QPen(QColor("#0a0e1a"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(QPointF(circle_cx - 4, circle_cy), QPointF(circle_cx - 1, circle_cy + 4))
            p.drawLine(QPointF(circle_cx - 1, circle_cy + 4), QPointF(circle_cx + 5, circle_cy - 4))

        font = QFont("Segoe UI", 12, QFont.Bold)
        p.setFont(font)
        if self._state == "done":
            p.setPen(QColor("#10b981"))
            p.drawText(QRectF(48, 0, w - 56, h), AlignVCenter, self._done_text)
        else:
            p.setPen(QColor(self._accent))
            p.drawText(QRectF(48, 0, w - 56, h), AlignVCenter, self._text)

        p.end()

"""
widgets/animations.py
---------------------
Анимации и плавные переходы для KUS Pro.
"""

from PyQt5.QtWidgets import QWidget, QGraphicsOpacityEffect
from PyQt5.QtCore import (
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QSequentialAnimationGroup, QTimer, pyqtProperty, QRect
)
from PyQt5.QtGui import QColor


# ═══════════════════════════════════════════════════════════════════
#  Fade In/Out анимации
# ═══════════════════════════════════════════════════════════════════

def fade_in(widget, duration=300, start=0.0, end=1.0, on_finished=None):
    """Плавное появление виджета."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setEasingCurve(QEasingCurve.OutCubic)

    if on_finished:
        anim.finished.connect(on_finished)

    anim.start()
    # Сохраняем ссылку чтобы GC не удалил
    widget._fade_anim = anim
    return anim


def fade_out(widget, duration=300, start=1.0, end=0.0, on_finished=None):
    """Плавное исчезновение виджета."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setEasingCurve(QEasingCurve.InCubic)

    if on_finished:
        anim.finished.connect(on_finished)

    anim.start()
    widget._fade_anim = anim
    return anim


def fade_toggle(widget, duration=300):
    """Переключает видимость виджета с анимацией."""
    effect = widget.graphicsEffect()
    if effect and isinstance(effect, QGraphicsOpacityEffect):
        current = effect.opacity()
        target = 0.0 if current > 0.5 else 1.0
    else:
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        target = 0.0 if widget.isVisible() else 1.0
        current = 0.0 if widget.isVisible() else 1.0

    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(current)
    anim.setEndValue(target)
    anim.setEasingCurve(QEasingCurve.InOutCubic)
    anim.start()
    widget._fade_anim = anim
    return anim


# ═══════════════════════════════════════════════════════════════════
#  Slide анимации
# ═══════════════════════════════════════════════════════════════════

def slide_in(widget, direction="left", duration=350):
    """Плавное появление виджета со сдвигом."""
    start_pos = widget.pos()
    w = widget.width()

    if direction == "left":
        end_pos = QPoint(start_pos.x(), start_pos.y())
        start_pos = QPoint(start_pos.x() - w, start_pos.y())
    elif direction == "right":
        end_pos = QPoint(start_pos.x(), start_pos.y())
        start_pos = QPoint(start_pos.x() + w, start_pos.y())
    elif direction == "top":
        end_pos = QPoint(start_pos.x(), start_pos.y())
        start_pos = QPoint(start_pos.x(), start_pos.y() - widget.height())
    elif direction == "bottom":
        end_pos = QPoint(start_pos.x(), start_pos.y())
        start_pos = QPoint(start_pos.x(), start_pos.y() + widget.height())

    widget.move(start_pos)

    anim = QPropertyAnimation(widget, b"pos")
    anim.setDuration(duration)
    anim.setStartValue(start_pos)
    anim.setEndValue(end_pos)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.start()
    widget._slide_anim = anim
    return anim


def slide_out(widget, direction="left", duration=300):
    """Плавное исчезновение виджета со сдвигом."""
    start_pos = widget.pos()
    w = widget.width()

    if direction == "left":
        end_pos = QPoint(start_pos.x() - w, start_pos.y())
    elif direction == "right":
        end_pos = QPoint(start_pos.x() + w, start_pos.y())
    elif direction == "top":
        end_pos = QPoint(start_pos.x(), start_pos.y() - widget.height())
    elif direction == "bottom":
        end_pos = QPoint(start_pos.x(), start_pos.y() + widget.height())

    anim = QPropertyAnimation(widget, b"pos")
    anim.setDuration(duration)
    anim.setStartValue(start_pos)
    anim.setEndValue(end_pos)
    anim.setEasingCurve(QEasingCurve.InCubic)
    anim.start()
    widget._slide_anim = anim
    return anim


# ═══════════════════════════════════════════════════════════════════
#  Scale анимации
# ═══════════════════════════════════════════════════════════════════

def scale_in(widget, duration=300):
    """Плавное появление с масштабированием."""
    widget.setMinimumSize(0, 0)

    anim = QPropertyAnimation(widget, b"maximumSize")
    anim.setDuration(duration)
    anim.setStartValue(QSize(0, 0))
    anim.setEndValue(QSize(16777215, 16777215))
    anim.setEasingCurve(QEasingCurve.OutBack)
    anim.start()
    widget._scale_anim = anim
    return anim


# ═══════════════════════════════════════════════════════════════════
#  Pulse анимации
# ═══════════════════════════════════════════════════════════════════

def pulse(widget, duration=600, scale=1.05):
    """Пульсирующая анимация (микро-масштабирование)."""
    original_size = widget.size()

    anim = QPropertyAnimation(widget, b"maximumSize")
    anim.setDuration(duration // 2)
    anim.setStartValue(original_size)
    anim.setEndValue(QSize(int(original_size.width() * scale),
                           int(original_size.height() * scale)))
    anim.setEasingCurve(QEasingCurve.OutCubic)

    anim2 = QPropertyAnimation(widget, b"maximumSize")
    anim2.setDuration(duration // 2)
    anim2.setStartValue(QSize(int(original_size.width() * scale),
                              int(original_size.height() * scale)))
    anim2.setEndValue(original_size)
    anim2.setEasingCurve(QEasingCurve.InCubic)

    group = QSequentialAnimationGroup()
    group.addAnimation(anim)
    group.addAnimation(anim2)
    group.start()
    widget._pulse_anim = group
    return group


def glow_pulse(widget, color="#00ff88", duration=1000):
    """Пульсирующее свечение виджета."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(0.7)
    anim.setKeyValueAt(0.5, 1.0)
    anim.setEndValue(0.7)
    anim.setEasingCurve(QEasingCurve.InOutSine)
    anim.setLoopCount(-1)  # Бесконечный цикл
    anim.start()
    widget._glow_anim = anim
    return anim


# ═══════════════════════════════════════════════════════════════════
#  Page Transition анимации
# ═══════════════════════════════════════════════════════════════════

def page_transition(old_page, new_page, duration=350, direction="fade"):
    """
    Плавный переход между страницами.
    direction: "fade", "slide_left", "slide_right", "slide_up", "slide_down"
    """
    if not old_page or not new_page:
        return

    # Создаём эффект прозрачности
    old_effect = QGraphicsOpacityEffect(old_page)
    new_effect = QGraphicsOpacityEffect(new_page)
    old_page.setGraphicsEffect(old_effect)
    new_page.setGraphicsEffect(new_effect)

    # Группа анимаций
    group = QParallelAnimationGroup()

    # Анимация ухода старой страницы
    fade_out_anim = QPropertyAnimation(old_effect, b"opacity")
    fade_out_anim.setDuration(duration // 2)
    fade_out_anim.setStartValue(1.0)
    fade_out_anim.setEndValue(0.0)
    fade_out_anim.setEasingCurve(QEasingCurve.InCubic)
    group.addAnimation(fade_out_anim)

    # Анимация появления новой страницы
    fade_in_anim = QPropertyAnimation(new_effect, b"opacity")
    fade_in_anim.setDuration(duration // 2)
    fade_in_anim.setStartValue(0.0)
    fade_in_anim.setEndValue(1.0)
    fade_in_anim.setEasingCurve(QEasingCurve.OutCubic)

    # Запускаем появление с задержкой
    QTimer.singleShot(duration // 2, lambda: fade_in_anim.start())
    group.addAnimation(fade_in_anim)

    # Сдвиг для slide анимаций
    if direction.startswith("slide"):
        old_pos = old_page.pos()
        new_pos = new_page.pos()

        if direction == "slide_left":
            old_end = QPoint(old_pos.x() - old_page.width(), old_pos.y())
            new_start = QPoint(new_pos.x() + new_page.width(), new_pos.y())
        elif direction == "slide_right":
            old_end = QPoint(old_pos.x() + old_page.width(), old_pos.y())
            new_start = QPoint(new_pos.x() - new_page.width(), new_pos.y())
        elif direction == "slide_up":
            old_end = QPoint(old_pos.x(), old_pos.y() - old_page.height())
            new_start = QPoint(new_pos.x(), new_pos.y() + new_page.height())
        elif direction == "slide_down":
            old_end = QPoint(old_pos.x(), old_pos.y() + old_page.height())
            new_start = QPoint(new_pos.x(), new_pos.y() - new_page.height())

        old_slide = QPropertyAnimation(old_page, b"pos")
        old_slide.setDuration(duration // 2)
        old_slide.setStartValue(old_pos)
        old_slide.setEndValue(old_end)
        old_slide.setEasingCurve(QEasingCurve.InCubic)
        group.addAnimation(old_slide)

        new_page.move(new_start)
        new_slide = QPropertyAnimation(new_page, b"pos")
        new_slide.setDuration(duration // 2)
        new_slide.setStartValue(new_start)
        new_slide.setEndValue(new_pos)
        new_slide.setEasingCurve(QEasingCurve.OutCubic)
        QTimer.singleShot(duration // 2, lambda: new_slide.start())
        group.addAnimation(new_slide)

    group.start()
    return group


# ═══════════════════════════════════════════════════════════════════
#  Staggered анимации (последовательное появление элементов)
# ═══════════════════════════════════════════════════════════════════

def staggered_fade_in(widgets, delay=50, duration=300):
    """Последовательное появление списка виджетов с задержкой."""
    group = QSequentialAnimationGroup()

    for i, widget in enumerate(widgets):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        # Сохраняем ссылки чтобы GC не удалил
        if not hasattr(widget, '_stagger_anims'):
            widget._stagger_anims = []
        widget._stagger_anims.append(anim)
        widget._stagger_anims.append(effect)

        # Запускаем с задержкой
        QTimer.singleShot(i * delay, lambda a=anim: a.start())
        group.addAnimation(anim)

    return group


def staggered_slide_in(widgets, direction="left", delay=80, duration=300):
    """Последовательное появление списка виджетов со сдвигом."""
    group = QSequentialAnimationGroup()

    for i, widget in enumerate(widgets):
        start_pos = widget.pos()

        if direction == "left":
            widget.move(start_pos.x() - 50, start_pos.y())
        elif direction == "right":
            widget.move(start_pos.x() + 50, start_pos.y())
        elif direction == "top":
            widget.move(start_pos.x(), start_pos.y() - 30)
        elif direction == "bottom":
            widget.move(start_pos.x(), start_pos.y() + 30)

        anim = QPropertyAnimation(widget, b"pos")
        anim.setDuration(duration)
        anim.setStartValue(widget.pos())
        anim.setEndValue(start_pos)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        # Сохраняем ссылки чтобы GC не удалил
        if not hasattr(widget, '_stagger_anims'):
            widget._stagger_anims = []
        widget._stagger_anims.append(anim)

        QTimer.singleShot(i * delay, lambda a=anim: a.start())
        group.addAnimation(anim)

    return group


# ═══════════════════════════════════════════════════════════════════
#  Bounce анимации
# ═══════════════════════════════════════════════════════════════════

def bounce(widget, duration=600):
    """Пружинящая анимация появления."""
    original = widget.geometry()

    # Сжимаем
    compressed = QRect(
        original.x() + original.width() // 4,
        original.y() + original.height() // 4,
        original.width() // 2,
        original.height() // 2
    )

    anim1 = QPropertyAnimation(widget, b"geometry")
    anim1.setDuration(duration // 3)
    anim1.setStartValue(original)
    anim1.setEndValue(compressed)
    anim1.setEasingCurve(QEasingCurve.InCubic)

    # Растягиваем обратно
    anim2 = QPropertyAnimation(widget, b"geometry")
    anim2.setDuration(duration // 3)
    anim2.setStartValue(compressed)
    anim2.setEndValue(original)
    anim2.setEasingCurve(QEasingCurve.OutBack)

    group = QSequentialAnimationGroup()
    group.addAnimation(anim1)
    group.addAnimation(anim2)
    group.start()
    widget._bounce_anim = group
    return group

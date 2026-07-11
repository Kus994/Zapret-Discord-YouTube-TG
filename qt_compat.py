"""
qt_compat.py — Совместимость PyQt5 и PyQt6
"""

import sys

# Определяем версию
try:
    from PyQt5.QtWidgets import QFrame, QSizePolicy, QHeaderView, QAbstractItemView
    from PyQt5.QtCore import Qt
    QT6 = False
except ImportError:
    from PyQt6.QtWidgets import QFrame, QSizePolicy, QHeaderView, QAbstractItemView
    from PyQt6.QtCore import Qt
    QT6 = True

# Простые алиасы для enum'ов
if QT6:
    AlignLeft = Qt.AlignmentFlag.AlignLeft
    AlignRight = Qt.AlignmentFlag.AlignRight
    AlignCenter = Qt.AlignmentFlag.AlignCenter
    AlignHCenter = Qt.AlignmentFlag.AlignHCenter
    AlignVCenter = Qt.AlignmentFlag.AlignVCenter
    AlignJustify = Qt.AlignmentFlag.AlignJustify

    SplashScreen = Qt.WindowType.SplashScreen
    FramelessWindowHint = Qt.WindowType.FramelessWindowHint
    WindowStaysOnTopHint = Qt.WindowType.WindowStaysOnTopHint
    Tool = Qt.WindowType.Tool

    PointingHandCursor = Qt.CursorShape.PointingHandCursor
    WaitCursor = Qt.CursorShape.WaitCursor

    KeepAspectRatioByExpanding = Qt.AspectRatioMode.KeepAspectRatioByExpanding
    KeepAspectRatio = Qt.AspectRatioMode.KeepAspectRatio
    SmoothTransformation = Qt.TransformationMode.SmoothTransformation

    Horizontal = Qt.Orientation.Horizontal
    Vertical = Qt.Orientation.Vertical

    LeftButton = Qt.MouseButton.LeftButton
    RightButton = Qt.MouseButton.RightButton

    TextSelectableByMouse = Qt.TextInteractionFlag.TextSelectableByMouse
    TextWordWrap = Qt.TextFlag.TextWordWrap

    HLine = QFrame.Shape.HLine
    VLine = QFrame.Shape.VLine
    NoFrame = QFrame.Shape.NoFrame
    Box = QFrame.Shape.Box
    Panel = QFrame.Shape.Panel
    StyledPanel = QFrame.Shape.StyledPanel

    Expanding = QSizePolicy.Policy.Expanding
    Fixed = QSizePolicy.Policy.Fixed
    Minimum = QSizePolicy.Policy.Minimum
    Maximum = QSizePolicy.Policy.Maximum
    Preferred = QSizePolicy.Policy.Preferred

    ResizeToContents = QHeaderView.ResizeMode.ResizeToContents
    Stretch = QHeaderView.ResizeMode.Stretch
    Interactive = QHeaderView.ResizeMode.Interactive

    SelectRows = QAbstractItemView.SelectionMode.SelectRows
    NoSelection = QAbstractItemView.SelectionMode.NoSelection
    SingleSelection = QAbstractItemView.SelectionMode.SingleSelection
    NoEditTriggers = QAbstractItemView.EditTrigger.NoEditTriggers

else:
    AlignLeft = Qt.AlignLeft
    AlignRight = Qt.AlignRight
    AlignCenter = Qt.AlignCenter
    AlignHCenter = Qt.AlignHCenter
    AlignVCenter = Qt.AlignVCenter
    AlignJustify = Qt.AlignJustify

    SplashScreen = Qt.SplashScreen
    FramelessWindowHint = Qt.FramelessWindowHint
    WindowStaysOnTopHint = Qt.WindowStaysOnTopHint
    Tool = Qt.Tool

    PointingHandCursor = Qt.PointingHandCursor
    WaitCursor = Qt.WaitCursor

    KeepAspectRatioByExpanding = Qt.KeepAspectRatioByExpanding
    KeepAspectRatio = Qt.KeepAspectRatio
    SmoothTransformation = Qt.SmoothTransformation

    Horizontal = Qt.Horizontal
    Vertical = Qt.Vertical

    LeftButton = Qt.LeftButton
    RightButton = Qt.RightButton

    TextSelectableByMouse = Qt.TextSelectableByMouse
    TextWordWrap = Qt.TextWordWrap

    HLine = QFrame.HLine
    VLine = QFrame.VLine
    NoFrame = QFrame.NoFrame
    Box = QFrame.Box
    Panel = QFrame.Panel
    StyledPanel = QFrame.StyledPanel

    Expanding = QSizePolicy.Expanding
    Fixed = QSizePolicy.Fixed
    Minimum = QSizePolicy.Minimum
    Maximum = QSizePolicy.Maximum
    Preferred = QSizePolicy.Preferred

    ResizeToContents = QHeaderView.ResizeToContents
    Stretch = QHeaderView.Stretch
    Interactive = QHeaderView.Interactive

    SelectRows = QAbstractItemView.SelectRows
    NoSelection = QAbstractItemView.NoSelection
    SingleSelection = QAbstractItemView.SingleSelection
    NoEditTriggers = QAbstractItemView.NoEditTriggers


def exec_app(app):
    """Запуск QApplication."""
    if QT6:
        return app.exec()
    else:
        return app.exec_()

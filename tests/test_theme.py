"""
test_theme.py — Тесты модуля темы.
"""

import pytest


class TestTheme:
    """Тесты констант и функций темы."""

    def test_colors_defined(self):
        from theme import ACCENT, BG_DEEP, BG_CARD, TEXT_MAIN, TEXT_DIM
        assert ACCENT.startswith("#")
        assert BG_DEEP.startswith("#")
        assert BG_CARD.startswith("#")
        assert TEXT_MAIN.startswith("#")

    def test_qss_not_empty(self):
        from theme import QSS, TABLE_QSS
        assert len(QSS) > 100
        assert len(TABLE_QSS) > 50

    def test_version_defined(self):
        from theme import VERSION
        assert VERSION
        assert "." in VERSION


class TestThemeManager:
    """Тесты менеджера тем."""

    def test_default_is_dark(self):
        from theme import ThemeManager
        ThemeManager._current_theme = "dark"
        assert ThemeManager.is_dark() is True
        assert ThemeManager.is_light() is False

    def test_switch_to_light(self):
        from theme import ThemeManager
        ThemeManager.switch_to("light")
        assert ThemeManager.is_light() is True
        ThemeManager.switch_to("dark")  # возврат

    def test_toggle(self):
        from theme import ThemeManager
        ThemeManager._current_theme = "dark"
        ThemeManager.toggle()
        assert ThemeManager.is_light() is True
        ThemeManager.toggle()
        assert ThemeManager.is_dark() is True

    def test_get_color_dark(self):
        from theme import ThemeManager, ACCENT
        ThemeManager.switch_to("dark")
        color = ThemeManager.get_color("ACCENT")
        assert color == ACCENT

    def test_get_color_light(self):
        from theme import ThemeManager, LIGHT_THEME
        ThemeManager.switch_to("light")
        color = ThemeManager.get_color("BG_DEEP")
        assert color == LIGHT_THEME["BG_DEEP"]
        ThemeManager.switch_to("dark")  # возврат

    def test_get_qss_dark(self):
        from theme import ThemeManager, QSS
        ThemeManager.switch_to("dark")
        qss = ThemeManager.get_qss()
        assert qss == QSS

    def test_get_qss_light(self):
        from theme import ThemeManager, LIGHT_QSS
        ThemeManager.switch_to("light")
        qss = ThemeManager.get_qss()
        assert qss == LIGHT_QSS
        ThemeManager.switch_to("dark")  # возврат

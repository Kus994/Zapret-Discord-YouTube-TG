"""
test_hotkeys.py — Тесты модуля горячих клавиш.
"""

import pytest


class TestParseHotkey:
    """Тесты парсинга хоткеев."""

    def test_simple_combo(self):
        from modules.hotkeys import parse_hotkey
        result = parse_hotkey("Ctrl+Alt+G")
        assert result is not None
        modifiers, vk = result
        assert vk == 0x47  # G

    def test_ctrl_only(self):
        from modules.hotkeys import parse_hotkey
        result = parse_hotkey("Ctrl+F1")
        assert result is not None
        modifiers, vk = result
        assert vk == 0x70  # F1

    def test_empty_string(self):
        from modules.hotkeys import parse_hotkey
        assert parse_hotkey("") is None

    def test_none(self):
        from modules.hotkeys import parse_hotkey
        assert parse_hotkey(None) is None

    def test_invalid_key(self):
        from modules.hotkeys import parse_hotkey
        assert parse_hotkey("Ctrl+1") is None

    def test_shift_modifier(self):
        from modules.hotkeys import parse_hotkey, MOD_SHIFT
        result = parse_hotkey("Shift+A")
        assert result is not None
        modifiers, vk = result
        assert modifiers & MOD_SHIFT

    def test_win_modifier(self):
        from modules.hotkeys import parse_hotkey, MOD_WIN
        result = parse_hotkey("Win+G")
        assert result is not None
        modifiers, vk = result
        assert modifiers & MOD_WIN

    def test_f12_key(self):
        from modules.hotkeys import parse_hotkey
        result = parse_hotkey("Ctrl+F12")
        assert result is not None
        _, vk = result
        assert vk == 0x7B  # F12

    def test_case_insensitive_modifiers(self):
        from modules.hotkeys import parse_hotkey
        result = parse_hotkey("ctrl+alt+g")
        assert result is not None

    def test_multiple_modifiers(self):
        from modules.hotkeys import parse_hotkey, MOD_CONTROL, MOD_ALT, MOD_SHIFT
        result = parse_hotkey("Ctrl+Alt+Shift+G")
        assert result is not None
        modifiers, vk = result
        assert modifiers & MOD_CONTROL
        assert modifiers & MOD_ALT
        assert modifiers & MOD_SHIFT


class TestVKCodes:
    """Тесты таблицы VK-кодов."""

    def test_a_to_z(self):
        from modules.hotkeys import VK_CODES
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert letter in VK_CODES

    def test_f1_to_f12(self):
        from modules.hotkeys import VK_CODES
        for i in range(1, 13):
            assert "F{}".format(i) in VK_CODES

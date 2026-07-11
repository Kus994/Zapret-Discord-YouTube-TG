"""
modules/hotkeys.py — KUS Pro

Глобальная горячая клавиша для переключения игрового режима,
работающая даже когда окно приложения свёрнуто или не в фокусе.

Реализовано через нативный WinAPI RegisterHotKey/UnregisterHotKey —
без сторонних библиотек (вроде `keyboard`, которая требует root/admin
на некоторых системах и тянет лишнюю зависимость). Qt не предоставляет
обёртку для системных хоткеев напрямую (QShortcut работает только
когда окно в фокусе), поэтому здесь используется низкоуровневый
оконный API через ctypes + перехват WM_HOTKEY в MainWindow.nativeEvent.
"""

import ctypes
from ctypes import wintypes

WM_HOTKEY = 0x0312

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Виртуальные коды клавиш, которые имеет смысл предлагать в UI —
# полный список VK-кодов гораздо больше, но для горячей клавиши
# игрового режима этого набора достаточно (буквы и функциональные).
VK_CODES = {
    **{chr(c): c for c in range(0x41, 0x5B)},      # A-Z
    **{"F{}".format(i): 0x70 + i - 1 for i in range(1, 13)},  # F1-F12
}

HOTKEY_ID_GAME_MODE = 1


def parse_hotkey(combo: str):
    """Разбирает строку вида 'Ctrl+Alt+G' в (modifiers, vk_code).
    Возвращает None, если строка не распознана."""
    if not combo:
        return None
    parts = [p.strip() for p in combo.split("+") if p.strip()]
    if not parts:
        return None

    modifiers = MOD_NOREPEAT
    key_part = None
    mod_map = {"ctrl": MOD_CONTROL, "control": MOD_CONTROL,
              "alt": MOD_ALT, "shift": MOD_SHIFT, "win": MOD_WIN}

    for p in parts:
        low = p.lower()
        if low in mod_map:
            modifiers |= mod_map[low]
        else:
            key_part = p.upper()

    if not key_part or key_part not in VK_CODES:
        return None

    return modifiers, VK_CODES[key_part]


def register_hotkey(hwnd: int, combo: str, hotkey_id: int = HOTKEY_ID_GAME_MODE) -> bool:
    """Регистрирует глобальный хоткей для окна с дескриптором hwnd.
    Возвращает True при успехе. Если хоткей уже занят другой
    программой, Windows вернёт 0 (неудача) — это нормальная ситуация,
    не ошибка приложения."""
    parsed = parse_hotkey(combo)
    if not parsed:
        return False
    modifiers, vk = parsed
    user32 = ctypes.windll.user32
    return bool(user32.RegisterHotKey(wintypes.HWND(hwnd), hotkey_id, modifiers, vk))


def unregister_hotkey(hwnd: int, hotkey_id: int = HOTKEY_ID_GAME_MODE) -> bool:
    user32 = ctypes.windll.user32
    return bool(user32.UnregisterHotKey(wintypes.HWND(hwnd), hotkey_id))


def is_hotkey_message(msg, hotkey_id: int = HOTKEY_ID_GAME_MODE) -> bool:
    """Проверяет, является ли нативное Windows-сообщение WM_HOTKEY
    с нужным ID. msg — это MSG-структура, которую Qt передаёт в
    nativeEvent в виде указателя; вызывающая сторона должна сначала
    привести его через ctypes (см. MainWindow.nativeEvent)."""
    return msg.message == WM_HOTKEY and msg.wParam == hotkey_id

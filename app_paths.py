"""
app_paths.py — KUS Pro
Единая точка определения всех путей приложения.

В dev-режиме (python main.py) — пути относительно исходников.
В frozen-режиме (PyInstaller .exe) — пути относительно .exe файла.
Для onefile сборки: bundled-данные в sys._MEIPASS, записываемые рядом с exe.
"""

import os
import sys
import shutil
from pathlib import Path


def _base_dir() -> Path:
    """Корневая директория приложения (рядом с exe)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _data_dir() -> Path:
    """Директория bundled-данных (read-only, внутри exe для onefile)."""
    if getattr(sys, "frozen", False):
        # sys._MEIPASS — временная папка куда PyInstaller извлекает --add-data
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


BASE_DIR = _base_dir()
DATA_DIR = _data_dir()

# Файлы данных — рядом с exe (записываемые)
CONFIG_FILE = BASE_DIR / "config.json"
TIMETRACK_FILE = BASE_DIR / "timetrack_data.json"

# Папки с записью — рядом с exe
ZAPRET_DIR = BASE_DIR / "zapret"
TG_PROXY_DIR = BASE_DIR / "tg_proxy"

# Папки read-only — из bundled данных
ASSETS_DIR = DATA_DIR / "assets"
MODULES_DIR = DATA_DIR / "modules"

# Иконка
ICON_FILE = ASSETS_DIR / "icon.ico"

# Фон
BG_FILE = ASSETS_DIR / "background.png"

# Zapret
ZAPRET_VERSION_FILE = ZAPRET_DIR / "current_version.txt"

# TG Proxy
TG_PROXY_EXE = "TgWsProxy_windows.exe"


def ensure_config():
    """Копирует bundled config.json рядом с exe если его там нет."""
    if getattr(sys, "frozen", False) and DATA_DIR != BASE_DIR:
        bundled = DATA_DIR / "config.json"
        target = BASE_DIR / "config.json"
        if bundled.exists() and not target.exists():
            shutil.copy2(bundled, target)

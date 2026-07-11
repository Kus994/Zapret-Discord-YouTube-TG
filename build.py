"""
build.py — KUS Pro
Скрипт сборки standalone .exe через PyInstaller.

Запуск:
    python build.py

Результат:
    dist/KUS_Pro/KUS_Pro.exe  — автономное приложение без Python.

Скрипт автоматически:
  1. Устанавливает PyInstaller (если нет)
  2. Собирает все data-файлы (assets, config, modules, zapret, tg_proxy)
  3. Добавляет все hidden imports для корректной сборки
  4. Создаёт .exe в папке dist/
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
APP_NAME = "KUS_Pro"
MAIN_SCRIPT = BASE_DIR / "main.py"


def check_pyinstaller():
    """Проверяет наличие PyInstaller и устанавливает при необходимости."""
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("[INFO] PyInstaller не найден, устанавливаю...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller установлен.")


def bump_version(skip=False):
    """Автоматически инкрементирует patch-версию в theme.py перед сборкой.
    skip=True — пропускает автоматический бамп (для dev-сборок)."""
    if skip:
        print("[INFO] Автобамп версии пропущен (skip=True)")
        return None

    theme_path = BASE_DIR / "theme.py"
    if not theme_path.exists():
        return "?"

    text = theme_path.read_text(encoding="utf-8")
    import re
    m = re.search(r'VERSION\s*=\s*"(\d+)\.(\d+)(?:\.(\d+))?"', text)
    if not m:
        return "?"

    major, minor = int(m.group(1)), int(m.group(2))
    patch = int(m.group(3)) + 1 if m.group(3) else 1

    new_ver = f"{major}.{minor}.{patch}"
    old_ver = f"{major}.{minor}.{m.group(3) or ''}".rstrip(".")

    new_text = text[:m.start()] + f'VERSION = "{new_ver}"' + text[m.end():]
    theme_path.write_text(new_text, encoding="utf-8")

    print(f"[INFO] Версия: {old_ver} → {new_ver}")
    return new_ver


def _patch_pyqt5_path():
    """Патчит путь PyQt5 если в пути есть кириллица (PyInstaller не умеет)."""
    try:
        import PyQt5
        cur = os.path.dirname(PyQt5.__file__)
        if any(ord(c) > 127 for c in cur):
            # Создаём junction: C:\PyEnv → Python314
            py_env = Path("C:/PyEnv")
            if py_env.exists():
                patched = str(py_env / "Lib" / "site-packages" / "PyQt5")
                if os.path.isdir(patched):
                    PyQt5.__file__ = os.path.join(patched, "__init__.py")
                    PyQt5.__path__ = [patched]
                    PyQt5.__spec__.submodule_search_locations = [patched]
                    print(f"[FIX] PyQt5 path → {patched}")
                    return
            # Если junction нет — пробуем короткий путь Windows
            import ctypes
            buf = ctypes.create_unicode_buffer(512)
            ctypes.windll.kernel32.GetShortPathNameW(cur, buf, 512)
            short = buf.value
            if short and short != cur:
                PyQt5.__file__ = os.path.join(short, "__init__.py")
                PyQt5.__path__ = [short]
                PyQt5.__spec__.submodule_search_locations = [short]
                print(f"[FIX] PyQt5 path → {short}")
    except Exception as e:
        print(f"[WARN] Не удалось патчить PyQt5: {e}")


def collect_data_args():
    """Собирает --add-data аргументы для PyInstaller."""
    args = []

    # ── Assets (только нужные файлы) ──
    assets_dir = BASE_DIR / "assets"
    if assets_dir.exists():
        for f in assets_dir.glob("*"):
            if f.is_file() and f.suffix in (".png", ".ico", ".gif"):
                args.append(f"--add-data={f};assets")

    # ── Config ──
    config = BASE_DIR / "config.json"
    if config.exists():
        args.append(f"--add-data={config};.")

    # ── Core modules (app_paths, config_manager) ──
    for mod_name in ("app_paths.py", "config_manager.py"):
        mod_file = BASE_DIR / mod_name
        if mod_file.exists():
            args.append(f"--add-data={mod_file};.")

    # ── Modules (Python) ──
    modules_dir = BASE_DIR / "modules"
    if modules_dir.exists():
        for f in modules_dir.glob("*.py"):
            args.append(f"--add-data={f};modules")

    # ── Zapret (только .bat и .json, НЕ .exe — скачиваются при первом запуске) ──
    zapret_dir = BASE_DIR / "zapret"
    if zapret_dir.exists():
        for f in zapret_dir.rglob("*"):
            if f.is_file() and f.suffix in (".bat", ".json", ".txt"):
                rel = f.relative_to(BASE_DIR)
                args.append(f"--add-data={f};{rel.parent}")

    # ── TG Proxy (только .py и .json, НЕ .exe — скачиваются при первом запуске) ──
    tg_dir = BASE_DIR / "tg_proxy"
    if tg_dir.exists():
        for f in tg_dir.rglob("*"):
            if f.is_file() and f.suffix in (".py", ".json", ".toml"):
                rel = f.relative_to(BASE_DIR)
                args.append(f"--add-data={f};{rel.parent}")

    # ── timetrack_data.json ──
    tt_data = BASE_DIR / "timetrack_data.json"
    if tt_data.exists():
        args.append(f"--add-data={tt_data};.")

    return args


def build():
    """Основная функция сборки."""
    print("=" * 60)
    print("  KUS Pro — Сборка standalone .exe")
    print("=" * 60)
    print()

    check_pyinstaller()

    # Автобамп версии (пропускается при --skip-version)
    skip_version = "--skip-version" in sys.argv
    new_ver = bump_version(skip=skip_version)

    # Фикс кириллицы в пути: подменяем PYTHONPATH чтобы C:\PyEnv был первым
    _patch_pyqt5_path()

    # Очищаем предыдущие сборки
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            print(f"[INFO] Очистка {d}...")
            shutil.rmtree(d, ignore_errors=True)

    # Собираем data-файлы
    data_args = collect_data_args()
    print(f"[INFO] Data-файлов: {len(data_args)}")

    # Hidden imports
    hidden_imports = [
        "psutil",
        "certifi",
        "app_paths", "config_manager",
        "modules.cleanup", "modules.elevation",
        "modules.game_mode", "modules.hotkeys", "modules.monitor",
        "modules.network", "modules.processes", "modules.security",
        "modules.timetrack", "modules.updates", "modules.tg_bot",
        "modules.battery", "modules.services",
        "modules.export", "modules.action_log",
        "modules.download_utils", "modules.hardware",
        "modules.autostart", "modules.notifications",
        "modules.search", "modules.optimizer",
        "modules.scheduler", "modules.settings_backup",
        "widgets", "theme", "base_page", "worker", "animations",
        "page_battery", "page_services", "page_export",
        "page_action_log", "page_optimizer", "page_settings",
    ]

    # Проверяем наличие иконки
    icon_path = BASE_DIR / "assets" / "icon.ico"
    icon_arg = f"--icon={icon_path}" if icon_path.exists() else ""

    # Формируем команду
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name", APP_NAME,
        "--onefile",
        "--windowed",
        "--strip",
    ]

    if icon_arg:
        cmd.append(icon_arg)

    # Явно указываем путь к PyQt5 для корректного сбора плагинов
    # Используем junction C:\PyEnv если кириллица в пути
    pyqt5_path = None
    try:
        import PyQt5
        qt_path = os.path.dirname(PyQt5.__file__)
        if any(ord(c) > 127 for c in qt_path):
            py_env = Path("C:/PyEnv")
            if py_env.exists():
                qt_path = str(py_env / "Lib" / "site-packages" / "PyQt5")
        pyqt5_path = qt_path
        cmd.extend(["--paths", qt_path])
    except ImportError:
        pass

    # Собираем только нужные PyQt5 модули (не все!)
    # Основные: Core, Gui, Widgets, OpenGL, WinExtras
    # НЕ нужны: Qt3D, QtMultimedia, QtQuick, QtWebEngine, QtQml, QtSvg, и т.д.
    needed_qt = ["PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets",
                 "PyQt5.QtOpenGL", "PyQt5.QtWinExtras"]
    for qt_mod in needed_qt:
        cmd.extend(["--hidden-import", qt_mod])

    # Исключаем тяжёлые ненужные модули
    excluded_modules = [
        "PyQt5.Qt3D", "PyQt5.Qt3DAnimation", "PyQt5.Qt3DCore",
        "PyQt5.Qt3DExtras", "PyQt5.Qt3DInput", "PyQt5.Qt3DLogic",
        "PyQt5.Qt3DRender", "PyQt5.QtBluetooth", "PyQt5.QtDBus",
        "PyQt5.QtDesigner", "PyQt5.QtHelp", "PyQt5.QtLocation",
        "PyQt5.QtMultimedia", "PyQt5.QtMultimediaWidgets",
        "PyQt5.QtNfc", "PyQt5.QtPositioning", "PyQt5.QtPrintSupport",
        "PyQt5.QtQml", "PyQt5.QtQuick", "PyQt5.QtQuick3D",
        "PyQt5.QtQuickWidgets", "PyQt5.QtRemoteObjects",
        "PyQt5.QtSensors", "PyQt5.QtSerialPort", "PyQt5.QtSql",
        "PyQt5.QtSvg", "PyQt5.QtTest", "PyQt5.QtTextToSpeech",
        "PyQt5.QtWebChannel", "PyQt5.QtWebSockets",
        "PyQt5.QtXml", "PyQt5.QtXmlPatterns",
        "PyQt5.QtAxContainer", "PyQt5.QtBluetooth",
        "PyQt5.QtLocation", "PyQt5.QtPositioning",
        "PyQt5.QtWebEngine", "PyQt5.QtWebEngineWidgets",
        "numpy", "pandas", "scipy", "matplotlib",
        "PIL", "tkinter", "unittest", "test",
    ]
    for mod in excluded_modules:
        cmd.extend(["--exclude-module", mod])

    # Hidden imports
    for hi in hidden_imports:
        cmd.extend(["--hidden-import", hi])

    # Collect-all для certifi (нужны CA-сертификаты для HTTPS)
    cmd.extend(["--collect-all", "certifi"])

    # Data-файлы
    cmd.extend(data_args)

    # Точка входа
    cmd.append(str(MAIN_SCRIPT))

    print(f"[INFO] Запуск PyInstaller...")
    print(f"[CMD] {cmd[3]} {cmd[4]} ... (см. полный список в build.py)")
    print()

    # Передаём PYTHONPATH с junction-путём первым чтобы PyInstaller не ломался на кириллице
    env = os.environ.copy()
    py_env_site = r"C:\PyEnv\Lib\site-packages"
    if os.path.isdir(py_env_site):
        old_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = py_env_site + (";" + old_pp if old_pp else "")
        print(f"[FIX] PYTHONPATH → {py_env_site} (первый)")

    result = subprocess.run(cmd, cwd=str(BASE_DIR), env=env)

    if result.returncode != 0:
        print()
        print("[ERROR] Сборка завершилась с ошибкой!")
        print("[HINT]  Проверьте вывод выше и исправьте ошибки.")
        return False

    # Копируем runtime-файлы рядом с exe
    dist_app = DIST_DIR / APP_NAME
    exe_path = DIST_DIR / f"{APP_NAME}.exe"

    # Для onefile — exe лежит прямо в dist/
    if not exe_path.exists():
        # fallback: ищем exe в подпапке
        dist_app_dir = DIST_DIR / APP_NAME
        exe_path = dist_app_dir / f"{APP_NAME}.exe"
        if exe_path.exists():
            # Копируем exe на уровень выше
            import shutil as _sh
            _sh.copy2(exe_path, DIST_DIR / f"{APP_NAME}.exe")
            exe_path = DIST_DIR / f"{APP_NAME}.exe"

    # Копируем config.json рядом с exe
    config_src = BASE_DIR / "config.json"
    if config_src.exists():
        shutil.copy2(config_src, DIST_DIR / "config.json")

    if exe_path.exists():
        total_size = exe_path.stat().st_size

        print()
        print("=" * 60)
        print("  Сборка завершена успешно!")
        print()
        print(f"  Версия:  {new_ver}")
        print(f"  EXE:     {exe_path}")
        print(f"  Размер:  {total_size / 1024 / 1024:.1f} МБ")
        print()
        print("  Скопируйте KUS_Pro.exe на другой ПК и запустите.")
        print("  Python и зависимости НЕ требуются.")
        print("=" * 60)
        return True

    print("[ERROR] EXE не найден после сборки!")
    return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)

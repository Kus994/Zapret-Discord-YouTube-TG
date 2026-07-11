"""
main.py - KUS Pro - Entry point
"""
import os
import sys
from pathlib import Path

# Папка проекта всегда в sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ["KUS_BASE_DIR"] = str(BASE_DIR)


def _fix_console_encoding():
    """ФИКС: run.bat включает `chcp 65001` (UTF-8) для консоли и
    перенаправляет вывод в run_log.txt (`> run_log.txt 2>&1`), который
    потом печатается через `type`. Но при перенаправлении в файл
    Python на Windows по умолчанию может писать не в UTF-8, а в
    системную ANSI-кодировку (например, cp1251) — из-за рассинхрона
    с chcp 65001 кириллический текст лога превращался в ромбики (♦)
    вместо букв. Явно переключаем stdout/stderr на UTF-8 до первого
    print(), чтобы байты в run_log.txt совпадали с кодировкой,
    которую ожидает консоль.

    Второй случай: при повышении прав (UAC) новый процесс запускается
    напрямую через ShellExecuteW, МИНУЯ cmd.exe — то есть `chcp 65001`
    из run.bat на это НОВОЕ консольное окно не действует вообще, у
    него своя, отдельная консоль с кодировкой по умолчанию (обычно
    OEM cp866). Поэтому дополнительно переключаем саму консоль
    Windows на UTF-8 через WinAPI, а не только сторону Python."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass  # Python < 3.7 или поток без reconfigure — не критично

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass  # нет консоли (например, pythonw.exe) — не критично


_fix_console_encoding()


def fix_qt_plugins():
    """
    Фикс ошибки: Could not find the Qt platform plugin 'windows'
    Ищет qwindows.dll по всем известным путям.
    Поддерживает PyQt5 и PyQt6.
    """
    if sys.platform != "win32":
        return

    if os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"):
        return

    # Пробуем PyQt6, потом PyQt5
    for qt_pkg in ["PyQt6", "PyQt5"]:
        try:
            qt_mod = __import__(qt_pkg)
            qt_base = Path(qt_mod.__file__).parent

            # Стандартные пути
            candidates = [
                qt_base / "Qt6"    / "plugins" / "platforms",
                qt_base / "Qt5"    / "plugins" / "platforms",
                qt_base / "Qt"     / "plugins" / "platforms",
                qt_base / "plugins" / "platforms",
                qt_base / "Qt6"    / "plugins",
                qt_base / "Qt5"    / "plugins",
                qt_base / "Qt"     / "plugins",
            ]

            for p in candidates:
                if p.is_dir() and (p / "qwindows.dll").exists():
                    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(p)
                    print("[Qt] Found at:", str(p))
                    return

            # Рекурсивный поиск
            for root, dirs, files in os.walk(str(qt_base)):
                if "qwindows.dll" in files:
                    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = root
                    print("[Qt] Found at:", root)
                    return

            print("[Qt] WARNING: qwindows.dll not found! App may crash.")
            return

        except ImportError:
            continue
        except Exception as e:
            print("[Qt] fix error:", e)
            return

    print("[ERROR] Neither PyQt5 nor PyQt6 installed!")
    print("Run: pip install PyQt5 psutil certifi")
    input("Press Enter to exit...")
    sys.exit(1)


def request_admin():
    """UAC - запрос прав администратора на Windows.

    ФИКС: раньше при попытке повышения прав текущий процесс
    завершался безусловно (sys.exit(0)) сразу после вызова
    ShellExecuteW, не проверяя, удался ли реальный перезапуск.
    Если пользователь отклонял диалог UAC — окно приложения никогда
    не появлялось, а процесс тихо завершался с кодом 0 и пустым
    логом (именно так выглядела жалоба «ничего не открывается»).

    Теперь: если повышение прав не удалось по любой причине —
    приложение просто продолжает работу в текущем процессе без прав
    администратора, а не исчезает совсем. Лучше запуститься с
    ограниченными правами, чем не запуститься вообще."""
    if sys.platform != "win32":
        return
    try:
        from modules.elevation import is_admin, relaunch_as_admin
        if is_admin():
            return
        success, message = relaunch_as_admin()
        print("[UAC]", message)
        if success:
            sys.exit(0)
        # success=False: не выходим, продолжаем без прав администратора
        print("[UAC] Продолжаем без прав администратора.")
    except SystemExit:
        raise
    except Exception as exc:
        print("[UAC] Ошибка при попытке повышения прав:", exc)
        print("[UAC] Продолжаем без прав администратора.")


_SINGLE_INSTANCE_MUTEX = None  # держим handle живым весь срок работы процесса


def _acquire_single_instance_lock() -> bool:
    """УЛУЧШЕНИЕ: не даёт запустить второй экземпляр KUS Pro.

    Без этой проверки повторный запуск (например, случайный двойной
    клик по run.bat) создавал второй процесс, второй запрос UAC,
    второй значок в трее и второй набор фоновых воркеров — а
    RegisterHotKey для игрового режима в одном из них тихо не
    срабатывал, потому что комбинация уже занята первым экземпляром.
    Внешне это выглядело как «утилита работает через раз».

    Именованный мьютекс проверяется ПОСЛЕ request_admin(), а не до —
    иначе исходный (не повышенный) процесс успевал бы занять мьютекс
    перед тем, как передать управление повышенной копии, и та копия
    сама бы решила, что уже "уже запущена"."""
    if sys.platform != "win32":
        return True
    global _SINGLE_INSTANCE_MUTEX
    try:
        import ctypes
        ERROR_ALREADY_EXISTS = 183
        handle = ctypes.windll.kernel32.CreateMutexW(
            None, False, "Global\\KUS_Pro_SingleInstance_Mutex"
        )
        if not handle:
            return True  # не удалось создать — не блокируем запуск
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            ctypes.windll.kernel32.CloseHandle(handle)
            return False
        _SINGLE_INSTANCE_MUTEX = handle  # не даём Python закрыть handle через GC
        return True
    except Exception:
        return True  # не удалось проверить — лучше запуститься, чем нет


def _install_global_excepthook():
    """УЛУЧШЕНИЕ: раньше исключение внутри nativeEvent() (см. крэш с
    _hotkey_registered) вообще не попадало в наш try/except в
    `if __name__ == "__main__":` и не писалось в crash_log.txt —
    оно вывалилось сырым traceback'ом прямо в консоль. Причина: Qt
    вызывает переопределённые методы вроде nativeEvent/paintEvent/
    eventFilter из C++ во время app.exec_(), и необработанное
    исключение там уходит через sys.excepthook в обход обычного
    Python-стека вызовов, а не через return main() -> except.
    Ставим свой excepthook ДО app.exec_(), чтобы такие исключения
    тоже гарантированно попадали в crash_log.txt."""
    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        try:
            _write_crash_log(exc_value)
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


def check_windows_version():
    """Проверяет версию Windows и предупреждает, если она ниже поддерживаемой.

    Минимальная версия для полной поддержки: Windows 10 (10.0 build 10240).
    На Windows 7/8/8.1 часть функций (прозрачность, dark mode, авто-скрытие
    панели задач) будет недоступна — но приложение всё равно запустится.

    Возвращает True если можно продолжать, False если стоит прервать запуск."""
    if sys.platform != "win32":
        return True

    try:
        ver = sys.getwindowsversion()
    except Exception:
        return True  # не смогли определить — не блокируем

    major, minor, build = ver.major, ver.minor, ver.build

    # Windows 10 = 10.0, Windows 11 = 10.0 (build >= 22000)
    # Windows 8.1 = 6.3, Windows 8 = 6.2, Windows 7 = 6.1
    win10_build = 10240  # первый релиз Windows 10

    if major < 10:
        # Windows 7 / 8 / 8.1 — предупреждаем, но не блокируем
        ver_names = {
            (6, 1): "Windows 7",
            (6, 2): "Windows 8",
            (6, 3): "Windows 8.1",
        }
        name = ver_names.get((major, minor), "версия {}.{}.{}".format(major, minor, build))

        msg = (
            "KUS Pro\n\n"
            "Обнаружена неподдерживаемая версия ОС: {}\n\n"
            "Минимальная рекомендуемая версия — Windows 10.\n"
            "На текущей версии возможны следующие проблемы:\n"
            "  - Не работает переключение прозрачности окон\n"
            "  - Недоступна тёмная тема интерфейса\n"
            "  - Не управляется авто-скрытие панели задач\n"
            "  - Некоторые функции мониторинга могут работать некорректно\n\n"
            "Продолжить на свой страх и риск?"
        ).format(name)

        try:
            import ctypes
            MB_YESNO = 0x04
            MB_ICONWARNING = 0x30
            MB_DEFBUTTON2 = 0x0100
            result = ctypes.windll.user32.MessageBoxW(
                None, msg, "KUS Pro — предупреждение",
                MB_YESNO | MB_ICONWARNING | MB_DEFBUTTON2,
            )
            return result == 6  # IDYES = 6
        except Exception:
            return True  # не смогли показать диалог — продолжаем

    if major == 10 and build < win10_build:
        # Очень ранняя сборка Windows 10 (Technology Preview)
        msg = (
            "KUS Pro\n\n"
            "Обнаружена предварительная сборка Windows 10 (build {}).\n"
            "Рекомендуется обновиться до стабильной версии Windows 10 или новее.\n\n"
            "Продолжить?"
        ).format(build)
        try:
            import ctypes
            MB_YESNO = 0x04
            MB_ICONWARNING = 0x30
            result = ctypes.windll.user32.MessageBoxW(
                None, msg, "KUS Pro — предупреждение",
                MB_YESNO | MB_ICONWARNING,
            )
            return result == 6
        except Exception:
            return True

    return True


def _check_updates_on_startup():
    """Фоновая проверка обновлений KUS Pro при запуске."""
    try:
        from auto_updater import check_kus_pro_update
        import webbrowser
        
        has_update, current, latest, url = check_kus_pro_update()
        if has_update and latest:
            print("[UPDATE] Доступна версия {} (текущая: {})".format(latest, current))
            # Показываем уведомление в трее
            try:
                from PyQt5.QtWidgets import QSystemTrayIcon, QMessageBox
                from PyQt5.QtGui import QIcon
                
                # Используем QTimer чтобы показать уведомление после инициализации окна
                def _show_update_notification():
                    try:
                        reply = QMessageBox.information(
                            None,
                            "Обновление KUS Pro",
                            "Доступна новая версия {}!\n\n"
                            "Текущая версия: {}\n\n"
                            "Открыть страницу скачивания?".format(latest, current),
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.Yes
                        )
                        if reply == QMessageBox.Yes:
                            webbrowser.open(url)
                    except Exception:
                        pass
                
                # Показываем через 3 секунды после запуска
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(3000, _show_update_notification)
            except Exception:
                pass
        else:
            print("[UPDATE] KUS Pro актуален (v{})".format(current))
    except Exception as e:
        print("[UPDATE] Ошибка проверки обновлений:", e)


def main():
    # Шаг 1: фикс Qt ДО любого импорта PyQt5
    fix_qt_plugins()

    # Шаг 1.5: проверка версии Windows
    if not check_windows_version():
        sys.exit(0)

    # Шаг 1.6: копируем bundled config рядом с exe (для onefile сборки)
    from app_paths import ensure_config
    ensure_config()

    # Шаг 3: права администратора ДО QApplication
    request_admin()

    # Шаг 4: не даём запустить второй экземпляр (см. комментарий в
    # _acquire_single_instance_lock — специально ПОСЛЕ request_admin()).
    if not _acquire_single_instance_lock():
        print("[INSTANCE] KUS Pro уже запущен — новый экземпляр не открываю.")
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    None,
                    "KUS Pro уже запущен.\nПроверьте значок в системном трее рядом с часами.",
                    "KUS Pro",
                    0x40,  # MB_ICONINFORMATION
                )
            except Exception:
                pass
        return

    # Шаг 5: импорт Qt только здесь
    # Сброс QT_QPA_PLATFORM чтобы не было конфликтов с offscreen
    os.environ.pop("QT_QPA_PLATFORM", None)

    from qt_compat import exec_app

    # Автовыбор PyQt5 (первый) или PyQt6
    try:
        from PyQt5.QtWidgets import QApplication
        QT6 = False
    except ImportError:
        from PyQt6.QtWidgets import QApplication
        QT6 = True

    if not QT6:
        from PyQt5.QtCore import Qt
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("KUS Pro")
    app.setOrganizationName("KUS")
    app.setQuitOnLastWindowClosed(False)

    from app_paths import ASSETS_DIR, BG_FILE, ICON_FILE

    if QT6:
        from PyQt6.QtWidgets import QSplashScreen, QLabel
        from PyQt6.QtGui import QPixmap, QColor
        from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
    else:
        from PyQt5.QtWidgets import QSplashScreen, QLabel
        from PyQt5.QtGui import QPixmap, QColor
        from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve

    # Сплеш-скрин
    splash_pixmap = QPixmap(420, 320)
    splash_pixmap.fill(QColor("#0a0e1a"))
    splash = QSplashScreen(splash_pixmap)

    if QT6:
        splash.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        splash.showMessage(
            "KUS PRO\nЗагрузка...",
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            QColor("#00ff88"),
        )
    else:
        splash.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        splash.showMessage(
            "KUS PRO\nЗагрузка...",
            Qt.AlignCenter | Qt.AlignVCenter,
            QColor("#00ff88"),
        )
    splash.setObjectName("splash")

    screen = app.primaryScreen().geometry()
    splash.move((screen.width() - 420) // 2, (screen.height() - 320) // 2)
    splash.show()
    splash.raise_()
    splash.activateWindow()
    app.processEvents()

    _install_global_excepthook()

    # Шаг 6: проверка обновлений при запуске (фоново)
    QTimer.singleShot(1000, _check_updates_on_startup)

    from main_window import MainWindow
    win = MainWindow()

    start_minimized = False
    autostart_zapret = False
    autostart_zapret_preset = ""
    autostart_tg_proxy = False
    try:
        from config_manager import get_value
        start_minimized = bool(get_value("start_minimized", False))
        autostart_zapret = bool(get_value("autostart_zapret", False))
        autostart_zapret_preset = str(get_value("autostart_zapret_preset", ""))
        autostart_tg_proxy = bool(get_value("autostart_tg_proxy", False))
    except Exception:
        pass

    def _show_main():
        splash.close()
        splash.deleteLater()
        win.show()
        # Fade-in анимация
        win._fade_anim = QPropertyAnimation(win, b"windowOpacity")
        win._fade_anim.setDuration(350)
        win._fade_anim.setStartValue(0.0)
        win._fade_anim.setEndValue(1.0)
        win._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        win._fade_anim.start()
        
        # Автозапуск Zapret с сохранённым пресетом
        if autostart_zapret and autostart_zapret_preset:
            try:
                from app_paths import ZAPRET_DIR
                from page_zapret import _save_ver, _get_versions, _is_running, _fn_start
                from worker import Worker
                
                versions = _get_versions()
                if versions and not _is_running():
                    ver = versions[0]  # Последняя версия
                    bat_path = str(ZAPRET_DIR / ver / autostart_zapret_preset)
                    from pathlib import Path
                    if Path(bat_path).exists():
                        _save_ver(ver)
                        ver_dir = str(ZAPRET_DIR / ver)
                        worker = Worker(_fn_start, bat_path, ver_dir)
                        worker.start()
                        print("[AUTO] Zapret autostart: {} / {}".format(ver, autostart_zapret_preset))
            except Exception as e:
                print("[AUTO] Zapret autostart error:", e)
        
        # Автозапуск Telegram Proxy
        if autostart_tg_proxy:
            try:
                from page_tg_proxy import _find_exe, _is_running as tg_running
                exe = _find_exe()
                if exe and not tg_running():
                    import subprocess
                    subprocess.Popen([str(exe)], cwd=str(exe.parent))
                    print("[AUTO] Telegram Proxy autostart")
            except Exception as e:
                print("[AUTO] TG Proxy autostart error:", e)

    if start_minimized:
        splash.close()
        win._hide_to_tray()
        # Автозапуск модулей даже в свёрнутом режиме
        if autostart_zapret and autostart_zapret_preset:
            try:
                from app_paths import ZAPRET_DIR
                from page_zapret import _save_ver, _get_versions, _is_running, _fn_start
                from worker import Worker
                
                versions = _get_versions()
                if versions and not _is_running():
                    ver = versions[0]
                    bat_path = str(ZAPRET_DIR / ver / autostart_zapret_preset)
                    from pathlib import Path
                    if Path(bat_path).exists():
                        _save_ver(ver)
                        ver_dir = str(ZAPRET_DIR / ver)
                        worker = Worker(_fn_start, bat_path, ver_dir)
                        worker.start()
            except Exception:
                pass
        if autostart_tg_proxy:
            try:
                from page_tg_proxy import _find_exe, _is_running as tg_running
                exe = _find_exe()
                if exe and not tg_running():
                    import subprocess
                    subprocess.Popen([str(exe)], cwd=str(exe.parent))
            except Exception:
                pass
    else:
        QTimer.singleShot(1200, _show_main)

    # exec() для PyQt6, exec_() для PyQt5
    sys.exit(exec_app(app))


def _write_crash_log(exc: BaseException) -> Path:
    """Записывает traceback в файл рядом с приложением — иначе при
    запуске через .bat без паузы окно консоли мигает и закрывается,
    не давая прочитать причину сбоя."""
    import traceback
    import datetime

    log_path = BASE_DIR / "crash_log.txt"

    # УЛУЧШЕНИЕ: без ротации файл мог бы неограниченно расти при частых
    # перезапусках со сбоем. Если он раздулся больше 2 МБ — оставляем
    # только последнюю (самую свежую) треть содержимого.
    try:
        if log_path.exists() and log_path.stat().st_size > 2 * 1024 * 1024:
            old = log_path.read_text(encoding="utf-8", errors="replace")
            log_path.write_text(old[-(700 * 1024):], encoding="utf-8")
    except Exception:
        pass

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 60 + "\n")
        f.write("Сбой при запуске: {}\n".format(timestamp))
        f.write("Python: {}\n".format(sys.version))
        f.write("Платформа: {}\n".format(sys.platform))
        f.write("-" * 60 + "\n")
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
    return log_path


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        log_path = _write_crash_log(exc)
        print("\n[KUS Pro] Произошла ошибка при запуске.")
        print("Подробности записаны в: {}".format(log_path))
        print("-" * 60)
        import traceback
        traceback.print_exc()
        print("-" * 60)
        try:
            input("Нажмите Enter, чтобы закрыть окно...")
        except Exception:
            pass
        sys.exit(1)

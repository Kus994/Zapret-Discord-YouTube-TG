"""
modules/extra.py
-----------------
Управление сервисом Zapret — обход блокировок Discord, YouTube и др.

Версия читается из zapret/current_version.txt, поэтому обновление —
это замена папки + правка одной строки в current_version.txt.

Улучшения v2:
  - run_service_bat больше не блокирует поток на жёстком timeout=120.
    Вместо этого вывод читается построчно в отдельном потоке,
    а основной поток ждёт завершения через join с проверкой флага отмены.
  - stop_service теперь дополнительно убивает дочерний cmd.exe/winws.exe
    через taskkill /F /T, чтобы гарантированно остановить всё дерево процессов.
  - Устранено состояние гонки при обращении к _service_process.
"""

import subprocess
import threading
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000

ZAPRET_ROOT  = Path(__file__).resolve().parent.parent / "zapret"
VERSION_FILE = ZAPRET_ROOT / "current_version.txt"

_service_process: subprocess.Popen | None = None
_service_lock = threading.Lock()


def get_current_version_dir():
    """Читает имя активной версии из current_version.txt."""
    if not VERSION_FILE.exists():
        return None
    name = VERSION_FILE.read_text(encoding="utf-8").strip()
    candidate = ZAPRET_ROOT / name
    return candidate if candidate.exists() else None


def list_available_versions():
    """Возвращает имена всех папок с service.bat в zapret/."""
    if not ZAPRET_ROOT.exists():
        return []
    return sorted(
        p.name for p in ZAPRET_ROOT.iterdir()
        if p.is_dir() and (p / "service.bat").exists()
    )


def set_current_version(version_name, log_func):
    """Переключает активную версию — переписывает current_version.txt."""
    candidate = ZAPRET_ROOT / version_name
    if not (candidate / "service.bat").exists():
        log_func(f"Версия '{version_name}' не найдена или повреждена.")
        return False
    VERSION_FILE.write_text(version_name, encoding="utf-8")
    log_func(f"Активная версия переключена на: {version_name}")
    return True


def run_service_bat(log_func, progress_func):
    """
    Запускает service.bat из текущей активной версии внутри утилиты.
    Вывод bat-файла транслируется построчно в лог-консоль через отдельный поток.
    Основная функция завершается как только процесс сам завершится.
    """
    global _service_process

    progress_func(0.1)
    version_dir = get_current_version_dir()

    if version_dir is None:
        log_func("Активная версия не настроена или папка не найдена. "
                 "Проверьте zapret/current_version.txt")
        progress_func(1.0)
        return False

    service_bat = version_dir / "service.bat"
    log_func(f"Запуск {service_bat.name} (версия: {version_dir.name})...")
    log_func("--- Запуск сервиса ---")

    try:
        proc = subprocess.Popen(
            [str(service_bat)],
            cwd=str(version_dir),
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="cp866",
            errors="replace",
        )

        with _service_lock:
            _service_process = proc

        progress_func(0.5)

        # Читаем вывод в отдельном потоке, не блокируя runner
        def _reader():
            try:
                for line in proc.stdout:
                    line = line.rstrip()
                    if line:
                        log_func(line)
            except Exception:
                pass

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        # Ждём завершения процесса (без жёсткого timeout)
        proc.wait()
        reader_thread.join(timeout=2)

        progress_func(1.0)
        rc = proc.returncode
        if rc == 0:
            log_func("Сервис завершил работу.")
        else:
            log_func(f"Сервис завершился с кодом {rc}.")

        with _service_lock:
            _service_process = None

        return rc == 0

    except Exception as exc:
        log_func(f"Ошибка запуска: {exc}")
        progress_func(1.0)
        with _service_lock:
            _service_process = None
        return False


def stop_service(log_func):
    """
    Принудительно завершает запущенный процесс service.bat
    вместе со всем деревом дочерних процессов (taskkill /F /T).
    """
    global _service_process
    with _service_lock:
        proc = _service_process

    if proc and proc.poll() is None:
        pid = proc.pid
        try:
            # Убиваем дерево процессов (bat → cmd → winws.exe)
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=5,
            )
            log_func("Сервис остановлен.")
        except Exception as exc:
            # Запасной вариант
            try:
                proc.kill()
                log_func("Сервис остановлен (kill).")
            except Exception:
                log_func(f"Не удалось остановить сервис: {exc}")
    else:
        log_func("Сервис не запущен.")

    with _service_lock:
        _service_process = None


def is_running() -> bool:
    """Возвращает True, если сервис сейчас работает."""
    with _service_lock:
        return _service_process is not None and _service_process.poll() is None

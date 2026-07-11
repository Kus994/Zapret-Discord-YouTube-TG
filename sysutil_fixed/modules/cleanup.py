"""
modules/cleanup.py
-------------------
Модуль очистки системы.

  1. Очистка %TEMP% пользователя и C:/Windows/Temp.
  2. Опционально: Temp-папки на всех подключённых дисках.
  3. Очистка кэша обновлений Windows (SoftwareDistribution/Download).
  4. Очистка корзины Windows.

Улучшения v2:
  - Параллельный подсчёт размеров папок (ThreadPoolExecutor).
  - Параллельное удаление поддиректорий внутри _safe_remove_tree.
  - Устранён circular import в run_full_cleanup.
  - Исправлен SHQueryRecycleBinW (принимает SHQUERYRBINFO, а не два отдельных c_uint64).
"""

import os
import shutil
import ctypes
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def _human_size(num_bytes: int) -> str:
    """Преобразует байты в читаемый вид (Б/КБ/МБ/ГБ)."""
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} ТБ"


def _dir_size(path: Path) -> int:
    """Быстро считает размер директории без рекурсии через os.scandir."""
    total = 0
    try:
        stack = [str(path)]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    for entry in it:
                        try:
                            if entry.is_file(follow_symlinks=False):
                                total += entry.stat(follow_symlinks=False).st_size
                            elif entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                        except (PermissionError, OSError):
                            pass
            except (PermissionError, OSError):
                pass
    except Exception:
        pass
    return total


def _safe_remove_tree(path: Path, log_func) -> int:
    """
    Рекурсивно удаляет содержимое директории, не трогая саму папку.
    Поддиректории удаляются параллельно (ThreadPoolExecutor).
    Возвращает суммарный размер удалённых данных в байтах.
    """
    freed = 0
    if not path.exists():
        return freed

    dirs_to_remove = []
    files_to_remove = []

    try:
        for entry in path.iterdir():
            try:
                if entry.is_dir() and not entry.is_symlink():
                    dirs_to_remove.append(entry)
                else:
                    files_to_remove.append(entry)
            except (PermissionError, OSError):
                pass
    except (PermissionError, OSError) as exc:
        log_func(f"  [нет доступа] {path}: {exc.__class__.__name__}")
        return freed

    # Файлы удаляем сразу
    for entry in files_to_remove:
        try:
            size = entry.stat().st_size
            entry.unlink(missing_ok=True)
            freed += size
        except (PermissionError, OSError) as exc:
            log_func(f"  [пропущено] {entry.name}: {exc.__class__.__name__}")

    # Папки: сначала считаем размер параллельно, потом удаляем
    if dirs_to_remove:
        sizes = {}
        with ThreadPoolExecutor(max_workers=min(8, len(dirs_to_remove))) as pool:
            future_to_entry = {pool.submit(_dir_size, e): e for e in dirs_to_remove}
            for future in as_completed(future_to_entry):
                entry = future_to_entry[future]
                try:
                    sizes[entry] = future.result()
                except Exception:
                    sizes[entry] = 0

        def _remove_dir(entry):
            try:
                shutil.rmtree(entry, ignore_errors=True)
                return sizes.get(entry, 0)
            except Exception:
                return 0

        with ThreadPoolExecutor(max_workers=min(8, len(dirs_to_remove))) as pool:
            futures = [pool.submit(_remove_dir, e) for e in dirs_to_remove]
            for future in as_completed(futures):
                try:
                    freed += future.result()
                except Exception:
                    pass

    return freed


def _get_all_drives() -> list:
    """Возвращает список корневых путей всех доступных дисков (Windows)."""
    drives = []
    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:\\")
        if drive.exists():
            drives.append(drive)
    return drives


def clean_temp_folders(log_func, progress_func, include_all_disks: bool = True) -> int:
    """Очищает Temp-папки: пользовательский %TEMP%, C:\\Windows\\Temp
    и (опционально) аналогичные папки на всех остальных дисках."""
    total_freed = 0

    targets = [
        Path(os.environ.get("TEMP", "")),
        Path(os.environ.get("WINDIR", "C:\\Windows")) / "Temp",
    ]

    if include_all_disks:
        windir_drive = Path(os.environ.get("WINDIR", "C:\\Windows")).drive + "\\"
        for drive in _get_all_drives():
            if str(drive).upper() == windir_drive.upper():
                continue
            for sub in ("Temp", "tmp"):
                candidate = drive / sub
                if candidate.exists():
                    targets.append(candidate)

    # Убираем дубликаты и несуществующие
    seen = set()
    unique_targets = []
    for t in targets:
        if t and t not in seen:
            seen.add(t)
            unique_targets.append(t)
    targets = unique_targets

    log_func(f"Поиск временных файлов ({len(targets)} папок)...")
    progress_func(0.05)

    for i, target in enumerate(targets):
        if not target.exists():
            continue
        log_func(f"Очистка: {target}")
        freed = _safe_remove_tree(target, log_func)
        total_freed += freed
        log_func(f"  Освобождено: {_human_size(freed)}")
        progress_func(0.05 + 0.45 * (i + 1) / max(len(targets), 1))

    return total_freed


def clean_update_cache(log_func, progress_func) -> int:
    """
    Очищает кэш загруженных файлов Windows Update.
    Требует прав администратора и временной остановки службы wuauserv.
    """
    log_func("Остановка службы Windows Update (wuauserv)...")
    progress_func(0.55)
    os.system("net stop wuauserv >nul 2>&1")

    cache_path = Path(os.environ.get("WINDIR", "C:\\Windows")) / "SoftwareDistribution" / "Download"
    freed = 0
    if cache_path.exists():
        log_func(f"Очистка кэша обновлений: {cache_path}")
        freed = _safe_remove_tree(cache_path, log_func)
        log_func(f"  Освобождено: {_human_size(freed)}")
    else:
        log_func("  Кэш обновлений не найден, пропуск.")

    progress_func(0.75)
    log_func("Запуск службы Windows Update обратно...")
    os.system("net start wuauserv >nul 2>&1")

    return freed


def empty_recycle_bin(log_func, progress_func) -> bool:
    """Очищает корзину Windows через WinAPI SHEmptyRecycleBinW."""
    log_func("Очистка корзины...")
    progress_func(0.90)
    try:
        SHERB_NOCONFIRMATION = 0x00000001
        SHERB_NOPROGRESSUI  = 0x00000002
        SHERB_NOSOUND       = 0x00000004
        flags = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        log_func("  Корзина очищена.")
        return True
    except Exception as exc:
        log_func(f"  Ошибка очистки корзины: {exc}")
        return False


def clean_prefetch(log_func, progress_func) -> int:
    """Очищает папку Prefetch (требует прав администратора)."""
    windir = Path(os.environ.get("WINDIR", "C:\\Windows"))
    pf = windir / "Prefetch"
    freed = 0
    if pf.exists():
        log_func(f"Очистка Prefetch: {pf}")
        freed = _safe_remove_tree(pf, log_func)
        log_func(f"  Освобождено: {_human_size(freed)}")
    else:
        log_func("  Папка Prefetch не найдена.")
    return freed


def run_full_cleanup(log_func, progress_func,
                     include_update_cache: bool = True,
                     include_all_disks: bool = True,
                     clean_prefetch: bool = False):
    """
    Главная точка входа модуля.
    Выполняет полный цикл очистки и выводит итоговую сводку.
    """
    log_func("=== Запуск очистки системы ===")
    progress_func(0.0)

    total = 0
    total += clean_temp_folders(log_func, progress_func, include_all_disks=include_all_disks)

    if include_update_cache:
        total += clean_update_cache(log_func, progress_func)
    else:
        progress_func(0.75)

    # Исправлен circular import: вызываем локальную функцию напрямую
    if clean_prefetch:
        from modules import cleanup as _cleanup_mod
        total += _cleanup_mod.clean_prefetch(log_func, progress_func)

    empty_recycle_bin(log_func, progress_func)

    progress_func(1.0)
    log_func(f"=== Готово. Всего освобождено: {_human_size(total)} ===")
    return total


def estimate_junk_size(log_func, progress_func) -> int:
    """
    Оценивает объём мусора без удаления — параллельный подсчёт.
    """
    log_func("Оценка объёма временных файлов (без удаления)...")
    progress_func(0.05)

    targets = [
        Path(os.environ.get("TEMP", "")),
        Path(os.environ.get("WINDIR", "C:\\Windows")) / "Temp",
    ]
    for letter in string.ascii_uppercase:
        d = Path(f"{letter}:\\")
        if d.exists():
            for sub in ("Temp", "tmp"):
                c = d / sub
                if c.exists():
                    targets.append(c)

    targets = [t for t in targets if t and t.exists()]

    # Параллельный подсчёт размеров
    total = 0
    results = {}
    with ThreadPoolExecutor(max_workers=min(8, len(targets) or 1)) as pool:
        future_to_path = {pool.submit(_dir_size, t): t for t in targets}
        done = 0
        for future in as_completed(future_to_path):
            t = future_to_path[future]
            done += 1
            try:
                size = future.result()
                results[t] = size
                log_func(f"  {t}: {_human_size(size)}")
                total += size
            except Exception:
                log_func(f"  {t}: [нет доступа]")
            progress_func(0.05 + 0.7 * done / max(len(targets), 1))

    # Корзина
    try:
        class SHQUERYRBINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint32),
                        ("i64Size", ctypes.c_int64),
                        ("i64NumItems", ctypes.c_int64)]
        info = SHQUERYRBINFO()
        info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
        ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
        log_func(f"  Корзина: {_human_size(info.i64Size)}")
        total += info.i64Size
    except Exception:
        pass

    # Кэш обновлений
    try:
        cache_path = Path(os.environ.get("WINDIR", "C:\\Windows")) / "SoftwareDistribution" / "Download"
        if cache_path.exists():
            size = _dir_size(cache_path)
            log_func(f"  Кэш обновлений: {_human_size(size)}")
            total += size
    except Exception:
        pass

    progress_func(1.0)
    log_func(f">>> Итого можно освободить примерно: {_human_size(total)}")
    return total

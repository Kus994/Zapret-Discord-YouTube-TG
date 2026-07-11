"""
modules/cleanup.py
-------------------
Модуль очистки системы.

  1. Очистка %TEMP% пользователя и C:/Windows/Temp.
  2. Опционально: Temp-папки на всех подключённых дисках.
  3. Очистка кэша обновлений Windows (SoftwareDistribution/Download).
  4. Очистка корзины Windows.
"""

import os
import shutil
import ctypes
import string
from pathlib import Path


def human_size(num_bytes: int) -> str:
    """Преобразует байты в читаемый вид (Б/КБ/МБ/ГБ)."""
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} ТБ"


def _safe_remove_tree(path: Path, log_func) -> int:
    """
    Рекурсивно удаляет содержимое директории, не трогая саму папку.
    Возвращает суммарный размер удалённых данных в байтах.
    """
    freed = 0
    if not path.exists():
        return freed

    for entry in path.iterdir():
        try:
            if entry.is_dir() and not entry.is_symlink():
                size = sum(
                    f.stat().st_size for f in entry.rglob("*") if f.is_file()
                )
                shutil.rmtree(entry, ignore_errors=True)
                freed += size
            else:
                size = entry.stat().st_size
                entry.unlink(missing_ok=True)
                freed += size
        except (PermissionError, OSError) as exc:
            log_func(f"  [пропущено] {entry.name}: {exc.__class__.__name__}")
    return freed


def _get_all_drives() -> list:
    """Возвращает список корневых путей всех доступных дисков (Windows)."""
    drives = []
    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:\\")
        if drive.exists():
            drives.append(drive)
    return drives


def clean_temp_folders(log_func, progress_func, include_all_disks: bool = True,
                       include_user_temp: bool = True, include_system_temp: bool = True) -> int:
    """Очищает Temp-папки: пользовательский %TEMP%, C:\\Windows\\Temp
    и (опционально) аналогичные папки на всех остальных дисках.

    include_user_temp / include_system_temp позволяют по отдельности
    отключить очистку пользовательского %TEMP% и системного
    C:\\Windows\\Temp — раньше эти два пункта были чекбоксами в UI,
    но игнорировались самой функцией."""
    total_freed = 0

    targets = []
    if include_user_temp:
        temp_path = Path(os.environ.get("TEMP", ""))
        if temp_path and temp_path.exists():
            targets.append(temp_path)
    if include_system_temp:
        sys_temp = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Temp"
        if sys_temp.exists():
            targets.append(sys_temp)

    if include_all_disks:
        windir_drive = Path(os.environ.get("WINDIR", "C:\\Windows")).drive
        for drive in _get_all_drives():
            if str(drive).upper() == windir_drive.upper():
                continue  # уже добавили выше
            # Типичные Temp-папки на дополнительных дисках.
            # ПРИМЕЧАНИЕ: $Recycle.Bin сюда намеренно не входит — корзину
            # чистит empty_recycle_bin() через SHEmptyRecycleBinW
            # (корректно, через Shell API), а не прямым удалением файлов
            # из служебной папки корзины, где вручную легко повредить
            # системные метаданные.
            for sub in ("Temp", "tmp"):
                candidate = drive / sub
                if candidate.exists():
                    targets.append(candidate)

    log_func(f"Поиск временных файлов ({len(targets)} папок)...")
    progress_func(0.05)

    for i, target in enumerate(targets):
        if not target or not target.exists():
            continue
        log_func(f"Очистка: {target}")
        freed = _safe_remove_tree(target, log_func)
        total_freed += freed
        log_func(f"  Освобождено: {human_size(freed)}")
        progress_func(0.05 + 0.45 * (i + 1) / max(len(targets), 1))

    return total_freed


def clean_update_cache(log_func, progress_func) -> int:
    """
    Очищает кэш загруженных файлов Windows Update.
    Требует прав администратора и временной остановки службы wuauserv.
    """
    import subprocess
    CREATE_NO_WINDOW = 0x08000000

    log_func("Остановка службы Windows Update (wuauserv)...")
    progress_func(0.55)
    try:
        subprocess.run(
            ["net", "stop", "wuauserv"],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=30,
        )
    except Exception:
        pass

    cache_path = Path(os.environ.get("WINDIR", "C:\\Windows")) / "SoftwareDistribution" / "Download"
    freed = 0
    if cache_path.exists():
        log_func(f"Очистка кэша обновлений: {cache_path}")
        freed = _safe_remove_tree(cache_path, log_func)
        log_func(f"  Освобождено: {human_size(freed)}")
    else:
        log_func("  Кэш обновлений не найден, пропуск.")

    progress_func(0.75)
    log_func("Запуск службы Windows Update обратно...")
    try:
        subprocess.run(
            ["net", "start", "wuauserv"],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=30,
        )
    except Exception:
        pass

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


def run_full_cleanup(log_func, progress_func,
                     include_update_cache: bool = True,
                     include_all_disks: bool = True,
                     clean_prefetch_flag: bool = False,
                     include_user_temp: bool = True,
                     include_system_temp: bool = True,
                     include_recycle_bin: bool = True):
    """
    Главная точка входа модуля.
    Выполняет полный цикл очистки и выводит итоговую сводку.
    """
    log_func("=== Запуск очистки системы ===")
    progress_func(0.0)

    total = 0
    total += clean_temp_folders(
        log_func, progress_func,
        include_all_disks=include_all_disks,
        include_user_temp=include_user_temp,
        include_system_temp=include_system_temp,
    )

    if include_update_cache:
        total += clean_update_cache(log_func, progress_func)
    else:
        progress_func(0.75)

    if clean_prefetch_flag:
        clean_prefetch(log_func, progress_func)

    if include_recycle_bin:
        empty_recycle_bin(log_func, progress_func)
    else:
        log_func("Очистка корзины отключена — пропуск.")
        progress_func(0.95)

    progress_func(1.0)
    log_func(f"=== Готово. Всего освобождено: {human_size(total)} ===")
    return total


def estimate_junk_size(log_func, progress_func) -> int:
    """Оценивает объём мусора без удаления — только подсчёт."""
    log_func("Оценка объёма временных файлов (без удаления)...")
    progress_func(0.05)
    total = 0
    targets = []
    temp_path = Path(os.environ.get("TEMP", ""))
    if temp_path.exists():
        targets.append(temp_path)
    sys_temp = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Temp"
    if sys_temp.exists():
        targets.append(sys_temp)
    for letter in string.ascii_uppercase:
        d = Path(f"{letter}:\\")
        if d.exists():
            for sub in ("Temp", "tmp"):
                c = d / sub
                if c.exists():
                    targets.append(c)

    for i, t in enumerate(targets):
        if not t or not t.exists():
            continue
        try:
            size = sum(f.stat().st_size for f in t.rglob("*") if f.is_file())
            log_func(f"  {t}: {human_size(size)}")
            total += size
        except Exception:
            log_func(f"  {t}: [нет доступа]")
        progress_func(0.05 + 0.7 * (i + 1) / max(len(targets), 1))

    # ФИКС: SHQueryRecycleBinW ожидает указатель на структуру
    # SHQUERYRBINFO с ЗАРАНЕЕ выставленным полем cbSize (так WinAPI
    # проверяет версию структуры) — раньше сюда передавался голый
    # ctypes.c_uint64, из-за чего вызов почти наверняка завершался
    # ошибкой, которая тихо проглатывалась в except Exception: pass, и
    # строка "Корзина: ..." в оценке объёма никогда не показывалась.
    try:
        class _SHQUERYRBINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint32),
                ("i64Size", ctypes.c_int64),
                ("i64NumItems", ctypes.c_int64),
            ]

        rb_info = _SHQUERYRBINFO()
        rb_info.cbSize = ctypes.sizeof(_SHQUERYRBINFO)
        # pszRootPath=None -> суммарно по всем дискам/корзинам сразу.
        ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(rb_info))
        log_func(f"  Корзина: {human_size(rb_info.i64Size)}")
        total += rb_info.i64Size
    except Exception:
        pass

    # Кэш обновлений
    try:
        cache_path = Path(os.environ.get("WINDIR", "C:\\Windows")) / "SoftwareDistribution" / "Download"
        if cache_path.exists():
            size = sum(f.stat().st_size for f in cache_path.rglob("*") if f.is_file())
            log_func(f"  Кэш обновлений: {human_size(size)}")
            total += size
    except Exception:
        pass

    progress_func(1.0)
    log_func(f">>> Итого можно освободить примерно: {human_size(total)}")
    return total


def clean_prefetch(log_func, progress_func) -> int:
    """Очищает папку Prefetch (требует прав администратора)."""
    windir = Path(os.environ.get("WINDIR", "C:\\Windows"))
    pf = windir / "Prefetch"
    freed = 0
    if pf.exists():
        log_func(f"Очистка Prefetch: {pf}")
        freed = _safe_remove_tree(pf, log_func)
        log_func(f"  Освобождено: {human_size(freed)}")
    else:
        log_func("  Папка Prefetch не найдена.")
    return freed


# ── Кэш браузеров ────────────────────────────────────────────────────── #

# Профили браузеров на базе Chromium хранят кэш в одной и той же
# относительной структуре (Cache / Code Cache) внутри каталога профиля —
# поэтому достаточно знать только базовый AppData-путь каждого браузера.
_CHROMIUM_BROWSERS = {
    "Google Chrome":  Path("Google") / "Chrome" / "User Data",
    "Microsoft Edge":  Path("Microsoft") / "Edge" / "User Data",
    "Brave":           Path("BraveSoftware") / "Brave-Browser" / "User Data",
    "Opera":           Path("Opera Software") / "Opera Stable",
    "Yandex Browser":  Path("Yandex") / "YandexBrowser" / "User Data",
}

_CHROMIUM_CACHE_SUBDIRS = ("Cache", "Code Cache", "GPUCache")


def _chromium_cache_dirs(base: Path):
    """Находит подкаталоги Cache/Code Cache/GPUCache во всех профилях
    браузера (Default, Profile 1, Profile 2, ...)."""
    if not base.exists():
        return []
    dirs = []
    # base сам может быть профилем (Opera) или содержать профили (Chrome/Edge)
    candidates = [base] + [p for p in base.iterdir() if p.is_dir()] if base.is_dir() else []
    for prof in candidates:
        for sub in _CHROMIUM_CACHE_SUBDIRS:
            c = prof / sub
            if c.exists():
                dirs.append(c)
    return dirs


def clean_browser_cache(log_func, progress_func, browsers=None) -> dict:
    """
    Очищает кэш (не куки, не пароли, не историю — только Cache/Code
    Cache/GPUCache) для установленных браузеров на базе Chromium и
    отдельно для Firefox.

    browsers: список имён браузеров для очистки (см. ключи
    _CHROMIUM_BROWSERS + "Mozilla Firefox"), либо None — почистить все
    найденные.

    ВАЖНО: перед очисткой браузер должен быть закрыт, иначе часть
    файлов кэша будет занята процессом и просто пропущена (это не
    ошибка — Chromium и Firefox both корректно создают кэш заново при
    следующем запуске).

    Возвращает {browser_name: freed_bytes}.
    """
    log_func("=== Очистка кэша браузеров ===")
    progress_func(0.0)

    local_appdata = Path(os.environ.get("LOCALAPPDATA", ""))
    appdata = Path(os.environ.get("APPDATA", ""))
    result = {}

    targets = []  # [(label, [Path, ...])]

    for label, rel in _CHROMIUM_BROWSERS.items():
        if browsers is not None and label not in browsers:
            continue
        base = local_appdata / rel
        dirs = _chromium_cache_dirs(base)
        if dirs:
            targets.append((label, dirs))

    if browsers is None or "Mozilla Firefox" in (browsers or []):
        ff_profiles = appdata / "Mozilla" / "Firefox" / "Profiles"
        ff_dirs = []
        if ff_profiles.exists():
            for prof in ff_profiles.iterdir():
                cache2 = appdata / "Mozilla" / "Firefox" / "Profiles" / prof.name / "cache2"
                if cache2.exists():
                    ff_dirs.append(cache2)
        if ff_dirs:
            targets.append(("Mozilla Firefox", ff_dirs))

    if not targets:
        log_func("Установленные браузеры с кэшем не найдены.", "WARN")
        progress_func(1.0)
        return result

    for i, (label, dirs) in enumerate(targets):
        log_func(f"Очистка кэша: {label} ({len(dirs)} директорий)")
        freed = 0
        for d in dirs:
            freed += _safe_remove_tree(d, log_func)
        result[label] = freed
        log_func(f"  {label}: освобождено {human_size(freed)}")
        progress_func((i + 1) / len(targets))

    total = sum(result.values())
    log_func(f"=== Готово. Всего освобождено из кэша браузеров: {human_size(total)} ===", "OK")
    return result


def detect_installed_browsers() -> list:
    """Возвращает список браузеров, для которых найден профиль с кэшем —
    используется UI, чтобы показать чекбоксы только для реально
    установленных браузеров, а не для всех потенциально поддерживаемых."""
    local_appdata = Path(os.environ.get("LOCALAPPDATA", ""))
    appdata = Path(os.environ.get("APPDATA", ""))
    found = []

    for label, rel in _CHROMIUM_BROWSERS.items():
        base = local_appdata / rel
        if _chromium_cache_dirs(base):
            found.append(label)

    ff_profiles = appdata / "Mozilla" / "Firefox" / "Profiles"
    if ff_profiles.exists() and any(ff_profiles.iterdir()):
        found.append("Mozilla Firefox")

    return found


# ── Поиск дублей файлов ──────────────────────────────────────────────── #

def find_duplicate_files(log_func, progress_func, root_dir: str,
                         min_size_bytes: int = 1024) -> list:
    """
    Ищет файлы-дубликаты внутри root_dir по содержимому (хеш SHA-256),
    с предварительной группировкой по размеру файла — это позволяет не
    хешировать заведомо разные по размеру файлы и не тратить время на
    каждый файл подряд.

    min_size_bytes отсекает совсем маленькие файлы (по умолчанию 1 КБ) —
    у них почти всегда множество случайных совпадений (пустые файлы,
    однострочные конфиги), которые не дают реальной экономии места.

    Возвращает список групп:
    [{"hash": ..., "size": ..., "files": [path, ...], "wasted": ...}, ...]
    отсортированный по объёму "лишнего" места (wasted) по убыванию.
    """
    import hashlib

    root = Path(root_dir)
    if not root.exists() or not root.is_dir():
        log_func(f"Папка не найдена: {root_dir}", "ERR")
        return []

    log_func(f"Поиск дублей в «{root_dir}»…")
    progress_func(0.0)

    # Шаг 1: группировка по размеру (дешёвая операция)
    by_size = {}
    all_files = []
    try:
        all_files = [f for f in root.rglob("*") if f.is_file()]
    except (PermissionError, OSError) as exc:
        log_func(f"Ошибка чтения директории: {exc}", "ERR")
        return []

    log_func(f"Найдено файлов: {len(all_files)}. Группировка по размеру...")
    progress_func(0.1)

    for f in all_files:
        try:
            size = f.stat().st_size
        except OSError:
            continue
        if size < min_size_bytes:
            continue
        by_size.setdefault(size, []).append(f)

    # Шаг 2: хешируем только те размеры, где есть ≥2 файла-кандидата —
    # уникальные по размеру файлы точно не дубли, хешировать их незачем.
    candidates = {size: files for size, files in by_size.items() if len(files) > 1}
    total_to_hash = sum(len(v) for v in candidates.values())

    log_func(f"Файлов-кандидатов на дубликат (по размеру): {total_to_hash}")
    progress_func(0.2)

    by_hash = {}
    hashed = 0

    def _file_hash(path, block_size=65536):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(block_size), b""):
                h.update(block)
        return h.hexdigest()

    for size, files in candidates.items():
        for f in files:
            try:
                digest = _file_hash(f)
                by_hash.setdefault((size, digest), []).append(f)
            except (PermissionError, OSError):
                pass
            hashed += 1
            if total_to_hash:
                progress_func(0.2 + 0.75 * hashed / total_to_hash)

    groups = []
    for (size, digest), files in by_hash.items():
        if len(files) > 1:
            groups.append({
                "hash": digest,
                "size": size,
                "files": [str(f) for f in files],
                "wasted": size * (len(files) - 1),
            })

    groups.sort(key=lambda g: g["wasted"], reverse=True)

    total_wasted = sum(g["wasted"] for g in groups)
    progress_func(1.0)
    log_func(
        f"Найдено групп дублей: {len(groups)}. "
        f"Потенциально лишнее место: {human_size(total_wasted)}",
        "OK"
    )
    return groups


def delete_duplicate_files(log_func, progress_func, files_to_delete: list) -> int:
    """
    Удаляет конкретный список путей (обычно — все файлы группы дублей,
    кроме одного «оригинала», который UI оставляет пользователю выбрать).
    Возвращает суммарный размер удалённых файлов в байтах.

    Удаляет файлы напрямую (а не в корзину) — это совпадает с поведением
    остальных функций модуля (clean_temp_folders и т.д.), которые тоже
    удаляют безвозвратно. UI обязан запросить подтверждение перед
    вызовом — как и для остальных деструктивных операций приложения.
    """
    freed = 0
    total = len(files_to_delete)
    for i, path_str in enumerate(files_to_delete):
        p = Path(path_str)
        try:
            if p.exists():
                size = p.stat().st_size
                p.unlink()
                freed += size
                log_func(f"Удалено: {p}")
            else:
                log_func(f"Файл уже не существует: {p}", "WARN")
        except (PermissionError, OSError) as exc:
            log_func(f"Не удалось удалить {p}: {exc}", "WARN")
        progress_func((i + 1) / max(total, 1))

    log_func(f"Удаление завершено. Освобождено: {human_size(freed)}", "OK")
    return freed

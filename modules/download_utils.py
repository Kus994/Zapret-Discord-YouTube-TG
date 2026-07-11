"""
modules/download_utils.py
-------------------------
Общая логика скачивания файлов с GitHub API.
Используется в auto_updater.py и downloader.py (DRY).
"""

import ssl
import json
import zipfile
import urllib.request
import urllib.error
from pathlib import Path


def ssl_ctx():
    """
    Контекст SSL с ПОЛНОЙ проверкой сертификата и хоста.
    Используем certifi, если он установлен — на некоторых сборках Windows
    (особенно "голый" embeddable Python) системное хранилище сертификатов
    бывает пустым/неполным, из-за чего verify падает даже для легитимных
    хостов. certifi даёт собственный, актуальный набор корневых CA.
    """
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def get_latest_release(owner: str, repo: str, asset_suffix: str,
                       retries: int = 2):
    """
    Возвращает (url, filename, tag) последнего релиза с GitHub.
    asset_suffix: ".zip", "_windows.exe" и т.д.
    retries — количество повторных попыток при сетевой ошибке.
    """
    api = "https://api.github.com/repos/{}/{}/releases/latest".format(owner, repo)
    headers = {
        "User-Agent": "KUS-Pro/2.0",
        "Accept": "application/vnd.github+json",
    }

    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(api, headers=headers)
            with urllib.request.urlopen(req, timeout=20, context=ssl_ctx()) as r:
                data = json.loads(r.read().decode())

            tag = data.get("tag_name", "")
            assets = data.get("assets", [])

            suffix_lower = asset_suffix.lower()
            for a in assets:
                if a["name"].lower().endswith(suffix_lower):
                    return a["browser_download_url"], a["name"], tag

            return data.get("zipball_url", ""), "{}-{}.zip".format(repo, tag), tag

        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            last_err = e
            if attempt < retries:
                import time
                time.sleep(1 * (attempt + 1))
                continue
            break

    raise ConnectionError(
        "Не удалось получить релиз {}/{} после {} попыток: {}".format(
            owner, repo, retries + 1, last_err)
    )


def download_file(url: str, dest: str, progress_cb=None):
    """Скачивает файл по URL с прогресс-колбэком (0.0..1.0)."""
    req = urllib.request.Request(url, headers={"User-Agent": "KUS-Pro/2.0"})
    with urllib.request.urlopen(req, timeout=120, context=ssl_ctx()) as r:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        with open(dest, "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress_cb and total:
                    progress_cb(done / total * 0.85)


def extract_zip(zpath: str, dest_dir: str, progress_cb=None):
    """Распаковывает ZIP с защитой от Zip Slip."""
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        tops = {n.split("/")[0] for n in names if n.strip("/")}
        strip = (tops.pop() + "/") if len(tops) == 1 else ""
        dest = Path(dest_dir).resolve()
        for i, m in enumerate(names):
            tname = m[len(strip):] if strip and m.startswith(strip) else m
            if not tname:
                continue
            tpath = (dest / tname).resolve()
            # Защита от Zip Slip
            if dest not in tpath.parents and tpath != dest:
                if progress_cb:
                    progress_cb(0.85 + i / max(len(names), 1) * 0.15)
                continue
            if m.endswith("/"):
                tpath.mkdir(parents=True, exist_ok=True)
            else:
                tpath.parent.mkdir(parents=True, exist_ok=True)
                with z.open(m) as src, open(tpath, "wb") as dst:
                    dst.write(src.read())
            if progress_cb:
                progress_cb(0.85 + i / max(len(names), 1) * 0.15)

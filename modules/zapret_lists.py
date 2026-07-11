"""
modules/zapret_lists.py
----------------------
Интеграция с комьюнити-списками для Zapret.
Автоматическое обновление списков доменов.
"""

import json
import urllib.request
import ssl
from pathlib import Path
from datetime import datetime

try:
    from app_paths import ZAPRET_DIR
except ImportError:
    ZAPRET_DIR = Path(__file__).parent.parent / "zapret"


def _ssl_ctx():
    """SSL контекст."""
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    return ctx


# GitHub репозитории с комьюнити-списками
COMMUNITY_REPOS = [
    {
        "name": "Zapret Community Lists",
        "owner": "Flowseal",
        "repo": "zapret-discord-youtube",
        "file": "list-general-user.txt",
        "description": "Основной список доменов",
    },
    {
        "name": "Zapret Blocklist",
        "owner": "bol-van",
        "repo": "zapret",
        "file": "winws/exclude.txt",
        "description": "Список исключений",
    },
]


def get_available_lists() -> list:
    """Возвращает список доступных комьюнити-списков."""
    return COMMUNITY_REPOS


def check_list_updates() -> list:
    """Проверяет обновления комьюнити-списков."""
    results = []

    for repo_info in COMMUNITY_REPOS:
        try:
            api_url = "https://api.github.com/repos/{}/{}/commits?path={}&per_page=1".format(
                repo_info["owner"], repo_info["repo"], repo_info["file"]
            )
            req = urllib.request.Request(api_url, headers={"User-Agent": "KUS-Pro/1.0"})

            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ctx = ssl.create_default_context()

            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                commits = json.loads(r.read().decode())

            if commits:
                last_commit = commits[0]
                commit_date = last_commit.get("commit", {}).get("committer", {}).get("date", "")
                results.append({
                    "name": repo_info["name"],
                    "repo": repo_info["repo"],
                    "last_update": commit_date,
                    "available": True,
                })
            else:
                results.append({
                    "name": repo_info["name"],
                    "repo": repo_info["repo"],
                    "last_update": "Нет данных",
                    "available": False,
                })
        except Exception as e:
            results.append({
                "name": repo_info["name"],
                "repo": repo_info["repo"],
                "last_update": "Ошибка",
                "available": False,
                "error": str(e)[:50],
            })

    return results


def download_list(repo_info: dict, dest_dir: str) -> dict:
    """Скачивает комьюнити-список."""
    try:
        api_url = "https://api.github.com/repos/{}/{}/contents/{}".format(
            repo_info["owner"], repo_info["repo"], repo_info["file"]
        )
        req = urllib.request.Request(api_url, headers={"User-Agent": "KUS-Pro/1.0"})

        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = ssl.create_default_context()

        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            data = json.loads(r.read().decode())

        if "content" in data:
            import base64
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")

            dest_path = Path(dest_dir) / repo_info["file"]
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text(content, encoding="utf-8")

            return {
                "success": True,
                "path": str(dest_path),
                "size": len(content),
                "message": "Список сохранён: {}".format(dest_path),
            }
        else:
            return {"success": False, "error": "Нет данных в ответе"}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}

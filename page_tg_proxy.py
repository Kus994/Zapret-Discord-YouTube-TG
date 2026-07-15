"""
page_tg_proxy.py — KUS Pro
Telegram MTProto прокси через TgWsProxy.
Скачивает готовый .exe с GitHub (TgWsProxy_windows.exe),
запускает его как системный трей-процесс.
Порт по умолчанию: 1443 (MTProto), Secret — из логов приложения.
"""

import os
import sys

from qt_compat import *

import socket
import subprocess
import threading
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QSizePolicy, QPushButton, QGridLayout, QApplication,
)
from PyQt5.QtGui import QClipboard
from PyQt5.QtCore import Qt, QTimer

from base_page import BasePage
from app_paths import BASE_DIR, TG_PROXY_DIR
from config_manager import load_config
from theme import ACCENT, ACCENT_DIM, TEXT_DIM, INFO

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

EXE_NAME = "TgWsProxy_windows.exe"
EXE_PATH = TG_PROXY_DIR / EXE_NAME

GH_OWNER = "Flowseal"
GH_REPO  = "tg-ws-proxy"
EXE_ASSET_SUFFIX = "_windows.exe"

_proxy_proc: Optional[subprocess.Popen] = None
_proxy_lock = threading.Lock()

# ACCENT, ACCENT_DIM, TEXT_DIM imported from theme above
TEXT_MID = "#a09888"
BG_CARD = "#1e1c1a"
BG_DARK = "#161412"
BORDER = "#2e2a26"
GREEN = "#4caf7d"
RED = "#e05252"

# Типичные порты для MTProto прокси
COMMON_PORTS = [8080, 1443, 443, 8443, 1080, 3128, 8118, 9050]


def _is_port_free(port):
    """Проверяет, свободен ли порт."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        return result != 0  # True если свободен
    except Exception:
        return True


def _find_available_port(preferred=8080):
    """Находит лучший свободный порт для MTProto прокси.
    Приоритет: preferred → типичные порты → рандомный диапазон."""
    # 1. Проверяем предпочтительный порт
    if _is_port_free(preferred):
        return preferred

    # 2. Проверяем типичные порты
    for port in COMMON_PORTS:
        if port != preferred and _is_port_free(port):
            return port

    # 3. Ищем свободный в диапазоне 10000-10100
    for port in range(10000, 10100):
        if _is_port_free(port):
            return port

    return preferred  # Fallback


def _find_exe():
    """Ищет TgWsProxy*.exe в TG_PROXY_DIR."""
    if not TG_PROXY_DIR.exists():
        return None
    for pattern in ["TgWsProxy_windows.exe",
                    "TgWsProxy*.exe",
                    "*windows*.exe",
                    "*.exe"]:
        hits = list(TG_PROXY_DIR.glob(pattern))
        hits = [h for h in hits
                if "install" not in h.name.lower()
                and "setup" not in h.name.lower()]
        if hits:
            return hits[0]
    return None


def _is_running():
    with _proxy_lock:
        return _proxy_proc is not None and _proxy_proc.poll() is None


def _fn_start_exe(log_func, progress_func, exe_path: str):
    global _proxy_proc
    exe = Path(exe_path)
    if not exe.exists():
        log_func("EXE не найден: {}".format(exe_path), "ERR")
        return
    log_func("Запуск: {}".format(exe.name), "INFO")
    progress_func(0.3)

    # Авто-определение незанятого порта
    cfg = load_config()
    preferred_port = cfg.get("tg_proxy_port", 8080)
    available_port = _find_available_port(preferred_port)
    if available_port != preferred_port:
        log_func("Порт {} занят, выбран свободный: {}".format(preferred_port, available_port), "WARN")

    try:
        with _proxy_lock:
            _proxy_proc = subprocess.Popen(
                [str(exe)],
                cwd=str(exe.parent),
            )
        log_func("TgWsProxy запущен (PID: {})".format(_proxy_proc.pid), "OK")
        log_func("Приложение свернулось в системный трей.", "INFO")
        log_func("Порт MTProto: {}  |  Подключите Telegram вручную:".format(available_port), "INFO")
        log_func("  Настройки → Продвинутые → Тип подключения → Прокси", "INFO")
        log_func("  Тип: MTProto  |  Сервер: 127.0.0.1  |  Порт: {}".format(available_port), "INFO")
        log_func("  Secret: смотрите в трей-меню TgWsProxy → Настройки", "INFO")
        progress_func(0.6)
        _proxy_proc.wait()
        log_func("TgWsProxy завершён.", "WARN")
    except Exception as e:
        log_func("Ошибка запуска: {}".format(e), "ERR")
    finally:
        progress_func(1.0)
        with _proxy_lock:
            _proxy_proc = None


def _fn_stop_exe(log_func, progress_func):
    global _proxy_proc
    pid = None
    with _proxy_lock:
        proc_ref = _proxy_proc
    if proc_ref and proc_ref.poll() is None:
        pid = proc_ref.pid
        try:
            proc_ref.terminate()
            proc_ref.wait(timeout=5)
            log_func("TgWsProxy остановлен.", "OK")
        except Exception:
            try:
                proc_ref.kill()
                log_func("TgWsProxy принудительно остановлен.", "OK")
            except Exception:
                pass
    if pid:
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                creationflags=CREATE_NO_WINDOW, capture_output=True, timeout=5
            )
        except Exception:
            pass
    with _proxy_lock:
        _proxy_proc = None
    progress_func(1.0)


# ── Helper: styled QLabel ──────────────────────────────────────────────── #

def _label(text, size=13, color="#a09888", bold=False, align=AlignLeft):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color:{}; font-size:{}px; font-weight:{}; background:transparent;".format(
            color, size, "bold" if bold else "normal"
        )
    )
    lbl.setAlignment(align)
    lbl.setWordWrap(True)
    return lbl


def _sep():
    line = QFrame()
    line.setFrameShape(HLine)
    line.setStyleSheet("background:{}; max-height:1px;".format(BORDER))
    return line


def _config_block(lines):
    """Returns a styled frame that looks like a code/config block."""
    frame = QFrame()
    frame.setStyleSheet(
        "QFrame {{ background:{}; border:1px solid {}; border-radius:6px; padding:10px; }}".format(
            BG_DARK, BORDER
        )
    )
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(14, 10, 14, 10)
    lay.setSpacing(3)
    for text in lines:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color:{}; font-family:Consolas,'Courier New',monospace; font-size:12px; background:transparent;".format(
                ACCENT
            )
        )
        lay.addWidget(lbl)
    return frame


def _step_indicator(number):
    """Circle with a number inside."""
    lbl = QLabel(str(number))
    lbl.setFixedSize(28, 28)
    lbl.setAlignment(AlignCenter)
    lbl.setStyleSheet(
        "color:{}; font-size:13px; font-weight:bold; "
        "background:{}; border-radius:14px; border:1px solid {};".format(
            ACCENT, BG_DARK, ACCENT_DIM
        )
    )
    return lbl


# ══════════════════════════════════════════════════════════════════════════ #

class TgProxyPage(BasePage):
    PAGE_TITLE = "✈  Telegram Proxy"
    PAGE_SUB   = "MTProto-прокси для Telegram через WebSocket (TgWsProxy)"

    def build_ui(self):
        # Кэшируем конфиг один раз
        cfg = load_config()

        # ── 1. Status card ──────────────────────────────────────────── #
        status_card = self.card("Статус")
        status_card.setStyleSheet(
            "QFrame#card {{ border:1px solid {}; border-radius:8px; background:{}; }}".format(
                BORDER, BG_CARD
            )
        )
        self._status_row = QHBoxLayout()
        self._status_row.setSpacing(14)

        self._status_icon = QLabel("●")
        self._status_icon.setFixedSize(48, 48)
        self._status_icon.setAlignment(AlignCenter)
        self._status_icon.setStyleSheet(
            "color:{}; font-size:36px; background:{}; border-radius:24px;".format(RED, BG_DARK)
        )
        self._status_row.addWidget(self._status_icon)

        status_text_lay = QVBoxLayout()
        status_text_lay.setSpacing(2)
        self._status_title = QLabel("Остановлен")
        self._status_title.setStyleSheet(
            "color:{}; font-size:16px; font-weight:bold; background:transparent;".format(TEXT_DIM)
        )
        status_text_lay.addWidget(self._status_title)

        self._status_detail = QLabel("Прокси не активен")
        self._status_detail.setStyleSheet(
            "color:{}; font-size:12px; background:transparent;".format(TEXT_DIM)
        )
        status_text_lay.addWidget(self._status_detail)

        self._status_row.addLayout(status_text_lay)
        self._status_row.addStretch()
        status_card.lay.addLayout(self._status_row)
        self._content.addWidget(status_card)

        # ── 2. Installation card ────────────────────────────────────── #
        install_card = self.card("Установка TgWsProxy")
        install_card.setStyleSheet(
            "QFrame#card {{ border:1px solid {}; border-radius:8px; background:{}; }}".format(
                BORDER, BG_CARD
            )
        )

        install_desc = QLabel(
            "Standalone EXE-файл с GitHub. Python-зависимости не нужны.\n"
            "После запуска сворачивается в системный трей."
        )
        install_desc.setStyleSheet("color:{}; font-size:12px; background:transparent;".format(TEXT_DIM))
        install_desc.setWordWrap(True)
        install_card.lay.addWidget(install_desc)
        install_card.lay.addSpacing(4)

        dl_row = QHBoxLayout()
        dl_row.setSpacing(8)
        self._dl_btn = self._reg_btn(
            self.btn("⬇  Скачать TgWsProxy (.exe)", obj="btn_sec")
        )
        self._dl_btn.clicked.connect(self._download)
        dl_row.addWidget(self._dl_btn)

        self._open_btn = self.btn("📂  Открыть папку", obj="btn_sec")
        self._open_btn.clicked.connect(self._open_folder)
        dl_row.addWidget(self._open_btn)
        dl_row.addStretch()
        install_card.lay.addLayout(dl_row)

        self._file_info_label = _label("", size=11, color=TEXT_DIM)
        install_card.lay.addWidget(self._file_info_label)
        self._content.addWidget(install_card)

        # ── 3. Connection guide — visual steps ──────────────────────── #
        guide_card = self.card("Как подключить Telegram")
        guide_card.setStyleSheet(
            "QFrame#card {{ border:1px solid {}; border-radius:8px; background:{}; }}".format(
                BORDER, BG_CARD
            )
        )

        port = cfg.get("tg_proxy_port", 8080)
        steps = [
            ("Запустите прокси", "Нажмите «▶ Запустить» — TgWsProxy откроется в трее"),
            ("Откройте Telegram", "Настройки → Продвинутые настройки → Тип подключения"),
            ("Добавьте прокси", "Использовать прокси → Добавить прокси"),
            ("Настройте подключение", "Тип: MTProto  •  Сервер: 127.0.0.1  •  Порт: {}".format(port)),
            ("Введите Secret", "ПКМ на иконку TgWsProxy в трее → Скопировать ссылку"),
        ]

        for i, (title, detail) in enumerate(steps, 1):
            step_lay = QHBoxLayout()
            step_lay.setSpacing(12)
            step_lay.addWidget(_step_indicator(i))

            text_lay = QVBoxLayout()
            text_lay.setSpacing(1)
            text_lay.addWidget(_label(title, size=13, color="#d0c8b8", bold=True))
            text_lay.addWidget(_label(detail, size=11, color=TEXT_DIM))
            step_lay.addLayout(text_lay)
            step_lay.addStretch()
            guide_card.lay.addLayout(step_lay)

            if i < len(steps):
                guide_card.lay.addSpacing(2)

        self._content.addWidget(guide_card)

        # ── 4. Proxy configuration card ─────────────────────────────── #
        cfg_card = self.card("Параметры подключения")
        cfg_card.setStyleSheet(
            "QFrame#card {{ border:1px solid {}; border-radius:8px; background:{}; }}".format(
                BORDER, BG_CARD
            )
        )

        cfg_card.lay.addWidget(_label(
            "Используйте эти данные при настройке прокси в Telegram:",
            size=12, color=TEXT_DIM
        ))
        cfg_card.lay.addSpacing(4)

        port = cfg.get("tg_proxy_port", 8080)
        from modules.tg_proxy_health import get_secret_from_logs
        secret = get_secret_from_logs()
        secret_display = secret if secret else "(см. трей-меню TgWsProxy)"

        # dd-padding checkbox
        dd_row = QHBoxLayout()
        dd_row.setSpacing(8)
        self._dd_check = QPushButton("dd-padding")
        self._dd_check.setCheckable(True)
        self._dd_check.setChecked(False)
        self._dd_check.setFixedHeight(28)
        self._dd_check.setToolTip(
            "Random padding: добавляет 'dd' перед secret для маскировки\n"
            "размера пакетов (помогает против DPI-фильтров)"
        )
        self._dd_check.setStyleSheet(
            "QPushButton {{ color:{}; background:{}; border:1px solid {}; "
            "border-radius:4px; padding:2px 10px; font-size:11px; }}"
            "QPushButton:checked {{ color:{}; background:{}; border-color:{}; }}".format(
                TEXT_DIM, BG_DARK, BORDER, ACCENT, "#1a2a1a", ACCENT_DIM
            )
        )
        self._dd_check.clicked.connect(self._update_config_block)
        dd_row.addWidget(self._dd_check)
        dd_row.addStretch()
        cfg_card.lay.addLayout(dd_row)

        self._cfg_block = _config_block([
            "Server:    127.0.0.1",
            "Port:      {}".format(port),
            "Type:      MTProto",
            "Secret:    {}".format(secret_display),
        ])
        self._proxy_link_label = _label("", size=11, color=INFO)
        self._proxy_link_label.setOpenExternalLinks(True)
        self._proxy_link_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        cfg_card.lay.addWidget(self._proxy_link_label)
        self._update_proxy_link(port, secret)
        cfg_card.lay.addWidget(self._cfg_block)

        copy_row = QHBoxLayout()
        copy_row.setSpacing(8)
        self._copy_btn = QPushButton("📋  Копировать параметры")
        self._copy_btn.setStyleSheet(
            "QPushButton {{ color:{}; background:{}; border:1px solid {}; "
            "border-radius:5px; padding:6px 16px; font-size:12px; font-weight:bold; }}"
            "QPushButton:hover {{ background:{}; border-color:{}; }}".format(
                ACCENT, BG_DARK, ACCENT_DIM, "#2a2622", ACCENT
            )
        )
        self._copy_btn.setCursor(PointingHandCursor)
        self._copy_btn.clicked.connect(self._copy_config)
        copy_row.addWidget(self._copy_btn)
        copy_row.addStretch()
        cfg_card.lay.addLayout(copy_row)

        self._content.addWidget(cfg_card)

        # ── 5. Control panel ────────────────────────────────────────── #
        ctrl_card = self.card("Управление")
        ctrl_card.setStyleSheet(
            "QFrame#card {{ border:1px solid {}; border-radius:8px; background:{}; }}".format(
                BORDER, BG_CARD
            )
        )

        ctrl_lay = QHBoxLayout()
        ctrl_lay.setSpacing(10)

        self._btn_start = self.btn("▶  Запустить")
        self._btn_start.setFixedHeight(42)
        self._btn_start.setStyleSheet(
            "QPushButton {{ background:{}; color:#1a1816; border:none; border-radius:6px; "
            "font-size:14px; font-weight:bold; padding:0 24px; }}"
            "QPushButton:hover {{ background:{}; }}"
            "QPushButton:disabled {{ background:{}; color:#555; }}".format(
                ACCENT, ACCENT_DIM, "#3a3430"
            )
        )
        self._btn_start.setCursor(PointingHandCursor)
        self._btn_start.clicked.connect(self._start)
        ctrl_lay.addWidget(self._btn_start)

        self._btn_stop = self.btn("■  Остановить", obj="btn_danger")
        self._btn_stop.setFixedHeight(42)
        self._btn_stop.setStyleSheet(
            "QPushButton {{ background:{}; color:#fff; border:none; border-radius:6px; "
            "font-size:14px; font-weight:bold; padding:0 24px; }}"
            "QPushButton:hover {{ background:#c04040; }}"
            "QPushButton:disabled {{ background:#3a3430; color:#555; }}".format(RED)
        )
        self._btn_stop.setCursor(PointingHandCursor)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop)
        ctrl_lay.addWidget(self._btn_stop)

        port = cfg.get("tg_proxy_port", 8080)
        self._btn_test = self.btn("🔍  Тест порта {}".format(port), obj="btn_sec")
        self._btn_test.setFixedHeight(42)
        self._btn_test.setStyleSheet(
            "QPushButton {{ color:{}; background:{}; border:1px solid {}; "
            "border-radius:6px; font-size:13px; padding:0 20px; }}"
            "QPushButton:hover {{ background:{}; border-color:{}; }}".format(
                TEXT_MID, BG_DARK, BORDER, "#2a2622", TEXT_MID
            )
        )
        self._btn_test.setCursor(PointingHandCursor)
        self._btn_test.clicked.connect(self._test)
        ctrl_lay.addWidget(self._btn_test)

        ctrl_lay.addStretch()
        ctrl_card.lay.addLayout(ctrl_lay)

        # Health check row
        health_row = QHBoxLayout()
        health_row.setSpacing(8)

        self._health_status = QLabel("Статус не проверен")
        self._health_status.setStyleSheet(
            "color:{}; font-size:12px; background:transparent;".format(TEXT_DIM))
        health_row.addWidget(self._health_status)
        health_row.addStretch()

        btn_health = self._reg_btn(self.btn("Проверить здоровье", obj="btn_sec"))
        btn_health.setFixedHeight(34)
        btn_health.clicked.connect(self._check_health)
        health_row.addWidget(btn_health)

        btn_fix = self._reg_btn(self.btn("Авто-фикс", obj="btn_sec"))
        btn_fix.setFixedHeight(34)
        btn_fix.clicked.connect(self._auto_fix_media)
        health_row.addWidget(btn_fix)

        ctrl_card.lay.addLayout(health_row)
        self._content.addWidget(ctrl_card)

        # ── 6. MTProto info card ──────────────────────────────────────── #
        info_card = self.card("Справка: MTProto vs SOCKS5 vs VPN")
        info_card.setStyleSheet(
            "QFrame#card {{ border:1px solid {}; border-radius:8px; background:{}; }}".format(
                BORDER, BG_CARD
            )
        )

        info_rows = [
            ("MTProto Proxy", "Только Telegram", "Высокая для Telegram", "IP, время, трафик, метаданные", GREEN),
            ("SOCKS5", "Зависит от приложения", "Нет (нужна доп. настройка)", "IP, время, трафик", ACCENT),
            ("VPN", "Весь трафик устройства", "Зависит от протокола", "Многое зависит от сервиса", TEXT_DIM),
        ]
        header_lay = QHBoxLayout()
        for txt in ["Протокол", "Трафик", "Маскировка", "Что видит оператор"]:
            lbl = _label(txt, size=10, color=TEXT_DIM, bold=True)
            header_lay.addWidget(lbl)
        info_card.lay.addLayout(header_lay)

        for name, traffic, mask, sees, color in info_rows:
            row_lay = QHBoxLayout()
            row_lay.addWidget(_label(name, size=11, color=color, bold=True))
            row_lay.addWidget(_label(traffic, size=10, color=TEXT_DIM))
            row_lay.addWidget(_label(mask, size=10, color=TEXT_DIM))
            row_lay.addWidget(_label(sees, size=10, color=TEXT_DIM))
            info_card.lay.addLayout(row_lay)

        info_card.lay.addSpacing(6)
        info_card.lay.addWidget(_label(
            "MTProto не заменяет VPN и SOCKS5 — это точечный инструмент только для Telegram.\n"
            "DD-padding ('dd' перед secret) помогает против фильтров по размеру пакетов.\n"
            "Для чувствительных сценариев используйте VPN поверх MTProto.",
            size=10, color=TEXT_DIM
        ))
        self._content.addWidget(info_card)

        # Poll timer
        self._poll = QTimer(self)
        self._poll.timeout.connect(self._refresh_badge)
        self._poll.start(2000)

        self._check_installed()

    # ── Installed check ──────────────────────────────────────────────── #

    def _check_installed(self):
        exe = _find_exe()
        if exe:
            self.log("TgWsProxy найден: {}".format(exe), "OK")
            self._dl_btn.setText("✔  Переустановить")
            size_mb = exe.stat().st_size / (1024 * 1024)
            self._file_info_label.setText(
                "Файл: {}  |  Размер: {:.1f} MB".format(exe.name, size_mb)
            )
        else:
            self.log("TgWsProxy не найден в {}".format(TG_PROXY_DIR), "WARN")
            self.log("Нажмите «Скачать TgWsProxy (.exe)»", "INFO")
            self._file_info_label.setText("Файл не найден — нажмите «Скачать»")

    # ── Download ─────────────────────────────────────────────────────── #

    def _download(self):
        self._dl_btn.setEnabled(False)
        self.log("Поиск последнего релиза на GitHub...", "INFO")
        from downloader import DownloadWorker
        TG_PROXY_DIR.mkdir(parents=True, exist_ok=True)
        self._dl_w = DownloadWorker(
            dest_dir=str(TG_PROXY_DIR),
            owner=GH_OWNER,
            repo=GH_REPO,
            asset_suffix=EXE_ASSET_SUFFIX,
            parent=self,
        )
        self._dl_w.log.connect(self.log)
        self._dl_w.progress.connect(self.set_progress)
        self._dl_w.done.connect(self._on_dl_done)
        self._dl_w.start()

    def _on_dl_done(self, ok, msg):
        self.log(msg, "OK" if ok else "ERR")
        self._dl_btn.setEnabled(True)
        if ok:
            self._check_installed()

    # ── Open folder ──────────────────────────────────────────────────── #

    def _open_folder(self):
        TG_PROXY_DIR.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(["explorer", str(TG_PROXY_DIR)])
        except Exception:
            pass

    # ── Start / Stop / Test ──────────────────────────────────────────── #

    def _start(self):
        exe = _find_exe()
        if not exe:
            self.log("TgWsProxy не установлен. Нажмите «Скачать».", "ERR")
            return
        if _is_running():
            self.log("TgWsProxy уже запущен.", "WARN")
            return
        self._run_worker(_fn_start_exe, str(exe), on_done=self._refresh_badge)

    def _stop(self):
        self._run_worker(_fn_stop_exe, on_done=self._refresh_badge)

    def _test(self):
        from config_manager import load_config
        port = load_config().get("tg_proxy_port", 8080)
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=2)
            s.close()
            self.log("Порт {} открыт — TgWsProxy слушает ✓".format(port), "OK")
        except Exception as e:
            self.log("Порт {} закрыт: {} — запустите TgWsProxy".format(port, e), "ERR")

    # ── Copy config ──────────────────────────────────────────────────── #

    def _update_proxy_link(self, port, secret):
        """Обновляет deep link для быстрого подключения."""
        if secret:
            dd = self._dd_check.isChecked() if hasattr(self, '_dd_check') else False
            display_secret = "dd" + secret if dd else secret
            link = "https://t.me/proxy?server=127.0.0.1&port={}&secret={}".format(port, display_secret)
            self._proxy_link_label.setText(
                "Ссылка для подключения: {}".format(link)
            )
        else:
            self._proxy_link_label.setText(
                "Ссылка появится после запуска TgWsProxy (secret в трей-меню)"
            )

    def _update_config_block(self):
        """Обновляет config block с учётом dd-padding."""
        from config_manager import load_config
        from modules.tg_proxy_health import get_secret_from_logs
        port = load_config().get("tg_proxy_port", 8080)
        secret = get_secret_from_logs()
        dd = self._dd_check.isChecked()

        if secret:
            secret_display = ("dd" + secret) if dd else secret
        else:
            secret_display = "(см. трей-меню TgWsProxy)"

        # Rebuild config block
        parent = self._cfg_block.parentWidget().layout() if self._cfg_block.parentWidget() else None
        if parent:
            idx = parent.indexOf(self._cfg_block)
            if idx >= 0:
                new_block = _config_block([
                    "Server:    127.0.0.1",
                    "Port:      {}".format(port),
                    "Type:      MTProto",
                    "Secret:    {}".format(secret_display),
                ])
                parent.removeWidget(self._cfg_block)
                self._cfg_block.deleteLater()
                self._cfg_block = new_block
                parent.insertWidget(idx, new_block)

        self._update_proxy_link(port, secret)

    def _copy_config(self):
        from config_manager import load_config
        from modules.tg_proxy_health import get_secret_from_logs
        port = load_config().get("tg_proxy_port", 8080)
        secret = get_secret_from_logs()
        dd = self._dd_check.isChecked() if hasattr(self, '_dd_check') else False
        display_secret = ("dd" + secret) if (secret and dd) else (secret or "(см. трей-меню)")

        link = "https://t.me/proxy?server=127.0.0.1&port={}&secret=dd{}&type=mtproto".format(port, secret) if (secret and dd) else ""
        text = (
            "Server: 127.0.0.1\n"
            "Port: {}\n"
            "Type: MTProto\n"
            "Secret: {}"
        ).format(port, display_secret)
        if link:
            text += "\n\nСсылка: " + link
        cb = QApplication.clipboard()
        if cb:
            cb.setText(text, QClipboard.Clipboard)
            self.log("Параметры скопированы в буфер обмена", "OK")
            old = self._copy_btn.text()
            self._copy_btn.setText("✔  Скопировано")
            QTimer.singleShot(1500, lambda: self._copy_btn.setText(old))
        else:
            self.log("Не удалось скопировать — буфер обмена недоступен", "ERR")

    # ── Status refresh ───────────────────────────────────────────────── #

    def _check_health(self):
        """Проверка здоровья прокси."""
        from modules.tg_proxy_health import check_proxy_health
        from config_manager import load_config
        port = load_config().get("tg_proxy_port", 8080)
        
        self.log("Проверка здоровья прокси...")
        health = check_proxy_health(port)
        
        if health["status"] == "ok":
            self._health_status.setText("●  Прокси работает. Telegram доступен. ({}мс)".format(
                health.get("latency_ms", 0)
            ))
            self._health_status.setStyleSheet("color:{}; font-size:14px; font-weight:600; background:transparent;".format(GREEN))
            self.log("Health Check: OK — {}".format(health["message"]), "OK")
        elif health["status"] == "port_closed":
            self._health_status.setText("●  Порт закрыт — прокси не запущен")
            self._health_status.setStyleSheet("color:{}; font-size:14px; font-weight:600; background:transparent;".format(RED))
            self.log("Health Check: {}".format(health["message"]), "WARN")
        else:
            self._health_status.setText("●  {}".format(health["message"]))
            self._health_status.setStyleSheet("color:{}; font-size:14px; font-weight:600; background:transparent;".format(RED))
            self.log("Health Check: {}".format(health["message"]), "WARN")
    
    def _auto_fix_media(self):
        """Авто-фикс проблем с медиа."""
        from modules.tg_proxy_health import auto_fix_media_issues
        from config_manager import load_config
        port = load_config().get("tg_proxy_port", 8080)
        
        self.log("Запуск авто-фикса медиа...")
        result = auto_fix_media_issues(port)
        
        if result["success"]:
            self.log("Авто-фикс: {}".format(result["message"]), "OK")
            for fix in result.get("fixes", []):
                self.log("  Применено: {}".format(fix))
        else:
            self.log("Авто-фикс: {}".format(result["message"]), "WARN")
        
        # Обновляем статус после фикса
        self._check_health()

    def _refresh_badge(self):
        running = _is_running()

        if running:
            self._status_icon.setStyleSheet(
                "color:{}; font-size:36px; background:{}; border-radius:24px;".format(
                    GREEN, BG_DARK
                )
            )
            self._status_title.setText("Работает")
            self._status_title.setStyleSheet(
                "color:{}; font-size:16px; font-weight:bold; background:transparent;".format(GREEN)
            )
            from config_manager import load_config
            port = load_config().get("tg_proxy_port", 8080)
            with _proxy_lock:
                pid = _proxy_proc.pid if _proxy_proc else "?"
            self._status_detail.setText(
                "127.0.0.1:{}  •  MTProto  •  PID: {}".format(port, pid)
            )
            self._status_detail.setStyleSheet(
                "color:{}; font-size:12px; background:transparent;".format(TEXT_MID)
            )
        else:
            self._status_icon.setStyleSheet(
                "color:{}; font-size:36px; background:{}; border-radius:24px;".format(
                    RED, BG_DARK
                )
            )
            self._status_title.setText("Остановлен")
            self._status_title.setStyleSheet(
                "color:{}; font-size:16px; font-weight:bold; background:transparent;".format(TEXT_DIM)
            )
            self._status_detail.setText("Прокси не активен")
            self._status_detail.setStyleSheet(
                "color:{}; font-size:12px; background:transparent;".format(TEXT_DIM)
            )

        self._btn_start.setEnabled(not running)
        self._btn_stop.setEnabled(running)

    # ── Show / Hide ──────────────────────────────────────────────────── #

    def showEvent(self, e):
        self._poll.start(2000)
        super().showEvent(e)

    def hideEvent(self, e):
        self._poll.stop()
        super().hideEvent(e)

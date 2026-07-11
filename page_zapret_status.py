"""
page_zapret_status.py — KUS Pro
Страница логов и статуса Zapret.
"""

import subprocess
from pathlib import Path

from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QTextEdit, QTabWidget, QWidget,
    QCheckBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QTextCursor

from base_page import BasePage
from app_paths import ZAPRET_DIR
from qt_compat import *

CNW = 0x08000000
SUH = subprocess.STARTUPINFO()
SUH.dwFlags |= subprocess.STARTF_USESHOWWINDOW
SUH.wShowWindow = 0


def _run_cmd(cmd, timeout=5):
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            creationflags=CNW, startupinfo=SUH,
            timeout=timeout, encoding="cp866", errors="replace",
        )
        return r.returncode, r.stdout.strip()
    except Exception:
        return -1, ""


class ZapretStatusPage(BasePage):
    PAGE_TITLE = "Zapret — Статус и логи"
    PAGE_SUB = "Мониторинг, логи, диагностика"

    def build_ui(self):
        # ── Верхняя панель ──
        top = QHBoxLayout()
        top.setSpacing(12)
        self._badge = QLabel("Остановлен")
        self._badge.setObjectName("badge_stop")
        top.addWidget(self._badge)
        self._exe_label = QLabel("—")
        self._exe_label.setStyleSheet("color:#5a5248; font-size:11px; background:transparent;")
        top.addWidget(self._exe_label)
        top.addStretch()
        btn_refresh = self.btn("Обновить", obj="btn_sec")
        btn_refresh.setFixedHeight(32)
        btn_refresh.clicked.connect(self._refresh_all)
        top.addWidget(btn_refresh)
        self._content.addLayout(top)

        # ── Карточки статуса ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        # Процесс
        proc_card = QGroupBox("Процесс")
        pl = QGridLayout(proc_card)
        pl.setSpacing(6)
        self._proc_status = QLabel("—")
        self._proc_status.setStyleSheet("color:#5a5248; font-size:11px;")
        pl.addWidget(QLabel("Статус:"), 0, 0); pl.addWidget(self._proc_status, 0, 1)
        self._proc_exe = QLabel("—")
        self._proc_exe.setStyleSheet("color:#5a5248; font-size:11px;")
        pl.addWidget(QLabel("EXE:"), 1, 0); pl.addWidget(self._proc_exe, 1, 1)
        self._proc_pid = QLabel("—")
        self._proc_pid.setStyleSheet("color:#5a5248; font-size:11px;")
        pl.addWidget(QLabel("PID:"), 2, 0); pl.addWidget(self._proc_pid, 2, 1)
        stats_row.addWidget(proc_card, 1)

        # Сервис
        svc_card = QGroupBox("Сервис Windows")
        sl = QGridLayout(svc_card)
        sl.setSpacing(6)
        self._svc_status = QLabel("—")
        self._svc_status.setStyleSheet("color:#5a5248; font-size:11px;")
        sl.addWidget(QLabel("Статус:"), 0, 0); sl.addWidget(self._svc_status, 0, 1)
        self._svc_type = QLabel("—")
        self._svc_type.setStyleSheet("color:#5a5248; font-size:11px;")
        sl.addWidget(QLabel("Тип:"), 1, 0); sl.addWidget(self._svc_type, 1, 1)
        stats_row.addWidget(svc_card, 1)

        # Файлы
        files_card = QGroupBox("Файлы Zapret")
        fl = QGridLayout(files_card)
        fl.setSpacing(6)
        self._files_status = QLabel("—")
        self._files_status.setStyleSheet("color:#5a5248; font-size:11px;")
        fl.addWidget(QLabel("Бинарники:"), 0, 0); fl.addWidget(self._files_status, 0, 1)
        self._lua_status = QLabel("—")
        self._lua_status.setStyleSheet("color:#5a5248; font-size:11px;")
        fl.addWidget(QLabel("Lua:"), 1, 0); fl.addWidget(self._lua_status, 1, 1)
        self._wd_status = QLabel("—")
        self._wd_status.setStyleSheet("color:#5a5248; font-size:11px;")
        fl.addWidget(QLabel("WinDivert:"), 2, 0); fl.addWidget(self._wd_status, 2, 1)
        stats_row.addWidget(files_card, 1)

        self._content.addLayout(stats_row)

        # ── Вкладки логов ──
        tabs = QTabWidget()

        # Лог запуска
        tab_run = QWidget()
        tab_run.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(tab_run)
        rl.setContentsMargins(14, 14, 14, 14)
        rl.setSpacing(8)
        rl.addWidget(QLabel("Лог запуска (run_log.txt)"))
        self._run_log = QTextEdit()
        self._run_log.setReadOnly(True)
        self._run_log.setFont(QFont("Consolas", 10))
        rl.addWidget(self._run_log, 1)
        rl_btns = QHBoxLayout()
        btn1 = self.btn("Обновить", obj="btn_sec"); btn1.setFixedHeight(32)
        btn1.clicked.connect(self._load_run_log); rl_btns.addWidget(btn1)
        btn2 = self.btn("Очистить", obj="btn_sec"); btn2.setFixedHeight(32)
        btn2.clicked.connect(lambda: self._clear_file("run_log.txt", self._run_log))
        rl_btns.addWidget(btn2)
        rl_btns.addStretch(); rl.addLayout(rl_btns)
        tabs.addTab(tab_run, "Лог запуска")

        # Crash log
        tab_crash = QWidget()
        tab_crash.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(tab_crash)
        cl.setContentsMargins(14, 14, 14, 14)
        cl.setSpacing(8)
        cl.addWidget(QLabel("Crash-лог (crash_log.txt)"))
        self._crash_log = QTextEdit()
        self._crash_log.setReadOnly(True)
        self._crash_log.setFont(QFont("Consolas", 10))
        cl.addWidget(self._crash_log, 1)
        cl_btns = QHBoxLayout()
        btn3 = self.btn("Обновить", obj="btn_sec"); btn3.setFixedHeight(32)
        btn3.clicked.connect(self._load_crash_log); cl_btns.addWidget(btn3)
        btn4 = self.btn("Очистить", obj="btn_sec"); btn4.setFixedHeight(32)
        btn4.clicked.connect(lambda: self._clear_file("crash_log.txt", self._crash_log))
        cl_btns.addWidget(btn4)
        cl_btns.addStretch(); cl.addLayout(cl_btns)
        tabs.addTab(tab_crash, "Crash-лог")

        # Диагностика
        tab_diag = QWidget()
        tab_diag.setStyleSheet("background: transparent;")
        dl = QVBoxLayout(tab_diag)
        dl.setContentsMargins(14, 14, 14, 14)
        dl.setSpacing(8)
        dl.addWidget(QLabel("Диагностика компонентов Zapret"))
        self._diag_log = QTextEdit()
        self._diag_log.setReadOnly(True)
        self._diag_log.setFont(QFont("Consolas", 10))
        dl.addWidget(self._diag_log, 1)
        btn_diag = self.btn("Запустить диагностику", obj="btn_glow")
        btn_diag.setFixedHeight(36)
        btn_diag.clicked.connect(self._run_diagnostics)
        dl.addWidget(btn_diag)
        tabs.addTab(tab_diag, "Диагностика")

        self._content.addWidget(tabs, 1)

        # Таймер
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._auto_refresh)
        self._timer.start(3000)

        self._refresh_all()

    def _refresh_all(self):
        self._check_process()
        self._check_service()
        self._check_files()
        self._load_run_log()
        self._load_crash_log()

    def _auto_refresh(self):
        self._check_process()
        self._check_service()

    def _check_process(self):
        running = False
        exe_name = ""
        pid = "—"
        for exe in ["winws2.exe", "winws.exe"]:
            code, out = _run_cmd(["tasklist", "/FI", "IMAGENAME eq {}".format(exe), "/FO", "CSV", "/NH"], 3)
            if exe.lower() in out.lower():
                running = True
                exe_name = exe
                for line in out.splitlines():
                    if exe.lower() in line.lower():
                        parts = line.split(",")
                        if len(parts) >= 2:
                            pid = parts[1].strip('"')
                        break
                break
        if running:
            self._badge.setText("Активен")
            self._badge.setObjectName("badge_run")
            self._proc_status.setText("✅ Работает")
            self._proc_status.setStyleSheet("color:#00ff88; font-size:11px; font-weight:bold;")
            self._proc_exe.setText(exe_name)
            self._proc_pid.setText(pid)
        else:
            self._badge.setText("Остановлен")
            self._badge.setObjectName("badge_stop")
            self._proc_status.setText("⏹ Остановлен")
            self._proc_status.setStyleSheet("color:#ff4444; font-size:11px; font-weight:bold;")
            self._proc_exe.setText("—")
            self._proc_pid.setText("—")
        self._badge.style().unpolish(self._badge)
        self._badge.style().polish(self._badge)

    def _check_service(self):
        code, out = _run_cmd(["sc", "query", "zapret"], 5)
        if "RUNNING" in out.upper():
            self._svc_status.setText("✅ Работает")
            self._svc_status.setStyleSheet("color:#00ff88; font-size:11px; font-weight:bold;")
        elif "STOPPED" in out.upper():
            self._svc_status.setText("⏹ Остановлен")
            self._svc_status.setStyleSheet("color:#ff4444; font-size:11px;")
        else:
            self._svc_status.setText("Не установлен")
            self._svc_status.setStyleSheet("color:#5a5248; font-size:11px;")
        code2, out2 = _run_cmd(["sc", "qc", "zapret"], 5)
        if "AUTO_START" in out2.upper():
            self._svc_type.setText("Автоматический")
        elif "DEMAND_START" in out2.upper():
            self._svc_type.setText("Вручную")
        else:
            self._svc_type.setText("—")

    def _check_files(self):
        binaries_ok = all((ZAPRET_DIR / e).exists() for e in ["winws2.exe", "WinDivert.dll", "WinDivert64.sys"])
        self._files_status.setText("✅ OK" if binaries_ok else "⚠️ Часть отсутствует")
        self._files_status.setStyleSheet("color:{}; font-size:11px;".format("#00ff88" if binaries_ok else "#fbbf24"))
        lua_dir = ZAPRET_DIR / "lua"
        if lua_dir.exists():
            self._lua_status.setText("✅ {} файлов".format(len(list(lua_dir.glob("*.lua")))))
            self._lua_status.setStyleSheet("color:#00ff88; font-size:11px;")
        else:
            self._lua_status.setText("⚠️ Не найдена")
            self._lua_status.setStyleSheet("color:#fbbf24; font-size:11px;")
        wd_ok = (ZAPRET_DIR / "WinDivert.dll").exists() and (ZAPRET_DIR / "WinDivert64.sys").exists()
        self._wd_status.setText("✅ Установлен" if wd_ok else "⚠️ Не найден")
        self._wd_status.setStyleSheet("color:{}; font-size:11px;".format("#00ff88" if wd_ok else "#fbbf24"))

    def _find_log(self, name):
        for p in [Path(name), ZAPRET_DIR / name, Path.cwd() / name]:
            if p.exists():
                return p
        return Path(name)

    def _load_run_log(self):
        path = self._find_log("run_log.txt")
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8", errors="replace")[-50000:]
                self._run_log.setPlainText(content)
                cursor = self._run_log.textCursor()
                cursor.movePosition(QTextCursor.End)
                self._run_log.setTextCursor(cursor)
            except Exception as e:
                self._run_log.setPlainText("Ошибка: {}".format(e))
        else:
            self._run_log.setPlainText("run_log.txt не найден")

    def _load_crash_log(self):
        path = self._find_log("crash_log.txt")
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8", errors="replace")[-50000:]
                self._crash_log.setPlainText(content)
                cursor = self._crash_log.textCursor()
                cursor.movePosition(QTextCursor.End)
                self._crash_log.setTextCursor(cursor)
            except Exception as e:
                self._crash_log.setPlainText("Ошибка: {}".format(e))
        else:
            self._crash_log.setPlainText("crash_log.txt не найден")

    def _clear_file(self, name, widget):
        path = self._find_log(name)
        try:
            path.write_text("", encoding="utf-8")
            widget.clear()
        except Exception:
            pass

    def _run_diagnostics(self):
        self._diag_log.clear()
        self._diag_log.append("=== Диагностика Zapret ===\n")
        checks = {
            "winws2.exe": ZAPRET_DIR / "winws2.exe",
            "WinDivert.dll": ZAPRET_DIR / "WinDivert.dll",
            "WinDivert64.sys": ZAPRET_DIR / "WinDivert64.sys",
            "zapret-lib.lua": ZAPRET_DIR / "lua" / "zapret-lib.lua",
            "zapret-antidpi.lua": ZAPRET_DIR / "lua" / "zapret-antidpi.lua",
        }
        for name, path in checks.items():
            status = "✅" if path.exists() else "❌"
            size = " ({} KB)".format(path.stat().st_size // 1024) if path.exists() else ""
            self._diag_log.append("  {} {}{}".format(status, name, size))
        self._diag_log.append("\n=== Готово ===")

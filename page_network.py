"""Сетевая диагностика — редизайн по ТЗ (карточки)."""
import threading

from qt_compat import *


from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QSizePolicy,
    QGridLayout, QPushButton, QScrollArea, QWidget,
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from base_page import BasePage
from theme import TABLE_QSS


def _fn_connections(log_func, progress_func):
    from modules.network import get_active_connections
    return get_active_connections(log_func, progress_func)

def _fn_flush_dns(log_func, progress_func):
    from modules.network import flush_dns
    flush_dns(log_func, progress_func)

def _fn_reset_tcp(log_func, progress_func):
    from modules.network import reset_tcpip_stack
    reset_tcpip_stack(log_func, progress_func)

def _fn_top_processes(log_func, progress_func):
    from modules.network import get_top_network_processes
    return get_top_network_processes(log_func, progress_func, limit=8)

def _fn_get_dns(log_func, progress_func):
    from modules.network import get_current_dns
    return get_current_dns(log_func, progress_func)

def _fn_set_dns(log_func, progress_func, primary, secondary=""):
    from modules.network import set_dns
    set_dns(log_func, progress_func, primary, secondary)

def _fn_reset_dns(log_func, progress_func):
    from modules.network import reset_dns
    reset_dns(log_func, progress_func)


def _fn_speed_test(log_func, progress_func):
    """Активный тест скорости — скачивает тестовый файл для замера реальной пропускной способности."""
    import time
    import urllib.request
    import ssl

    # Тестовые файлы разных размеров для точного замера
    test_urls = [
        ("https://speed.cloudflare.com/__down?bytes=10000000", "10 МБ"),
        ("https://proof.ovh.net/files/10Mb.dat", "10 МБ"),
        ("http://speedtest.tele2.net/10MB.zip", "10 МБ"),
    ]

    # SSL контекст
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()

    log_func("=== Тест скорости ===")
    progress_func(0.1)

    # 1. Пинг (latency)
    log_func("Измерение задержки...")
    latencies = []
    import re
    for host in ["1.1.1.1", "8.8.8.8", "google.com"]:
        try:
            import subprocess
            CREATE_NO_WINDOW = 0x08000000
            result = subprocess.run(
                ["ping", "-n", "3", host],
                capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=10
            )
            out = result.stdout.decode("cp866", errors="replace")
            # Парсим время из строки "time=12ms" или "время=12мс"
            for line in out.splitlines():
                m = re.search(r"time[=\s=]*(\d+)\s*м?с", line.lower())
                if m:
                    latencies.append(int(m.group(1)))
        except Exception:
            pass

    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    log_func("Средняя задержка: {:.0f} мс".format(avg_latency))
    progress_func(0.3)

    # 2. Download тест
    log_func("Тест загрузки (download)...")
    download_speed = 0

    for url, size_label in test_urls:
        try:
            log_func("Подключение к {}...".format(url.split("/")[2]))
            req = urllib.request.Request(url, headers={"User-Agent": "KUS-Pro-SpeedTest/1.0"})

            t1 = time.time()
            with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                total = 0
                while True:
                    chunk = r.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
            t2 = time.time()

            elapsed = max(t2 - t1, 0.001)
            speed_bps = total / elapsed
            download_speed = speed_bps * 8 / 1000000  # Мбит/с

            log_func("Загружено: {:.1f} МБ за {:.1f} сек = {:.1f} Мбит/с".format(
                total / 1048576, elapsed, download_speed
            ), "OK")
            progress_func(0.6)
            break
        except Exception as e:
            log_func("Ошибка с {}: {}".format(url.split("/")[2], str(e)[:60]), "WARN")
            continue

    if download_speed == 0:
        log_func("Не удалось выполнить тест загрузки", "ERR")

    # 3. Upload тест (Cloudflare speed test server)
    log_func("Тест отправки (upload)...")
    upload_speed = 0

    upload_urls = [
        ("https://speed.cloudflare.com/__up", "Cloudflare"),
        ("https://proof.ovh.net/files/10Mb.dat", "OVH"),
    ]

    for upload_url, server_name in upload_urls:
        try:
            # Создаём 10 МБ данных для отправки
            test_data = b"x" * (10 * 1024 * 1024)
            log_func("Подключение к {}...".format(server_name))
            req = urllib.request.Request(
                upload_url,
                data=test_data,
                headers={"User-Agent": "KUS-Pro-SpeedTest/1.0", "Content-Type": "application/octet-stream"},
                method="POST"
            )
            t1 = time.time()
            with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                r.read()
            t2 = time.time()

            elapsed = max(t2 - t1, 0.001)
            upload_speed = len(test_data) * 8 / 1000000 / elapsed
            log_func("Отправлено: 10.0 МБ за {:.1f} сек = {:.1f} Мбит/с ({})".format(
                elapsed, upload_speed, server_name
            ), "OK")
            break
        except Exception as e:
            log_func("Ошибка с {}: {}".format(server_name, str(e)[:60]), "WARN")
            continue

    if upload_speed == 0:
        log_func("Не удалось выполнить тест отправки", "ERR")

    progress_func(1.0)
    log_func("=== Тест завершён: ↓{:.1f} ↑{:.1f} Мбит/с, пинг {:.0f} мс ===".format(
        download_speed, upload_speed, avg_latency
    ), "OK")

    return {
        "download_mbps": round(download_speed, 1),
        "upload_mbps": round(upload_speed, 1),
        "latency_ms": round(avg_latency, 1),
    }


class _SpeedThread(QThread):
    speed_ready = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        import time
        import psutil
        while not self._stop_event.is_set():
            try:
                t1 = time.time()
                before = psutil.net_io_counters()
                # Ждём 1 секунду — QThread.msleep вместо threading.Event.wait,
                # чтобы не вызывать предупреждение Qt о таймерах из чужого потока
                self.msleep(1000)
                if self._stop_event.is_set():
                    break
                after = psutil.net_io_counters()
                t2 = time.time()
                elapsed = max(t2 - t1, 0.001)
                down_kbps = max(0, after.bytes_recv - before.bytes_recv) / 1024.0 / elapsed
                up_kbps = max(0, after.bytes_sent - before.bytes_sent) / 1024.0 / elapsed
                speed = {
                    "download_kbps": round(down_kbps, 1),
                    "upload_kbps": round(up_kbps, 1),
                    "download_mbps": round(down_kbps * 8 / 1024.0, 2),
                    "upload_mbps": round(up_kbps * 8 / 1024.0, 2),
                }
                if not self._stop_event.is_set():
                    self.speed_ready.emit(speed)
            except Exception:
                pass


def _stat_card(icon, label, value, color):
    """Цветная карточка-действие в стиле _action_card из page_updates."""
    card = QFrame()
    card.setStyleSheet(
        "QFrame {{ background:rgba(255,255,255,0.025);"
        "border:1px solid rgba(255,255,255,0.06);"
        "border-radius:10px; }}"
        "QFrame:hover {{ border:1px solid rgba({r},{g},{b},0.3); }}".format(
            r=int(color[1:3], 16), g=int(color[3:5], 16), b=int(color[5:7], 16)
        )
    )
    card.setSizePolicy(Expanding, Fixed)
    lay = QHBoxLayout(card)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(12)

    icon_lbl = QLabel(icon)
    icon_lbl.setFixedSize(40, 40)
    icon_lbl.setAlignment(AlignCenter)
    icon_lbl.setStyleSheet(
        "font-size:18px; color:{}; background:rgba({r},{g},{b},0.1); "
        "border-radius:10px;".format(
            color, r=int(color[1:3], 16), g=int(color[3:5], 16), b=int(color[5:7], 16)
        )
    )
    lay.addWidget(icon_lbl)

    text = QVBoxLayout()
    text.setSpacing(2)
    t = QLabel(label)
    t.setStyleSheet("color:{}; font-size:14px; font-weight:700; background:transparent;".format(color))
    text.addWidget(t)
    v = QLabel(value)
    v.setObjectName("card_value")
    v.setStyleSheet("color:#e8ddd0; font-size:16px; font-weight:800; background:transparent;")
    text.addWidget(v)
    lay.addLayout(text, 1)

    return card, v


class NetworkPage(BasePage):
    PAGE_TITLE = "🌐  Сеть"
    PAGE_SUB   = "Активные соединения, DNS и TCP/IP"

    def build_ui(self):
        # ══════════════════════════════════════════════════════════════ #
        #  1. TOP ROW — 3 colored stat cards                          #
        # ══════════════════════════════════════════════════════════════ #
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)

        card_total, self._val_total = _stat_card("🔗", "Всего", "0", "#5b9df0")
        stats_row.addWidget(card_total)

        card_tcp, self._val_tcp = _stat_card("🔵", "TCP", "0", "#4ac9c9")
        stats_row.addWidget(card_tcp)

        card_udp, self._val_udp = _stat_card("🟣", "UDP", "0", "#a070e0")
        stats_row.addWidget(card_udp)

        self._content.addLayout(stats_row)

        # ══════════════════════════════════════════════════════════════ #
        #  2. SPEED CARD — download + upload + toggle                  #
        # ══════════════════════════════════════════════════════════════ #
        speed_card = QFrame()
        speed_card.setObjectName("card")
        sp_lay = QVBoxLayout(speed_card)
        sp_lay.setContentsMargins(18, 16, 18, 16)
        sp_lay.setSpacing(10)

        sp_title = QLabel("Скорость сети")
        sp_title.setObjectName("card_title")
        sp_lay.addWidget(sp_title)

        sp_values = QHBoxLayout()
        sp_values.setSpacing(20)

        self._lbl_down = QLabel("⬇  0.0 Мбит/с")
        self._lbl_down.setStyleSheet(
            "color:#4caf7d; font-size:14px; font-weight:700; background:transparent;"
        )
        sp_values.addWidget(self._lbl_down)

        self._lbl_up = QLabel("⬆  0.0 Мбит/с")
        self._lbl_up.setStyleSheet(
            "color:#5b9df0; font-size:14px; font-weight:700; background:transparent;"
        )
        sp_values.addWidget(self._lbl_up)

        sp_values.addStretch()

        self._btn_speed_toggle = self.btn("⏸  Стоп", obj="btn_sec")
        self._btn_speed_toggle.setFixedHeight(34)
        self._btn_speed_toggle.clicked.connect(self._toggle_speed_monitor)
        sp_values.addWidget(self._btn_speed_toggle)

        self._btn_speed_test = self.btn("🚀  Замер", obj="btn_glow")
        self._btn_speed_test.setFixedHeight(34)
        self._btn_speed_test.clicked.connect(self._run_speed_test)
        sp_values.addWidget(self._btn_speed_test)

        sp_lay.addLayout(sp_values)

        # Speed test result label
        self._lbl_speed_test = QLabel("")
        self._lbl_speed_test.setStyleSheet("color:#fbbf24; font-size:13px; font-weight:700; background:transparent;")
        sp_lay.addWidget(self._lbl_speed_test)

        self._content.addWidget(speed_card)

        # ══════════════════════════════════════════════════════════════ #
        #  3. DNS CARD — status + presets grid + DHCP reset            #
        # ══════════════════════════════════════════════════════════════ #
        dns_card = self.card("DNS-СЕРВЕРЫ")

        dns_status_row = QHBoxLayout()
        dns_status_row.setSpacing(8)

        self._dns_status = QLabel("●  Текущий DNS не определён")
        self._dns_status.setStyleSheet(
            "color:#a09888; font-size:12px; font-weight:600; background:transparent;"
        )
        dns_status_row.addWidget(self._dns_status)
        dns_status_row.addStretch()

        btn_check_dns = self._reg_btn(self.btn("🔄", obj="btn_sec"))
        btn_check_dns.setFixedSize(28, 24)
        btn_check_dns.clicked.connect(self._refresh_dns_status)
        dns_status_row.addWidget(btn_check_dns)

        btn_reset_dhcp = self._reg_btn(self.btn("Сбросить на DHCP", obj="btn_sec"))
        btn_reset_dhcp.setFixedHeight(30)
        btn_reset_dhcp.clicked.connect(self._reset_to_dhcp)
        dns_status_row.addWidget(btn_reset_dhcp)

        dns_card.lay.addLayout(dns_status_row)

        from modules.network import DNS_PRESETS

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background:transparent; border:none; }"
            "QScrollArea > QWidget > QWidget { background:transparent; }"
        )
        scroll.setMinimumHeight(200)
        scroll.setMaximumHeight(500)

        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(8)
        grid.setContentsMargins(0, 4, 0, 4)

        for idx, preset in enumerate(DNS_PRESETS):
            card = self._make_dns_preset_card(preset)
            grid.addWidget(card, idx // 2, idx % 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        scroll.setWidget(grid_w)
        dns_card.lay.addWidget(scroll)

        self._content.addWidget(dns_card)

        # ══════════════════════════════════════════════════════════════ #
        #  4. TOP PROCESSES CARD — refresh + process list              #
        # ══════════════════════════════════════════════════════════════ #
        proc_card = self.card("АКТИВНОСТЬ ПО ПРОЦЕССАМ")

        proc_hdr = QHBoxLayout()
        proc_hdr.addStretch()
        b_proc_refresh = self.btn("🔄", obj="btn_sec")
        b_proc_refresh.setFixedSize(28, 24)
        b_proc_refresh.clicked.connect(self._refresh_top_processes)
        proc_hdr.addWidget(b_proc_refresh)
        proc_card.lay.addLayout(proc_hdr)

        self._proc_list_label = QLabel("Нажмите 🔄, чтобы посмотреть, какие процессы держат больше всего сетевых соединений.")
        self._proc_list_label.setWordWrap(True)
        self._proc_list_label.setStyleSheet("color:#a8a098; font-size:11px; background:transparent;")
        proc_card.lay.addWidget(self._proc_list_label)

        self._content.addWidget(proc_card)

        # ══════════════════════════════════════════════════════════════ #
        #  5. CONNECTIONS TABLE — full width                           #
        # ══════════════════════════════════════════════════════════════ #
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["ПРОТОКОЛ", "ЛОКАЛЬНЫЙ АДРЕС", "УДАЛЁННЫЙ АДРЕС", "СОСТОЯНИЕ", "PID"]
        )
        self._table.setStyleSheet(TABLE_QSS)
        self._table.setAlternatingRowColors(False)
        self._table.setShowGrid(False)
        self._table.setSelectionBehavior(SelectRows)
        self._table.setEditTriggers(NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(40)
        self._table.setFrameShape(NoFrame)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Fixed);    hdr.resizeSection(0, 100)
        hdr.setSectionResizeMode(1, Stretch)
        hdr.setSectionResizeMode(2, Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.Fixed);    hdr.resizeSection(3, 130)
        hdr.setSectionResizeMode(4, QHeaderView.Fixed);    hdr.resizeSection(4, 72)
        hdr.setDefaultAlignment(AlignLeft | AlignVCenter)
        hdr.setHighlightSections(False)

        self._content.addWidget(self._table, 1)

        # ══════════════════════════════════════════════════════════════ #
        #  6. ACTION BUTTONS ROW (moved from top)                      #
        # ══════════════════════════════════════════════════════════════ #
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self._btn_refresh = self._reg_btn(self.btn("🔄  Обновить соединения"))
        self._btn_refresh.setObjectName("")
        self._btn_refresh.setFixedHeight(38)
        self._btn_refresh.clicked.connect(self._refresh)
        action_row.addWidget(self._btn_refresh)

        self._btn_dns = self._reg_btn(self.btn("🗑  Сбросить DNS"))
        self._btn_dns.setObjectName("btn_sec")
        self._btn_dns.setFixedHeight(38)
        self._btn_dns.clicked.connect(self._flush_dns)
        action_row.addWidget(self._btn_dns)

        self._btn_tcp = self._reg_btn(self.btn("🛡  Сброс TCP/IP"))
        self._btn_tcp.setObjectName("btn_danger")
        self._btn_tcp.setFixedHeight(38)
        self._btn_tcp.setToolTip("Потребует перезагрузки ПК")
        self._btn_tcp.clicked.connect(self._reset_tcp)
        action_row.addWidget(self._btn_tcp)

        action_row.addStretch()

        self._status = QLabel("●  Система в норме")
        self._status.setObjectName("badge_run")
        action_row.addWidget(self._status)

        self._content.addLayout(action_row)

        # ── Авто-замер скорости сети ──────────────────────────────────── #
        self._speed_thread = _SpeedThread(self)
        self._speed_thread.speed_ready.connect(self._on_speed_update)
        self._speed_thread.start()

    # ── DNS карточка пресета ────────────────────────────────────────── #
    def _make_dns_preset_card(self, preset):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background:rgba(255,255,255,0.025);"
            "border:1px solid rgba(255,255,255,0.06);"
            "border-radius:10px; }"
            "QFrame:hover { border:1px solid rgba(245,166,35,0.25); }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(3)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        name_lbl = QLabel(preset["name"])
        name_lbl.setStyleSheet(
            "color:#f5a623; font-size:12px; font-weight:700; background:transparent;"
        )
        top_row.addWidget(name_lbl)
        top_row.addStretch()

        if preset.get("primary"):
            btn = self._reg_btn(self.btn("Применить", obj="btn_sec"))
            btn.setFixedSize(80, 22)
            btn.setStyleSheet(
                "QPushButton { font-size:10px; padding:2px 8px; border-radius:4px; }"
            )
            btn.clicked.connect(
                lambda _, pri=preset["primary"], sec=preset.get("secondary", ""):
                    self._apply_dns(pri, sec)
            )
            top_row.addWidget(btn)
        lay.addLayout(top_row)

        if preset.get("primary"):
            ip_text = preset["primary"]
            if preset.get("secondary"):
                ip_text += "  /  " + preset["secondary"]
            ip_lbl = QLabel(ip_text)
            ip_lbl.setFont(QFont("Consolas", 10))
            ip_lbl.setStyleSheet("color:#c8c0b8; background:transparent;")
            lay.addWidget(ip_lbl)

        if preset.get("description"):
            desc_lbl = QLabel(preset["description"])
            desc_lbl.setWordWrap(True)
            desc_lbl.setMaximumHeight(28)
            desc_lbl.setStyleSheet("color:#7a7068; font-size:9px; background:transparent;")
            lay.addWidget(desc_lbl)

        if preset.get("tags"):
            tags_row = QHBoxLayout()
            tags_row.setSpacing(3)
            tag_colors = ["#4caf7d", "#5b9df0", "#a070e0", "#f5c842", "#f08060", "#c080f0"]
            for ti, tag in enumerate(preset["tags"][:3]):
                t = QLabel(tag)
                t.setStyleSheet(
                    "color:{}; font-size:8px; font-weight:600;"
                    "background:rgba(255,255,255,0.04);"
                    "border:1px solid rgba(255,255,255,0.08);"
                    "border-radius:3px; padding:1px 4px;".format(
                        tag_colors[ti % len(tag_colors)]
                    )
                )
                tags_row.addWidget(t)
            tags_row.addStretch()
            lay.addLayout(tags_row)

        return frame

    # ── DNS статус и действия ───────────────────────────────────────── #
    def _refresh_dns_status(self):
        self._run_worker(_fn_get_dns, on_result=self._update_dns_status)

    def _update_dns_status(self, result):
        if not result:
            self._dns_status.setText("●  DNS не определён (возможно, нет прав администратора)")
            self._dns_status.setStyleSheet("color:#7a7068; font-size:12px; font-weight:600; background:transparent;")
            return
        servers = ", ".join(r["dns"] for r in result if r.get("dns"))
        self._dns_status.setText("●  Текущий DNS: {}".format(servers or "DHCP"))
        self._dns_status.setStyleSheet("color:#4caf7d; font-size:12px; font-weight:600; background:transparent;")

    def _apply_dns(self, primary, secondary):
        self._run_worker(_fn_set_dns, primary, secondary)

    def _reset_to_dhcp(self):
        self._run_worker(_fn_reset_dns)

    def _refresh(self):
        self._table.setRowCount(0)
        self._run_worker(_fn_connections, on_result=self._fill_table)

    def _fill_table(self, conns):
        STATE_COLOR = {
            "ESTABLISHED": "#4caf7d",
            "LISTEN":      "#5b9df0",
            "TIME_WAIT":   "#f5c842",
            "CLOSE_WAIT":  "#f5a623",
            "CLOSE":       "#e05252",
            "SYN_SENT":    "#c080f0",
            "FIN_WAIT1":   "#f08060",
            "FIN_WAIT2":   "#f09060",
        }
        PROTO_COLOR = {"TCP": "#5b9df0", "UDP": "#a070e0"}

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(conns))

        tcp = udp = 0
        bold_font = QFont(); bold_font.setBold(True)
        mono_font = QFont("Consolas", 12)

        for r, c in enumerate(conns):
            proto  = c.get("proto", "")
            local  = c.get("local", "")
            remote = c.get("remote", "") or "—"
            state  = c.get("state", "") or "—"
            pid    = str(c.get("pid", ""))

            if proto == "TCP": tcp += 1
            elif proto == "UDP": udp += 1

            for col, val in enumerate([proto, local, remote, state, pid]):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                if col == 0:
                    item.setForeground(QColor(PROTO_COLOR.get(proto, "#c0b8b0")))
                    item.setFont(bold_font)
                elif col in (1, 2):
                    item.setForeground(QColor("#c8c0b8"))
                    item.setFont(mono_font)
                elif col == 3:
                    color = STATE_COLOR.get(state.upper(), "#7a7068")
                    item.setForeground(QColor(color))
                    item.setFont(bold_font)
                elif col == 4:
                    item.setForeground(QColor("#7a7068"))
                    item.setTextAlignment(AlignRight | AlignVCenter)

                self._table.setItem(r, col, item)

        self._table.setSortingEnabled(True)
        self._val_total.setText(str(len(conns)))
        self._val_tcp.setText(str(tcp))
        self._val_udp.setText(str(udp))

    def _flush_dns(self):
        self._run_worker(_fn_flush_dns)

    def _reset_tcp(self):
        if QMessageBox.question(
            self, "Сброс TCP/IP",
            "Сброс TCP/IP и Winsock потребует перезагрузки.\nПродолжить?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        self._run_worker(_fn_reset_tcp)

    # ── Скорость сети (фоновый поток) ──────────────────────────────── #
    def _on_speed_update(self, speed):
        down = speed.get("download_mbps", 0.0)
        up = speed.get("upload_mbps", 0.0)
        self._lbl_down.setText("⬇  {:.1f} Мбит/с".format(down))
        self._lbl_up.setText("⬆  {:.1f} Мбит/с".format(up))

    def _toggle_speed_monitor(self):
        if self._speed_thread.isRunning():
            self._speed_thread.stop()
            self._speed_thread.wait(1500)
            self._btn_speed_toggle.setText("▶  Старт")
            self._lbl_down.setText("⬇  — (остановлено)")
            self._lbl_up.setText("⬆  — (остановлено)")
        else:
            # Clean up old thread before creating new one
            if self._speed_thread is not None and self._speed_thread.isFinished():
                try:
                    self._speed_thread.speed_ready.disconnect(self._on_speed_update)
                except (TypeError, RuntimeError):
                    pass
                self._speed_thread.deleteLater()
            self._speed_thread = _SpeedThread(self)
            self._speed_thread.speed_ready.connect(self._on_speed_update)
            self._speed_thread.start()
            self._btn_speed_toggle.setText("⏸  Стоп")

    # ── Тест скорости (активный замер) ─────────────────────────────── #
    def _run_speed_test(self):
        """Запускает активный тест скорости — скачивает тестовый файл."""
        self._btn_speed_test.setEnabled(False)
        self._btn_speed_test.setText("⏳  Замер...")
        self._lbl_speed_test.setText("Запуск теста скорости...")
        self._run_worker(_fn_speed_test, on_result=self._on_speed_test_result)

    def _on_speed_test_result(self, result):
        self._btn_speed_test.setEnabled(True)
        self._btn_speed_test.setText("🚀  Тест скорости")
        if result:
            down = result.get("download_mbps", 0)
            up = result.get("upload_mbps", 0)
            latency = result.get("latency_ms", 0)
            self._lbl_speed_test.setText(
                "📥 Download: {:.1f} Мбит/с  |  📤 Upload: {:.1f} Мбит/с  |  ⏱ Пинг: {:.0f} мс".format(
                    down, up, latency
                )
            )
            from modules.action_log import log_action
            log_action("speed_test", "Тест скорости: ↓{:.1f} ↑{:.1f} Мбит/с, пинг {:.0f} мс".format(
                down, up, latency
            ))
        else:
            self._lbl_speed_test.setText("❌ Ошибка теста скорости")

    # ── Топ процессов по сети ──────────────────────────────────────── #
    def _refresh_top_processes(self):
        self._run_worker(_fn_top_processes, on_result=self._fill_top_processes)

    def _fill_top_processes(self, procs):
        if not procs:
            self._proc_list_label.setText(
                "Активных сетевых соединений не найдено, либо недостаточно прав "
                "(запустите приложение от имени администратора)."
            )
            return
        lines = []
        for p in procs:
            lines.append("{}  —  {} соединений  (PID {})".format(
                p["name"], p["connections"], p["pid"]
            ))
        self._proc_list_label.setText("\n".join(lines))

    # ── Жизненный цикл страницы ─────────────────────────────────────── #
    def hideEvent(self, e):
        if self._speed_thread.isRunning():
            self._speed_thread.stop()
            self._speed_thread.wait(1500)
        super().hideEvent(e)

    def showEvent(self, e):
        if self._speed_thread is None or self._speed_thread.isFinished():
            self._speed_thread = _SpeedThread(self)
            self._speed_thread.speed_ready.connect(self._on_speed_update)
            self._speed_thread.start()
            self._btn_speed_toggle.setText("⏸  Остановить замер")
        super().showEvent(e)

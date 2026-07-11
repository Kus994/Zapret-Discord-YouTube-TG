"""Менеджер процессов — стиль Windows 11 Task Manager."""
import platform

from qt_compat import *

import socket
from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QSizePolicy, QMenu, QPushButton, QWidget, QAction,
)
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt, QTimer
from base_page import BasePage
from theme import TABLE_QSS


def _fn_list(log_func, progress_func, quiet=False):
    from modules.processes import list_processes
    from modules.monitor import get_snapshot
    lf = None if quiet else log_func
    pf = None if quiet else progress_func
    procs = list_processes(lf, pf)
    try:
        snapshot = get_snapshot()
    except Exception:
        snapshot = {}
    return {"procs": procs, "snapshot": snapshot}


def _fn_kill_many(log_func, progress_func, pids, with_children=False, force=False):
    from modules.processes import kill_processes
    return kill_processes(pids, log_func, progress_func, with_children=with_children, force=force)


class _NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            return self.data(Qt.UserRole) < other.data(Qt.UserRole)
        except (TypeError, AttributeError):
            return super().__lt__(other)


_GROUP_APPS = 0
_GROUP_NONE = 1
_GROUP_USER = 2
_GROUP_STATUS = 3

_STATUS_COLORS = {
    "Running": "#4caf7d",
    "Suspended": "#f5c842",
}

_GROUP_BTN_NORMAL = (
    "QPushButton { background:rgba(245,166,35,0.04);"
    "color:#5a5248; border:1px solid rgba(245,166,35,0.12);"
    "border-radius:6px; padding:5px 12px; font-size:11px;"
    "font-weight:600; }"
    "QPushButton:hover { background:rgba(245,166,35,0.08);"
    "color:#a09080; border-color:rgba(245,166,35,0.25); }"
)
_GROUP_BTN_ACTIVE = (
    "QPushButton { background:rgba(245,166,35,0.12);"
    "color:#f5a623; border:1px solid rgba(245,166,35,0.3);"
    "border-radius:6px; padding:5px 12px; font-size:11px;"
    "font-weight:700; }"
)


def _action_card(icon, label, color):
    """Цветная карточка-статистика в стиле Windows 11 Task Manager."""
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    card = QFrame()
    card.setStyleSheet(
        "QFrame {{ background:rgba(255,255,255,0.025);"
        "border:1px solid rgba(255,255,255,0.06);"
        "border-radius:10px; }}"
        "QFrame:hover {{ border:1px solid rgba({},{},{},0.35); }}".format(r, g, b)
    )
    card.setFixedHeight(72)
    card.setSizePolicy(Expanding, Fixed)
    lay = QHBoxLayout(card)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(10)

    icon_lbl = QLabel(icon)
    icon_lbl.setFixedSize(32, 32)
    icon_lbl.setAlignment(AlignCenter)
    icon_lbl.setStyleSheet(
        "font-size:16px; color:{}; background:rgba({},{},{},0.1); "
        "border-radius:8px;".format(color, r, g, b)
    )
    lay.addWidget(icon_lbl)

    text_lay = QVBoxLayout()
    text_lay.setSpacing(1)
    lbl = QLabel(label)
    lbl.setStyleSheet("color:#5a5248; font-size:9px; font-weight:700; letter-spacing:0.8px; background:transparent;")
    text_lay.addWidget(lbl)
    val = QLabel("—")
    val.setObjectName("stat_val")
    val.setStyleSheet("color:{}; font-size:20px; font-weight:800; background:transparent;".format(color))
    text_lay.addWidget(val)
    lay.addLayout(text_lay, 1)

    return card, val


def _device_banner():
    """Верхняя панель устройства — как в скриншоте Диспетчера задач
    Windows 11: значок + имя компьютера/ОС слева, бейджи CPU/Память/
    Диск/Сеть справа. В отличие от карточек ниже (которые считаются по
    списку процессов), эти значения — реальные системные метрики из
    modules.monitor.get_snapshot() (то же, что видит вкладка
    «Мониторинг»), а не сумма по видимым процессам."""
    card = QFrame()
    card.setObjectName("card")
    card.setFixedHeight(64)
    lay = QHBoxLayout(card)
    lay.setContentsMargins(14, 8, 18, 8)
    lay.setSpacing(14)

    icon = QLabel("🖥")
    icon.setFixedSize(44, 44)
    icon.setAlignment(AlignCenter)
    icon.setStyleSheet(
        "font-size:20px; background:rgba(245,166,35,0.10); border-radius:9px;"
    )
    lay.addWidget(icon)

    name_lay = QVBoxLayout()
    name_lay.setSpacing(1)
    try:
        host = socket.gethostname()
    except Exception:
        host = "—"
    lbl_host = QLabel(host)
    lbl_host.setStyleSheet("color:#e8ddd0; font-size:14px; font-weight:700; background:transparent;")
    name_lay.addWidget(lbl_host)

    # Определяем реальную версию Windows (10 vs 11)
    os_name = platform.system()
    if os_name == "Windows":
        ver = platform.version()
        try:
            build = int(ver.split(".")[-1])
            os_label = "Windows 11" if build >= 22000 else "Windows 10"
        except (ValueError, IndexError):
            os_label = "Windows {}".format(platform.release())
    else:
        os_label = "{} {}".format(os_name, platform.release())
    lbl_os = QLabel(os_label)
    lbl_os.setStyleSheet("color:#7a7068; font-size:11px; background:transparent;")
    name_lay.addWidget(lbl_os)
    lay.addLayout(name_lay)

    lay.addStretch()

    badges = {}
    for key, icon_ch, label, color in [
        ("cpu", "⚡", "CPU", "#4caf7d"),
        ("mem", "💾", "Память", "#5b9df0"),
        ("disk", "💽", "Диск", "#f5a623"),
        ("net", "🌐", "Сеть", "#a070e0"),
    ]:
        b_lay = QVBoxLayout()
        b_lay.setSpacing(0)
        b_lay.setAlignment(AlignCenter)
        val = QLabel("—")
        val.setAlignment(AlignCenter)
        val.setStyleSheet("color:{}; font-size:15px; font-weight:800; background:transparent;".format(color))
        b_lay.addWidget(val)
        lbl = QLabel("{} {}".format(icon_ch, label))
        lbl.setAlignment(AlignCenter)
        lbl.setStyleSheet("color:#5a5248; font-size:9px; font-weight:600; background:transparent;")
        b_lay.addWidget(lbl)
        holder = QWidget()
        holder.setLayout(b_lay)
        holder.setFixedWidth(84)
        lay.addWidget(holder)
        badges[key] = val

    return card, badges


class ProcessesPage(BasePage):
    PAGE_TITLE = "⚙  Процессы"
    PAGE_SUB = "Управление запущенными процессами"

    def build_ui(self):
        self._auto_refresh = False
        self._procs = []
        self._group_mode = _GROUP_APPS
        self._collapsed_groups = set()

        # ══════════════════════════════════════════════════════════════ #
        #  0. DEVICE BANNER — как в скриншоте Диспетчера задач Win11     #
        # ══════════════════════════════════════════════════════════════ #
        banner, self._banner_badges = _device_banner()
        self._content.addWidget(banner)

        # ══════════════════════════════════════════════════════════════ #
        #  1. STATS ROW — 5 цветных карточек как Win11 Task Manager     #
        # ══════════════════════════════════════════════════════════════ #
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)

        self._stat_cpu_card, self._stat_cpu_val = _action_card("⚡", "CPU", "#4caf7d")
        stats_row.addWidget(self._stat_cpu_card)

        self._stat_mem_card, self._stat_mem_val = _action_card("💾", "Память", "#5b9df0")
        stats_row.addWidget(self._stat_mem_card)

        self._stat_procs_card, self._stat_procs_val = _action_card("📋", "Процессов", "#f5a623")
        stats_row.addWidget(self._stat_procs_card)

        self._stat_active_card, self._stat_active_val = _action_card("▶", "Активных", "#a070e0")
        stats_row.addWidget(self._stat_active_card)

        self._stat_protected_card, self._stat_protected_val = _action_card("🔒", "Защищённых", "#e05252")
        stats_row.addWidget(self._stat_protected_card)

        self._content.addLayout(stats_row)

        # ══════════════════════════════════════════════════════════════ #
        #  2. SEARCH CARD                                               #
        # ══════════════════════════════════════════════════════════════ #
        search_card = QFrame()
        search_card.setObjectName("card")
        search_card.setFixedHeight(44)
        sc_lay = QHBoxLayout(search_card)
        sc_lay.setContentsMargins(14, 0, 14, 0)
        sc_lay.setSpacing(10)

        icon = QLabel("🔍")
        icon.setStyleSheet("background:transparent;")
        sc_lay.addWidget(icon)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Поиск по имени или PID…")
        self._search.setStyleSheet("QLineEdit { background:transparent; border:none; color:#e8ddd0; font-size:13px; }")
        self._search.textChanged.connect(self._on_filter_text_changed)
        sc_lay.addWidget(self._search, 1)

        clear_btn = QPushButton("✕")
        clear_btn.setFixedSize(24, 24)
        clear_btn.setStyleSheet(
            "QPushButton { background:transparent; color:#5a5248; border:none; font-size:13px; font-weight:bold; }"
            "QPushButton:hover { color:#f5a623; }"
        )
        clear_btn.clicked.connect(lambda: self._search.clear())
        sc_lay.addWidget(clear_btn)

        self._content.addWidget(search_card)

        # ══════════════════════════════════════════════════════════════ #
        #  3. TOOLBAR — чекбоксы + кнопки группировки                     #
        # ══════════════════════════════════════════════════════════════ #
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        from widgets import GalahhadToggle
        self._cb_auto = GalahhadToggle("Авто-обновление")
        self._cb_auto.toggled.connect(self._toggle_auto_refresh)
        toolbar.addWidget(self._cb_auto)

        self._cb_tree = GalahhadToggle("С дочерними")
        self._cb_tree.setToolTip("Завершать вместе с дочерними процессами")
        toolbar.addWidget(self._cb_tree)

        toolbar.addStretch()

        lbl_group = QLabel("Группа:")
        lbl_group.setStyleSheet("color:#5a5248; font-size:11px; font-weight:600; background:transparent;")
        toolbar.addWidget(lbl_group)

        self._group_btns = []
        for i, (label, _key) in enumerate([
            ("Приложения", "apps"), ("Нет", "none"),
            ("Пользователь", "user"), ("Статус", "status"),
        ]):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(i == _GROUP_APPS)
            b.clicked.connect(lambda checked, idx=i: self._set_group(idx))
            b._style_normal = _GROUP_BTN_NORMAL
            b._style_active = _GROUP_BTN_ACTIVE
            b.setStyleSheet(_GROUP_BTN_ACTIVE if i == _GROUP_APPS else _GROUP_BTN_NORMAL)
            toolbar.addWidget(b)
            self._group_btns.append(b)

        self._content.addLayout(toolbar)

        # ══════════════════════════════════════════════════════════════ #
        #  4. PROCESS TABLE — стиль Windows 11 Task Manager             #
        #     Порядок колонок как в скриншоте: Имя/Статус/CPU/Память/   #
        #     Диск — плюс Пользователь и PID справа (их нет в скрине,   #
        #     но они нужны для группировки/выделения и уже были в UI).  #
        # ══════════════════════════════════════════════════════════════ #
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["Имя", "Статус", "CPU %", "Память (МБ)", "Диск (МБ/с)", "Пользователь", "PID"]
        )
        self._table.setStyleSheet(TABLE_QSS)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.setSelectionBehavior(SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(38)
        self._table.setFrameShape(NoFrame)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._context_menu)

        COL_NAME, COL_STATUS, COL_CPU, COL_MEM, COL_DISK, COL_USER, COL_PID = range(7)
        self._COL_PID = COL_PID

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(COL_NAME, Stretch)
        hdr.setSectionResizeMode(COL_STATUS, QHeaderView.Fixed);  hdr.resizeSection(COL_STATUS, 90)
        hdr.setSectionResizeMode(COL_CPU, QHeaderView.Fixed);     hdr.resizeSection(COL_CPU, 70)
        hdr.setSectionResizeMode(COL_MEM, QHeaderView.Fixed);     hdr.resizeSection(COL_MEM, 110)
        hdr.setSectionResizeMode(COL_DISK, QHeaderView.Fixed);    hdr.resizeSection(COL_DISK, 100)
        hdr.setSectionResizeMode(COL_USER, QHeaderView.Fixed);    hdr.resizeSection(COL_USER, 120)
        hdr.setSectionResizeMode(COL_PID, QHeaderView.Fixed);     hdr.resizeSection(COL_PID, 70)
        hdr.setHighlightSections(False)

        self._table.selectionModel().selectionChanged.connect(self._update_status)
        self._content.addWidget(self._table, 1)

        # ══════════════════════════════════════════════════════════════ #
        #  5. BOTTOM BAR — кнопки действий + статистика                   #
        # ══════════════════════════════════════════════════════════════ #
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self._lbl_count = QLabel("Процессов: 0")
        self._lbl_count.setStyleSheet("color:#7a7068; font-size:12px; font-weight:600; background:transparent;")
        bar.addWidget(self._lbl_count)

        self._lbl_cpu = QLabel("CPU: 0%")
        self._lbl_cpu.setStyleSheet("color:#4caf7d; font-size:12px; background:transparent;")
        bar.addWidget(self._lbl_cpu)

        self._lbl_mem = QLabel("Память: 0 ГБ")
        self._lbl_mem.setStyleSheet("color:#5b9df0; font-size:12px; background:transparent;")
        bar.addWidget(self._lbl_mem)

        self._lbl_sel = QLabel("")
        self._lbl_sel.setStyleSheet("color:#f5a623; font-size:12px; font-weight:600; background:transparent;")
        bar.addWidget(self._lbl_sel)

        bar.addStretch()

        b_ref = self._reg_btn(self.btn("🔄 Обновить"))
        b_ref.setFixedHeight(36)
        b_ref.clicked.connect(self._refresh)
        bar.addWidget(b_ref)

        self._b_kill = self._reg_btn(self.btn("⛔ Завершить", obj="btn_danger"))
        self._b_kill.setFixedHeight(36)
        self._b_kill.clicked.connect(self._kill_selected)
        bar.addWidget(self._b_kill)

        self._b_tree = self._reg_btn(self.btn("🌳 Дерево", obj="btn_danger"))
        self._b_tree.setFixedHeight(36)
        self._b_tree.clicked.connect(self._kill_tree)
        bar.addWidget(self._b_tree)

        self._b_killall = self._reg_btn(self.btn("☠️ ВСЕ", obj="btn_danger"))
        self._b_killall.setFixedHeight(36)
        self._b_killall.clicked.connect(self._kill_all)
        bar.addWidget(self._b_killall)

        self._content.addLayout(bar)

        # Timer
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(2000)
        self._auto_timer.timeout.connect(self._auto_tick)

        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(150)
        self._filter_timer.timeout.connect(self._apply_filter)

        self._refresh()

    # ── Stats ──────────────────────────────────────────────────────── #
    def _update_stats(self, count, cpu, mem):
        cpu_pct = min(cpu / self._cpu_count(), 100.0)
        mem_gb = mem / 1024.0
        running = sum(1 for p in self._procs if p.get("status") == "Running")
        protected = sum(1 for p in self._procs if p.get("protected", False))

        self._stat_procs_val.setText(str(count))

        cpu_c = "#e05252" if cpu_pct > 80 else "#f5c842" if cpu_pct > 50 else "#4caf7d"
        self._stat_cpu_val.setText("{:.0f}%".format(cpu_pct))
        self._stat_cpu_val.setStyleSheet("color:{}; font-size:20px; font-weight:800; background:transparent;".format(cpu_c))

        mem_c = "#e05252" if mem_gb > 12 else "#f5c842" if mem_gb > 8 else "#5b9df0"
        self._stat_mem_val.setText("{:.1f} ГБ".format(mem_gb))
        self._stat_mem_val.setStyleSheet("color:{}; font-size:20px; font-weight:800; background:transparent;".format(mem_c))

        self._stat_active_val.setText(str(running))
        self._stat_protected_val.setText(str(protected))

    # ── Group ──────────────────────────────────────────────────────── #
    def _set_group(self, idx):
        self._group_mode = idx
        self._collapsed_groups.clear()
        for i, b in enumerate(self._group_btns):
            b.setChecked(i == idx)
            b.setStyleSheet(b._style_active if i == idx else b._style_normal)
        self._refresh()

    def _toggle_group_collapse(self, group_key):
        if group_key in self._collapsed_groups:
            self._collapsed_groups.discard(group_key)
        else:
            self._collapsed_groups.add(group_key)
        self._fill_table(self._procs)

    # ── Refresh ────────────────────────────────────────────────────── #
    def _refresh(self):
        self._run_worker(_fn_list, on_result=self._on_list_result)

    def _auto_tick(self):
        if self._worker and self._worker.isRunning():
            return
        self._run_worker(_fn_list, quiet=True, on_result=self._on_list_result)

    def _on_list_result(self, result):
        """Разбирает результат _fn_list: список процессов идёт в
        таблицу, системный снимок (snapshot) — в баннер устройства."""
        self._update_banner(result.get("snapshot") or {})
        self._fill_table(result.get("procs") or [])

    def _update_banner(self, snapshot):
        if not snapshot:
            return
        cpu = snapshot.get("cpu_percent", 0.0)
        mem = snapshot.get("ram_percent", 0.0)
        disk = snapshot.get("disk_read_mbs", 0.0) + snapshot.get("disk_write_mbs", 0.0)
        net_kbs = snapshot.get("net_down_kbs", 0.0) + snapshot.get("net_up_kbs", 0.0)

        self._banner_badges["cpu"].setText("{:.0f}%".format(cpu))
        self._banner_badges["mem"].setText("{:.0f}%".format(mem))
        self._banner_badges["disk"].setText("{:.1f} МБ/с".format(disk))
        if net_kbs >= 1024:
            self._banner_badges["net"].setText("{:.1f} МБ/с".format(net_kbs / 1024.0))
        else:
            self._banner_badges["net"].setText("{:.0f} КБ/с".format(net_kbs))

    def _toggle_auto_refresh(self, checked):
        self._auto_refresh = checked
        if checked:
            self._auto_timer.start()
            self.log("Авто-обновление включено (2 сек).")
        else:
            self._auto_timer.stop()
            self.log("Авто-обновление выключено.")

    def showEvent(self, e):
        if self._auto_refresh:
            self._auto_timer.start()
        super().showEvent(e)

    def hideEvent(self, e):
        self._auto_timer.stop()
        super().hideEvent(e)

    # ── CPU count ──────────────────────────────────────────────────── #
    def _cpu_count(self):
        try:
            from modules.processes import _CPU_COUNT
            return _CPU_COUNT
        except Exception:
            return 1

    # ── Table ──────────────────────────────────────────────────────── #
    def _fill_table(self, procs):
        self._procs = procs
        selected_pids = self._selected_pids()

        self._table.setSortingEnabled(False)

        mono = QFont("Consolas", 11)
        bold = QFont()
        bold.setBold(True)

        total_cpu = 0.0
        total_mem = 0.0
        NUM_COLS = 7

        # Build row descriptors first
        if self._group_mode == _GROUP_APPS:
            apps = [p for p in procs if p.get("is_app")]
            bg = [p for p in procs if not p.get("is_app")]
            groups = [
                ("Приложения", apps),
                ("Фоновые процессы", bg),
            ]
        elif self._group_mode == _GROUP_NONE:
            groups = [(None, procs)]
        elif self._group_mode == _GROUP_USER:
            ug = {}
            for p in procs:
                u = p.get("user") or "—"
                ug.setdefault(u, []).append(p)
            groups = sorted(ug.items(), key=lambda x: x[0].lower())
        else:
            sg = {}
            for p in procs:
                s = p.get("status") or "Running"
                sg.setdefault(s, []).append(p)
            groups = [("Running", sg.get("Running", [])), ("Suspended", sg.get("Suspended", []))]

        rows = []  # list of (type, data) tuples
        for grp_label, grp_procs in groups:
            if grp_label is not None and self._group_mode != _GROUP_NONE:
                is_collapsed = grp_label in self._collapsed_groups
                rows.append(("header", grp_label, len(grp_procs), is_collapsed))
                if is_collapsed:
                    continue
            for p in grp_procs:
                mem = p["memory_mb"]
                cpu = p["cpu_percent"]
                disk = p.get("disk_mb_s", 0.0)
                total_cpu += cpu
                total_mem += mem
                protected = p.get("protected", False)
                name_text = ("🔒 " + p["name"]) if protected else p["name"]
                vals = [
                    name_text,
                    p.get("status", "—"),
                    "{:.1f}".format(cpu),
                    "{:.1f}".format(mem),
                    "{:.2f}".format(disk) if disk > 0.005 else "—",
                    p.get("user", "—"),
                    str(p["pid"]),
                ]
                rows.append(("data", vals, cpu, mem, disk, protected, p["pid"]))

        # Differential update: if row count matches, update in place
        old_count = self._table.rowCount()
        new_count = len(rows)
        differential = (old_count == new_count and old_count > 0)

        if not differential:
            self._table.setRowCount(0)

        for i, row_desc in enumerate(rows):
            if row_desc[0] == "header":
                _, grp_label, count, is_collapsed = row_desc
                arrow = "▶" if is_collapsed else "▼"
                group_key = grp_label
                if not differential:
                    r = self._table.rowCount()
                    self._table.insertRow(r)
                else:
                    r = i
                    self._table.setSpan(r, 0, 1, 1)  # reset span
                h = QTableWidgetItem("  {}  {}  ({})".format(arrow, grp_label, count))
                h.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                h.setBackground(QColor(20, 22, 30))
                h.setForeground(QColor(158, 148, 136))
                f = QFont("Segoe UI", 11)
                f.setBold(True)
                h.setFont(f)
                h.setData(Qt.UserRole, "group_{}".format(grp_label))
                h.setData(Qt.UserRole + 1, group_key)
                self._table.setItem(r, 0, h)
                self._table.setSpan(r, 0, 1, NUM_COLS)
            else:
                _, vals, cpu, mem, disk, protected, pid = row_desc
                if not differential:
                    r = self._table.rowCount()
                    self._table.insertRow(r)
                else:
                    r = i
                    self._table.setSpan(r, 0, 1, 1)  # reset span

                for col, val in enumerate(vals):
                    item = _NumericItem(val) if col in (2, 3, 4, 6) else QTableWidgetItem(val)
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                    if col == 0:
                        item.setForeground(QColor("#e05252" if protected else "#e8ddd0"))
                    elif col == 1:
                        sc = _STATUS_COLORS.get(val, "#a09888")
                        item.setForeground(QColor(sc))
                        item.setFont(bold)
                    elif col == 2:
                        c = "#e05252" if cpu > 50 else "#f5c842" if cpu > 20 else "#c0b8b0"
                        item.setForeground(QColor(c))
                        if cpu > 20:
                            item.setFont(bold)
                        item.setTextAlignment(AlignRight | AlignVCenter)
                        item.setData(Qt.UserRole, cpu)
                        if cpu > 50:
                            item.setBackground(QColor(224, 82, 82, 22))
                        elif cpu > 20:
                            item.setBackground(QColor(245, 166, 35, 16))
                    elif col == 3:
                        c = "#e05252" if mem > 500 else "#f5a623" if mem > 200 else "#c8d8c0"
                        item.setForeground(QColor(c))
                        item.setTextAlignment(AlignRight | AlignVCenter)
                        item.setData(Qt.UserRole, mem)
                        if mem > 500:
                            item.setBackground(QColor(224, 82, 82, 22))
                        elif mem > 200:
                            item.setBackground(QColor(245, 166, 35, 16))
                    elif col == 4:
                        c = "#5b9df0" if disk > 1.0 else "#a09888"
                        item.setForeground(QColor(c))
                        item.setTextAlignment(AlignRight | AlignVCenter)
                        item.setData(Qt.UserRole, disk)
                        if disk > 5.0:
                            item.setBackground(QColor(91, 157, 240, 20))
                    elif col == 5:
                        item.setForeground(QColor("#c0b8b0"))
                    elif col == 6:
                        item.setForeground(QColor("#c0b8b0"))
                        item.setFont(mono)
                        item.setTextAlignment(AlignRight | AlignVCenter)
                        item.setData(Qt.UserRole, float(pid))

                    self._table.setItem(r, col, item)

        self._table.setSortingEnabled(True)
        self._update_stats(len(procs), total_cpu, total_mem)
        self._lbl_count.setText("Процессов: {}".format(len(procs)))
        normalized_cpu = min(total_cpu / self._cpu_count(), 100.0)
        self._lbl_cpu.setText("CPU: {:.0f}%".format(normalized_cpu))
        self._lbl_mem.setText("Память: {:.1f} ГБ".format(total_mem / 1024.0))
        self._apply_filter()
        self._restore_selection(selected_pids)

    def _on_filter_text_changed(self, _text):
        self._filter_timer.start()

    def _apply_filter(self, text=None):
        if text is None:
            text = self._search.text()
        text = text.lower().strip()
        vis = 0
        for r in range(self._table.rowCount()):
            it = self._table.item(r, 0)
            hide = bool(text) and (it is None or text not in it.text().lower())
            self._table.setRowHidden(r, hide)
            if not hide:
                vis += 1
        if text:
            self._lbl_count.setText("Показано: {} / {}".format(vis, self._table.rowCount()))
        else:
            self._lbl_count.setText("Процессов: {}".format(self._table.rowCount()))

    # ── Selection ──────────────────────────────────────────────────── #
    def _selected_pids(self):
        pids = []
        for idx in self._table.selectionModel().selectedRows():
            item = self._table.item(idx.row(), self._COL_PID)
            if item:
                try:
                    pids.append(int(item.text()))
                except ValueError:
                    pass
        return pids

    def _restore_selection(self, pids):
        if not pids:
            return
        wanted = set(pids)
        for r in range(self._table.rowCount()):
            item = self._table.item(r, self._COL_PID)
            if item:
                try:
                    if int(item.text()) in wanted:
                        self._table.selectRow(r)
                except ValueError:
                    pass

    def _update_status(self):
        n = len(self._table.selectionModel().selectedRows())
        self._lbl_sel.setText("Выбрано: {}".format(n) if n else "")
        self._b_kill.setEnabled(n > 0)
        self._b_tree.setEnabled(n > 0)

    # ── Context menu ───────────────────────────────────────────────── #
    def _context_menu(self, pos):
        rows = sorted({idx.row() for idx in self._table.selectionModel().selectedRows()})
        if not rows:
            return
        items = []
        for row in rows:
            pid_item = self._table.item(row, self._COL_PID)
            name_item = self._table.item(row, 0)
            if pid_item and name_item:
                try:
                    raw_name = name_item.text().replace("🔒 ", "")
                    items.append((int(pid_item.text()), raw_name))
                except ValueError:
                    pass
        if not items:
            return

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu {{ background:#14161e; color:#e8ddd0; border:1px solid rgba(245,166,35,0.15);"
            "border-radius:8px; padding:4px; font-size:12px; }}"
            "QMenu::item {{ padding:8px 20px; border-radius:4px; }}"
            "QMenu::item:selected {{ background:rgba(245,166,35,0.12); color:#f5a623; }}"
        )
        a_end = menu.addAction("⛔  Завершить")
        a_tree = menu.addAction("🌳  Завершить дерево")
        menu.addSeparator()
        a_info = menu.addAction("ℹ️  Свойства")

        action = menu.exec_(self._table.viewport().mapToGlobal(pos))
        if action == a_end:
            self._confirm_and_kill(items, with_children=False)
        elif action == a_tree:
            self._confirm_and_kill(items, with_children=True)
        elif action == a_info:
            self._show_properties(items[0] if items else None)

    def _show_properties(self, item):
        if not item:
            return
        pid, name = item
        info = "PID: {}\nИмя: {}".format(pid, name)
        for p in self._procs:
            if p["pid"] == pid:
                info += "\nСтатус: {}".format(p.get("status", "—"))
                info += "\nПользователь: {}".format(p.get("user", "—"))
                info += "\nПамять: {:.1f} МБ".format(p.get("memory_mb", 0))
                info += "\nCPU: {:.1f}%".format(p.get("cpu_percent", 0))
                info += "\nЗащищён: {}".format("Да" if p.get("protected") else "Нет")
                break
        QMessageBox.information(self, "Свойства процесса", info)

    # ── Kill ───────────────────────────────────────────────────────── #
    def _kill_selected(self):
        rows = sorted({idx.row() for idx in self._table.selectionModel().selectedRows()})
        if not rows:
            self.log("Выберите процесс(ы) в таблице.", "WARN")
            return
        items = []
        for row in rows:
            pid_item = self._table.item(row, self._COL_PID)
            name_item = self._table.item(row, 0)
            if pid_item and name_item:
                try:
                    raw_name = name_item.text().replace("🔒 ", "")
                    items.append((int(pid_item.text()), raw_name))
                except ValueError:
                    pass
        self._confirm_and_kill(items, with_children=self._cb_tree.isChecked())

    def _kill_tree(self):
        rows = sorted({idx.row() for idx in self._table.selectionModel().selectedRows()})
        if not rows:
            self.log("Выберите процесс для завершения дерева.", "WARN")
            return
        items = []
        for row in rows:
            pid_item = self._table.item(row, self._COL_PID)
            name_item = self._table.item(row, 0)
            if pid_item and name_item:
                try:
                    raw_name = name_item.text().replace("🔒 ", "")
                    items.append((int(pid_item.text()), raw_name))
                except ValueError:
                    pass
        self._confirm_and_kill(items, with_children=True)

    def _kill_all(self):
        if not self._procs:
            self.log("Список процессов пуст.", "WARN")
            return
        killable = [(p["pid"], p["name"]) for p in self._procs if not p.get("protected", False)]
        if not killable:
            self.log("Нет процессов для завершения (все защищены).", "WARN")
            return
        question = "⚠️  Завершить ВСЕ {} процессов?\nСистемные и защищённые (🔒) НЕ будут затронуты.".format(len(killable))
        if QMessageBox.question(
            self, "Завершить ВСЕ", question,
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel
        ) != QMessageBox.Yes:
            return
        self.log("Завершение {} процессов...".format(len(killable)), "WARN")
        pids = [pid for pid, _ in killable]
        self._run_worker(
            _fn_kill_many, pids, with_children=False, force=False,
            on_done=lambda: QTimer.singleShot(800, self._refresh),
        )

    def _confirm_and_kill(self, items, with_children=False):
        if len(items) == 1:
            pid, name = items[0]
            question = "Завершить «{}» (PID {})?".format(name, pid)
        else:
            names = ", ".join(n for _, n in items[:5])
            more = "" if len(items) <= 5 else " и ещё {}".format(len(items) - 5)
            question = "Завершить {} процесса(ов)?\n{}{}".format(len(items), names, more)
        if with_children:
            question += "\n\nВместе с дочерними процессами."

        if QMessageBox.question(
            self, "Завершить", question,
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return

        pids = [pid for pid, _ in items]
        self._run_worker(
            _fn_kill_many, pids, with_children=with_children,
            on_done=lambda: QTimer.singleShot(600, self._refresh),
        )

    # ── Keyboard ───────────────────────────────────────────────────── #
    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Delete:
            self._kill_selected()
        else:
            super().keyPressEvent(e)


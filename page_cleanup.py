"""Очистка системы."""
from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QCheckBox, QGroupBox, QMessageBox,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from base_page import BasePage
from theme import TABLE_QSS
from widgets import UiverseToggle
from qt_compat import *


def _fn_cleanup(log_func, progress_func,
                include_update_cache, include_all_disks, clean_prefetch,
                include_user_temp, include_system_temp, include_recycle_bin):
    from modules.cleanup import run_full_cleanup
    from modules.action_log import log_action
    result = run_full_cleanup(log_func, progress_func,
                     include_update_cache=include_update_cache,
                     include_all_disks=include_all_disks,
                     clean_prefetch_flag=clean_prefetch,
                     include_user_temp=include_user_temp,
                     include_system_temp=include_system_temp,
                     include_recycle_bin=include_recycle_bin)
    log_action("cleanup", "Полная очистка системы: {} байт".format(result))


def _fn_estimate(log_func, progress_func):
    from modules.cleanup import estimate_junk_size
    return estimate_junk_size(log_func, progress_func)


def _fn_detect_browsers(log_func, progress_func):
    from modules.cleanup import detect_installed_browsers
    progress_func(1.0)
    return detect_installed_browsers()


def _fn_clean_browsers(log_func, progress_func, browsers):
    from modules.cleanup import clean_browser_cache
    return clean_browser_cache(log_func, progress_func, browsers=browsers)


def _fn_find_duplicates(log_func, progress_func, root_dir, min_size_kb):
    from modules.cleanup import find_duplicate_files
    return find_duplicate_files(log_func, progress_func, root_dir,
                                min_size_bytes=min_size_kb * 1024)


def _fn_delete_duplicates(log_func, progress_func, files):
    from modules.cleanup import delete_duplicate_files
    return delete_duplicate_files(log_func, progress_func, files)


class CleanupPage(BasePage):
    PAGE_TITLE = "🧹  Очистка системы"
    PAGE_SUB   = "Temp-файлы, кэш обновлений Windows, кэш браузеров, дубликаты и корзина"

    def build_ui(self):
        # ── Базовая очистка ─────────────────────────────────────────── #
        grp = QGroupBox("Системная очистка")
        glay = QVBoxLayout(grp)
        glay.setSpacing(10)

        from widgets import GalahhadToggle
        self._cb_temp    = GalahhadToggle("Temp пользователя  (%TEMP%)", accent="#14b8a6")
        self._cb_wtemp   = GalahhadToggle("Системный Temp  (C:\\Windows\\Temp)", accent="#3b82f6")
        self._cb_cache   = GalahhadToggle("Кэш обновлений Windows", accent="#a78bfa")
        self._cb_all     = GalahhadToggle("Temp-папки на всех дисках", accent="#22d3ee")
        self._cb_pref    = GalahhadToggle("Prefetch  (C:\\Windows\\Prefetch)", accent="#f59e0b")
        self._cb_recycle = GalahhadToggle("Корзина", accent="#ef4444")

        for cb in (self._cb_temp, self._cb_wtemp, self._cb_cache,
                   self._cb_all, self._cb_pref, self._cb_recycle):
            cb.setChecked(True)
            glay.addWidget(cb)

        self._content.addWidget(grp)

        row = QHBoxLayout()
        b_run = self._reg_btn(self.btn("🧹  Запустить очистку"))
        b_run.setFixedHeight(42)
        b_run.setStyleSheet(
            "background: #00ff88; color: #0a0e14; font-weight: 700; "
            "font-size: 14px; border-radius: 10px; border: none; padding: 10px 28px;"
        )
        b_run.clicked.connect(self._run)
        row.addWidget(b_run)

        b_est = self._reg_btn(self.btn("📊  Оценить объём мусора"))
        b_est.setFixedHeight(42)
        b_est.setStyleSheet(
            "background: #fbbf24; color: #0a0e14; font-weight: 700; "
            "font-size: 14px; border-radius: 10px; border: none; padding: 10px 28px;"
        )
        b_est.clicked.connect(self._estimate)
        row.addWidget(b_est)

        # Кнопка "Выбрать папку" для ручного выбора папки для очистки
        b_folder = self.btn("📁  Выбрать папку")
        b_folder.setStyleSheet(
            "background: rgba(0,255,136,0.15); color: #00ff88; font-weight: 700; "
            "font-size: 13px; border-radius: 10px; border: 1px solid rgba(0,255,136,0.25); padding: 10px 24px;"
        )
        b_folder.clicked.connect(self._choose_folder)
        row.addWidget(b_folder)

        row.addStretch()
        self._content.addLayout(row)

        # ── Кэш браузеров ───────────────────────────────────────────── #
        browser_grp = QGroupBox("Кэш браузеров")
        bgl = QVBoxLayout(browser_grp)
        bgl.setSpacing(8)

        bhint = QLabel(
            "Удаляется только кэш (Cache/Code Cache) — пароли, история и закладки "
            "не трогаются. Рекомендуется закрыть браузер перед очисткой."
        )
        bhint.setWordWrap(True)
        bhint.setStyleSheet("color:#6a6258; font-size:11px; background:transparent;")
        bgl.addWidget(bhint)

        self._browser_checks_layout = QVBoxLayout()
        bgl.addLayout(self._browser_checks_layout)
        self._browser_checks = {}
        self._browser_placeholder = QLabel("Нажмите «Найти браузеры», чтобы увидеть установленные.")
        self._browser_placeholder.setStyleSheet("color:#6a6258; font-size:11px; background:transparent;")
        self._browser_checks_layout.addWidget(self._browser_placeholder)

        b_row = QHBoxLayout()
        b_detect = self.btn("🔍  Найти браузеры")
        b_detect.setStyleSheet(
            "background: rgba(0,255,136,0.15); color: #00ff88; font-weight: 700; "
            "font-size: 13px; border-radius: 10px; border: 1px solid rgba(0,255,136,0.25); padding: 10px 24px;"
        )
        b_detect.clicked.connect(self._detect_browsers)
        b_row.addWidget(b_detect)

        self._b_clean_browsers = self._reg_btn(self.btn("🧽  Очистить кэш браузеров"))
        self._b_clean_browsers.setStyleSheet(
            "background: rgba(0,255,136,0.15); color: #00ff88; font-weight: 700; "
            "font-size: 13px; border-radius: 10px; border: 1px solid rgba(0,255,136,0.25); padding: 10px 24px;"
        )
        self._b_clean_browsers.clicked.connect(self._clean_browsers)
        self._b_clean_browsers.setEnabled(False)
        b_row.addWidget(self._b_clean_browsers)
        b_row.addStretch()
        bgl.addLayout(b_row)

        self._content.addWidget(browser_grp)

        # ── Поиск дублей файлов ─────────────────────────────────────── #
        dup_grp = QGroupBox("Поиск дублей файлов")
        dgl = QVBoxLayout(dup_grp)
        dgl.setSpacing(8)

        dhint = QLabel(
            "Ищет файлы с одинаковым содержимым (по хешу SHA-256) в указанной "
            "папке и подпапках. Полезно для папок «Загрузки», «Документы», фотоархивов."
        )
        dhint.setWordWrap(True)
        dhint.setStyleSheet("color:#6a6258; font-size:11px; background:transparent;")
        dgl.addWidget(dhint)

        path_row = QHBoxLayout()
        self._dup_path = QLineEdit()
        self._dup_path.setPlaceholderText("Папка для поиска дублей…")
        path_row.addWidget(self._dup_path, 1)
        b_browse = QPushButton("…")
        b_browse.setFixedWidth(34)
        b_browse.clicked.connect(self._browse_dup_folder)
        path_row.addWidget(b_browse)
        dgl.addLayout(path_row)

        find_row = QHBoxLayout()
        self._b_find_dup = self._reg_btn(self.btn("🔎  Найти дубли"))
        self._b_find_dup.setStyleSheet(
            "background: #fbbf24; color: #0a0e14; font-weight: 700; "
            "font-size: 13px; border-radius: 10px; border: none; padding: 10px 24px;"
        )
        self._b_find_dup.clicked.connect(self._find_duplicates)
        find_row.addWidget(self._b_find_dup)

        self._b_delete_dup = self._reg_btn(self.btn("🗑  Удалить отмеченные"))
        self._b_delete_dup.setStyleSheet(
            "background: #ff4444; color: #fff; font-weight: 700; "
            "font-size: 13px; border-radius: 10px; border: none; padding: 10px 24px;"
        )
        self._b_delete_dup.clicked.connect(self._delete_duplicates)
        self._b_delete_dup.setEnabled(False)
        find_row.addWidget(self._b_delete_dup)
        find_row.addStretch()
        dgl.addLayout(find_row)

        self._dup_table = QTableWidget(0, 3)
        self._dup_table.setHorizontalHeaderLabels(["ОСТАВИТЬ", "ФАЙЛ", "РАЗМЕР"])
        self._dup_table.setStyleSheet(TABLE_QSS)
        self._dup_table.setShowGrid(False)
        self._dup_table.setSelectionBehavior(SelectRows)
        self._dup_table.setEditTriggers(NoEditTriggers)
        self._dup_table.verticalHeader().setVisible(False)
        self._dup_table.verticalHeader().setDefaultSectionSize(32)
        self._dup_table.setFrameShape(NoFrame)
        self._dup_table.setFixedHeight(180)
        hdr = self._dup_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Fixed); hdr.resizeSection(0, 70)
        hdr.setSectionResizeMode(1, Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.Fixed); hdr.resizeSection(2, 90)
        dgl.addWidget(self._dup_table)

        self._dup_summary = QLabel("")
        self._dup_summary.setStyleSheet("color:#a8a098; font-size:11px; background:transparent;")
        dgl.addWidget(self._dup_summary)

        self._content.addWidget(dup_grp)
        self._content.addStretch()

        self._dup_groups = []     # последний результат find_duplicate_files
        self._dup_row_meta = []   # [(group_idx, file_path), ...] параллельно строкам таблицы

    # ── Базовая очистка ──────────────────────────────────────────────── #
    def _run(self):
        cbs = (self._cb_temp, self._cb_wtemp, self._cb_cache,
               self._cb_all, self._cb_pref, self._cb_recycle)
        if not any(cb.isChecked() for cb in cbs):
            self.log("Не выбрано ни одного пункта для очистки.", "WARN")
            return

        dlg = QMessageBox(self)
        dlg.setWindowTitle("Очистка системы")
        dlg.setText("Выбранные файлы будут безвозвратно удалены.\nПродолжить?")
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dlg.setDefaultButton(QMessageBox.No)
        if dlg.exec() != QMessageBox.Yes:
            return
        self._run_worker(
            _fn_cleanup,
            include_update_cache=self._cb_cache.isChecked(),
            include_all_disks=self._cb_all.isChecked(),
            clean_prefetch=self._cb_pref.isChecked(),
            include_user_temp=self._cb_temp.isChecked(),
            include_system_temp=self._cb_wtemp.isChecked(),
            include_recycle_bin=self._cb_recycle.isChecked(),
        )

    def _estimate(self):
        self._run_worker(_fn_estimate)

    def _choose_folder(self):
        """Открывает диалог выбора папки для ручной очистки."""
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку для очистки", "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if folder:
            self.log("Выбрана папка: {}".format(folder), "INFO")
            # Очищаем выбранную папку
            from modules.cleanup import _safe_remove_tree
            from pathlib import Path
            import os
            freed = 0
            for entry in os.scandir(folder):
                try:
                    if entry.is_dir():
                        import shutil
                        size = sum(
                            f.stat().st_size for f in Path(entry.path).rglob("*") if f.is_file()
                        )
                        shutil.rmtree(entry.path, ignore_errors=True)
                        freed += size
                    else:
                        size = Path(entry.path).stat().st_size
                        os.unlink(entry.path)
                        freed += size
                except (PermissionError, OSError) as exc:
                    self.log("  [пропущено] {}: {}".format(entry.name, exc.__class__.__name__), "WARN")

            from modules.cleanup import human_size
            self.log("Очистка папки завершена. Освобождено: {}".format(human_size(freed)), "OK")

    # ── Кэш браузеров ──────────────────────────────────────────────────── #
    def _detect_browsers(self):
        self._run_worker(_fn_detect_browsers, on_result=self._fill_browsers)

    def _fill_browsers(self, browsers):
        while self._browser_checks_layout.count():
            item = self._browser_checks_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        self._browser_checks = {}

        if not browsers:
            lbl = QLabel("Установленные браузеры с кэшем не найдены.")
            lbl.setStyleSheet("color:#7a7068; font-size:11px; background:transparent;")
            self._browser_checks_layout.addWidget(lbl)
            self._b_clean_browsers.setEnabled(False)
            return

        from widgets import GalahhadToggle
        for name in browsers:
            cb = GalahhadToggle(name)
            cb.setChecked(True)
            self._browser_checks_layout.addWidget(cb)
            self._browser_checks[name] = cb

        self._b_clean_browsers.setEnabled(True)

    def _clean_browsers(self):
        selected = [name for name, cb in self._browser_checks.items() if cb.isChecked()]
        if not selected:
            self.log("Не выбрано ни одного браузера.", "WARN")
            return
        if QMessageBox.question(
            self, "Очистка кэша браузеров",
            "Очистить кэш для: {}?\n\nРекомендуется закрыть эти браузеры перед очисткой "
            "— иначе часть файлов кэша может быть пропущена.".format(", ".join(selected)),
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        self._run_worker(_fn_clean_browsers, browsers=selected)

    # ── Поиск дублей файлов ────────────────────────────────────────────── #
    def _browse_dup_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку для поиска дублей")
        if path:
            self._dup_path.setText(path)

    def _find_duplicates(self):
        root = self._dup_path.text().strip()
        if not root:
            self.log("Укажите папку для поиска дублей.", "WARN")
            return
        self._dup_table.setRowCount(0)
        self._b_delete_dup.setEnabled(False)
        self._run_worker(_fn_find_duplicates, root, 1, on_result=self._fill_duplicates)

    def _fill_duplicates(self, groups):
        self._dup_groups = groups
        self._dup_row_meta = []

        if not groups:
            self._dup_table.setRowCount(0)
            self._dup_summary.setText("Дубликаты не найдены.")
            self._b_delete_dup.setEnabled(False)
            return

        rows = []
        for gi, g in enumerate(groups):
            for fi, f in enumerate(g["files"]):
                rows.append((gi, fi, f, g["size"]))

        self._dup_table.setRowCount(len(rows))
        bold = QFont(); bold.setBold(True)

        for r, (gi, fi, f, size) in enumerate(rows):
            cb = QTableWidgetItem()
            cb.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            cb.setCheckState(Qt.Checked if fi == 0 else Qt.Unchecked)
            cb.setTextAlignment(AlignCenter)
            self._dup_table.setItem(r, 0, cb)

            name_item = QTableWidgetItem(f)
            name_item.setForeground(QColor("#a8a098" if fi == 0 else "#ddd8d0"))
            if fi == 0:
                name_item.setFont(bold)
            self._dup_table.setItem(r, 1, name_item)

            size_item = QTableWidgetItem(self._human_size(size))
            size_item.setForeground(QColor("#7a7068"))
            size_item.setTextAlignment(AlignRight | AlignVCenter)
            self._dup_table.setItem(r, 2, size_item)

            self._dup_row_meta.append((gi, fi, f))

        total_wasted = sum(g["wasted"] for g in groups)
        self._dup_summary.setText(
            "Найдено групп: {}. Первый файл в каждой группе (●) будет сохранён, "
            "остальные пойдут на удаление. Потенциально свободно: {}.".format(
                len(groups), self._human_size(total_wasted)
            )
        )
        self._b_delete_dup.setEnabled(True)

    @staticmethod
    def _human_size(n):
        for unit in ("Б", "КБ", "МБ", "ГБ"):
            if n < 1024:
                return "{:.1f} {}".format(n, unit)
            n /= 1024
        return "{:.1f} ТБ".format(n)

    def _delete_duplicates(self):
        # Delete files where the checkbox is unchecked
        to_delete = []
        for r, (gi, fi, f) in enumerate(self._dup_row_meta):
            item = self._dup_table.item(r, 0)
            if item and item.checkState() == Qt.Unchecked:
                to_delete.append(f)
        if not to_delete:
            self.log("Нет файлов для удаления.", "WARN")
            return
        if QMessageBox.question(
            self, "Удаление дублей",
            "Будет удалено {} файлов (отмеченные ● останутся).\n"
            "Это действие необратимо. Продолжить?".format(len(to_delete)),
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        self._run_worker(_fn_delete_duplicates, to_delete, on_done=self._after_delete_duplicates)

    def _after_delete_duplicates(self):
        self._dup_table.setRowCount(0)
        self._dup_groups = []
        self._dup_row_meta = []
        self._dup_summary.setText("Дубликаты удалены. Запустите поиск повторно для проверки.")
        self._b_delete_dup.setEnabled(False)


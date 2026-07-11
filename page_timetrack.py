"""
page_timetrack.py — KUS Pro
Хронометраж: «сначала фиксируем реальную картину — потом ищем
пожирателей времени». Две части:
  1. Автослежение за активным окном — ТОЛЬКО после явного согласия.
  2. Ручные записи бытовых/рабочих дел.
"""
import datetime as dt

from qt_compat import *


from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QComboBox,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QPushButton, QFrame,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from base_page import BasePage

TICK_SECONDS = 5  # как часто опрашиваем активное окно, если слежение включено

def _fmt_hms(total_seconds: int) -> str:
    from modules.timetrack import format_hms
    return format_hms(total_seconds)


class TimeTrackPage(BasePage):
    PAGE_TITLE = "⏱  Хронометраж"
    PAGE_SUB   = "Куда уходит время: авто-слежение + ручные записи"

    def build_ui(self):
        self._log_box.setFixedHeight(0)
        self._log_box.setVisible(False)
        self._progress.setVisible(False)

        from modules.timetrack import has_consent, CATEGORIES
        self._categories = CATEGORIES

        # ── Согласие ─────────────────────────────────────────────── #
        consent_card = self.card("Согласие на автослежение")
        note = QLabel(
            "При включении утилита каждые несколько секунд проверяет, какое "
            "окно активно на этом ПК, и суммирует время по приложениям — "
            "чтобы через несколько дней показать реальную картину: на что "
            "уходит время и где прячутся «пожиратели времени».\n\n"
            "Фиксируются только название процесса и заголовок активного "
            "окна. Содержимое экрана, нажатия клавиш и текст внутри окон "
            "НЕ записываются. Все данные хранятся локально на этом "
            "компьютере (timetrack_data.json) и никуда не отправляются. "
            "Слежение можно выключить в любой момент."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#a8a098; font-size:12px; background:transparent;")
        consent_card.lay.addWidget(note)

        row = QHBoxLayout()
        from widgets import GalahhadToggle
        self._cb_consent = GalahhadToggle("Разрешаю отслеживать активное окно и время работы за ПК")
        self._cb_consent.setChecked(has_consent())
        self._cb_consent.toggled.connect(self._on_consent_toggled)
        row.addWidget(self._cb_consent, 1)

        self._lbl_status = QLabel()
        self._lbl_status.setStyleSheet("font-size:12px; font-weight:700; background:transparent;")
        row.addWidget(self._lbl_status)
        consent_card.lay.addLayout(row)

        self._lbl_current = QLabel("—")
        self._lbl_current.setStyleSheet("color:#f5a623; font-size:12px; background:transparent;")
        consent_card.lay.addWidget(self._lbl_current)

        self._content.addWidget(consent_card)

        # ── Сегодня: авто-учёт по приложениям ───────────────────────── #
        auto_card = self.card("Сегодня — автоматически")
        self._table_auto = QTableWidget(0, 3)
        self._table_auto.setHorizontalHeaderLabels(["ПРИЛОЖЕНИЕ", "ВРЕМЯ", "КАТЕГОРИЯ"])
        self._style_table(self._table_auto)
        hdr = self._table_auto.horizontalHeader()
        hdr.setSectionResizeMode(0, Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.Fixed); hdr.resizeSection(1, 110)
        hdr.setSectionResizeMode(2, QHeaderView.Fixed); hdr.resizeSection(2, 150)
        self._table_auto.setMinimumHeight(160)
        auto_card.lay.addWidget(self._table_auto)
        self._content.addWidget(auto_card)

        # ── Ручные записи ───────────────────────────────────────────── #
        manual_card = self.card("Ручная запись дел", "Бытовые и рабочие задачи, которые не привязаны к конкретному окну")
        form = QHBoxLayout()
        form.setSpacing(8)

        self._cmb_cat = QComboBox()
        self._cmb_cat.addItems(self._categories)
        self._cmb_cat.setFixedWidth(110)
        form.addWidget(self._cmb_cat)

        self._ed_name = QLineEdit()
        self._ed_name.setPlaceholderText("Что делали? Например: «Уборка», «Созвон по проекту»…")
        form.addWidget(self._ed_name, 1)

        self._sp_minutes = QDoubleSpinBox()
        self._sp_minutes.setSuffix(" мин")
        self._sp_minutes.setRange(1, 24 * 60)
        self._sp_minutes.setValue(30)
        self._sp_minutes.setFixedWidth(100)
        form.addWidget(self._sp_minutes)

        self._ed_note = QLineEdit()
        self._ed_note.setPlaceholderText("Заметка (необязательно)")
        self._ed_note.setFixedWidth(180)
        form.addWidget(self._ed_note)

        b_add = self.btn("➕  Добавить")
        b_add.clicked.connect(self._add_manual)
        form.addWidget(b_add)

        manual_card.lay.addLayout(form)

        self._table_manual = QTableWidget(0, 5)
        self._table_manual.setHorizontalHeaderLabels(
            ["ВРЕМЯ", "КАТЕГОРИЯ", "НАЗВАНИЕ", "МИН.", ""]
        )
        self._style_table(self._table_manual)
        hdr2 = self._table_manual.horizontalHeader()
        hdr2.setSectionResizeMode(0, QHeaderView.Fixed); hdr2.resizeSection(0, 70)
        hdr2.setSectionResizeMode(1, QHeaderView.Fixed); hdr2.resizeSection(1, 90)
        hdr2.setSectionResizeMode(2, Stretch)
        hdr2.setSectionResizeMode(3, QHeaderView.Fixed); hdr2.resizeSection(3, 60)
        hdr2.setSectionResizeMode(4, QHeaderView.Fixed); hdr2.resizeSection(4, 90)
        self._table_manual.setMinimumHeight(140)
        manual_card.lay.addWidget(self._table_manual)
        self._content.addWidget(manual_card)

        # ── Итоги дня ────────────────────────────────────────────────── #
        summary_card = self.card("Итоги дня")
        self._lbl_summary = QLabel("—")
        self._lbl_summary.setWordWrap(True)
        self._lbl_summary.setStyleSheet("color:#ddd8d0; font-size:12px; background:transparent;")
        summary_card.lay.addWidget(self._lbl_summary)

        # Кнопки отправки отчёта
        report_row = QHBoxLayout()
        report_row.setSpacing(8)
        self._btn_send_daily = QPushButton("Отправить отчёт за день в Telegram")
        self._btn_send_daily.setObjectName("btn_sec")
        self._btn_send_daily.clicked.connect(self._send_daily_report)
        report_row.addWidget(self._btn_send_daily)

        self._btn_send_weekly = QPushButton("Недельный отчёт")
        self._btn_send_weekly.setObjectName("btn_sec")
        self._btn_send_weekly.clicked.connect(self._send_weekly_report)
        report_row.addWidget(self._btn_send_weekly)
        report_row.addStretch()
        summary_card.lay.addLayout(report_row)

        self._content.addWidget(summary_card)

        # ── Telegram Bot настройки ──────────────────────────────────── #
        tg_card = self.card("Telegram Bot",
                           "Настройте бота для получения отчётов в Telegram")

        tg_hint = QLabel(
            "1. Создайте бота через @BotFather в Telegram\n"
            "2. Скопируйте токен бота\n"
            "3. Узнайте chat_id: напишите боту /start, затем откройте\n"
            "   https://api.telegram.org/bot<TOKEN>/getUpdates"
        )
        tg_hint.setWordWrap(True)
        tg_hint.setStyleSheet("color:#5a5248; font-size:11px; background:transparent;")
        tg_card.lay.addWidget(tg_hint)

        from config_manager import get_value, set_value

        tg_form = QHBoxLayout()
        tg_form.setSpacing(8)

        tg_form.addWidget(QLabel("Токен:"))
        self._tg_token = QLineEdit(get_value("tg_bot_token", ""))
        self._tg_token.setPlaceholderText("123456:ABC-DEF...")
        self._tg_token.setEchoMode(QLineEdit.Password)
        tg_form.addWidget(self._tg_token, 1)

        tg_form.addWidget(QLabel("Chat ID:"))
        self._tg_chat_id = QLineEdit(get_value("tg_bot_chat_id", ""))
        self._tg_chat_id.setPlaceholderText("123456789")
        self._tg_chat_id.setFixedWidth(140)
        tg_form.addWidget(self._tg_chat_id)

        tg_card.lay.addLayout(tg_form)

        tg_btns = QHBoxLayout()
        tg_btns.setSpacing(8)
        self._tg_save_btn = QPushButton("Сохранить настройки")
        self._tg_save_btn.setObjectName("btn_sec")
        self._tg_save_btn.clicked.connect(self._save_tg_settings)
        tg_btns.addWidget(self._tg_save_btn)

        self._tg_test_btn = QPushButton("Тест соединения")
        self._tg_test_btn.clicked.connect(self._test_tg_connection)
        tg_btns.addWidget(self._tg_test_btn)
        tg_btns.addStretch()
        tg_card.lay.addLayout(tg_btns)

        self._tg_status = QLabel("")
        self._tg_status.setStyleSheet("color:#5a5248; font-size:11px; background:transparent;")
        tg_card.lay.addWidget(self._tg_status)

        self._content.addWidget(tg_card)

        self._content.addStretch()

        # ── Таймер авто-слежения ────────────────────────────────────── #
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_SECONDS * 1000)
        self._timer.timeout.connect(self._tick)
        self._update_status_label()
        if has_consent():
            self._timer.start()
        self._refresh_today()

    # ── Стилизация таблиц (переиспользуем общий стиль из theme.py) #
    def _style_table(self, table):
        from theme import TABLE_QSS
        table.setStyleSheet(TABLE_QSS)
        table.setAlternatingRowColors(False)
        table.setShowGrid(False)
        table.setSelectionBehavior(SelectRows)
        table.setEditTriggers(NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(32)
        table.setFrameShape(NoFrame)

    # ── Согласие / слежение ─────────────────────────────────────────── #
    def _on_consent_toggled(self, checked):
        from modules.timetrack import set_consent
        set_consent(checked)
        if checked:
            self._timer.start()
            self.log("Автослежение за активным окном включено — данные хранятся локально.", "OK")
        else:
            self._timer.stop()
            self._lbl_current.setText("—")
            self.log("Автослежение выключено.")
        self._update_status_label()

    def _update_status_label(self):
        if self._cb_consent.isChecked():
            self._lbl_status.setText("● Слежение включено")
            self._lbl_status.setStyleSheet("color:#4caf7d; font-size:12px; font-weight:700; background:transparent;")
        else:
            self._lbl_status.setText("○ Слежение выключено")
            self._lbl_status.setStyleSheet("color:#7a7068; font-size:12px; font-weight:700; background:transparent;")

    def _tick(self):
        try:
            from modules.timetrack import tick
            result = tick(TICK_SECONDS)
            if result:
                self._lbl_current.setText(
                    "Сейчас активно: {}  ·  сегодня набежало {}".format(
                        result["app"], _fmt_hms(result["total_seconds"])
                    )
                )
            self._refresh_today()
        except Exception as exc:
            self.log(f"Ошибка авто-слежения: {exc}", "ERR")

    # Это НЕ MonitorPage: слежение должно продолжаться, даже если
    # пользователь переключился на другую страницу приложения (иначе
    # хронометраж будет учитывать только время, проведённое именно на
    # этой странице, что бессмысленно) — поэтому таймер НЕ
    # останавливается в hideEvent.

    # ── Сегодняшняя сводка ───────────────────────────────────────────── #
    def _refresh_today(self):
        from modules.timetrack import get_day_summary, set_app_category, format_minutes

        summary = get_day_summary()

        # Авто-таблица
        self._table_auto.setRowCount(len(summary["auto"]))
        for r, row in enumerate(summary["auto"]):
            item_app = QTableWidgetItem(row["app"])
            item_app.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_app.setToolTip(row.get("last_title", ""))
            self._table_auto.setItem(r, 0, item_app)

            item_time = QTableWidgetItem(_fmt_hms(row["seconds"]))
            item_time.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_time.setForeground(QColor("#f5a623"))
            item_time.setTextAlignment(AlignRight | AlignVCenter)
            self._table_auto.setItem(r, 1, item_time)

            cmb = QComboBox()
            cmb.addItem("Нейтрально", "neutral")
            cmb.addItem("Продуктивно", "productive")
            cmb.addItem("Отвлекает", "distracting")
            idx = cmb.findData(row["category"])
            cmb.setCurrentIndex(max(idx, 0))
            app_name = row["app"]
            cmb.currentIndexChanged.connect(
                lambda _, c=cmb, a=app_name: set_app_category(a, c.currentData())
            )
            self._table_auto.setCellWidget(r, 2, cmb)

        # Ручная таблица
        self._table_manual.setRowCount(len(summary["manual"]))
        for r, entry in enumerate(summary["manual"]):
            self._table_manual.setItem(r, 0, self._ro_item(entry["time"]))
            self._table_manual.setItem(r, 1, self._ro_item(entry["category"]))
            name_txt = entry["name"] + (f"  ({entry['note']})" if entry.get("note") else "")
            self._table_manual.setItem(r, 2, self._ro_item(name_txt))
            self._table_manual.setItem(r, 3, self._ro_item("{:.0f}".format(entry["minutes"])))

            b_del = QPushButton("🗑")
            b_del.setFixedWidth(36)
            entry_id = entry["id"]
            b_del.clicked.connect(lambda _, eid=entry_id: self._delete_manual(eid))
            self._table_manual.setCellWidget(r, 4, b_del)

        # Итоги
        total_auto = _fmt_hms(summary["total_auto_seconds"])
        total_manual = format_minutes(summary["total_manual_minutes"])
        distracting = _fmt_hms(summary["distracting_seconds"])
        top = summary["top_eaters"]
        if top:
            top_txt = ", ".join(
                "{} ({})".format(t["app"], _fmt_hms(t["seconds"])) for t in top[:3]
            )
        else:
            top_txt = "пока нет данных"

        self._lbl_summary.setText(
            "Автоматически отслежено: <b>{}</b>  ·  Ручных записей: <b>{}</b><br>"
            "Отмечено как «отвлекает»: <b>{}</b><br>"
            "Больше всего времени сегодня ушло на: {}".format(
                total_auto, total_manual, distracting, top_txt
            )
        )
        self._lbl_summary.setTextFormat(Qt.RichText)

    def _ro_item(self, text):
        it = QTableWidgetItem(str(text))
        it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return it

    def _delete_manual(self, entry_id):
        from modules.timetrack import delete_manual_entry
        delete_manual_entry(entry_id)
        self._refresh_today()

    def _add_manual(self):
        from modules.timetrack import add_manual_entry
        try:
            add_manual_entry(
                self._cmb_cat.currentText(),
                self._ed_name.text(),
                self._sp_minutes.value(),
                self._ed_note.text(),
            )
        except ValueError as exc:
            self.log(str(exc), "WARN")
            return
        self._ed_name.clear()
        self._ed_note.clear()
        self._sp_minutes.setValue(30)
        self.log("Запись добавлена.", "OK")
        self._refresh_today()

    # ── Telegram Bot ──────────────────────────────────────────────── #
    def _save_tg_settings(self):
        from config_manager import set_value
        set_value("tg_bot_token", self._tg_token.text().strip())
        set_value("tg_bot_chat_id", self._tg_chat_id.text().strip())
        self.log("Настройки Telegram-бота сохранены.", "OK")
        self._tg_status.setText("Настройки сохранены")

    def _test_tg_connection(self):
        from modules.tg_bot import test_connection
        token = self._tg_token.text().strip()
        chat_id = self._tg_chat_id.text().strip()
        if not token or not chat_id:
            self.log("Заполните токен бота и chat_id.", "WARN")
            self._tg_status.setText("Заполните токен и chat_id")
            return
        self._tg_status.setText("Проверка соединения...")
        self._run_worker(self._fn_test_tg, token, chat_id, on_result=self._on_test_tg_result)

    def _fn_test_tg(self, log_func, progress_func, token, chat_id):
        from modules.tg_bot import test_connection
        progress_func(0.5)
        ok, msg = test_connection(token, chat_id)
        progress_func(1.0)
        return {"ok": ok, "msg": msg}

    def _on_test_tg_result(self, result):
        if result and result.get("ok"):
            self._tg_status.setText("Соединение установлено!")
            self._tg_status.setStyleSheet("color:#4caf7d; font-size:11px; background:transparent;")
            self.log("Telegram: {}".format(result.get("msg", "")), "OK")
        else:
            msg = result.get("msg", "Неизвестная ошибка") if result else "Неизвестная ошибка"
            self._tg_status.setText("Ошибка: {}".format(msg))
            self._tg_status.setStyleSheet("color:#e05252; font-size:11px; background:transparent;")
            self.log("Telegram: {}".format(msg), "ERR")

    def _send_daily_report(self):
        from config_manager import get_value
        token = get_value("tg_bot_token", "")
        chat_id = get_value("tg_bot_chat_id", "")
        if not token or not chat_id:
            self.log("Настройте Telegram-бота (токен и chat_id) внизу страницы.", "WARN")
            return
        self._run_worker(self._fn_daily_report, token, chat_id, on_result=self._on_daily_report_result)

    def _fn_daily_report(self, log_func, progress_func, token, chat_id):
        from modules.tg_bot import send_message, format_daily_report
        from modules.timetrack import get_day_summary
        progress_func(0.3)
        summary = get_day_summary()
        report = format_daily_report(summary)
        progress_func(0.7)
        result = send_message(token, chat_id, report)
        progress_func(1.0)
        return result

    def _on_daily_report_result(self, result):
        if result and result.get("ok"):
            self.log("Отчёт за день отправлен в Telegram.", "OK")
        else:
            desc = result.get("description", "Неизвестная ошибка") if result else "Неизвестная ошибка"
            self.log("Ошибка отправки: {}".format(desc), "ERR")

    def _send_weekly_report(self):
        from config_manager import get_value
        token = get_value("tg_bot_token", "")
        chat_id = get_value("tg_bot_chat_id", "")
        if not token or not chat_id:
            self.log("Настройте Telegram-бота (токен и chat_id) внизу страницы.", "WARN")
            return
        self._run_worker(self._fn_weekly_report, token, chat_id, on_result=self._on_weekly_report_result)

    def _fn_weekly_report(self, log_func, progress_func, token, chat_id):
        from modules.tg_bot import send_message, format_weekly_report
        from modules.timetrack import get_day_summary
        import datetime as dt

        progress_func(0.1)
        daily_summaries = []
        today = dt.date.today()
        for i in range(7):
            day = today - dt.timedelta(days=i)
            day_key = day.strftime("%Y-%m-%d")
            try:
                summary = get_day_summary(day_key)
                if summary.get("auto") or summary.get("manual"):
                    daily_summaries.append(summary)
            except Exception:
                pass

        if not daily_summaries:
            log_func("Нет данных за последние 7 дней.", "WARN")
            progress_func(1.0)
            return None

        progress_func(0.5)
        report = format_weekly_report(daily_summaries)
        progress_func(0.8)
        result = send_message(token, chat_id, report)
        progress_func(1.0)
        return result

    def _on_weekly_report_result(self, result):
        if result and result.get("ok"):
            self.log("Недельный отчёт отправлен в Telegram.", "OK")
        else:
            desc = result.get("description", "Неизвестная ошибка") if result else "Неизвестная ошибка"
            self.log("Ошибка отправки: {}".format(desc), "ERR")


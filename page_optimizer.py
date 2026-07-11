"""
page_optimizer.py — Страница оптимизации системы KUS Pro.
"""

from PyQt5.QtWidgets import (
    QLabel, QHBoxLayout, QVBoxLayout, QCheckBox, QMessageBox,
)
from PyQt5.QtCore import Qt

from base_page import BasePage
from theme import TEXT_MAIN, TEXT_DIM
from qt_compat import *


class OptimizerPage(BasePage):
    """Страница оптимизации системы."""

    PAGE_TITLE = "Оптимизация"
    PAGE_SUB = "Очистка и оптимизация производительности Windows"

    def build_ui(self):
        # Основная карточка
        opt_card = self.card("Оптимизация системы",
                             "Автоматическая очистка и оптимизация Windows")

        # Оценка
        self._estimate_label = QLabel("Нажмите «Оценить» для анализа")
        self._estimate_label.setStyleSheet(
            "color:{}; font-size:12px; background:transparent;".format(TEXT_DIM))
        opt_card.lay.addWidget(self._estimate_label)

        # Кнопки
        btn_row = QHBoxLayout()

        btn_estimate = self._reg_btn(self.btn("Оценить", "btn_sec"))
        btn_estimate.setFixedHeight(40)
        btn_estimate.clicked.connect(self._estimate)
        btn_row.addWidget(btn_estimate)

        btn_optimize = self._reg_btn(self.btn("Оптимизировать", "btn_glow"))
        btn_optimize.setFixedHeight(40)
        btn_optimize.clicked.connect(self._optimize)
        btn_row.addWidget(btn_optimize)

        btn_row.addStretch()
        opt_card.lay.addLayout(btn_row)

        self._content.addWidget(opt_card)

        # Опции — Очистка
        clean_card = self.card("Очистка")

        self._cb_temp = QCheckBox("Временные файлы (Temp)")
        self._cb_temp.setChecked(True)
        self._cb_temp.setStyleSheet("color:{}; background:transparent;".format(TEXT_MAIN))
        clean_card.lay.addWidget(self._cb_temp)

        self._cb_recycle = QCheckBox("Корзина Windows")
        self._cb_recycle.setChecked(True)
        self._cb_recycle.setStyleSheet("color:{}; background:transparent;".format(TEXT_MAIN))
        clean_card.lay.addWidget(self._cb_recycle)

        self._cb_update_cache = QCheckBox("Кэш обновлений Windows")
        self._cb_update_cache.setChecked(True)
        self._cb_update_cache.setStyleSheet("color:{}; background:transparent;".format(TEXT_MAIN))
        clean_card.lay.addWidget(self._cb_update_cache)

        self._cb_browser = QCheckBox("Кэш браузеров (Chrome, Edge, Firefox...)")
        self._cb_browser.setChecked(False)
        self._cb_browser.setStyleSheet("color:{}; background:transparent;".format(TEXT_MAIN))
        clean_card.lay.addWidget(self._cb_browser)

        self._cb_prefetch = QCheckBox("Prefetch (кэш запуска программ)")
        self._cb_prefetch.setChecked(False)
        self._cb_prefetch.setStyleSheet("color:{}; background:transparent;".format(TEXT_MAIN))
        clean_card.lay.addWidget(self._cb_prefetch)

        self._content.addWidget(clean_card)

        # Опции — Система
        sys_card = self.card("Система")

        self._cb_services = QCheckBox("Отключить ненужные службы Windows")
        self._cb_services.setChecked(True)
        self._cb_services.setStyleSheet("color:{}; background:transparent;".format(TEXT_MAIN))
        sys_card.lay.addWidget(self._cb_services)

        self._cb_dns = QCheckBox("Очистить DNS кэш")
        self._cb_dns.setChecked(True)
        self._cb_dns.setStyleSheet("color:{}; background:transparent;".format(TEXT_MAIN))
        sys_card.lay.addWidget(self._cb_dns)

        self._content.addWidget(sys_card)

    def _get_options(self):
        return {
            "temp": self._cb_temp.isChecked(),
            "recycle": self._cb_recycle.isChecked(),
            "update_cache": self._cb_update_cache.isChecked(),
            "browser": self._cb_browser.isChecked(),
            "prefetch": self._cb_prefetch.isChecked(),
            "services": self._cb_services.isChecked(),
            "dns": self._cb_dns.isChecked(),
        }

    def _estimate(self):
        from modules.optimizer import get_optimization_estimate
        self._run_worker(get_optimization_estimate, on_result=self._on_estimate)

    def _on_estimate(self, result):
        if result:
            from modules.cleanup import human_size
            junk = human_size(result.get("junk_size", 0))
            services = result.get("services_to_disable", 0)
            self._estimate_label.setText(
                "Мусор: {} | Служб к отключению: {}".format(junk, services)
            )

    def _optimize(self):
        options = self._get_options()
        active = sum(1 for v in options.values() if v)
        if active == 0:
            self.log("Выберите хотя бы одну опцию.", "WARN")
            return

        # Подтверждение если отключаются службы
        if options["services"]:
            reply = QMessageBox.question(
                self, "Подтверждение",
                "Будут отключены ненужные службы Windows.\nПродолжить?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        from modules.optimizer import optimize_system
        self._run_worker(optimize_system, options, on_result=self._on_optimized)

    def _on_optimized(self, result):
        if result is not None:
            from modules.cleanup import human_size
            self.log("Оптимизация завершена. Освобождено: {}".format(human_size(result)), "OK")

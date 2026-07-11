"""
page_battery.py — Страница мониторинга батареи KUS Pro.
"""

from PyQt5.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QFrame

from qt_compat import *

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

from base_page import BasePage
from theme import TEXT_MAIN, TEXT_DIM, ACCENT, SUCCESS, WARNING, DANGER, BG_CARD


class BatteryPage(BasePage):
    """Страница мониторинга батареи и энергопотребления."""

    PAGE_TITLE = "🔋  Мониторинг батареи"
    PAGE_SUB = "Состояние батареи и энергопотребление"

    def build_ui(self):
        from modules.battery import get_battery_info

        info = get_battery_info()
        has_battery = info.get("status") != "not present"

        if not has_battery:
            # Десктоп — показываем сообщение
            msg = QLabel("Батарея не обнаружена\n\nЭта страница доступна только для ноутбуков и планшетов с батареей.")
            msg.setAlignment(AlignCenter)
            msg.setStyleSheet("color:{}; font-size:16px; padding:60px 20px;".format(TEXT_DIM))
            self._content.addWidget(msg)

            # Всё равно показываем базовую информацию
            row = QHBoxLayout()
            self._card_percent = self.card("Заряд", "Нет батареи")
            row.addWidget(self._card_percent)
            self._card_status = self.card("Статус", "Не обнаружена")
            row.addWidget(self._card_status)
            self._content.addLayout(row)
        else:
            # Ноутбук — полная информация
            # Основные карточки
            row = QHBoxLayout()
            self._card_percent = self.card("Заряд", "—")
            row.addWidget(self._card_percent)
            self._card_status = self.card("Статус", "—")
            row.addWidget(self._card_status)
            self._card_time = self.card("Время работы", "—")
            row.addWidget(self._card_time)
            self._content.addLayout(row)

            row2 = QHBoxLayout()
            self._card_power = self.card("Потребление", "—")
            row2.addWidget(self._card_power)
            self._card_voltage = self.card("Напряжение", "—")
            row2.addWidget(self._card_voltage)
            self._card_temp = self.card("Температура", "—")
            row2.addWidget(self._card_temp)
            self._content.addLayout(row2)

            row3 = QHBoxLayout()
            self._card_capacity = self.card("Ёмкость", "—")
            row3.addWidget(self._card_capacity)
            self._card_cycles = self.card("Циклы заряда", "—")
            row3.addWidget(self._card_cycles)
            self._card_discharge = self.card("Скорость разряда", "—")
            row3.addWidget(self._card_discharge)
            self._content.addLayout(row3)

            # Кнопка обновления
            btn_row = QHBoxLayout()
            self._btn_refresh = self.btn("🔄  Обновить данные", "btn_sec")
            self._btn_refresh.setFixedHeight(36)
            self._btn_refresh.clicked.connect(self._refresh_data)
            btn_row.addWidget(self._btn_refresh)
            btn_row.addStretch()
            self._content.addLayout(btn_row)

            # Таймер обновления
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._refresh_data)
            self._timer.start(10000)

            # BatteryMonitor — создаём ОДИН раз, переиспользуем
            from modules.battery import BatteryMonitor
            self._battery_monitor = BatteryMonitor()
            self._battery_monitor.start()

            self._refresh_data()

    def hideEvent(self, event):
        """Останавливаем мониторинг при скрытии страницы."""
        if hasattr(self, '_battery_monitor'):
            self._battery_monitor.stop()
        if hasattr(self, '_timer'):
            self._timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        """Возобновляем мониторинг при показе страницы."""
        if hasattr(self, '_timer'):
            self._timer.start(10000)
        if hasattr(self, '_battery_monitor'):
            self._battery_monitor.start()
        super().showEvent(event)

    def _refresh_data(self):
        """Обновляет данные о батарее."""
        from modules.battery import get_battery_info

        info = get_battery_info()

        # Процент
        percent = info["percent"]
        color = SUCCESS if percent > 50 else WARNING if percent > 20 else DANGER
        self._card_percent.findChild(QLabel).setText(
            '<span style="font-size:36px;font-weight:700;color:{};">{}%</span>'.format(color, int(percent))
        )

        # Статус
        status_map = {
            "charging": ("Заряжается", ACCENT),
            "discharging": ("Разряжается", WARNING),
            "full": ("Полная", SUCCESS),
            "not present": ("Не обнаружена", TEXT_DIM),
        }
        status_text, status_color = status_map.get(info["status"], ("Неизвестно", TEXT_DIM))
        self._card_status.findChild(QLabel).setText(
            '<span style="font-size:18px;color:{};">{}</span>'.format(status_color, status_text)
        )

        # Время
        if info["time_left_sec"]:
            h = info["time_left_sec"] // 3600
            m = (info["time_left_sec"] % 3600) // 60
            time_str = "{} ч {} мин".format(h, m) if h > 0 else "{} мин".format(m)
        else:
            time_str = "—"
        self._card_time.findChild(QLabel).setText(
            '<span style="font-size:18px;color:{};">{}</span>'.format(TEXT_MAIN, time_str)
        )

        # Мощность
        power_info = self._battery_monitor.get_power_consumption()
        power_str = "{:.1f} W".format(power_info["power_watts"]) if power_info["power_watts"] else "—"
        self._card_power.findChild(QLabel).setText(
            '<span style="font-size:18px;color:{};">{}</span>'.format(TEXT_MAIN, power_str)
        )

        # Напряжение
        voltage_str = "{:.2f} V".format(info["voltage"]) if info["voltage"] else "—"
        self._card_voltage.findChild(QLabel).setText(
            '<span style="font-size:18px;color:{};">{}</span>'.format(TEXT_MAIN, voltage_str)
        )

        # Температура
        temp_str = "{:.1f}°C".format(info["temperature"]) if info["temperature"] else "—"
        self._card_temp.findChild(QLabel).setText(
            '<span style="font-size:18px;color:{};">{}</span>'.format(TEXT_MAIN, temp_str)
        )

        # Ёмкость
        if info["capacity_design"]:
            cap_str = "{:.0f} Wh".format(info["capacity_design"])
        else:
            cap_str = "—"
        self._card_capacity.findChild(QLabel).setText(
            '<span style="font-size:18px;color:{};">{}</span>'.format(TEXT_MAIN, cap_str)
        )

        # Циклы
        cycles_str = str(info["cycle_count"]) if info["cycle_count"] is not None else "—"
        self._card_cycles.findChild(QLabel).setText(
            '<span style="font-size:18px;color:{};">{}</span>'.format(TEXT_MAIN, cycles_str)
        )

        # Скорость разряда
        rate = self._battery_monitor.get_discharge_rate()
        if rate > 0:
            rate_str = "{:.1f} %/ч".format(rate)
        else:
            rate_str = "—"
        self._card_discharge.findChild(QLabel).setText(
            '<span style="font-size:18px;color:{};">{}</span>'.format(TEXT_MAIN, rate_str)
        )

        self.log("Данные батареи обновлены: {}% — {}".format(int(percent), status_text))

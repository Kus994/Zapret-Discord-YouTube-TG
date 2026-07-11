"""
modules/battery.py
-------------------
Мониторинг батареи и энергопотребления ноутбука.

Функции:
  - Текущий уровень заряда (% и время работы)
  - Статус зарядки (charging/discharging/full/not present)
  - Время до полного заряда / до разряда
  - Мощность потребления (W) через WMI
  - История заряда/разряда
  - Предупреждения о низком заряде
"""

import time
import threading
from datetime import datetime, timedelta

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def get_battery_info() -> dict:
    """
    Возвращает текущую информацию о батарее:
    {
        "percent": float,           # 0-100
        "status": str,              # "charging" / "discharging" / "full" / "not present"
        "time_left_sec": int|None,  # секунды до разряда/заряда
        "power_plugged": bool,      # подключена ли зарядка
        "voltage": float|None,      # напряжение (V)
        "capacity_design": float|None,  #_design capacity (Wh)
        "capacity_current": float|None, # текущая ёмкость (Wh)
        "cycle_count": int|None,    # количество циклов заряда
        "temperature": float|None,  # температура батареи (°C)
    }
    """
    if not HAS_PSUTIL:
        return _empty_battery()

    try:
        bat = psutil.sensors_battery()
    except Exception:
        return _empty_battery()

    if bat is None:
        return _empty_battery()

    percent = bat.percent
    plugged = getattr(bat, 'power_plugged', False)

    # Статус
    if hasattr(bat, 'secsleft'):
        if bat.secsleft == psutil.POWER_TIME_UNLIMITED:
            status = "full"
            time_left = None
        elif bat.secsleft == psutil.POWER_TIME_UNKNOWN:
            status = "not present" if percent == 0 else "charging" if plugged else "discharging"
            time_left = None
        else:
            status = "charging" if plugged else "discharging"
            time_left = bat.secsleft
    else:
        status = "charging" if plugged else "discharging"
        time_left = None

    result = {
        "percent": percent,
        "status": status,
        "time_left_sec": time_left,
        "power_plugged": plugged,
        "voltage": None,
        "capacity_design": None,
        "capacity_current": None,
        "cycle_count": None,
        "temperature": None,
    }

    # Попытка получить доп. информацию через WMI (Windows)
    _enrich_with_wmi(result)

    return result


def _empty_battery() -> dict:
    return {
        "percent": 0,
        "status": "not present",
        "time_left_sec": None,
        "power_plugged": False,
        "voltage": None,
        "capacity_design": None,
        "capacity_current": None,
        "cycle_count": None,
        "temperature": None,
    }


def _enrich_with_wmi(result: dict):
    """Дополняет результат данными из WMI (если доступно)."""
    try:
        import wmi as _wmi
        conn = _wmi.WMI(namespace=r"root\WMI")

        # ACPIBattery
        try:
            batteries = conn.BatteryStatus()
            if batteries:
                bat = batteries[0]
                result["voltage"] = getattr(bat, 'Voltage', None)
                if result["voltage"]:
                    result["voltage"] = result["voltage"] / 1000.0  # mV -> V
        except Exception:
            pass

        # BatteryCycleCount
        try:
            bat_info = conn.BatteryCycleCount()
            if bat_info:
                result["cycle_count"] = getattr(bat_info[0], 'CycleCount', None)
        except Exception:
            pass

        # BatteryTemperature
        try:
            bat_temp = conn.BatteryTemperature()
            if bat_temp:
                temp = getattr(bat_temp[0], 'Temperature', None)
                if temp:
                    result["temperature"] = (temp - 2732) / 10.0  # deciKelvin -> Celsius
        except Exception:
            pass

        # DesignCapacity
        try:
            bat_static = conn.BatteryStaticData()
            if bat_static:
                result["capacity_design"] = getattr(bat_static[0], 'DesignedCapacity', None)
                if result["capacity_design"]:
                    result["capacity_design"] = result["capacity_design"] / 1000.0  # mWh -> Wh
        except Exception:
            pass

    except ImportError:
        pass
    except Exception:
        pass


class BatteryMonitor:
    """
    Мониторинг батареи с историей заряда.
    Записывает данные каждые N секунд для построения графика.
    """

    def __init__(self, interval: int = 60, max_history: int = 24 * 60):
        """
        interval: интервал записи (секунды)
        max_history: максимальное количество записей (по умолчанию 24 часа при interval=60)
        """
        self.interval = interval
        self.max_history = max_history
        self._history = []  # [(timestamp, percent, status), ...]
        self._thread = None
        self._running = False
        self._lock = threading.Lock()

    def start(self):
        """Запускает мониторинг в фоновом потоке."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Останавливает мониторинг."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _monitor_loop(self):
        while self._running:
            info = get_battery_info()
            with self._lock:
                self._history.append((
                    datetime.now().isoformat(),
                    info["percent"],
                    info["status"],
                ))
                if len(self._history) > self.max_history:
                    self._history = self._history[-self.max_history:]
            time.sleep(self.interval)

    def get_history(self) -> list:
        """Возвращает копию истории заряда."""
        with self._lock:
            return list(self._history)

    def get_discharge_rate(self) -> float:
        """
        Возвращает среднюю скорость разряда в %/час.
        Анализирует только участки разряда (когда батарея не на зарядке).
        """
        with self._lock:
            if len(self._history) < 2:
                return 0.0

            discharge_points = []
            for i in range(1, len(self._history)):
                prev_ts, prev_pct, prev_status = self._history[i - 1]
                curr_ts, curr_pct, curr_status = self._history[i]

                if curr_status == "discharging" and prev_status == "discharging":
                    try:
                        t1 = datetime.fromisoformat(prev_ts)
                        t2 = datetime.fromisoformat(curr_ts)
                        dt_hours = (t2 - t1).total_seconds() / 3600
                        if dt_hours > 0:
                            delta_pct = prev_pct - curr_pct
                            if delta_pct > 0:
                                discharge_points.append(delta_pct / dt_hours)
                    except Exception:
                        continue

            if not discharge_points:
                return 0.0

            return sum(discharge_points) / len(discharge_points)

    def estimate_empty_time(self) -> str:
        """
        Оценивает время до разряда в читаемом виде.
        Возвращает строку вида "2 ч 30 мин" или "Недостаточно данных".
        """
        rate = self.get_discharge_rate()
        if rate <= 0:
            return "Недостаточно данных"

        info = get_battery_info()
        if info["status"] != "discharging":
            return "На зарядке"

        remaining_pct = info["percent"]
        hours_left = remaining_pct / rate
        total_min = int(hours_left * 60)
        h, m = divmod(total_min, 60)

        if h > 0:
            return "{} ч {} мин".format(h, m)
        return "{} мин".format(m)

    def get_power_consumption(self) -> dict:
        """
        Оценивает потребление мощности (W) через WMI.
        Возвращает {"power_watts": float|None, "source": str}.
        """
        try:
            import wmi as _wmi
            conn = _wmi.WMI(namespace=r"root\\OpenHardwareMonitor")

            # Ищем сенсоры мощности
            sensors = conn.Sensor()
            for s in sensors:
                if getattr(s, "SensorType", "") == "Power":
                    return {
                        "power_watts": float(getattr(s, "Value", 0)),
                        "source": getattr(s, "Parent", "Unknown"),
                    }
        except Exception:
            pass

        return {"power_watts": None, "source": "N/A"}

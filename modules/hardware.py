"""
modules/hardware.py
-------------------
Hardware sensor monitoring: temperatures, fan speeds, voltages.

Primary: psutil.sensors_temperatures(), psutil.sensors_fans()
Fallback: WMI (Windows Management Instrumentation) when psutil returns empty.
"""

import platform

_HAS_PSUTIL_SENSORS = False
try:
    import psutil
    _HAS_PSUTIL_SENSORS = hasattr(psutil, "sensors_temperatures") and hasattr(psutil, "sensors_fans")
except ImportError:
    psutil = None

_WMI_CONN = None


def _get_wmi():
    """Lazy-init WMI connection (Windows only)."""
    global _WMI_CONN
    if _WMI_CONN is not None:
        return _WMI_CONN
    if platform.system() != "Windows":
        return None
    try:
        import wmi as _wmi
        _WMI_CONN = _wmi.WMI(namespace=r"root\OpenHardwareMonitor")
        return _WMI_CONN
    except Exception:
        pass
    try:
        import wmi as _wmi
        _WMI_CONN = _wmi.WMI()
        return _WMI_CONN
    except Exception:
        return None


def _psutil_temperatures():
    """Read temperatures via psutil. Returns dict of sensor -> list of {label, current, high, critical}."""
    if not _HAS_PSUTIL_SENSORS:
        return {}
    try:
        raw = psutil.sensors_temperatures()
        if not raw:
            return {}
        result = {}
        for name, entries in raw.items():
            items = []
            for e in entries:
                items.append({
                    "label": getattr(e, "label", "") or name,
                    "current": getattr(e, "current", None),
                    "high": getattr(e, "high", None),
                    "critical": getattr(e, "critical", None),
                })
            result[name] = items
        return result
    except Exception:
        return {}


def _psutil_fans():
    """Read fan speeds via psutil. Returns dict of sensor -> list of {label, current}."""
    if not _HAS_PSUTIL_SENSORS:
        return {}
    try:
        raw = psutil.sensors_fans()
        if not raw:
            return {}
        result = {}
        for name, entries in raw.items():
            items = []
            for e in entries:
                items.append({
                    "label": getattr(e, "label", "") or name,
                    "current": getattr(e, "current", 0),
                })
            result[name] = items
        return result
    except Exception:
        return {}


def _wmi_temperatures():
    """Read temperatures via WMI (OpenHardwareMonitor or MSAcpi)."""
    conn = _get_wmi()
    if conn is None:
        return {}
    try:
        sensors = conn.Sensor()
        temps = {}
        for s in sensors:
            if getattr(s, "SensorType", "") == "Temperature":
                name = getattr(s, "Parent", "Hardware")
                current = float(getattr(s, "Value", 0))
                label = getattr(s, "Name", "")
                if name not in temps:
                    temps[name] = []
                temps[name].append({
                    "label": label,
                    "current": current,
                    "high": None,
                    "critical": None,
                })
        return temps
    except Exception:
        return {}


def _wmi_fans():
    """Read fan speeds via WMI."""
    conn = _get_wmi()
    if conn is None:
        return {}
    try:
        sensors = conn.Sensor()
        fans = {}
        for s in sensors:
            if getattr(s, "SensorType", "") == "Fan":
                name = getattr(s, "Parent", "Hardware")
                current = float(getattr(s, "Value", 0))
                label = getattr(s, "Name", "")
                if name not in fans:
                    fans[name] = []
                fans[name].append({
                    "label": label,
                    "current": current,
                })
        return fans
    except Exception:
        return {}


def _wmi_voltages():
    """Read voltages via WMI."""
    conn = _get_wmi()
    if conn is None:
        return {}
    try:
        sensors = conn.Sensor()
        volts = {}
        for s in sensors:
            if getattr(s, "SensorType", "") == "Voltage":
                name = getattr(s, "Parent", "Hardware")
                current = float(getattr(s, "Value", 0))
                label = getattr(s, "Name", "")
                if name not in volts:
                    volts[name] = []
                volts[name].append({
                    "label": label,
                    "current": current,
                })
        return volts
    except Exception:
        return {}


def get_hardware_sensors() -> dict:
    """
    Returns a consolidated hardware sensor snapshot:

    {
        "temperatures": [
            {"sensor": "coretemp", "label": "Core 0", "current": 55.0, "high": 100.0, "critical": None},
            ...
        ],
        "fans": [
            {"sensor": "nct6775", "label": "Fan 1", "current": 1200.0},
            ...
        ],
        "voltages": [
            {"sensor": "acpi", "label": "CPU Core", "current": 1.15},
            ...
        ],
    }

    Each list is flattened from per-sensor-group dicts. If psutil returns
    empty on Windows, falls back to WMI. Returns empty lists on unsupported
    platforms or when no sensors are available.
    """
    temps_raw = _psutil_temperatures()
    fans_raw = _psutil_fans()
    volts_raw = {}

    # psutil doesn't expose voltages on most platforms; try WMI for those
    if platform.system() == "Windows" and not temps_raw:
        temps_raw = _wmi_temperatures()
        fans_raw = _wmi_fans()
        volts_raw = _wmi_voltages()

    # Flatten temperatures
    temperatures = []
    for sensor_name, entries in temps_raw.items():
        for e in entries:
            temperatures.append({
                "sensor": sensor_name,
                "label": e["label"],
                "current": e["current"],
                "high": e["high"],
                "critical": e["critical"],
            })

    # Flatten fans
    fans = []
    for sensor_name, entries in fans_raw.items():
        for e in entries:
            fans.append({
                "sensor": sensor_name,
                "label": e["label"],
                "current": e["current"],
            })

    # Flatten voltages
    voltages = []
    for sensor_name, entries in volts_raw.items():
        for e in entries:
            voltages.append({
                "sensor": sensor_name,
                "label": e["label"],
                "current": e["current"],
            })

    return {
        "temperatures": temperatures,
        "fans": fans,
        "voltages": voltages,
    }

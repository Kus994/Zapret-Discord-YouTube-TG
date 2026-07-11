\"\"\"
MIGRATION_PLAN.md
────────────────
Полный план миграции Kus на архитектуру v2 с асинхронностью
\"\"\"

# 🚀 План миграции Kus на архитектуру v2

## Fase 1: Подготовка (1-2 дня)

### 1.1 Создание новой структуры папок

```bash
sysutil/
├── main.py
├── requirements.txt
├── README.md
│
├── core/                      # ← НОВОЕ
│   ├── __init__.py
│   ├── task_handler.py        # Асинхронное управление задачами
│   ├── logger.py              # Логирование с цветами
│   ├── event_bus.py           # Event Bus (pub-sub)
│   └── module_loader.py       # Ленивая загрузка модулей
│
├── config/                    # ← НОВОЕ
│   ├── __init__.py
│   ├── constants.py           # Цвета, пути, константы
│   └── settings.py            # Настройки пользователя (JSON/YAML)
│
├── ui/
│   ├── __init__.py
│   ├── app.py                 # Главное окно (ПЕРЕПИСАНО)
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── wave_progress.py   # Волновой прогресс-бар
│   │   ├── colored_log.py     # Логирование в UI
│   │   └── status_bar.py      # Статус-бар и системный трей
│   └── tabs/
│       ├── __init__.py
│       ├── cleanup_tab.py     # ПЕРЕПИСАНО (асинхронная)
│       ├── monitor_tab.py     # ПЕРЕПИСАНО
│       ├── network_tab.py     # ПЕРЕПИСАНО
│       ├── processes_tab.py   # ПЕРЕПИСАНО
│       ├── updates_tab.py     # ПЕРЕПИСАНО
│       └── settings_tab.py    # НОВОЕ
│
├── modules/                   # Существующие модули (с небольшими изменениями)
│   ├── __init__.py
│   ├── cleanup.py             # Добавить async функции
│   ├── monitor.py             # Добавить async функции
│   ├── network.py             # Добавить async функции
│   ├── processes.py           # Добавить async функции
│   ├── updates.py             # Добавить async функции
│   ├── autostart.py           # ← НОВОЕ
│   ├── temperature.py         # ← НОВОЕ (опционально)
│   └── winget_manager.py      # ← НОВОЕ (опционально)
│
├── utils/                     # ← НОВОЕ
│   ├── __init__.py
│   ├── system_utils.py        # Системные утилиты
│   ├── file_utils.py          # Работа с файлами
│   └── validators.py          # Валидация данных
│
├── assets/
│   ├── background.jpg
│   ├── icons/                 # ← НОВОЕ: SVG иконки
│   └── themes/                # ← НОВОЕ: Темы
│
└── tests/                     # ← НОВОЕ: Модульные тесты
    ├── __init__.py
    ├── test_task_handler.py
    ├── test_logger.py
    └── test_modules.py
```

### 1.2 Обновите requirements.txt

```txt
# Базовые зависимости
customtkinter>=5.2.2
pillow>=10.0.0
psutil>=5.9.0

# Асинхронность и работа с файлами
aiofiles>=23.0.0
aiohttp>=3.8.0

# Windows API
pywin32>=305
pyperclip>=1.8.2

# Информация о системе
py-cpuinfo>=9.0.0

# Опционально: мониторинг GPU
# nvidia-ml-py3>=7.352.0
# pyadl>=0.0.6

# Опционально: для сборки
# pyinstaller>=5.0.0

# Опционально: для разработки
# pytest>=7.0.0
# black>=22.0.0
# pylint>=2.0.0
```

---

## Fase 2: Интеграция основных компонентов (3-5 дней)

### 2.1 Создайте core/event_bus.py

```python
# core/event_bus.py
import asyncio
import threading
from typing import Callable, Dict, List
from dataclasses import dataclass

@dataclass
class Event:
    name: str
    data: dict = None
    timestamp: str = None

class EventBus:
    \"\"\"Простая реализация pub-sub паттерна\"\"\"
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
    
    def subscribe(self, event_name: str, callback: Callable) -> str:
        \"\"\"Подписывается на событие. Возвращает subscription_id\"\"\"
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(callback)
        return f\"{event_name}_{id(callback)}\"
    
    def unsubscribe(self, event_name: str, callback: Callable):
        \"\"\"Отписывается от события\"\"\"
        with self._lock:
            if event_name in self._subscribers:
                try:
                    self._subscribers[event_name].remove(callback)
                except ValueError:
                    pass
    
    async def emit(self, event_name: str, data: dict = None):
        \"\"\"Эмитит событие всем подписчикам (асинхронно)\"\"\"
        with self._lock:
            callbacks = self._subscribers.get(event_name, []).copy()
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data or {})
                else:
                    callback(data or {})
            except Exception as e:
                print(f\"Error in event callback: {e}\")
```

### 2.2 Обновите modules/cleanup.py на асинхронный

```python
# modules/cleanup.py (ОБНОВЛЕННАЯ ВЕРСИЯ)

import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Callable, Optional

class CleanupManager:
    \"\"\"Менеджер очистки системы с поддержкой асинхронности\"\"\"
    
    def __init__(self, on_progress: Optional[Callable] = None):
        self.on_progress = on_progress
        self.freed_bytes = 0
        self.files_deleted = 0
        self.errors_count = 0
    
    async def cleanup_temp(self) -> Dict:
        \"\"\"Асинхронная очистка временных файлов\"\"\"
        result = {
            \"temp_path\": None,
            \"freed\": 0,
            \"files\": 0,
            \"errors\": 0
        }
        
        temp_path = Path.home() / \"AppData\" / \"Local\" / \"Temp\"
        
        if not temp_path.exists():
            return result
        
        try:
            for item in temp_path.iterdir():
                try:
                    if item.is_dir():
                        # Асинхронное удаление папки
                        await asyncio.to_thread(
                            lambda: __import__(\"shutil\").rmtree(item, ignore_errors=True)
                        )
                    else:
                        # Асинхронное удаление файла
                        await asyncio.to_thread(item.unlink)
                    
                    result[\"files\"] += 1
                    result[\"freed\"] += item.stat().st_size
                    
                except Exception as e:
                    result[\"errors\"] += 1
        
        except Exception as e:
            print(f\"Error in cleanup_temp: {e}\")
        
        result[\"temp_path\"] = str(temp_path)
        return result
    
    async def cleanup_all(self) -> Dict:
        \"\"\"Полная асинхронная очистка\"\"\"
        
        # Выполняем операции параллельно
        results = await asyncio.gather(
            self.cleanup_temp(),
            self.cleanup_cache(),
            self.cleanup_trash(),
            return_exceptions=True
        )
        
        return {
            \"total_freed\": sum(r.get(\"freed\", 0) for r in results if isinstance(r, dict)),
            \"total_files\": sum(r.get(\"files\", 0) for r in results if isinstance(r, dict)),
            \"total_errors\": sum(r.get(\"errors\", 0) for r in results if isinstance(r, dict)),
            \"details\": results
        }
    
    async def cleanup_cache(self) -> Dict:
        # Реализация...
        pass
    
    async def cleanup_trash(self) -> Dict:
        # Реализация...
        pass
```

### 2.3 Обновите главное окно (ui/app.py)

```python
# ui/app.py (основные изменения)

import asyncio
import customtkinter as ctk
from core.task_handler import TaskHandler, EventBus
from core.logger import ColoredLogger
from config.constants import Colors

class KusApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title(\"Kus v2 - System Utility\")
        self.geometry(\"900x700\")
        
        # Инициализируем основные компоненты
        self.event_bus = EventBus()
        self.task_handler = TaskHandler(event_bus=self.event_bus)
        self.logger = ColoredLogger(\"Kus\")
        
        # Подписываемся на события
        self._setup_event_subscriptions()
        
        # Создаем UI
        self._create_ui()
        
        # Запускаем Event Loop
        self._setup_async()
    
    def _setup_event_subscriptions(self):
        \"\"\"Подписываемся на события от компонентов\"\"\"
        self.event_bus.subscribe(\"task:started\", self._on_task_started)
        self.event_bus.subscribe(\"task:completed\", self._on_task_completed)
        self.event_bus.subscribe(\"task:error\", self._on_task_error)
        self.event_bus.subscribe(\"task:progress\", self._on_task_progress)
    
    def _create_ui(self):
        \"\"\"Создает интерфейс приложения\"\"\"
        # ... ваша логика UI ...
        pass
    
    def _setup_async(self):
        \"\"\"Настраивает asyncio для работы с Tkinter\"\"\"
        # Запускаем обработку событий asyncio
        self._run_async_loop()
    
    def _run_async_loop(self):
        \"\"\"Запускает async event loop в отдельном потоке\"\"\"
        import threading
        
        self.loop = asyncio.new_event_loop()
        
        def run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()
    
    async def execute_cleanup(self):
        \"\"\"Пример выполнения асинхронной операции\"\"\"
        from modules.cleanup import CleanupManager
        
        async def cleanup_operation():
            manager = CleanupManager()
            return await manager.cleanup_all()
        
        result = await self.task_handler.execute_task(
            task_id=\"cleanup_001\",
            task_name=\"Очистка системы\",
            operation=cleanup_operation(),
            on_progress=lambda p: print(f\"Progress: {p*100:.0f}%\")
        )
        
        return result
    
    async def _on_task_started(self, data):
        print(f\"✓ Задача начата: {data['task_name']}\")
    
    async def _on_task_completed(self, data):
        print(f\"✓ Завершено: {data['task_name']} ({data['duration']:.2f}s)\")
    
    async def _on_task_error(self, data):
        print(f\"✗ Ошибка: {data['error']}\")
    
    async def _on_task_progress(self, data):
        progress = data['progress']
        print(f\"Прогресс: {progress*100:.0f}%\")
```

---

## Fase 3: Миграция вкладок (5-7 дней)

### 3.1 Проверочный список для каждой вкладки

```
Для cleanup_tab:
  ☐ Заменить синхронные функции на async
  ☐ Добавить прогресс-бар с анимацией
  ☐ Добавить цветное логирование
  ☐ Добавить красивый отчет о результатах
  ☐ Добавить кнопку отмены задачи
  
Для monitor_tab:
  ☐ Использовать asyncio для мониторинга в реальном времени
  ☐ Добавить графики с обновлением каждую секунду
  ☐ Оптимизировать потребление памяти
  
Для network_tab:
  ☐ Конвертировать сетевые операции на async
  ☐ Добавить прогресс для долгих операций
  ☐ Обработать ошибки подключения
  
Для процессов и обновлений:
  ☐ Аналогичные изменения как выше
```

### 3.2 Пример переписания monitor_tab

```python
# ui/tabs/monitor_tab.py (V2)

import asyncio
import customtkinter as ctk
import psutil

class MonitorTab(ctk.CTkFrame):
    def __init__(self, master, task_handler=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.task_handler = task_handler
        self.is_monitoring = False
        self._monitoring_task = None
        
        # Создаем UI элементы для отображения метрик
        self._create_ui()
    
    def _create_ui(self):
        \"\"\"Создает интерфейс мониторинга\"\"\"
        # CPU Chart
        self.cpu_label = ctk.CTkLabel(self, text=\"CPU: 0%\")
        self.cpu_label.pack()
        
        # Memory Chart
        self.memory_label = ctk.CTkLabel(self, text=\"RAM: 0%\")
        self.memory_label.pack()
        
        # Кнопки управления
        self.start_btn = ctk.CTkButton(self, text=\"Начать\", command=self.start_monitoring)
        self.start_btn.pack()
        
        self.stop_btn = ctk.CTkButton(self, text=\"Стоп\", command=self.stop_monitoring)
        self.stop_btn.pack()
    
    def start_monitoring(self):
        \"\"\"Начинает мониторинг\"\"\"
        if not self.is_monitoring:
            self.is_monitoring = True
            self._monitoring_task = asyncio.create_task(self._monitor_loop())
    
    def stop_monitoring(self):
        \"\"\"Останавливает мониторинг\"\"\"
        self.is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
    
    async def _monitor_loop(self):
        \"\"\"Главный цикл мониторинга (асинхронный)\"\"\"
        try:
            while self.is_monitoring:
                # Получаем метрики в отдельном потоке
                cpu_percent = await asyncio.to_thread(psutil.cpu_percent, interval=0.1)
                memory = await asyncio.to_thread(psutil.virtual_memory)
                
                # Обновляем UI в главном потоке
                self.cpu_label.configure(text=f\"CPU: {cpu_percent}%\")
                self.memory_label.configure(text=f\"RAM: {memory.percent}%\")
                
                # Обновляем каждую секунду
                await asyncio.sleep(1)
        
        except asyncio.CancelledError:
            print(\"Monitoring stopped\")
```

---

## Fase 4: Добавление новых модулей (3-5 дней)

### 4.1 modules/autostart.py

```python
# modules/autostart.py

import winreg
from typing import List, Dict
from pathlib import Path

class AutostartManager:
    \"\"\"Менеджер программ в автозагрузке\"\"\"
    
    HKEY_STARTUP_CURRENT = r\"Software\\Microsoft\\Windows\\CurrentVersion\\Run\"
    HKEY_STARTUP_MACHINE = r\"Software\\Microsoft\\Windows\\CurrentVersion\\Run\"
    
    @staticmethod
    def get_autostart_apps() -> List[Dict]:
        \"\"\"Получает список программ из автозагрузки\"\"\"
        apps = []
        
        # Текущий пользователь
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AutostartManager.HKEY_STARTUP_CURRENT) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    name, value, _ = winreg.EnumValue(key, i)
                    apps.append({
                        \"name\": name,
                        \"path\": value,
                        \"scope\": \"HKCU\"
                    })
        except:
            pass
        
        # Все пользователи
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, AutostartManager.HKEY_STARTUP_MACHINE) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    name, value, _ = winreg.EnumValue(key, i)
                    apps.append({
                        \"name\": name,
                        \"path\": value,
                        \"scope\": \"HKLM\"
                    })
        except:
            pass
        
        return apps
    
    @staticmethod
    def add_to_autostart(app_name: str, app_path: str, scope: str = \"HKCU\"):
        \"\"\"Добавляет программу в автозагрузку\"\"\"
        hkey = winreg.HKEY_CURRENT_USER if scope == \"HKCU\" else winreg.HKEY_LOCAL_MACHINE
        
        try:
            with winreg.OpenKey(hkey, AutostartManager.HKEY_STARTUP_CURRENT, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
                return True
        except:
            return False
    
    @staticmethod
    def remove_from_autostart(app_name: str, scope: str = \"HKCU\"):
        \"\"\"Удаляет программу из автозагрузки\"\"\"
        hkey = winreg.HKEY_CURRENT_USER if scope == \"HKCU\" else winreg.HKEY_LOCAL_MACHINE
        
        try:
            with winreg.OpenKey(hkey, AutostartManager.HKEY_STARTUP_CURRENT, 0, winreg.KEY_WRITE) as key:
                winreg.DeleteValue(key, app_name)
                return True
        except:
            return False
```

### 4.2 modules/temperature.py

```python
# modules/temperature.py

import subprocess
import asyncio
from typing import Optional, Dict

class TemperatureMonitor:
    \"\"\"Мониторит температуру CPU и GPU\"\"\"
    
    @staticmethod
    async def get_cpu_temp() -> Optional[float]:
        \"\"\"Получает температуру CPU через WMI\"\"\"
        try:
            cmd = 'wmic OS get CurrentTimeZone'
            # На Windows 10/11
            result = await asyncio.to_thread(
                subprocess.run,
                \"powershell -Command \\\"Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace \\\"root/wmi\\\" | Select -ExpandProperty CurrentTemperature\\\"\",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                temp_kelvin = int(result.stdout.strip()) / 10
                temp_celsius = temp_kelvin - 273.15
                return temp_celsius
        except:
            return None
    
    @staticmethod
    async def get_gpu_temp() -> Optional[Dict]:
        \"\"\"Получает температуру GPU (NVIDIA)\"\"\"
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                \"nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader\",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                temps = result.stdout.strip().split(\"\\n\")
                return {\"nvidia\": [int(t.strip()) for t in temps]}
        except:
            return None
    
    @staticmethod
    async def get_all_temps() -> Dict:
        \"\"\"Получает все доступные температуры\"\"\"
        return {
            \"cpu\": await TemperatureMonitor.get_cpu_temp(),
            \"gpu\": await TemperatureMonitor.get_gpu_temp()
        }
```

---

## Fase 5: Тестирование и оптимизация (3-4 дня)

### 5.1 Модульные тесты

```bash
# tests/test_task_handler.py
pytest tests/test_task_handler.py -v

# tests/test_modules.py
pytest tests/test_modules.py -v

# Запуск всех тестов
pytest tests/ -v --cov
```

### 5.2 Профилирование производительности

```python
# tools/profile_memory.py
import memory_profiler
import asyncio
from core.task_handler import TaskHandler

@memory_profiler.profile
async def test_cleanup():
    handler = TaskHandler()
    # ваша операция
    pass

asyncio.run(test_cleanup())
```

---

## График выполнения

```
Неделя 1 (Phase 1-2):
  День 1-2:  Создание структуры и core компоненты
  День 3-5:  Интеграция TaskHandler и logger

Неделя 2-3 (Phase 3):
  День 1-7:  Миграция вкладок на async

Неделя 4 (Phase 4):
  День 1-5:  Добавление новых модулей

Неделя 5 (Phase 5):
  День 1-4:  Тестирование и оптимизация

ИТОГО: ~4 недели для полной миграции
```

---

## Критерии успеха

✅ **Готово к релизу v2 если:**
- [ ] Все вкладки работают асинхронно без зависаний UI
- [ ] TaskHandler правильно обрабатывает все операции
- [ ] Логирование работает с цветами
- [ ] Event Bus корректно эмитит события
- [ ] Добавлены новые модули (autostart, temperature)
- [ ] Все модули имеют тесты
- [ ] Документация обновлена
- [ ] Performance метрики улучшены

---

## Что дальше?

После успешной миграции на v2:

1. **Go + Wails миграция** (опционально, через 6 месяцев)
   - Переписать UI на React/Vue
   - Переписать backend на Go
   - Ожидаемое улучшение: 5x быстрее, -60% RAM

2. **Популярные фичи**
   - Поддержка плагинов
   - Синхронизация между ПК
   - Облачные обновления

3. **Монетизация** (если нужно)
   - Free tier + Pro версия
   - Интеграция с IDE (VS Code extension)
   - GitHub Actions integration

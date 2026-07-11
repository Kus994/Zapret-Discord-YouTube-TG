"""
📚 ПОЛНАЯ ПОШАГОВАЯ ИНСТРУКЦИЯ ПО РЕШЕНИЮ ВСЕХ ПРОБЛЕМ KUS
═════════════════════════════════════════════════════════════════════════════

Эта инструкция содержит ВСЕ шаги для исправления 10 проблем.
Следуй её ШАГ ЗА ШАГОМ - и приложение полностью переделается!

Время для прочтения: 30-40 минут
Время для реализации: 5-7 дней (если работать 2-3 часа в день)
"""

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 1: ПОДГОТОВКА (День 1, утро - 30 минут)
# ═════════════════════════════════════════════════════════════════════════════

"""
ЗАДАЧА: Создать правильную структуру проекта

ТЕКУЩАЯ СТРУКТУРА (НЕПРАВИЛЬНАЯ):
sysutil/
├── main.py                      ← 850 строк, монолит!
├── modules/
│   ├── cleanup.py              ← Синхронные функции
│   ├── network.py              ← Синхронные функции
│   └── ...
└── assets/

ПРАВИЛЬНАЯ СТРУКТУРА:
sysutil/
├── main.py                      ← Точка входа (5-10 строк)
├── requirements.txt
│
├── config/                      ← НОВОЕ
│   ├── __init__.py
│   └── constants.py            (цвета, пути)
│
├── core/                        ← НОВОЕ
│   ├── __init__.py
│   ├── task_handler.py         (из примера)
│   ├── logger.py               (из примера)
│   └── event_bus.py            (pub-sub)
│
├── ui/                         ← ПЕРЕДЕЛАНО
│   ├── __init__.py
│   ├── app.py                 (главное окно, переписано)
│   ├── widgets/               (компоненты)
│   └── tabs/                  (вкладки)
│
├── modules/                    ← ПЕРЕДЕЛАНО
│   ├── __init__.py
│   ├── cleanup.py             (async версия)
│   ├── network.py             (async версия)
│   └── ...
│
└── assets/
"""

# ИНСТРУКЦИЯ:
print("""
ШАГ 1: Создай новые папки

1. Открой проводник в папке sysutil/
2. Создай новые папки:
   - config
   - core
   - ui/widgets
   - ui/tabs

Команда для bash/PowerShell:
""")

# PowerShell:
# mkdir config, core, ui\widgets, ui\tabs

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 2: КОПИРОВАНИЕ И ПЕРЕИМЕНОВАНИЕ ФАЙЛОВ (День 1, полдень - 15 минут)
# ═════════════════════════════════════════════════════════════════════════════

"""
ЗАДАЧА: Скопировать созданные файлы в правильные места

ЧТО ДЕЛАТЬ:
1. Скопируй core_task_handler.py → core/task_handler.py
2. Скопируй core_logger.py → core/logger.py
3. Скопируй cleanup_tab_v2.py → ui/tabs/cleanup_tab.py

КОМАНДЫ:
"""

commands = """
# Скопировать файлы
cp core_task_handler.py sysutil/core/task_handler.py
cp core_logger.py sysutil/core/logger.py
cp cleanup_tab_v2.py sysutil/ui/tabs/cleanup_tab.py

# Переименовать текущий main.py для сохранения
cp sysutil/main.py sysutil/main_old.py

# Создать новую структуру:
touch sysutil/config/__init__.py
touch sysutil/config/constants.py
touch sysutil/core/__init__.py
touch sysutil/core/event_bus.py
touch sysutil/ui/__init__.py
touch sysutil/ui/app.py
touch sysutil/ui/tabs/__init__.py
touch sysutil/ui/widgets/__init__.py
"""

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 3: СОЗДАНИЕ config/constants.py (День 1, 16:00 - 10 минут)
# ═════════════════════════════════════════════════════════════════════════════

"""
ЗАДАЧА: Централизовать все константы

Почему это важно:
- Избежишь дублирования цветов
- Легче менять тему
- Всё в одном месте
"""

config_constants = """
# config/constants.py

from pathlib import Path

# ──── Пути ────
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / \"assets\"
BACKGROUND_PATH = ASSETS_DIR / \"background.jpg\"

# ──── Цвета ────
class Colors:
    BG_DARK         = \"#0B1220\"
    BG_PANEL        = \"#0F1823\"
    ACCENT          = \"#5AA9E6\"
    ACCENT_HOVER    = \"#3D8FCF\"
    TEXT_MAIN       = \"#E7EEF7\"
    TEXT_DIM        = \"#8FA3BD\"
    SUCCESS         = \"#4CC9A4\"
    WARN            = \"#F4A261\"
    ERROR           = \"#E15554\"
    LOG_BG          = \"#060A12\"

# ──── Шрифты ────
class Fonts:
    FAMILY = \"Segoe UI\"
    TITLE = (FAMILY, 16, \"bold\")
    SUBTITLE = (FAMILY, 13, \"bold\")
    NORMAL = (FAMILY, 11)
    SMALL = (FAMILY, 10)
    MONO = (\"Consolas\", 10)

# ──── Настройки приложения ────
APP_TITLE = \"Kus - System Utility\"
APP_VERSION = \"2.0.0\"
MIN_WINDOW_WIDTH = 900
MIN_WINDOW_HEIGHT = 700
"""

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 4: СОЗДАНИЕ core/event_bus.py (День 1, 16:30 - 20 минут)
# ═════════════════════════════════════════════════════════════════════════════

"""
ЗАДАЧА: Реализовать Event Bus для связи компонентов

Почему это важно:
- Компоненты не знают друг о друге (слабая связанность)
- Легко добавлять новые события
- Система становится масштабируемой
"""

event_bus_code = """
# core/event_bus.py

import asyncio
import threading
from typing import Callable, Dict, List

class EventBus:
    \"\"\"Простая реализация паттерна Pub-Sub\"\"\"
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
    
    def subscribe(self, event_name: str, callback: Callable) -> str:
        \"\"\"Подписывается на событие\"\"\"
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

# СОБЫТИЯ ПРИЛОЖЕНИЯ:
# task:started          - задача начала выполняться
# task:progress         - прогресс задачи (0.0-1.0)
# task:completed        - задача завершилась успешно
# task:error            - задача закончилась с ошибкой
# task:cancelled        - задача была отменена
# ui:update             - обновить UI
# log:message           - новое сообщение в логе
"""

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 5: ПЕРЕПИСАТЬ modules/cleanup.py НА ASYNC (День 2, 10:00 - 1.5 часа)
# ═════════════════════════════════════════════════════════════════════════════

"""
ЗАДАЧА: Конвертировать все модули в асинхронные функции

Проблема текущего кода:
    def clean_temp_folders(log_func, progress_func):
        for target in targets:
            freed = _safe_remove_tree(target, log_func)  # ← БЛОКИРУЕТ UI!

Решение:
    async def clean_temp_folders(log_func, progress_func):
        for target in targets:
            # Выполнять в отдельном потоке, не блокируя UI!
            freed = await asyncio.to_thread(_safe_remove_tree, target, log_func)
"""

cleanup_async_code = """
# modules/cleanup.py (НОВАЯ ВЕРСИЯ - АСИНХРОННАЯ)

import asyncio
import os
import shutil
from pathlib import Path
from typing import Dict, Callable, Optional

async def _safe_remove_tree_async(path: Path, log_func) -> int:
    \"\"\"Асинхронное удаление файлов (в отдельном потоке)\"\"\"
    return await asyncio.to_thread(_safe_remove_tree, path, log_func)

def _safe_remove_tree(path: Path, log_func) -> int:
    \"\"\"Синхронная функция удаления (может быть в отдельном потоке)\"\"\"
    freed = 0
    if not path.exists():
        return freed
    
    for entry in path.iterdir():
        try:
            if entry.is_dir() and not entry.is_symlink():
                size = sum(
                    f.stat().st_size for f in entry.rglob(\"*\") if f.is_file()
                )
                shutil.rmtree(entry, ignore_errors=True)
                freed += size
            else:
                size = entry.stat().st_size
                entry.unlink(missing_ok=True)
                freed += size
        except (PermissionError, OSError) as exc:
            log_func(f\"[пропущено] {entry.name}: {exc.__class__.__name__}\")
    
    return freed

async def clean_temp_folders(
    log_func: Callable,
    progress_func: Callable,
    update_progress_handler=None,  # ← NEW: для TaskHandler
    include_all_disks: bool = True
) -> Dict:
    \"\"\"АСИНХРОННАЯ очистка Temp-папок
    
    Теперь это не блокирует UI!
    \"\"\"
    
    total_freed = 0
    targets = [
        Path(os.environ.get(\"TEMP\", \"\")),
        Path(os.environ.get(\"WINDIR\", \"C:\\\\Windows\")) / \"Temp\",
    ]
    
    log_func(f\"Поиск временных файлов ({len(targets)} папок)...\")
    progress_func(0.05)
    if update_progress_handler:
        await update_progress_handler(1, len(targets))
    
    for i, target in enumerate(targets, 1):
        if not target or not target.exists():
            continue
        
        log_func(f\"Очистка: {target}\")
        
        # КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: выполняем в отдельном потоке!
        freed = await _safe_remove_tree_async(target, log_func)
        total_freed += freed
        log_func(f\"  Освобождено: {_human_size(freed)}\")
        
        progress_func(0.05 + 0.45 * i / len(targets))
        if update_progress_handler:
            await update_progress_handler(i, len(targets))
    
    return {
        \"success\": True,
        \"freed_bytes\": total_freed,
        \"freed_gb\": total_freed / (1024**3)
    }

# ПРИМЕНИТЬ ЖЕ ПРЕОБРАЗОВАНИЕ К:
# - modules/network.py
# - modules/processes.py
# - modules/updates.py
# - modules/monitor.py
#
# Везде использовать asyncio.to_thread() для длительных операций!
"""

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 6: ПЕРЕПИСАТЬ ГЛАВНОЕ ОКНО (День 2-3, 10:00 - 2 часа)
# ═════════════════════════════════════════════════════════════════════════════

"""
ЗАДАЧА: Переписать main.py с новой архитектурой

СТАРЫЙ КОД (ПЛОХО):
    import customtkinter as ctk
    from modules import cleanup, network, processes, ...  # ← Загружаются ВСЕ!
    
    class SysUtilApp(ctk.CTk):
        def __init__(self):
            super().__init__()
            # Всё в одном файле...

НОВЫЙ КОД (ХОРОШО):
    import asyncio
    from core.task_handler import TaskHandler, EventBus
    from core.logger import ColoredLogger
    
    class SysUtilApp(ctk.CTk):
        def __init__(self):
            super().__init__()
            
            # Инициализируем систему
            self.event_bus = EventBus()
            self.task_handler = TaskHandler(event_bus=self.event_bus)
            self.logger = ColoredLogger()
            
            # Запускаем asyncio
            self._setup_async()
"""

main_py_new = """
# main.py (ПОЛНОСТЬЮ ПЕРЕПИСАН)

import asyncio
import customtkinter as ctk
import sys
from pathlib import Path

# Импортируем ТОЛЬКО то, что нужно сейчас
from config.constants import Colors, Fonts, APP_TITLE, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from core.task_handler import TaskHandler, EventBus
from core.logger import ColoredLogger
from ui.app import KusApp

# ══════════════════════════════════════════════════════════════════════════════

def setup_styles():
    \"\"\"Настраивает стиль приложения\"\"\"
    ctk.set_appearance_mode(\"dark\")
    ctk.set_default_color_theme(\"blue\")

def main():
    \"\"\"Главная функция запуска\"\"\"
    
    # Проверка прав администратора
    from modules.elevation import is_admin, relaunch_as_admin
    
    if not is_admin():
        try:
            relaunch_as_admin()
            return
        except OSError:
            print(\"Пользователь отклонил запрос прав администратора.\")
    
    # Настройка стилей
    setup_styles()
    
    # Создание приложения
    app = KusApp()
    app.mainloop()

if __name__ == \"__main__\":
    main()
"""

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 7: СОЗДАНИЕ ui/app.py (День 3, 10:00 - 2.5 часа)
# ═════════════════════════════════════════════════════════════════════════════

"""
ЗАДАЧА: Написать новый главный класс приложения
"""

ui_app_code = """
# ui/app.py (НОВАЯ ВЕРСИЯ ГЛАВНОГО ОКНА)

import asyncio
import customtkinter as ctk
from pathlib import Path
from config.constants import Colors, Fonts, APP_TITLE, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from core.task_handler import TaskHandler, EventBus
from core.logger import ColoredLogger

class KusApp(ctk.CTk):
    \"\"\"Главное окно приложения Kus v2\"\"\"
    
    def __init__(self):
        super().__init__()
        
        # Инициализируем систему
        self.event_bus = EventBus()
        self.task_handler = TaskHandler(event_bus=self.event_bus)
        self.logger = ColoredLogger(\"Kus\")
        
        # Настройка окна
        self.title(APP_TITLE)
        self.geometry(f\"{MIN_WINDOW_WIDTH}x{MIN_WINDOW_HEIGHT}\")
        self.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.configure(fg_color=Colors.BG_DARK)
        
        # Подписываемся на события
        self._setup_event_subscriptions()
        
        # Создаем UI
        self._create_ui()
        
        # Запускаем asyncio event loop
        self._setup_async()
        
        # Обработчик закрытия
        self.protocol(\"WM_DELETE_WINDOW\", self._on_close)
    
    def _setup_event_subscriptions(self):
        \"\"\"Подписываемся на события\"\"\"
        self.event_bus.subscribe(\"task:started\", self._on_task_started)
        self.event_bus.subscribe(\"task:completed\", self._on_task_completed)
        self.event_bus.subscribe(\"task:error\", self._on_task_error)
        self.event_bus.subscribe(\"task:progress\", self._on_task_progress)
    
    def _create_ui(self):
        \"\"\"Создает интерфейс приложения\"\"\"
        
        # Основная сетка
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        
        # Боковая панель
        self._create_sidebar()
        
        # Основное содержимое
        self._create_content_area()
    
    def _create_sidebar(self):
        \"\"\"Создает боковую панель навигации\"\"\"
        sidebar = ctk.CTkFrame(
            self,
            width=240,
            fg_color=Colors.BG_PANEL,
            corner_radius=0
        )
        sidebar.grid(row=0, column=0, sticky=\"nsew\")
        sidebar.grid_propagate(False)
        
        # Заголовок
        title = ctk.CTkLabel(
            sidebar,
            text=\"Kus\",
            text_color=Colors.TEXT_MAIN,
            font=Fonts.TITLE
        )
        title.pack(anchor=\"w\", padx=20, pady=(24, 0))
        
        desc = ctk.CTkLabel(
            sidebar,
            text=\"Утилита системного администратора\",
            text_color=Colors.TEXT_DIM,
            font=Fonts.SMALL
        )
        desc.pack(anchor=\"w\", padx=20, pady=(0, 24))
        
        # Кнопки навигации
        self.nav_buttons = {}
        nav_items = [
            (\"cleanup\", \"🧹 Очистка системы\"),
            (\"network\", \"🌐 Сетевая диагностика\"),
            (\"processes\", \"⚙️ Менеджер процессов\"),
            (\"updates\", \"🔄 Обновления Windows\"),
            (\"monitor\", \"📊 Мониторинг ресурсов\"),
        ]
        
        for key, label in nav_items:
            btn = ctk.CTkButton(
                sidebar,
                text=label,
                fg_color=Colors.BG_PANEL,
                hover_color=Colors.ACCENT,
                text_color=Colors.TEXT_MAIN,
                font=Fonts.NORMAL,
                command=lambda k=key: self._show_section(k)
            )
            btn.pack(fill=\"x\", padx=12, pady=4)
            self.nav_buttons[key] = btn
        
        # Статус в низу
        status = ctk.CTkLabel(
            sidebar,
            text=\"✓ Права администратора\",
            text_color=Colors.SUCCESS,
            font=Fonts.SMALL
        )
        status.pack(side=\"bottom\", padx=20, pady=20, anchor=\"w\")
    
    def _create_content_area(self):
        \"\"\"Создает основную область содержимого\"\"\"
        content = ctk.CTkFrame(self, fg_color=Colors.BG_DARK)
        content.grid(row=0, column=1, sticky=\"nsew\")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        
        # Здесь будут вкладки
        self.content_frame = content
    
    def _show_section(self, section_key: str):
        \"\"\"Показывает секцию по ключу\"\"\"
        self.logger.info(f\"Переключение на: {section_key}\")
    
    def _setup_async(self):
        \"\"\"Настраивает asyncio event loop\"\"\"
        import threading
        
        self.loop = asyncio.new_event_loop()
        
        def run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()
    
    async def _on_task_started(self, data):
        \"\"\"Событие: задача начата\"\"\"
        self.logger.info(f\"✓ Задача начата: {data.get('task_name', '?')}\")
    
    async def _on_task_completed(self, data):
        \"\"\"Событие: задача завершена\"\"\"
        duration = data.get('duration', 0)
        self.logger.success(
            f\"✓ Завершено: {data.get('task_name', '?')} ({duration:.2f}s)\"
        )
    
    async def _on_task_error(self, data):
        \"\"\"Событие: ошибка в задаче\"\"\"
        self.logger.error(f\"✗ Ошибка: {data.get('error', '?')}\")
    
    async def _on_task_progress(self, data):
        \"\"\"Событие: прогресс задачи\"\"\"
        progress = data.get('progress', 0)
        # print(f\"Прогресс: {progress*100:.0f}%\")
    
    def _on_close(self):
        \"\"\"Обработчик закрытия приложения\"\"\"
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.destroy()
"""

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 8: ОБНОВИТЬ requirements.txt (День 3, 15:00 - 5 минут)
# ═════════════════════════════════════════════════════════════════════════════

new_requirements = """
# requirements.txt (НОВАЯ ВЕРСИЯ)

customtkinter>=5.2.2
pillow>=10.0.0
psutil>=5.9.0
aiofiles>=23.0.0
aiohttp>=3.8.0
pywin32>=305
"""

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 9: ТЕСТИРОВАНИЕ (День 4, 10:00 - 2 часа)
# ═════════════════════════════════════════════════════════════════════════════

"""
ЗАДАЧА: Протестировать новую архитектуру

ТЕСТЫ:
1. Проверить, что UI не зависает
2. Проверить, что можно отменить операцию
3. Проверить, что логирование работает
4. Проверить, что Event Bus работает
"""

test_code = '''
# tests/test_new_architecture.py

import asyncio
import pytest
from core.task_handler import TaskHandler, EventBus
from core.logger import ColoredLogger

@pytest.mark.asyncio
async def test_task_handler():
    """Тест TaskHandler"""
    handler = TaskHandler()
    
    async def simple_operation():
        await asyncio.sleep(0.1)
        return {\"result\": \"success\"}
    
    result = await handler.execute_task(
        task_id=\"test_001\",
        task_name=\"Test Task\",
        operation=simple_operation()
    )
    
    assert result.success
    assert result.data[\"result\"] == \"success\"

@pytest.mark.asyncio
async def test_event_bus():
    """Тест Event Bus"""
    bus = EventBus()
    events = []
    
    async def callback(data):
        events.append(data)
    
    bus.subscribe(\"test_event\", callback)
    await bus.emit(\"test_event\", {\"message\": \"Hello\"})
    
    assert len(events) == 1
    assert events[0][\"message\"] == \"Hello\"

def test_logger():
    """Тест логирования"""
    logger = ColoredLogger(\"Test\")
    
    # Просто проверяем, что не выбрасывает исключений
    logger.success(\"Success message\")
    logger.warning(\"Warning message\")
    logger.error(\"Error message\")
'''

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 10: РАЗВЕРТЫВАНИЕ (День 5, 10:00 - 1 час)
# ═════════════════════════════════════════════════════════════════════════════

"""
ЗАДАЧА: Собрать новую версию в .exe
"""

build_instructions = """
# Сборка в .exe

1. Убедитесь, что установлен PyInstaller:
   pip install pyinstaller

2. Выполните команду:
   pyinstaller --onefile --noconsole \\
       --add-data \"assets;assets\" \\
       --icon=assets/icon.ico \\
       --name=\"Kus\" \\
       main.py

3. Файл будет в dist/Kus.exe

ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ:
- Размер: ~150 МБ (как было)
- Время запуска: 4-5 сек (как было)
- ✅ UI НЕ ЗАВИСАЕТ! (главное улучшение)
"""

# ═════════════════════════════════════════════════════════════════════════════
print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                  🎯 ПОЛНАЯ ИНСТРУКЦИЯ ПО ИСПРАВЛЕНИЮ KUS                 ║
╚═══════════════════════════════════════════════════════════════════════════╝

ШАГ 1: Создай структуру проекта (30 мин)
ШАГ 2: Скопируй созданные файлы (15 мин)
ШАГ 3: Создай config/constants.py (10 мин)
ШАГ 4: Создай core/event_bus.py (20 мин)
ШАГ 5: Переписи modules/*.py на async (1.5 часа)
ШАГ 6: Переписи main.py (2 часа)
ШАГ 7: Создай ui/app.py (2.5 часа)
ШАГ 8: Обновить requirements.txt (5 мин)
ШАГ 9: Тестирование (2 часа)
ШАГ 10: Развертывание в .exe (1 час)

ИТОГО: 5-7 дней при работе 2-3 часа в день

РЕЗУЛЬТАТ:
✅ UI НЕ ЗАВИСАЕТ
✅ Можно отменить операцию
✅ Красивое логирование
✅ Event Bus для связи
✅ Правильная архитектура
✅ Легче развивать дальше

НАЧИНАЙ С ЭТАПА 1 ПРЯМО СЕЙЧАС! 🚀
""")
"""

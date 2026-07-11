"""
ГОТОВЫЙ КОД ДЛЯ КОПИРОВАНИЯ И ИСПОЛЬЗОВАНИЯ
═════════════════════════════════════════════════════════════════════════════

Эти файлы полностью готовы к использованию!
Просто скопируй их в свой проект и замени старые версии.

📂 main.py          → скопировать в sysutil/main.py
📂 app.py           → скопировать в sysutil/ui/app.py  
📂 constants.py     → скопировать в sysutil/config/constants.py
📂 event_bus.py     → скопировать в sysutil/core/event_bus.py
"""

# ═════════════════════════════════════════════════════════════════════════════
# FILE 1: sysutil/main.py (НОВАЯ ВЕРСИЯ)
# ═════════════════════════════════════════════════════════════════════════════

MAIN_PY = """
\"\"\"
main.py - Точка входа приложения Kus v2
════════════════════════════════════════

Новая версия: минимальный код, вся логика в других модулях.
\"\"\"

import sys
import customtkinter as ctk
from config.constants import Colors, APP_TITLE, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from ui.app import KusApp
from modules.elevation import is_admin, relaunch_as_admin

def setup_styles():
    \"\"\"Настраивает стиль приложения\"\"\"
    ctk.set_appearance_mode(\"dark\")
    ctk.set_default_color_theme(\"blue\")

def main():
    \"\"\"Главная функция запуска\"\"\"
    
    # Проверка прав администратора
    if not is_admin():
        try:
            relaunch_as_admin()
            return
        except OSError:
            print(\"Пользователь отклонил запрос прав администратора.\")
    
    # Настройка стилей
    setup_styles()
    
    # Создание и запуск приложения
    app = KusApp()
    app.mainloop()

if __name__ == \"__main__\":
    main()
\"\"\"

# ═════════════════════════════════════════════════════════════════════════════
# FILE 2: sysutil/config/constants.py (НОВАЯ ВЕРСИЯ)
# ═════════════════════════════════════════════════════════════════════════════

CONSTANTS_PY = """
\"\"\"
config/constants.py - Все константы приложения
═══════════════════════════════════════════════

Цвета, пути, шрифты, настройки - всё в одном месте!
\"\"\"

from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────
# ПУТИ
# ──────────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / \"assets\"
BACKGROUND_PATH = ASSETS_DIR / \"background.jpg\"

# ──────────────────────────────────────────────────────────────────────────
# ЦВЕТА
# ──────────────────────────────────────────────────────────────────────────

class Colors:
    \"\"\"Цветовая схема приложения\"\"\"
    BG_DARK         = \"#0B1220\"    # Тёмный фон
    BG_PANEL        = \"#0F1823\"    # Фон панели
    ACCENT          = \"#5AA9E6\"    # Основной цвет (голубой)
    ACCENT_HOVER    = \"#3D8FCF\"    # При наведении
    TEXT_MAIN       = \"#E7EEF7\"    # Основной текст (белый)
    TEXT_DIM        = \"#8FA3BD\"    # Затемнённый текст (серый)
    SUCCESS         = \"#4CC9A4\"    # Успех (зелёный)
    WARN            = \"#F4A261\"    # Предупреждение (оранжевый)
    ERROR           = \"#E15554\"    # Ошибка (красный)
    LOG_BG          = \"#060A12\"    # Фон логов (ещё темнее)

# ──────────────────────────────────────────────────────────────────────────
# ШРИФТЫ
# ──────────────────────────────────────────────────────────────────────────

class Fonts:
    \"\"\"Шрифты приложения\"\"\"
    FAMILY = \"Segoe UI\"
    TITLE = (FAMILY, 16, \"bold\")
    SUBTITLE = (FAMILY, 13, \"bold\")
    NORMAL = (FAMILY, 11)
    SMALL = (FAMILY, 10)
    MONO = (\"Consolas\", 10)

# ──────────────────────────────────────────────────────────────────────────
# НАСТРОЙКИ ПРИЛОЖЕНИЯ
# ──────────────────────────────────────────────────────────────────────────

APP_TITLE = \"Kus v2 - System Utility\"
APP_VERSION = \"2.0.0\"
MIN_WINDOW_WIDTH = 900
MIN_WINDOW_HEIGHT = 700

# ──────────────────────────────────────────────────────────────────────────
# ТАЙМАУТЫ (в секундах)
# ──────────────────────────────────────────────────────────────────────────

TIMEOUT_CLEANUP = 300         # 5 минут на очистку
TIMEOUT_NETWORK = 60          # 1 минута на сетевые операции
TIMEOUT_MONITOR = 30          # 30 сек на мониторинг
TIMEOUT_UPDATE = 600          # 10 минут на обновления
\"\"\"

# ═════════════════════════════════════════════════════════════════════════════
# FILE 3: sysutil/core/event_bus.py (НОВАЯ ВЕРСИЯ)
# ═════════════════════════════════════════════════════════════════════════════

EVENT_BUS_PY = """
\"\"\"
core/event_bus.py - Шина событий (Pub-Sub)
═══════════════════════════════════════════

Позволяет компонентам общаться друг с другом без прямых зависимостей.
\"\"\"

import asyncio
import threading
from typing import Callable, Dict, List, Optional

class EventBus:
    \"\"\"
    Простая реализация паттерна Pub-Sub для асинхронного общения.
    
    Использование:
    ──────────────
    bus = EventBus()
    
    # Подписка
    bus.subscribe(\"task:completed\", on_task_completed)
    
    # Эмитирование события
    await bus.emit(\"task:completed\", {\"task_id\": \"123\", \"result\": \"ok\"})
    \"\"\"
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
    
    def subscribe(self, event_name: str, callback: Callable) -> str:
        \"\"\"
        Подписывается на событие.
        
        Args:
            event_name: Название события (e.g. \"task:completed\")
            callback: Функция или async функция для вызова
        
        Returns:
            subscription_id для отписки
        \"\"\"
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(callback)
        
        return f\"{event_name}_{id(callback)}\"
    
    def unsubscribe(self, event_name: str, callback: Callable) -> bool:
        \"\"\"Отписывается от события\"\"\"
        with self._lock:
            if event_name in self._subscribers:
                try:
                    self._subscribers[event_name].remove(callback)
                    return True
                except ValueError:
                    return False
        return False
    
    async def emit(self, event_name: str, data: dict = None):
        \"\"\"
        Эмитирует событие всем подписчикам (асинхронно).
        
        Args:
            event_name: Название события
            data: Данные события
        \"\"\"
        with self._lock:
            callbacks = self._subscribers.get(event_name, []).copy()
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data or {})
                else:
                    callback(data or {})
            except Exception as e:
                print(f\"[EventBus Error] {event_name}: {e}\")
    
    def get_subscribers_count(self, event_name: str) -> int:
        \"\"\"Возвращает количество подписчиков на событие\"\"\"
        with self._lock:
            return len(self._subscribers.get(event_name, []))
    
    def clear_all(self):
        \"\"\"Удаляет всех подписчиков (для cleanup)\"\"\"
        with self._lock:
            self._subscribers.clear()

# ──────────────────────────────────────────────────────────────────────────
# События приложения
# ──────────────────────────────────────────────────────────────────────────

\"\"\"
СОБЫТИЯ КОТОРЫЕ ЭМИТИРУЕТ ПРИЛОЖЕНИЕ:

task:started
    - Когда задача начинает выполняться
    - data = {\"task_id\", \"task_name\", \"timestamp\"}

task:progress
    - Когда прогресс задачи изменяется
    - data = {\"task_id\", \"progress\": 0.0-1.0, \"current_step\", \"total_steps\"}

task:completed
    - Когда задача успешно завершилась
    - data = {\"task_id\", \"task_name\", \"duration\": float, \"result\": dict}

task:error
    - Когда произошла ошибка в задаче
    - data = {\"task_id\", \"task_name\", \"error\": str, \"exception_type\": str}

task:cancelled
    - Когда задача была отменена
    - data = {\"task_id\", \"task_name\"}

log:message
    - Новое сообщение для логирования
    - data = {\"level\": str, \"message\": str, \"timestamp\": str}

ui:update
    - Обновить UI
    - data = {\"section\": str, \"data\": dict}
\"\"\"
\"\"\"

# ═════════════════════════════════════════════════════════════════════════════
# FILE 4: sysutil/ui/app.py (НОВАЯ ВЕРСИЯ)
# ═════════════════════════════════════════════════════════════════════════════

APP_PY = """
\"\"\"
ui/app.py - Главное окно приложения Kus v2
═══════════════════════════════════════════

Содержит основное окно и управление жизненным циклом приложения.
\"\"\"

import asyncio
import customtkinter as ctk
import threading
from pathlib import Path

from config.constants import Colors, Fonts, APP_TITLE, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from core.task_handler import TaskHandler
from core.event_bus import EventBus
from core.logger import ColoredLogger

# ──────────────────────────────────────────────────────────────────────────

class NavButton(ctk.CTkButton):
    \"\"\"Кнопка навигации в боковой панели\"\"\"
    
    def __init__(self, master, text: str, command=None, **kwargs):
        super().__init__(
            master,
            text=text,
            command=command,
            fg_color=Colors.BG_PANEL,
            hover_color=Colors.ACCENT,
            text_color=Colors.TEXT_MAIN,
            font=Fonts.NORMAL,
            height=40,
            **kwargs
        )
        self._is_active = False
    
    def set_active(self, active: bool):
        \"\"\"Устанавливает активность кнопки\"\"\"
        self._is_active = active
        if active:
            self.configure(fg_color=Colors.ACCENT, text_color=\"white\")
        else:
            self.configure(fg_color=Colors.BG_PANEL, text_color=Colors.TEXT_MAIN)

# ──────────────────────────────────────────────────────────────────────────

class KusApp(ctk.CTk):
    \"\"\"
    Главное окно приложения Kus v2.
    
    Отвечает за:
    - Инициализацию системы (Event Bus, TaskHandler, Logger)
    - Создание UI (sidebar + content area)
    - Управление жизненным циклом приложения
    - Интеграцию asyncio с Tkinter
    \"\"\"
    
    def __init__(self):
        super().__init__()
        
        # Инициализируем ядро системы
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
        
        self.logger.info(f\"✓ {APP_TITLE} инициализировано\")
    
    def _setup_event_subscriptions(self):
        \"\"\"Подписываемся на события системы\"\"\"
        self.event_bus.subscribe(\"task:started\", self._on_task_started)
        self.event_bus.subscribe(\"task:completed\", self._on_task_completed)
        self.event_bus.subscribe(\"task:error\", self._on_task_error)
        self.event_bus.subscribe(\"task:progress\", self._on_task_progress)
    
    def _create_ui(self):
        \"\"\"Создает интерфейс приложения\"\"\"
        
        # Основная сетка (2 колонки: sidebar + content)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)  # Sidebar фиксированная ширина
        self.grid_columnconfigure(1, weight=1)  # Content растяжимая
        
        # Боковая панель
        sidebar = self._create_sidebar()
        sidebar.grid(row=0, column=0, sticky=\"nsew\")
        
        # Основное содержимое
        content = self._create_content_area()
        content.grid(row=0, column=1, sticky=\"nsew\")
    
    def _create_sidebar(self) -> ctk.CTkFrame:
        \"\"\"Создает боковую панель навигации\"\"\"
        
        sidebar = ctk.CTkFrame(
            self,
            width=240,
            fg_color=Colors.BG_PANEL,
            corner_radius=0
        )
        sidebar.grid_propagate(False)  # Фиксированная ширина
        
        # Заголовок приложения
        title = ctk.CTkLabel(
            sidebar,
            text=\"Kus\",
            text_color=Colors.TEXT_MAIN,
            font=Fonts.TITLE
        )
        title.pack(anchor=\"w\", padx=20, pady=(24, 0))
        
        # Подзаголовок
        desc = ctk.CTkLabel(
            sidebar,
            text=\"Утилита системного администратора\",
            text_color=Colors.TEXT_DIM,
            font=Fonts.SMALL
        )
        desc.pack(anchor=\"w\", padx=20, pady=(0, 24))
        
        # Линия-разделитель
        sep = ctk.CTkFrame(sidebar, height=1, fg_color=Colors.TEXT_DIM)
        sep.pack(fill=\"x\", padx=12, pady=(0, 12))
        
        # Кнопки навигации
        self.nav_buttons = {}
        nav_items = [
            (\"cleanup\", \"🧹  Очистка\"),
            (\"network\", \"🌐  Сеть\"),
            (\"processes\", \"⚙️  Процессы\"),
            (\"updates\", \"🔄  Обновления\"),
            (\"monitor\", \"📊  Мониторинг\"),
        ]
        
        for key, label in nav_items:
            btn = NavButton(
                sidebar,
                label,
                command=lambda k=key: self._show_section(k)
            )
            btn.pack(fill=\"x\", padx=12, pady=4)
            self.nav_buttons[key] = btn
        
        # Активируем первую кнопку
        self.nav_buttons[\"cleanup\"].set_active(True)
        
        # Статус в низу
        status_frame = ctk.CTkFrame(sidebar, fg_color=\"transparent\")
        status_frame.pack(side=\"bottom\", fill=\"x\", padx=12, pady=20)
        
        status = ctk.CTkLabel(
            status_frame,
            text=\"✓ Администратор\",
            text_color=Colors.SUCCESS,
            font=Fonts.SMALL
        )
        status.pack(anchor=\"w\")
        
        return sidebar
    
    def _create_content_area(self) -> ctk.CTkFrame:
        \"\"\"Создает основную область содержимого\"\"\"
        
        content = ctk.CTkFrame(self, fg_color=Colors.BG_DARK)
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        
        # Здесь будут размещены вкладки
        # (пока заглушка)
        placeholder = ctk.CTkLabel(
            content,
            text=\"Добро пожаловать в Kus v2!\\\\n\\\\nОК, я в разработке...\",
            text_color=Colors.TEXT_DIM,
            font=Fonts.NORMAL
        )
        placeholder.pack(expand=True, anchor=\"center\")
        
        self.content_frame = content
        return content
    
    def _show_section(self, section_key: str):
        \"\"\"Переключается на секцию по ключу\"\"\"
        
        # Обновляем активность кнопок
        for key, btn in self.nav_buttons.items():
            btn.set_active(key == section_key)
        
        self.logger.info(f\"Переключение: {section_key}\")
    
    def _setup_async(self):
        \"\"\"Настраивает asyncio event loop для работы с Tkinter\"\"\"
        
        # Создаем новый event loop
        self.loop = asyncio.new_event_loop()
        
        # Функция для запуска loop в отдельном потоке
        def run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        # Запускаем в daemon потоке
        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()
        
        self.logger.debug(\"✓ Asyncio event loop запущен\")
    
    # ──── EVENT HANDLERS ────
    
    async def _on_task_started(self, data: dict):
        \"\"\"Обработчик: задача начата\"\"\"
        task_name = data.get(\"task_name\", \"Unknown\")
        self.logger.info(f\"▶ Начало: {task_name}\")
    
    async def _on_task_completed(self, data: dict):
        \"\"\"Обработчик: задача завершена\"\"\"
        task_name = data.get(\"task_name\", \"Unknown\")
        duration = data.get(\"duration\", 0)
        self.logger.success(f\"✓ Готово: {task_name} ({duration:.2f}s)\")
    
    async def _on_task_error(self, data: dict):
        \"\"\"Обработчик: ошибка в задаче\"\"\"
        error = data.get(\"error\", \"Unknown error\")
        self.logger.error(f\"✗ Ошибка: {error}\")
    
    async def _on_task_progress(self, data: dict):
        \"\"\"Обработчик: прогресс задачи\"\"\"
        progress = data.get(\"progress\", 0)
        current = data.get(\"current_step\", 0)
        total = data.get(\"total_steps\", 0)
        
        if total > 0:
            self.logger.debug(
                f\"Прогресс: {progress*100:.0f}% ({current}/{total})\"
            )
    
    def _on_close(self):
        \"\"\"Обработчик закрытия приложения\"\"\"
        
        self.logger.info(\"Закрытие приложения...\")
        
        # Останавливаем event loop
        if hasattr(self, \"loop\") and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        # Закрываем окно
        self.destroy()
\"\"\"

# ═════════════════════════════════════════════════════════════════════════════
# КУДА КОПИРОВАТЬ
# ═════════════════════════════════════════════════════════════════════════════

INSTRUCTIONS = """
ИНСТРУКЦИЯ ПО УСТАНОВКЕ:

1. Откройте файлы ниже и скопируйте их содержимое:

   📄 MAIN_PY → sysutil/main.py
   📄 CONSTANTS_PY → sysutil/config/constants.py
   📄 EVENT_BUS_PY → sysutil/core/event_bus.py
   📄 APP_PY → sysutil/ui/app.py

2. Создайте пустые файлы __init__.py если их нет:
   touch sysutil/config/__init__.py
   touch sysutil/ui/__init__.py
   touch sysutil/ui/tabs/__init__.py
   touch sysutil/ui/widgets/__init__.py

3. Обновите requirements.txt:
   customtkinter>=5.2.2
   pillow>=10.0.0
   psutil>=5.9.0
   aiofiles>=23.0.0
   aiohttp>=3.8.0
   pywin32>=305

4. Установите зависимости:
   pip install -r requirements.txt

5. Запустите приложение:
   python main.py

6. Вы должны увидеть новое окно Kus v2 с боковой панелью!

Дальнейшие шаги:
- Переписать модули на async (как показано в COMPLETE_STEP_BY_STEP_GUIDE.md)
- Добавить вкладки из cleanup_tab_v2.py
- Интегрировать Task Handler
"""

print(INSTRUCTIONS)
"""

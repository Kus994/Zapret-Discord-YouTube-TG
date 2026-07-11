\"\"\"
core/logger.py
──────────────
Система логирования с поддержкой цветных выводов.

Используется для:
✓ Вывода сообщений в консоль с цветами
✓ Логирования в файлы
✓ Форматирования сообщений об ошибках
✓ Интеграции с UI через callbacks

Цветовая кодировка:
  ✓ Зеленый (#4CC9A4)   - успешные операции
  ⚠ Оранжевый (#F4A261) - предупреждения
  ✗ Красный (#E15554)   - ошибки
  ℹ Синий (#5AA9E6)     - информация
  ○ Серый (#8FA3BD)     - отладка
\"\"\"

import logging
import sys
from typing import Optional, Callable
from datetime import datetime
from enum import Enum
from pathlib import Path


class LogLevel(Enum):
    \"\"\"Уровни логирования\"\"\"
    DEBUG = \"DEBUG\"
    INFO = \"INFO\"
    SUCCESS = \"SUCCESS\"
    WARNING = \"WARNING\"
    ERROR = \"ERROR\"
    CRITICAL = \"CRITICAL\"


class Colors:
    \"\"\"ANSI коды для цветного вывода в консоль\"\"\"
    
    RESET = \"\\033[0m\"
    
    # Цвета текста
    BLACK = \"\\033[30m\"
    RED = \"\\033[31m\"        # Ошибки
    GREEN = \"\\033[32m\"      # Успех
    YELLOW = \"\\033[33m\"     # Предупреждения
    BLUE = \"\\033[34m\"       # Информация
    MAGENTA = \"\\033[35m\"
    CYAN = \"\\033[36m\"
    WHITE = \"\\033[37m\"
    GRAY = \"\\033[90m\"       # Отладка
    
    # Яркие цвета (для фона)
    LIGHT_RED = \"\\033[91m\"
    LIGHT_GREEN = \"\\033[92m\"
    LIGHT_YELLOW = \"\\033[93m\"
    LIGHT_BLUE = \"\\033[94m\"
    
    # Стили
    BOLD = \"\\033[1m\"
    DIM = \"\\033[2m\"
    ITALIC = \"\\033[3m\"
    UNDERLINE = \"\\033[4m\"


class ColoredFormatter(logging.Formatter):
    \"\"\"Форматтер логов с цветными выводами\"\"\"
    
    # Маппинг уровней на цвета
    COLORS = {
        \"DEBUG\": Colors.GRAY,
        \"INFO\": Colors.BLUE,
        \"SUCCESS\": Colors.GREEN,
        \"WARNING\": Colors.YELLOW,
        \"ERROR\": Colors.RED,
        \"CRITICAL\": Colors.LIGHT_RED,
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Получаем цвет для уровня логирования
        level_name = record.levelname
        color = self.COLORS.get(level_name, Colors.WHITE)
        
        # Форматируем сообщение
        timestamp = datetime.now().strftime(\"%H:%M:%S\")
        
        # Выбираем иконку
        icons = {
            \"DEBUG\": \"○\",
            \"INFO\": \"ℹ\",
            \"SUCCESS\": \"✓\",
            \"WARNING\": \"⚠\",
            \"ERROR\": \"✗\",
            \"CRITICAL\": \"‼\",
        }
        
        icon = icons.get(level_name, \"•\")
        
        # Строим финальное сообщение
        message = f\"{color}{icon}{Colors.BOLD} {level_name:8}{Colors.RESET} | {record.getMessage()}\"
        
        # Если есть исключение - добавляем трейсбэк
        if record.exc_info:
            message += f\"\\n{Colors.RED}{record.exc_text}{Colors.RESET}\"
        
        return message


class ColoredLogger:
    \"\"\"
    Логгер с поддержкой цветных выводов.
    
    Использование:
    ──────────────
    logger = ColoredLogger(\"MyApp\")
    logger.success(\"Операция выполнена!\")
    logger.warning(\"Внимание!\")
    logger.error(\"Произошла ошибка\")
    \"\"\"
    
    def __init__(
        self,
        name: str = \"Kus\",
        log_file: Optional[Path] = None,
        on_message: Optional[Callable] = None
    ):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.on_message = on_message
        
        # Очищаем старые обработчики
        self.logger.handlers.clear()
        
        # Консольный обработчик с цветами
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter())
        self.logger.addHandler(console_handler)
        
        # Файловый обработчик (если нужен)
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding=\"utf-8\")
            file_formatter = logging.Formatter(
                \"[%(asctime)s] %(levelname)8s | %(message)s\",
                datefmt=\"%Y-%m-%d %H:%M:%S\"
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # Добавляем кастомный уровень SUCCESS
        if not hasattr(logging, \"SUCCESS\"):
            logging.SUCCESS = 25
            logging.addLevelName(logging.SUCCESS, \"SUCCESS\")
    
    def debug(self, message: str, *args, **kwargs):
        \"\"\"Логирует отладочное сообщение\"\"\"
        self.logger.debug(message, *args, **kwargs)
        if self.on_message:
            self.on_message(LogLevel.DEBUG, message)
    
    def info(self, message: str, *args, **kwargs):
        \"\"\"Логирует информационное сообщение\"\"\"
        self.logger.info(message, *args, **kwargs)
        if self.on_message:
            self.on_message(LogLevel.INFO, message)
    
    def success(self, message: str, *args, **kwargs):
        \"\"\"Логирует успешное сообщение (зеленый цвет)\"\"\"
        self.logger.log(logging.SUCCESS, message, *args, **kwargs)
        if self.on_message:
            self.on_message(LogLevel.SUCCESS, message)
    
    def warning(self, message: str, *args, **kwargs):
        \"\"\"Логирует предупреждение (оранжевый цвет)\"\"\"
        self.logger.warning(message, *args, **kwargs)
        if self.on_message:
            self.on_message(LogLevel.WARNING, message)
    
    def error(self, message: str, *args, exc_info=False, **kwargs):
        \"\"\"Логирует ошибку (красный цвет)\"\"\"
        self.logger.error(message, *args, exc_info=exc_info, **kwargs)
        if self.on_message:
            self.on_message(LogLevel.ERROR, message)
    
    def critical(self, message: str, *args, **kwargs):
        \"\"\"Логирует критическую ошибку (красный цвет с восклицанием)\"\"\"
        self.logger.critical(message, *args, **kwargs)
        if self.on_message:
            self.on_message(LogLevel.CRITICAL, message)
    
    def section(self, title: str):
        \"\"\"Логирует заголовок раздела\"\"\"
        self.logger.info(f\"\\n{Colors.BOLD}{'='*60}{Colors.RESET}\")
        self.logger.info(f\"{Colors.BOLD}{title:^60}{Colors.RESET}\")
        self.logger.info(f\"{Colors.BOLD}{'='*60}{Colors.RESET}\")


# ──────────────────────────────────────────────────────────────────────────

# Пример использования
if __name__ == \"__main__\":
    
    # Создание логгера
    logger = ColoredLogger(\"Kus Demo\")
    
    # Демонстрация разных уровней
    logger.section(\"Демонстрация логирования\")
    
    logger.debug(\"Это отладочное сообщение\")
    logger.info(\"Это информационное сообщение\")
    logger.success(\"Операция выполнена успешно!\")
    logger.warning(\"Внимание: произошло кое-что странное\")
    logger.error(\"Произошла ошибка при выполнении операции\")
    logger.critical(\"Критическая ошибка! Приложение остановлено\")
    
    # Логирование с параметрами
    logger.info(f\"Обработано файлов: {1234} из {5678}\")
    logger.success(f\"Освобождено памяти: {2.4} ГБ\")
    logger.warning(f\"Пропущено файлов: {42}\")
    
    # Логирование исключений
    try:
        result = 10 / 0
    except ZeroDivisionError as e:
        logger.error(f\"Ошибка при делении: {e}\", exc_info=True)
    
    # Раздел
    logger.section(\"Анализ результатов\")
    logger.success(\"Анализ завершен успешно\")\n    logger.info(\"Всего операций: 127\")
    logger.info(\"Успешных: 124\")
    logger.info(\"С ошибками: 3\")

"""
ui/tabs/cleanup_tab_v2.py
─────────────────────────
Пример обновленной вкладки очистки с асинхронностью.

Демонстрирует:
✓ Асинхронное выполнение операции без блокировки UI
✓ Волновой прогресс-бар с анимацией
✓ Логирование с цветами (Green/Yellow/Red)
✓ Красивый финальный отчет о результатах
✓ Кнопка отмены задачи
"""

import asyncio
import customtkinter as ctk
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass
from datetime import datetime
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont

# ──────────────────────────────────────────────────────────────────────────

# Цветовая схема
class Colors:
    BG_DARK     = "#0B1220"
    BG_PANEL    = "#0F1823"
    ACCENT      = "#5AA9E6"
    ACCENT_HOVER = "#3D8FCF"
    TEXT_MAIN   = "#E7EEF7"
    TEXT_DIM    = "#8FA3BD"
    SUCCESS     = "#4CC9A4"
    WARN        = "#F4A261"
    ERROR       = "#E15554"
    LOG_BG      = "#060A12"

# ──────────────────────────────────────────────────────────────────────────

class ColoredLogBox(ctk.CTkTextbox):
    """
    Текстовое поле с поддержкой цветного логирования.
    
    Используется:
        log.log_success("Файл удален")
        log.log_warning("Папка недоступна")
        log.log_error("Ошибка доступа")
    """
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Настраиваем теги для разных уровней
        self.tag_config("success", text_color=Colors.SUCCESS)
        self.tag_config("warning", text_color=Colors.WARN)
        self.tag_config("error", text_color=Colors.ERROR)
        self.tag_config("info", text_color=Colors.TEXT_MAIN)
        self.tag_config("dim", text_color=Colors.TEXT_DIM)
    
    def log_success(self, message: str):
        """Логирует успешное сообщение (зеленый цвет)"""
        self.insert("end", f"✓ {message}\n", "success")
        self.see("end")
    
    def log_warning(self, message: str):
        """Логирует предупреждение (оранжевый цвет)"""
        self.insert("end", f"⚠ {message}\n", "warning")
        self.see("end")
    
    def log_error(self, message: str):
        """Логирует ошибку (красный цвет)"""
        self.insert("end", f"✗ {message}\n", "error")
        self.see("end")
    
    def log_info(self, message: str):
        \"\"\"Логирует информационное сообщение (белый цвет)\"\"\"
        self.insert("end", f"ℹ {message}\n", "info")
        self.see("end")
    
    def log_step(self, step_number: int, total: int, message: str):
        \"\"\"Логирует шаг процесса\"\"\"
        self.insert("end", f\"[{step_number}/{total}] \", \"dim\")
        self.insert(\"end\", f\"{message}\n\", \"info\")
        self.see(\"end\")
    
    def clear(self):
        \"\"\"Очищает логирование\"\"\"
        self.delete(\"1.0\", \"end\")


# ──────────────────────────────────────────────────────────────────────────

@dataclass
class CleanupResult:
    \"\"\"Результат операции очистки\"\"\"
    success: bool
    freed_gb: float = 0.0
    files_deleted: int = 0
    errors_count: int = 0
    skipped_count: int = 0
    duration_seconds: float = 0.0
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


# ──────────────────────────────────────────────────────────────────────────

class WaveProgressBar(ctk.CTkProgressBar):
    \"\"\"
    Улучшенный прогресс-бар с волновой анимацией.
    В реальности здесь будет Canvas с синусоидой, но для простоты
    используем стандартный CTkProgressBar с цветовым переходом.
    \"\"\"
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._progress = 0.0
    
    def set(self, value: float):
        \"\"\"Устанавливает прогресс (0..1)\"\"\"
        self._progress = max(0.0, min(1.0, value))
        super().set(self._progress)
    
    def get_animated_color(self) -> str:
        \"\"\"Возвращает цвет в зависимости от прогресса\"\"\"
        colors = [
            "#2265A8",  # 0%
            "#2E80D8",  # 25%
            \"#5AA9E6\",  # 50%
            \"#7FC4F5\",  # 75%
            \"#4CC9A4\",  # 100% (зеленый при завершении)
        ]
        index = int(self._progress * (len(colors) - 1))
        return colors[index]


# ──────────────────────────────────────────────────────────────────────────

class ResultReportFrame(ctk.CTkFrame):
    \"\"\"
    Красивый кадр для показа результатов операции.
    Показывает статус (✓/✗), длительность, и детали результата.
    \"\"\"
    
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PANEL, **kwargs)
        
        # Заголовок со статусом
        self.header_frame = ctk.CTkFrame(self, fg_color=\"transparent\")
        self.header_frame.pack(fill=\"x\", padx=20, pady=15)
        
        self.status_icon = ctk.CTkLabel(
            self.header_frame,
            text=\"✓\",
            text_color=Colors.SUCCESS,
            font=(\"Segoe UI\", 24, \"bold\")
        )
        self.status_icon.pack(side=\"left\", padx=10)
        
        self.status_text = ctk.CTkLabel(
            self.header_frame,
            text=\"Операция завершена\",
            text_color=Colors.TEXT_MAIN,
            font=(\"Segoe UI\", 18, \"bold\")
        )
        self.status_text.pack(side=\"left\", fill=\"x\", expand=True)
        
        # Линия-разделитель
        ctk.CTkLabel(self, text=\"\", fg_color=Colors.TEXT_DIM, height=1).pack(
            fill=\"x\", padx=20, pady=10
        )
        
        # Детали
        self.details_frame = ctk.CTkFrame(self, fg_color=\"transparent\")
        self.details_frame.pack(fill=\"both\", expand=True, padx=20, pady=15)
        
        self.details = {}
    
    def show_success(self, result: CleanupResult):
        \"\"\"Показать успешный результат\"\"\"
        self.status_icon.configure(text=\"✓\", text_color=Colors.SUCCESS)
        self.status_text.configure(text=\"✅ Очистка завершена\")
        
        # Очищаем старые детали
        for widget in self.details_frame.winfo_children():
            widget.destroy()
        
        # Добавляем новые детали
        details_data = [
            (\"Время выполнения\", f\"{result.duration_seconds:.2f} сек\"),
            (\"Освобождено памяти\", f\"{result.freed_gb:.2f} ГБ\"),
            (\"Удалено файлов\", f\"{result.files_deleted:,}\".replace(\",\", \" \")),
            (\"Ошибок при удалении\", f\"{result.errors_count}\"),
            (\"Пропущено\", f\"{result.skipped_count}\"),
        ]
        
        for label_text, value_text in details_data:
            row = ctk.CTkFrame(self.details_frame, fg_color=\"transparent\")
            row.pack(fill=\"x\", pady=5)
            
            label = ctk.CTkLabel(
                row,
                text=label_text + \":\",
                text_color=Colors.TEXT_DIM,
                font=(\"Segoe UI\", 13),
                justify=\"left\",
                anchor=\"w\"
            )
            label.pack(side=\"left\", fill=\"x\", expand=True)
            
            value = ctk.CTkLabel(
                row,
                text=value_text,
                text_color=Colors.SUCCESS,
                font=(\"Segoe UI\", 13, \"bold\"),
                justify=\"right\",
                anchor=\"e\"
            )
            value.pack(side=\"right\", padx=(10, 0))
    
    def show_error(self, error_message: str):
        \"\"\"Показать ошибку\"\"\"
        self.status_icon.configure(text=\"✗\", text_color=Colors.ERROR)
        self.status_text.configure(text=\"❌ Ошибка при выполнении\", text_color=Colors.ERROR)
        
        for widget in self.details_frame.winfo_children():
            widget.destroy()
        
        error_label = ctk.CTkLabel(
            self.details_frame,
            text=error_message,
            text_color=Colors.ERROR,
            font=(\"Segoe UI\", 12),
            justify=\"left\",
            wraplength=400
        )
        error_label.pack(fill=\"both\", expand=True, pady=10)


# ──────────────────────────────────────────────────────────────────────────

class CleanupTabV2(ctk.CTkFrame):
    \"\"\"
    Обновленная вкладка очистки с асинхронностью.
    
    Особенности:
    - Кнопка \"Очистить\" запускает асинхронную операцию
    - Волновой прогресс-бар показывает ход выполнения
    - Логирование в реальном времени с цветовой кодировкой
    - Красивый финальный отчет о результатах
    - Кнопка отмены задачи (если еще выполняется)
    \"\"\"
    
    def __init__(self, master, task_handler=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.task_handler = task_handler
        self.current_task_id = None
        self.is_running = False
        
        # ──── Панель управления ────
        control_frame = ctk.CTkFrame(self, fg_color=\"transparent\")
        control_frame.pack(fill=\"x\", padx=20, pady=15)
        
        # Заголовок
        title = ctk.CTkLabel(
            control_frame,
            text=\"🧹 Очистка системы\",
            text_color=Colors.TEXT_MAIN,
            font=(\"Segoe UI\", 16, \"bold\")
        )
        title.pack(anchor=\"w\")
        
        # Описание
        desc = ctk.CTkLabel(
            control_frame,
            text=\"Удалит временные файлы, кэш и другой мусор. Займет 2-5 минут.\",
            text_color=Colors.TEXT_DIM,
            font=(\"Segoe UI\", 11)
        )
        desc.pack(anchor=\"w\", pady=(5, 0))
        
        # ──── Опции очистки ────
        options_frame = ctk.CTkFrame(self, fg_color=Colors.BG_PANEL)
        options_frame.pack(fill=\"x\", padx=20, pady=10)
        
        self.check_temp = ctk.CTkCheckBox(
            options_frame,
            text=\"Очистить временные файлы (%TEMP%)\",
            text_color=Colors.TEXT_MAIN,
            checkbox_width=18,
            checkbox_height=18
        )
        self.check_temp.pack(anchor=\"w\", padx=15, pady=8)
        self.check_temp.select()
        
        self.check_cache = ctk.CTkCheckBox(
            options_frame,
            text=\"Очистить кэш обновлений Windows\",
            text_color=Colors.TEXT_MAIN,
            checkbox_width=18,
            checkbox_height=18
        )
        self.check_cache.pack(anchor=\"w\", padx=15, pady=8)
        
        self.check_trash = ctk.CTkCheckBox(
            options_frame,
            text=\"Очистить корзину\",
            text_color=Colors.TEXT_MAIN,
            checkbox_width=18,
            checkbox_height=18
        )
        self.check_trash.pack(anchor=\"w\", padx=15, pady=8)
        
        # ──── Кнопки управления ────
        button_frame = ctk.CTkFrame(self, fg_color=\"transparent\")
        button_frame.pack(fill=\"x\", padx=20, pady=15)
        
        self.btn_start = ctk.CTkButton(
            button_frame,
            text=\"Начать очистку\",
            text_color=\"white\",
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            font=(\"Segoe UI\", 12, \"bold\"),
            height=35,
            command=self._on_start_cleanup
        )
        self.btn_start.pack(side=\"left\", fill=\"x\", expand=True, padx=(0, 10))
        
        self.btn_cancel = ctk.CTkButton(
            button_frame,
            text=\"Отмена\",
            text_color=\"white\",
            fg_color=Colors.ERROR,
            hover_color=\"#C0423F\",
            font=(\"Segoe UI\", 12, \"bold\"),
            height=35,
            state=\"disabled\",
            command=self._on_cancel_cleanup
        )
        self.btn_cancel.pack(side=\"left\", padx=(0, 10))
        
        # ──── Прогресс-бар ────
        self.progress_bar = WaveProgressBar(
            self,
            progress_color=Colors.ACCENT,
            fg_color=Colors.BG_PANEL,
            height=18,
            border_width=0
        )
        self.progress_bar.pack(fill=\"x\", padx=20, pady=(15, 5))
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(
            self,
            text=\"Готово\",
            text_color=Colors.TEXT_DIM,
            font=(\"Segoe UI\", 10)
        )
        self.progress_label.pack(anchor=\"w\", padx=20, pady=(0, 15))
        
        # ──── Логирование ────
        log_label = ctk.CTkLabel(
            self,
            text=\"Журнал операций:\",
            text_color=Colors.TEXT_MAIN,
            font=(\"Segoe UI\", 11, \"bold\")
        )
        log_label.pack(anchor=\"w\", padx=20, pady=(10, 5))
        
        self.log_box = ColoredLogBox(
            self,
            fg_color=Colors.LOG_BG,
            text_color=Colors.TEXT_MAIN,
            font=(\"Consolas\", 10),
            height=150,
            state=\"normal\"
        )
        self.log_box.pack(fill=\"both\", expand=True, padx=20, pady=(5, 15))
        self.log_box.configure(state=\"disabled\")
        
        # ──── Результат (спрятан по умолчанию) ────
        self.result_frame = ResultReportFrame(self, height=200)
        # Не паковать по умолчанию
    
    async def _simulate_cleanup(self, task_id: str):
        \"\"\"
        Имитирует процесс очистки для демонстрации.
        В реальном коде здесь будет вызов cleanup.py модуля.
        \"\"\"
        
        steps = [
            (\"Сканирование %TEMP%...\", 0.15),
            (\"Удаление файлов (1/3)...\", 0.25),
            (\"Удаление файлов (2/3)...\", 0.35),
            (\"Удаление файлов (3/3)...\", 0.45),
            (\"Очистка кэша обновлений...\", 0.65),
            (\"Очистка корзины...\", 0.80),
            (\"Подсчет освобождённой памяти...\", 0.95),
            (\"Завершение...\", 1.0),
        ]
        
        for step_text, progress in steps:
            await asyncio.sleep(0.8)  # Имитация работы
            
            # Обновляем UI
            self.progress_bar.set(progress)
            self.progress_label.configure(text=f\"{progress*100:.0f}%\")
            self.log_box.configure(state=\"normal\")
            self.log_box.log_step(int(progress * 8), 8, step_text)
            self.log_box.configure(state=\"disabled\")
            self.update()
        
        # Добавляем итоговые логи
        self.log_box.configure(state=\"normal\")
        self.log_box.log_success(\"Все файлы успешно удалены!\")
        self.log_box.log_info(\"Выполнено: 8/8 операций\")
        self.log_box.configure(state=\"disabled\")
        
        return CleanupResult(
            success=True,
            freed_gb=2.4,
            files_deleted=12543,
            errors_count=0,
            skipped_count=3,
            duration_seconds=6.4
        )
    
    def _on_start_cleanup(self):
        \"\"\"Обработчик нажатия кнопки 'Начать очистку'\"\"\"
        if self.is_running:
            return
        
        self.is_running = True
        self.current_task_id = \"cleanup_\" + datetime.now().strftime(\"%Y%m%d_%H%M%S\")
        
        # Обновляем UI
        self.btn_start.configure(state=\"disabled\")
        self.btn_cancel.configure(state=\"normal\")
        self.log_box.configure(state=\"normal\")
        self.log_box.clear()
        self.log_box.log_info(\"Начинается процесс очистки...\\n\")
        self.log_box.configure(state=\"disabled\")
        self.progress_bar.set(0)
        
        # Скрываем результаты если они были
        if self.result_frame.winfo_manager():
            self.result_frame.pack_forget()
        
        # Запускаем асинхронную операцию
        asyncio.create_task(self._run_cleanup())
    
    async def _run_cleanup(self):
        \"\"\"Основной процесс очистки (асинхронный)\"\"\"
        try:
            result = await self._simulate_cleanup(self.current_task_id)
            
            # Показываем результат
            self.result_frame.pack(fill=\"x\", padx=20, pady=15)
            self.result_frame.show_success(result)
            
        except Exception as exc:
            self.result_frame.pack(fill=\"x\", padx=20, pady=15)
            self.result_frame.show_error(f\"Ошибка: {str(exc)}\")
        
        finally:
            self.is_running = False
            self.current_task_id = None
            self.btn_start.configure(state=\"normal\")
            self.btn_cancel.configure(state=\"disabled\")
    
    def _on_cancel_cleanup(self):
        \"\"\"Обработчик отмены операции\"\"\"
        self.is_running = False
        self.log_box.configure(state=\"normal\")
        self.log_box.log_error(\"Операция отменена пользователем\")
        self.log_box.configure(state=\"disabled\")
        
        self.btn_start.configure(state=\"normal\")
        self.btn_cancel.configure(state=\"disabled\")


# ──────────────────────────────────────────────────────────────────────────

# Пример запуска
if __name__ == \"__main__\":
    
    app = ctk.CTk()
    app.title(\"Kus - Cleanup Tab Demo\")
    app.geometry(\"800x600\")
    app.configure(fg_color=Colors.BG_DARK)
    
    ctk.set_appearance_mode(\"dark\")
    
    tab = CleanupTabV2(app, fg_color=Colors.BG_DARK)
    tab.pack(fill=\"both\", expand=True)
    
    app.mainloop()

"""
core/task_handler.py
────────────────────
Ядро системы управления задачами в Kus.

Основные возможности:
✓ Асинхронное выполнение операций без блокировки UI
✓ Управление жизненным циклом: инит → выполнение → завершение
✓ Система обработки ошибок с автоматическим логированием
✓ Event Bus для публикации событий в UI слой
✓ Поддержка отмены задач (CancellationToken)
✓ Метрики выполнения (время, прогресс, статус)
"""

import asyncio
import time
import threading
from typing import Callable, Coroutine, Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

# ─────────────────────────────────────────────────────────────────────────

class TaskStatus(Enum):
    """Статусы задачи"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskMetrics:
    """Метрики выполнения задачи"""
    task_id: str
    task_name: str
    status: TaskStatus = TaskStatus.IDLE
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0  # 0..1
    total_steps: int = 0
    current_step: int = 0
    error: Optional[str] = None
    result: Optional[Any] = None
    
    @property
    def duration_seconds(self) -> float:
        """Длительность выполнения в секундах"""
        if not self.started_at:
            return 0.0
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()
    
    @property
    def is_running(self) -> bool:
        return self.status == TaskStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)


@dataclass
class TaskResult:
    """Результат выполнения задачи"""
    success: bool
    task_id: str
    metrics: TaskMetrics
    data: Optional[Dict] = None
    error_message: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────

class EventBus:
    """Простая шина событий для связи между компонентами"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
    
    def subscribe(self, event_name: str, callback: Callable):
        """Подписывается на событие"""
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(callback)
    
    def unsubscribe(self, event_name: str, callback: Callable):
        """Отписывается от события"""
        with self._lock:
            if event_name in self._subscribers:
                self._subscribers[event_name].remove(callback)
    
    async def emit(self, event_name: str, data: Dict = None):
        """Эмитит событие всем подписчикам"""
        with self._lock:
            callbacks = self._subscribers.get(event_name, []).copy()
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data or {})
                else:
                    callback(data or {})
            except Exception as e:
                logging.error(f"Error in event callback {event_name}: {e}")


# ─────────────────────────────────────────────────────────────────────────

class CancellationToken:
    """Токен для отмены выполнения задачи"""
    
    def __init__(self):
        self._cancelled = False
    
    def cancel(self):
        """Отменить задачу"""
        self._cancelled = True
    
    @property
    def is_cancelled(self) -> bool:
        return self._cancelled
    
    def check(self):
        """Выбросить исключение если задача отменена"""
        if self._cancelled:
            raise asyncio.CancelledError("Task was cancelled")


# ─────────────────────────────────────────────────────────────────────────

class TaskHandler:
    """
    Оркестр асинхронных операций.
    
    Использование:
    ──────────────
    handler = TaskHandler()
    
    async def cleanup_operation():
        # твоя логика
        return {"freed_gb": 2.4, "files_deleted": 12543}
    
    result = await handler.execute_task(
        task_id="cleanup_001",
        task_name="Очистка системы",
        operation=cleanup_operation(),
        on_progress=lambda progress: print(f"{progress*100:.1f}%")
    )
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus()
        self.tasks: Dict[str, TaskMetrics] = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    async def execute_task(
        self,
        task_id: str,
        task_name: str,
        operation: Coroutine,
        total_steps: int = 0,
        on_progress: Optional[Callable[[float], None]] = None,
        on_step_complete: Optional[Callable[[int], None]] = None,
        on_complete: Optional[Callable[[TaskResult], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        timeout: Optional[float] = None,
    ) -> TaskResult:
        """
        Выполняет задачу с полным управлением жизненным циклом.
        
        Args:
            task_id: Уникальный ID задачи
            task_name: Читаемое имя задачи
            operation: Async coroutine для выполнения
            total_steps: Общее число шагов (для прогресса)
            on_progress: Callback(progress: float) вызывается по мере прогресса
            on_step_complete: Callback(current_step: int)
            on_complete: Callback(result: TaskResult)
            on_error: Callback(error_message: str)
            timeout: Таймаут в секундах
        
        Returns:
            TaskResult с статусом и метриками
        """
        
        # 1. Инициализация метрик
        metrics = TaskMetrics(
            task_id=task_id,
            task_name=task_name,
            status=TaskStatus.IDLE,
            total_steps=total_steps
        )
        
        with self._lock:
            self.tasks[task_id] = metrics
        
        try:
            # 2. Эмит события "старт задачи"
            await self.event_bus.emit("task:started", {
                "task_id": task_id,
                "task_name": task_name,
                "timestamp": datetime.now().isoformat()
            })
            
            # Обновляем статус
            metrics.status = TaskStatus.RUNNING
            metrics.started_at = datetime.now()
            
            # 3. Выполняем операцию с таймаутом
            self.logger.info(f"[TASK_START] {task_name} ({task_id})")
            
            if timeout:
                result_data = await asyncio.wait_for(operation, timeout=timeout)
            else:
                result_data = await operation
            
            # 4. Успешное завершение
            metrics.status = TaskStatus.COMPLETED
            metrics.completed_at = datetime.now()
            metrics.progress = 1.0
            metrics.result = result_data
            
            task_result = TaskResult(
                success=True,
                task_id=task_id,
                metrics=metrics,
                data=result_data
            )
            
            # 5. Эмит события "завершено"
            await self.event_bus.emit("task:completed", {
                "task_id": task_id,
                "task_name": task_name,
                "duration": metrics.duration_seconds,
                "result": result_data,
                "timestamp": datetime.now().isoformat()
            })
            
            # 6. Callback
            if on_complete:
                on_complete(task_result)
            
            self.logger.info(
                f"[TASK_DONE] {task_name} ({task_id}) "
                f"in {metrics.duration_seconds:.2f}s"
            )
            
            return task_result
        
        except asyncio.TimeoutError:
            error_msg = f"Task {task_name} exceeded timeout of {timeout}s"
            metrics.status = TaskStatus.FAILED
            metrics.error = error_msg
            metrics.completed_at = datetime.now()
            
            await self.event_bus.emit("task:error", {
                "task_id": task_id,
                "task_name": task_name,
                "error": error_msg
            })
            
            if on_error:
                on_error(error_msg)
            
            self.logger.error(f"[TASK_TIMEOUT] {error_msg}")
            
            return TaskResult(
                success=False,
                task_id=task_id,
                metrics=metrics,
                error_message=error_msg
            )
        
        except asyncio.CancelledError:
            metrics.status = TaskStatus.CANCELLED
            metrics.completed_at = datetime.now()
            
            await self.event_bus.emit("task:cancelled", {
                "task_id": task_id,
                "task_name": task_name
            })
            
            self.logger.warning(f"[TASK_CANCELLED] {task_name} ({task_id})")
            
            return TaskResult(
                success=False,
                task_id=task_id,
                metrics=metrics,
                error_message="Task was cancelled"
            )
        
        except Exception as exc:
            error_msg = f"{exc.__class__.__name__}: {str(exc)}"
            metrics.status = TaskStatus.FAILED
            metrics.error = error_msg
            metrics.completed_at = datetime.now()
            
            await self.event_bus.emit("task:error", {
                "task_id": task_id,
                "task_name": task_name,
                "error": error_msg,
                "exception_type": exc.__class__.__name__
            })
            
            if on_error:
                on_error(error_msg)
            
            self.logger.error(
                f"[TASK_ERROR] {task_name} ({task_id}): {error_msg}",
                exc_info=exc
            )
            
            return TaskResult(
                success=False,
                task_id=task_id,
                metrics=metrics,
                error_message=error_msg
            )
        
        finally:
            # Очищаем из активных задач если завершена
            if metrics.is_completed:
                with self._lock:
                    self.tasks.pop(task_id, None)
    
    def get_task_metrics(self, task_id: str) -> Optional[TaskMetrics]:
        """Получить метрики выполняющейся задачи"""
        with self._lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[TaskMetrics]:
        """Получить все активные задачи"""
        with self._lock:
            return list(self.tasks.values())
    
    async def update_progress(
        self,
        task_id: str,
        current_step: int,
        total_steps: Optional[int] = None,
        custom_progress: Optional[float] = None
    ):
        """Обновляет прогресс задачи (вызывается из операции)"""
        with self._lock:
            if task_id not in self.tasks:
                return
            
            metrics = self.tasks[task_id]
            metrics.current_step = current_step
            
            if total_steps is not None:
                metrics.total_steps = total_steps
            
            if custom_progress is not None:
                metrics.progress = max(0.0, min(1.0, custom_progress))
            elif metrics.total_steps > 0:
                metrics.progress = current_step / metrics.total_steps
            
            await self.event_bus.emit("task:progress", {
                "task_id": task_id,
                "progress": metrics.progress,
                "current_step": current_step,
                "total_steps": metrics.total_steps
            })
    
    async def cancel_task(self, task_id: str) -> bool:
        """Отменяет выполняющуюся задачу"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].status = TaskStatus.CANCELLED
                return True
        return False


# ─────────────────────────────────────────────────────────────────────────

# Пример использования
if __name__ == "__main__":
    
    async def example_cleanup_operation(handler: TaskHandler, task_id: str):
        \"\"\"Пример асинхронной операции очистки\"\"\"
        
        steps = ["Сканирование %TEMP%", "Удаление файлов", "Очистка кэша", "Завершение"]
        
        for i, step in enumerate(steps, 1):
            # Имитируем работу
            await asyncio.sleep(1)
            
            # Обновляем прогресс
            await handler.update_progress(task_id, i, len(steps))
            print(f"  → {step}...")
        
        return {
            "freed_gb": 2.4,
            "files_deleted": 12543,
            "errors": 3
        }
    
    async def main():
        handler = TaskHandler()
        
        # Подписываемся на события
        async def on_progress(data):
            print(f"Progress: {data['progress']*100:.0f}% ({data['current_step']}/{data['total_steps']})")
        
        async def on_complete(data):
            print(f"Completed: {data['task_id']}")
        
        handler.event_bus.subscribe("task:progress", on_progress)
        handler.event_bus.subscribe("task:completed", on_complete)
        
        # Выполняем задачу
        result = await handler.execute_task(
            task_id="cleanup_001",
            task_name="Очистка системы",
            operation=example_cleanup_operation(handler, "cleanup_001"),
            on_progress=lambda p: print(f"Прогресс: {p*100:.0f}%"),
            on_complete=lambda r: print(f"Результат: {r.data}")
        )
        
        print(f"\nИтоговый результат:")
        print(f"  Статус: {result.metrics.status.value}")
        print(f"  Длительность: {result.metrics.duration_seconds:.2f}s")
        print(f"  Данные: {result.data}")
    
    # Запуск
    asyncio.run(main())

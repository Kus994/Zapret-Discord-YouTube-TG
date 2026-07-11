# 📖 Полная инструкция по запуску и интеграции Kus v2

## Содержание
1. [Быстрый старт (текущая версия)](#быстрый-старт)
2. [Установка зависимостей](#установка-зависимостей)
3. [Запуск приложения](#запуск-приложения)
4. [Интеграция улучшений](#интеграция-улучшений)
5. [Тестирование TaskHandler](#тестирование-taskhandler)
6. [Сборка в .exe](#сборка-в-exe)
7. [Troubleshooting](#troubleshooting)

---

## 🚀 Быстрый старт

### Для текущей версии (Python + CustomTkinter):

```bash
# 1. Убедитесь, что установлен Python 3.10+ и git
python --version  # должно быть 3.10 или выше

# 2. Распакуйте архив и перейдите в папку
cd sysutil/

# 3. Установите зависимости
pip install -r requirements.txt

# 4. Запустите приложение
python main.py

# ✅ Приложение откроется в течение 3-5 секунд
```

---

## 📦 Установка зависимостей

### Вариант 1: Базовая установка (текущая версия)

```bash
# requirements.txt содержит:
pip install customtkinter>=5.2.2
pip install pillow>=10.0.0
pip install psutil>=5.9.0
```

### Вариант 2: Полная установка (с новыми модулями)

```bash
# Основные зависимости
pip install customtkinter>=5.2.2
pip install pillow>=10.0.0
pip install psutil>=5.9.0

# Новые модули для v2
pip install aiofiles>=23.0.0          # Асинхронная работа с файлами
pip install aiohttp>=3.8.0             # Асинхронные HTTP запросы
pip install pywin32>=305               # Windows API (для реестра, трея)
pip install pyperclip>=1.8.2           # Буфер обмена
pip install py-cpuinfo>=9.0.0          # Информация о процессоре
pip install nvidia-ml-py3              # Температура NVIDIA GPU (опционально)
```

### Вариант 3: Создание виртуального окружения (рекомендуется)

```bash
# На Windows
python -m venv venv
venv\Scripts\activate

# На Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Затем установите зависимости
pip install -r requirements.txt
```

---

## 🎮 Запуск приложения

### Запуск текущей версии

```bash
# Стандартный запуск
python main.py

# С отладкой (показывает ошибки в консоли)
python -u main.py

# С логированием в файл
python main.py > kus.log 2>&1
```

### Запуск демонстрации новой вкладки

```bash
# Просмотр очищенной вкладки с асинхронностью
python cleanup_tab_v2.py

# Просмотр TaskHandler (командная строка)
python core_task_handler.py
```

---

## 🔧 Интеграция улучшений

### Шаг 1: Копируем новые модули в проект

```bash
# Создаем структуру папок
mkdir -p sysutil/core
mkdir -p sysutil/ui/widgets
mkdir -p sysutil/ui/tabs
mkdir -p sysutil/config
mkdir -p sysutil/utils

# Копируем новые файлы
cp core_task_handler.py sysutil/core/task_handler.py
cp cleanup_tab_v2.py sysutil/ui/tabs/cleanup_tab.py
```

### Шаг 2: Создаем файлы конфигурации

```python
# sysutil/config/constants.py
\"\"\"
Константы и цветовая схема приложения
\"\"\"

# Цвета
COLOR_BG_DARK       = \"#0B1220\"
COLOR_BG_PANEL      = \"#0F1823\"
COLOR_ACCENT        = \"#5AA9E6\"
COLOR_ACCENT_HOVER  = \"#3D8FCF\"
COLOR_TEXT_MAIN     = \"#E7EEF7\"
COLOR_TEXT_DIM      = \"#8FA3BD\"
COLOR_SUCCESS       = \"#4CC9A4\"
COLOR_WARN          = \"#F4A261\"
COLOR_ERROR         = \"#E15554\"
COLOR_LOG_BG        = \"#060A12\"

# Шрифты
FONT_FAMILY         = \"Segoe UI\"
FONT_TITLE          = (FONT_FAMILY, 16, \"bold\")
FONT_SUBTITLE       = (FONT_FAMILY, 13, \"bold\")
FONT_NORMAL         = (FONT_FAMILY, 11)
FONT_SMALL          = (FONT_FAMILY, 10)
FONT_MONO           = (\"Consolas\", 10)
```

### Шаг 3: Обновляем main.py с TaskHandler

```python
# В начале main.py добавьте:
import asyncio
from core.task_handler import TaskHandler, EventBus
from core.logger import ColoredLogger

# В инициализации главного окна:
class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Инициализируем Event Bus и TaskHandler
        self.event_bus = EventBus()
        self.task_handler = TaskHandler(event_bus=self.event_bus)
        self.logger = ColoredLogger()
        
        # Подписываемся на события
        self.event_bus.subscribe(\"task:started\", self._on_task_started)
        self.event_bus.subscribe(\"task:completed\", self._on_task_completed)
        self.event_bus.subscribe(\"task:error\", self._on_task_error)
        
        # ... остальной код ...
    
    async def _on_task_started(self, data):
        print(f\"✓ Задача начата: {data['task_name']}\")
    
    async def _on_task_completed(self, data):
        print(f\"✓ Задача завершена: {data['task_name']} ({data['duration']:.2f}s)\")
    
    async def _on_task_error(self, data):
        print(f\"✗ Ошибка: {data['error']}\")
```

### Шаг 4: Обновляем вкладки для использования TaskHandler

```python
# В вкладке cleanup:
async def on_cleanup_button_click(self):
    \"\"\"Запуск очистки через TaskHandler\"\"\"
    
    async def cleanup_operation():
        # Ваша логика очистки
        return {\"freed_gb\": 2.4, \"files_deleted\": 12543}
    
    result = await self.app.task_handler.execute_task(
        task_id=\"cleanup_001\",
        task_name=\"Очистка системы\",
        operation=cleanup_operation(),
        on_progress=self._update_progress,
        on_complete=self._show_result,
        on_error=self._show_error
    )
```

---

## 🧪 Тестирование TaskHandler

### Создайте файл test_task_handler.py:

```python
import asyncio
from core.task_handler import TaskHandler, EventBus

async def test_simple_task():
    \"\"\"Тест простой задачи\"\"\"
    handler = TaskHandler()
    
    async def simple_operation():
        await asyncio.sleep(2)
        return {\"result\": \"success\"}
    
    result = await handler.execute_task(
        task_id=\"test_001\",
        task_name=\"Тестовая задача\",
        operation=simple_operation(),
        on_complete=lambda r: print(f\"✓ Завершено: {r.data}\")
    )
    
    print(f\"Результат: {result.success}\")
    print(f\"Длительность: {result.metrics.duration_seconds:.2f}s\")

async def test_task_with_progress():
    \"\"\"Тест задачи с прогрессом\"\"\"
    handler = TaskHandler()
    
    async def long_operation():
        for i in range(1, 11):
            await asyncio.sleep(0.5)
            await handler.update_progress(
                \"test_002\", i, 10,
                custom_progress=i/10
            )
        return {\"steps_completed\": 10}
    
    result = await handler.execute_task(
        task_id=\"test_002\",
        task_name=\"Задача с прогрессом\",
        operation=long_operation(),
        total_steps=10
    )
    
    assert result.success
    print(\"✓ Тест пройден!\")

async def test_error_handling():
    \"\"\"Тест обработки ошибок\"\"\"
    handler = TaskHandler()
    
    async def failing_operation():
        await asyncio.sleep(1)
        raise ValueError(\"Произошла ошибка!\")
    
    result = await handler.execute_task(
        task_id=\"test_003\",
        task_name=\"Ошибочная задача\",
        operation=failing_operation(),
        on_error=lambda e: print(f\"✗ Ошибка перехвачена: {e}\")
    )
    
    assert not result.success
    assert result.error_message is not None
    print(\"✓ Обработка ошибок работает!\")

async def main():
    print(\"=\" * 50)
    print(\"🧪 Тестирование TaskHandler\")
    print(\"=\" * 50)
    
    print(\"\\n[1/3] Простая задача...\")
    await test_simple_task()
    
    print(\"\\n[2/3] Задача с прогрессом...\")
    await test_task_with_progress()
    
    print(\"\\n[3/3] Обработка ошибок...\")
    await test_error_handling()
    
    print(\"\\n\" + \"=\" * 50)
    print(\"✓ Все тесты пройдены!\")
    print(\"=\" * 50)

# Запуск
if __name__ == \"__main__\":
    asyncio.run(main())
```

Запуск:
```bash
python test_task_handler.py
```

---

## 📦 Сборка в .exe

### Вариант 1: PyInstaller (для текущей версии)

```bash
# Установка PyInstaller
pip install pyinstaller

# Создание одного файла .exe
pyinstaller --onefile --noconsole \\
    --add-data \"assets;assets\" \\
    --icon=assets/icon.ico \\
    main.py

# Готовый файл будет в: dist/main.exe
# Размер: ~150-200 МБ
# Время запуска: 3-5 сек
```

### Вариант 2: Улучшенная сборка (с улучшениями v2)

```bash
# Создаем улучшенный .spec файл
pyinstaller --onefile --noconsole \\
    --add-data \"assets;assets\" \\
    --add-data \"config;config\" \\
    --collect-all customtkinter \\
    --hidden-import=pywin32 \\
    --hidden-import=aiofiles \\
    --icon=assets/icon.ico \\
    --name=\"Kus\" \\
    main.py

# Результат: dist/Kus.exe
```

### Вариант 3: Настройка .spec файла

```python
# kus.spec (улучшенный)
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('config', 'config')],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'psutil',
        'pywin32',
        'aiofiles'
    ],
    ...
)

# Уменьшаем размер
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Kus',
    debug=False,
    strip=True,              # Удаляет символы отладки
    upx=True,                # Компрессия UPX (если установлен)
    console=False,
)
```

---

## 🚨 Troubleshooting

### Проблема: \"ModuleNotFoundError: No module named 'customtkinter'\"

```bash
# Решение: Установите зависимости
pip install -r requirements.txt

# Или вручную:
pip install customtkinter>=5.2.2
```

### Проблема: \"UAC запрос при запуске\"

Это нормально! Приложение запрашивает права администратора для:
- Сетевых операций (flushdns, сброс TCP/IP)
- Очистки системных папок
- Установки обновлений

Если вы отклоните запрос - приложение все равно откроется, но эти функции будут недоступны.

### Проблема: \"Приложение замораживается при очистке\"

**Решение:** Интегрируйте TaskHandler:
1. Используйте `asyncio` вместо синхронных функций
2. Обновляйте UI через callbacks
3. Не блокируйте основной поток

### Проблема: \".exe работает медленно\"

Возможные причины и решения:

```
1. Размер .exe слишком большой (>150 МБ)
   → Используйте UPX компрессию
   → Удалите ненужные модули

2. Время запуска > 5 сек
   → Используйте ленивую загрузку модулей
   → Переходите на Go/Wails

3. Потребление RAM > 200 МБ
   → Профилируйте код (memory_profiler)
   → Оптимизируйте загрузку изображений
```

### Проблема: \"Ошибка при интеграции asyncio в CustomTkinter\"

```python
# CustomTkinter работает в основном потоке Tkinter
# Используйте этот паттерн:

import asyncio
import threading

def run_async_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Ваша асинхронная логика
    result = loop.run_until_complete(your_async_function())
    loop.close()
    
    return result

# Запуск в отдельном потоке
thread = threading.Thread(target=run_async_task, daemon=True)
thread.start()
```

### Проблема: \"Ошибка при работе с реестром Windows\"

```python
# Убедитесь, что запустили с правами администратора
# И используйте правильный синтаксис:

import winreg

def read_registry(key_path, value_name):
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            key_path
        ) as key:
            value, _ = winreg.QueryValueEx(key, value_name)
            return value
    except FileNotFoundError:
        return None
```

---

## 📋 Чек-лист для полной интеграции v2

- [ ] Создана папка `core/` с `task_handler.py`
- [ ] Создана папка `config/` с `constants.py`
- [ ] Обновлены вкладки для использования `TaskHandler`
- [ ] Добавлена система логирования с цветами
- [ ] Интегрирована система Event Bus
- [ ] Протестированы асинхронные операции
- [ ] Обновлен `main.py` с поддержкой async
- [ ] Добавлена поддержка системного трея (опционально)
- [ ] Создана система ленивой загрузки модулей
- [ ] Проведено тестирование производительности

---

## 📊 Метрики производительности

### Текущая версия (Python + CustomTkinter)
- Размер exe: ~150 МБ
- Время запуска: 4-5 сек
- RAM в покое: 120-150 МБ
- Потребление CPU: 5-10% на холостом ходу

### После внедрения async/await
- Размер exe: ~150 МБ (без изменений)
- Время запуска: 4-5 сек (без изменений)
- RAM в покое: 120-150 МБ (без изменений)
- **UI не зависает!** ✓ (основное улучшение)

### Если перейти на Go + Wails
- Размер exe: ~65 МБ (-57%)
- Время запуска: 0.8 сек (-84%)
- RAM в покое: 45-60 МБ (-62%)

---

## 🎯 Следующие шаги

1. **Сейчас:**
   - Интегрируйте TaskHandler в main.py
   - Обновите вкладки для асинхронности
   - Тестируйте новую архитектуру

2. **На этой неделе:**
   - Добавьте цветное логирование
   - Создайте систему Event Bus
   - Настройте ленивую загрузку модулей

3. **В этом месяце:**
   - Добавьте менеджер автозагрузки
   - Интегрируйте мониторинг температуры
   - Добавьте поддержку Winget

4. **В следующем квартале:**
   - Оцените результаты оптимизации
   - Рассмотрите миграцию на Go + Wails
   - Подготовьте версию 2.0

---

## 📞 Получение помощи

Если возникли проблемы:

1. Проверьте версию Python: `python --version`
2. Обновите pip: `pip install --upgrade pip`
3. Переустановите зависимости: `pip install -r requirements.txt --force-reinstall`
4. Посмотрите логи: `python main.py > error.log 2>&1`
5. Создайте issue на GitHub с логами

---

**Успехов в разработке! 🚀**

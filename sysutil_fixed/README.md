# SysUtil — утилита системного администратора

Модульная GUI-утилита для Windows на Python + CustomTkinter.

## Установка

1. Установите Python 3.10+ (с галочкой "Add to PATH").
2. В папке проекта выполните:
   ```
   pip install -r requirements.txt
   ```

## Запуск

```
python main.py
```

При старте появится стандартный запрос Windows (UAC) на права
администратора — это нужно для сетевых операций (сброс TCP/IP),
очистки кэша обновлений и установки обновлений Windows/драйверов.
Если отклонить запрос, утилита всё равно откроется, но часть функций
вернёт ошибку «Отказано в доступе».

## Структура проекта

```
sysutil/
├── main.py              # GUI и точка входа
├── requirements.txt
├── assets/
│   └── background.jpg   # фон интерфейса
└── modules/
    ├── cleanup.py        # очистка системы
    ├── network.py         # netstat / flushdns / сброс TCP-IP
    ├── processes.py       # список процессов и kill
    ├── updates.py          # Windows Update / драйверы / Планировщик задач
    ├── monitor.py           # CPU / RAM / диски в реальном времени
    └── elevation.py        # запрос прав администратора (UAC)
```

## Сборка в один .exe (опционально)

```
pip install pyinstaller
pyinstaller --onefile --noconsole --add-data "assets;assets" main.py
```

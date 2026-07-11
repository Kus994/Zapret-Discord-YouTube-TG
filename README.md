# KUS Pro

Универсальная системная утилита для Windows.

## Возможности

- **Очистка системы** — удаление мусора, временных файлов
- **Мониторинг** — CPU, RAM, диск, сеть в реальном времени
- **Безопасность** — аудит автозагрузки, проверка системы
- **Zapret** — обход DPI блокировок (Discord, YouTube, Telegram)
- **Telegram Proxy** — MTProto прокси
- **Game Mode** — оптимизация для игр
- **Экспорт данных** — выгрузка отчётов

## Быстрая установка

1. Скачайте [последний релиз](https://github.com/Kus993/Zapret Discord YouTube TG/releases/latest)
2. Распакуйте в папку без кириллицы (например `C:\KUS Pro`)
3. Запустите `run.bat` от имени администратора

Подробнее: [INSTALL.md](INSTALL.md)

## Требования

- Windows 10/11 (64-bit)
- Python 3.8+
- Права администратора (для Zapret)

## Запуск

```bash
# Автоматический запуск (рекомендуется)
run.bat

# Или вручную
pip install PyQt5
python main.py
```

## Сборка .exe

```bash
pip install pyinstaller
build.bat
```

## Структура

```
├── main.py           # Точка входа
├── page_*.py         # Страницы UI
├── modules/          # Бизнес-логика
├── zapret/           # DPI bypass
├── tg_proxy/         # Telegram Proxy
└── config.json       # Настройки
```

## Поддержка

- [DonationAlerts](https://www.donationalerts.com/r/kus_777) — донаты
- [GitHub Issues](https://github.com/Kus993/Zapret Discord YouTube TG/issues) — баг-репорты

## Лицензия

MIT License

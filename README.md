# KUS Pro

[![GitHub Stars](https://img.shields.io/github/stars/Kus994/Zapret-Discord-YouTube-TG?style=flat&logo=github)](https://github.com/Kus994/Zapret-Discord-YouTube-TG/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/Kus994/Zapret-Discord-YouTube-TG?style=flat&logo=github)](https://github.com/Kus994/Zapret-Discord-YouTube-TG/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/Kus994/Zapret-Discord-YouTube-TG?style=flat&logo=github)](https://github.com/Kus994/Zapret-Discord-YouTube-TG/issues)
[![License](https://img.shields.io/github/license/Kus994/Zapret-Discord-YouTube-TG?style=flat)](https://github.com/Kus994/Zapret-Discord-YouTube-TG/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D4?style=flat&logo=windows&logoColor=white)](https://www.microsoft.com/)

Универсальная системная утилита для Windows.

## Возможности

- **Очистка системы** -- удаление мусора, временных файлов, кэша браузеров
- **Мониторинг** -- CPU, RAM, диск, сеть в реальном времени
- **Безопасность** -- аудит автозагрузки, проверка системы
- **Оптимизация** -- настройка производительности, энергосбережения
- **Игровой режим** -- оптимизация для игр, закрытие фоновых процессов
- **Telegram Proxy** -- локальный MTProto прокси для подключения
- **Хронометраж** -- отслеживание времени за приложениями
- **Экспорт данных** -- выгрузка отчётов и статистики

## Быстрая установка

1. Скачайте [последний релиз](https://github.com/Kus994/Zapret-Discord-YouTube-TG/releases/latest)
2. Распакуйте в папку без кириллицы (например `C:\KUS Pro`)
3. Запустите `run.bat` от имени администратора

Подробнее: [INSTALL.md](INSTALL.md)

## Требования

- Windows 10/11 (64-bit)
- Python 3.10+
- Права администратора (для некоторых функций)

## Запуск

```bash
# Автоматический запуск (рекомендуется)
run.bat

# Или вручную
pip install PyQt5 psutil certifi
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
├── widgets.py        # Кастомные виджеты
├── theme.py          # Тема и стили
├── config.json       # Настройки
└── requirements.txt  # Зависимости
```

## Лицензия

MIT License -- см. [LICENSE](LICENSE)

## Поддержка

- [DonationAlerts](https://www.donationalerts.com/r/kus_777) -- донаты
- [GitHub Issues](https://github.com/Kus994/Zapret-Discord-YouTube-TG/issues) -- баг-репорты

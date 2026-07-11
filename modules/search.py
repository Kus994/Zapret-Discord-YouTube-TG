"""
modules/search.py
-----------------
Глобальный поиск по KUS Pro.
Поиск по страницам, настройкам и функциям.
"""

# Реестр всех страниц и их функций
SEARCH_REGISTRY = {
    "Очистка": {
        "module": "page_cleanup",
        "class": "CleanupPage",
        "keywords": ["очистка", "temp", "мусор", "кэш", "браузер", "дубли", "корзина", "prefetch"],
        "actions": [
            ("Очистка Temp", "Очистить временные файлы"),
            ("Кэш браузеров", "Очистить кэш Chromium/Firefox"),
            ("Дубликаты", "Найти дублирующиеся файлы"),
            ("Корзина", "Очистить корзину Windows"),
        ],
    },
    "Сеть": {
        "module": "page_network",
        "class": "NetworkPage",
        "keywords": ["сеть", "dns", "ip", "speed", "скорость", "соединения", "tcp", "udp", "тест"],
        "actions": [
            ("Сброс DNS", "Сброс кэша DNS"),
            ("Тест скорости", "Замерить скорость интернета"),
            ("DNS серверы", "Настроить DNS"),
            ("Сброс TCP/IP", "Сбросить сетевой стек"),
        ],
    },
    "Процессы": {
        "module": "page_processes",
        "class": "ProcessesPage",
        "keywords": ["процессы", "память", "cpu", "убить", "завершить", "диспетчер"],
        "actions": [
            ("Список процессов", "Показать все процессы"),
            ("Завершить процесс", "Принудительно завершить"),
        ],
    },
    "Мониторинг": {
        "module": "page_monitor",
        "class": "MonitorPage",
        "keywords": ["мониторинг", "cpu", "ram", "диски", "температура", "вентилятор", "нагрузка"],
        "actions": [
            ("CPU/RAM", "Загрузка процессора и памяти"),
            ("Диски", "Использование дисков"),
            ("Датчики", "Температуры и вентиляторы"),
        ],
    },
    "Батарея": {
        "module": "page_battery",
        "class": "BatteryPage",
        "keywords": ["батарея", "заряд", "аккумулятор", "ноутбук", "power"],
        "actions": [
            ("Заряд", "Уровень заряда батареи"),
            ("Мощность", "Потребление энергии"),
        ],
    },
    "Службы": {
        "module": "page_services",
        "class": "ServicesPage",
        "keywords": ["службы", "windows", "serv", "автозапуск", "служба"],
        "actions": [
            ("Список служб", "Показать все службы"),
            ("Запустить службу", "Запустить выбранную службу"),
            ("Остановить службу", "Остановить выбранную службу"),
        ],
    },
    "Хронометраж": {
        "module": "page_timetrack",
        "class": "TimeTrackPage",
        "keywords": ["время", "хронометраж", "отслеживание", "таблица", "категории"],
        "actions": [
            ("Включить отслеживание", "Начать отслеживание активного окна"),
            ("Добавить запись", "Добавить ручную запись"),
        ],
    },
    "Игровой режим": {
        "module": "page_game_mode",
        "class": "GameModePage",
        "keywords": ["игры", "game", "режим", "производительность", "оптимизация"],
        "actions": [
            ("Активировать", "Включить игровой режим"),
            ("Деактивировать", "Выключить игровой режим"),
        ],
    },
    "Безопасность": {
        "module": "page_security",
        "class": "SecurityPage",
        "keywords": ["безопасность", "автозагрузка", "вирус", ".registry"],
        "actions": [
            ("Сканировать", "Проверить автозагрузку"),
        ],
    },
    "Обновления": {
        "module": "page_updates",
        "class": "UpdatesPage",
        "keywords": ["обновления", "update", "windows", "драйвера"],
        "actions": [
            ("Проверить обновления", "Найти доступные обновления"),
            ("Обновления драйверов", "Найти обновления драйверов"),
        ],
    },
    "Zapret": {
        "module": "page_zapret",
        "class": "ZapretPage",
        "keywords": ["zapret", "запрет", "обход", "блокировка", "dpi"],
        "actions": [
            ("Запустить Zapret", "Запустить обход блокировок"),
            ("Диагностика", "Проверить работоспособность"),
        ],
    },
    "Telegram Proxy": {
        "module": "page_tg_proxy",
        "class": "TgProxyPage",
        "keywords": ["telegram", "tg", "proxy", "прокси", "mtproto"],
        "actions": [
            ("Запустить прокси", "Запустить MTProto прокси"),
            ("Настройка", "Настроить подключение"),
        ],
    },
    "Экспорт": {
        "module": "page_export",
        "class": "ExportPage",
        "keywords": ["экспорт", "export", "csv", "json", "html", "сохранить"],
        "actions": [
            ("Экспорт процессов", "Сохранить список процессов"),
            ("Экспорт настроек", "Сохранить настройки"),
        ],
    },
    "История": {
        "module": "page_action_log",
        "class": "ActionLogPage",
        "keywords": ["история", "лог", "журнал", "действия", "события"],
        "actions": [
            ("Просмотр истории", "Показать все действия"),
        ],
    },
    "Настройки": {
        "module": "page_settings",
        "class": "SettingsPage",
        "keywords": ["настройки", "settings", "конфигурация", "порт", "автозапуск"],
        "actions": [
            ("Настройки", "Открыть настройки"),
        ],
    },
}


def search(query: str) -> list:
    """
    Ищет по запросу в реестре страниц.
    Возвращает список результатов: [{"page": str, "action": str, "description": str}, ...]
    """
    if not query or len(query) < 2:
        return []

    query_lower = query.lower()
    results = []

    for page_name, page_info in SEARCH_REGISTRY.items():
        # Проверяем ключевые слова
        for keyword in page_info.get("keywords", []):
            if query_lower in keyword.lower():
                # Добавляем все действия этой страницы
                for action_name, action_desc in page_info.get("actions", []):
                    results.append({
                        "page": page_name,
                        "module": page_info["module"],
                        "action": action_name,
                        "description": action_desc,
                    })
                break

        # Проверяем названия действий
        for action_name, action_desc in page_info.get("actions", []):
            if query_lower in action_name.lower() or query_lower in action_desc.lower():
                results.append({
                    "page": page_name,
                    "module": page_info["module"],
                    "action": action_name,
                    "description": action_desc,
                })

    # Убираем дубликаты
    seen = set()
    unique_results = []
    for r in results:
        key = (r["page"], r["action"])
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    return unique_results

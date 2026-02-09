"""Вспомогательные утилиты для работы со временем и размерами файлов."""

import re
from datetime import datetime, timedelta

# Паттерн для распознавания даты/времени в логах: "2026-02-09 09:23:04,623"
LOG_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}")


def parse_relative_time(time_str: str, base_date: datetime) -> datetime:
    """
    Парсит относительное время (например, "10 min ago", "9 hours").
    
    Parameters
    ----------
    time_str : str
        Строка с относительным временем.
    base_date : datetime
        Базовая дата для расчета относительного времени.
    
    Returns
    -------
    datetime
        Рассчитанное абсолютное время.
    
    Raises
    ------
    ValueError
        Если формат относительного времени не распознан.
    
    Examples
    --------
    >>> base = datetime(2026, 2, 9, 10, 0, 0)
    >>> parse_relative_time("10 min ago", base)
    datetime.datetime(2026, 2, 9, 9, 50, 0)
    >>> parse_relative_time("9 hours", base)
    datetime.datetime(2026, 2, 9, 9, 0, 0)
    """
    time_str = time_str.strip().lower()
    
    # Обработка "X hours" -> установка времени на X:00:00 текущего дня
    hours_match = re.match(r"(\d+)\s*hours?", time_str)
    if hours_match:
        hour = int(hours_match.group(1))
        return base_date.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    # Обработка "X min ago" -> вычитание минут из текущего времени
    min_ago_match = re.match(r"(\d+)\s*min(?:ute)?s?\s+ago", time_str)
    if min_ago_match:
        minutes = int(min_ago_match.group(1))
        return base_date - timedelta(minutes=minutes)
    
    # Обработка "X hours ago" -> вычитание часов из текущего времени
    hours_ago_match = re.match(r"(\d+)\s*hour?s?\s+ago", time_str)
    if hours_ago_match:
        hours = int(hours_ago_match.group(1))
        return base_date - timedelta(hours=hours)
    
    raise ValueError(
        f"Не удалось распознать относительное время: '{time_str}'. "
        f"Поддерживаются форматы: 'X hours', 'X min ago', 'X hours ago'"
    )


# def parse_datetime_arg(arg_value: str, arg_name: str) -> datetime:
#     """
#     Парсит аргумент времени из CLI в объект datetime.
    
#     Parameters
#     ----------
#     arg_value : str
#         Значение аргумента из командной строки.
#     arg_name : str
#         Имя аргумента для сообщений об ошибках.
    
#     Returns
#     -------
#     datetime
#         Распарсенное время.
    
#     Raises
#     ------
#     ValueError
#         Если формат времени некорректен.
#     """
#     # Попытка распознать абсолютное время в формате %H:%M:%S
#     try:
#         time_obj = datetime.strptime(arg_value, "%H:%M:%S")
#         # Возвращаем время без привязки к дате (будет объединено с датой позже)
#         return time_obj
#     except ValueError:
#         pass
    
#     # Попытка распознать относительное время
#     try:
#         # Используем текущее время как базу для относительных вычислений
#         now = datetime.now()
#         return parse_relative_time(arg_value, now)
#     except ValueError:
#         pass
    
#     raise ValueError(
#         f"Некорректный формат времени для аргумента '{arg_name}': '{arg_value}'. "
#         f"Ожидается формат %H:%M:%S, 'X hours' или 'X min ago или 'X hours ago'"
#     )


def is_log_line_start(line: str) -> bool:
    """
    Проверяет, начинается ли строка с временной метки лога.
    
    Parameters
    ----------
    line : str
        Строка для проверки.
    
    Returns
    -------
    bool
        True, если строка начинается с временной метки лога.
    """
    return bool(LOG_TIMESTAMP_PATTERN.match(line))


def mb_to_bytes(mb: float) -> int:
    """
    Конвертирует мегабайты в байты.
    
    Parameters
    ----------
    mb : float
        Размер в мегабайтах.
    
    Returns
    -------
    int
        Размер в байтах.
    """
    return int(mb * 1024 * 1024)


def extract_instance_id(filename: str) -> int | None:
    """
    Извлекает ID экземпляра из имени файла лога.
    
    Parameters
    ----------
    filename : str
        Имя файла, например "instance 100_error.log".
    
    Returns
    -------
    Optional[int]
        ID экземпляра или None, если не найден.
    
    Examples
    --------
    >>> extract_instance_id("instance 100.log")
    100
    >>> extract_instance_id("instance 100_error.log")
    100
    """
    match = re.search(r"instance\s+(\d+)", filename, re.IGNORECASE)
    return int(match.group(1)) if match else None
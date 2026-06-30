"""Вспомогательные утилиты для работы со временем и размерами файлов."""

import re
from datetime import datetime, timedelta, time, date
from pathlib import Path

# Паттерн для распознавания даты/времени в логах: "2026-02-09 09:23:04,623"
# LOG_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}")


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
    
    
def parse_time_string(time_str: str, base_date: date | None = None, now: datetime | None = None) -> tuple[time | datetime, bool]:
    """
    Парсит временной спецификатор и определяет его тип.
    
    Возвращает кортеж (значение, является_относительным):
    - Для абсолютного времени: (datetime.time, False)
    - Для относительного времени: (datetime.datetime, True)
    
    Parameters
    ----------
    time_str : str
        Строка со временем или относительным выражением.
    base_date : date | None
        Базовая дата для комбинации с абсолютным временем.
    now : datetime | None
        Текущий момент для вычисления относительного времени. Если None — используется datetime.now().
    
    Returns
    -------
    Tuple[Union[time, datetime], bool]
        (значение, флаг_относительности)
    
    Examples
    --------
    >>> parse_time_specifier("09:00", base_date=date(2026, 2, 13))
    (datetime.time(9, 0), False)
    
    >>> parse_time_specifier("10 min ago", now=datetime(2026, 2, 14, 10, 0, 0))
    (datetime.datetime(2026, 2, 14, 9, 50), True)
    """
    time_str = time_str.strip()
    now = now or datetime.now()
    
    # 1. Абсолютное время: "9", "9:00", "09:00:00"
    try:
        if ":" not in time_str:
            # Только часы
            hour = int(time_str)
            return time(hour=hour, minute=0, second=0), False
        elif time_str.count(":") == 1:
            # Часы:минуты
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            return time(hour=hour, minute=minute, second=0), False
        else:
            # Часы:минуты:секунды
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            second = int(parts[2])
            return time(hour=hour, minute=minute, second=second), False
    except (ValueError, IndexError, AttributeError):
        pass  # Продолжаем попытки парсинга
    
    # 2. Относительное время
    try:
        # ref = reference_date or datetime.now()
        relative_dt = parse_relative_time(time_str, now)
        return relative_dt, True
    except ValueError:
        pass
    
    raise ValueError(
        f"Некорректный формат времени: '{time_str}'. "
        f"Поддерживаются: ЧЧ[:ММ[:СС]], 'X min ago', 'X hours'"
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


# def is_log_line_start(line: str) -> bool:
#     """
#     Проверяет, начинается ли строка с временной метки лога.
    
#     Parameters
#     ----------
#     line : str
#         Строка для проверки.
    
#     Returns
#     -------
#     bool
#         True, если строка начинается с временной метки лога.
#     """
#     return bool(LOG_TIMESTAMP_PATTERN.match(line))


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
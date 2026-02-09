"""CLI интерфейс утилиты для сбора логов."""

import argparse
import sys
from datetime import datetime, time
from pathlib import Path

from collector_logs.log_collector.utils import (
    mb_to_bytes,
    parse_relative_time,
)


class CLIArguments:
    """
    Обрабатывает и валидирует аргументы командной строки.
    
    Обеспечивает строгую валидацию параметров в соответствии с требованиями:
    - Обязательно должен быть указан либо --datetime, либо --date (с необязательным --time)
    - Уровень логов должен быть корректным
    """
    
    LEVEL_ALIASES = {
        "A": "all",
        "WE": "warning",
        "ER": "error",
        "all": "all",
        "warning": "warning",
        "error": "error",
    }
    
    def __init__(self, args: argparse.Namespace) -> None:
        """
        Инициализирует обработку аргументов.
        
        Parameters
        ----------
        args : argparse.Namespace
            Распарсенные аргументы argparse.
        
        Raises
        ------
        ValueError
            При некорректной комбинации параметров.
        """
        self._validate_datetime_args(args)
        self.start_time = self._determine_start_time(args)
        self.level = self._normalize_level(args.level)
        self.input_dir = Path(args.input) if args.input else Path.cwd()
        self.output_path = Path(args.output) if args.output else Path("collected_logs.txt")
        self.max_file_size = mb_to_bytes(args.mlength) if args.mlength else None
    
    def _validate_datetime_args(self, args: argparse.Namespace) -> None:
        """Валидирует комбинацию временных параметров."""
        has_datetime = args.datetime is not None
        has_date = args.date is not None
        has_time = args.time is not None
        
        if not (has_datetime or has_date):
            raise ValueError(
                "Обязательно должен быть указан один из параметров: "
                "--datetime ИЛИ --date (с опциональным --time)"
            )
        
        if has_datetime and (has_date or has_time):
            raise ValueError(
                "Параметр --datetime не может использоваться одновременно "
                "с --date или --time"
            )
    
    def _determine_start_time(self, args: argparse.Namespace) -> datetime:
        """Определяет начальное время фильтрации на основе аргументов."""
        if args.datetime:
            # Формат: %Y-%m-%d_%H:%M:%S
            try:
                return datetime.strptime(args.datetime, "%Y-%m-%d_%H:%M:%S")
            except ValueError as e:
                raise ValueError(
                    f"Некорректный формат --datetime: '{args.datetime}'. "
                    f"Ожидается формат: ГГГГ-ММ-ДД_ЧЧ:ММ:СС"
                ) from e
        
        # Используем --date (обязательный) и --time (опциональный)
        try:
            base_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Некорректный формат --date: '{args.date}'. "
                f"Ожидается формат: ГГГГ-ММ-ДД"
            ) from e
        
        
        # Если время не указано, используем начало дня
        if not args.time:
            return datetime.combine(base_date, time(0, 0, 0))
        
        # Парсим время: сначала пробуем абсолютный формат %H:%M:%S
        time_value = self._parse_time_argument(args.time, base_date)
        return datetime.combine(base_date, time_value)
    
    def _parse_time_argument(self, time_str: str, base_date: datetime) -> time:
        """
        Парсит аргумент времени из строки.
        
        Поддерживает:
        - Абсолютное время: "09:00:00", "9:00", "9" → 09:00:00
        - Относительное время: "10 min ago", "9 hours"
        
        Parameters
        ----------
        time_str : str
            Строка с временем.
        base_date : datetime.date
            Базовая дата для вычисления относительного времени.
        
        Returns
        -------
        datetime.time
            Распарсенное время.
        
        Raises
        ------
        ValueError
            Если формат времени не распознан.
        """
        time_str = time_str.strip()
        
        # 1. Пробуем абсолютный формат %H:%M:%S (гибкий парсинг)
        try:
            # Поддерживаем форматы: "9", "9:00", "09:00:00"
            if ":" not in time_str:
                # Только часы
                hour = int(time_str)
                return time(hour=hour, minute=0, second=0)
            elif time_str.count(":") == 1:
                # Часы:минуты
                hour, minute = map(int, time_str.split(":"))
                return time(hour=hour, minute=minute, second=0)
            else:
                # Часы:минуты:секунды
                hour, minute, second = map(int, time_str.split(":"))
                return time(hour=hour, minute=minute, second=second)
        except (ValueError, AttributeError):
            pass  # Продолжаем попытки парсинга
        
        # 2. Пробуем относительное время
        try:
            now = datetime.now()
            relative_dt = parse_relative_time(time_str, now)
            # Применяем время относительного результата к базовой дате
            return time(
                hour=relative_dt.hour,
                minute=relative_dt.minute,
                second=relative_dt.second,
                microsecond=relative_dt.microsecond
            )
        except ValueError:
            pass
        
        raise ValueError(
            f"Некорректный формат времени: '{time_str}'. "
            f"Поддерживаются форматы: ЧЧ:ММ:СС, ЧЧ:ММ, ЧЧ, 'X min ago', 'X hours'"
        )
    
    def _normalize_level(self, level_arg: str) -> str:
        """Нормализует уровень логов к каноническому виду."""
        normalized = self.LEVEL_ALIASES.get(level_arg.upper(), None)
        if normalized is None:
            valid = ", ".join(set(self.LEVEL_ALIASES.values()))
            raise ValueError(
                f"Некорректный уровень логов: '{level_arg}'. "
                f"Допустимые значения: {valid} (или сокращения: A, WE, ER)"
            )
        return normalized


def setup_argument_parser() -> argparse.ArgumentParser:
    """
    Настраивает парсер аргументов командной строки.
    
    Returns
    -------
    argparse.ArgumentParser
        Настроенный парсер с описанием всех параметров.
    """
    parser = argparse.ArgumentParser(
        description="Утилита для сбора и агрегации логов из распределенных источников",
        epilog="Примеры использования:\n"
               "  collect_log --date 2026-02-09 --time 09:00:00 --level error -o errors.txt\n"
               "  collect_log --datetime 2026-02-09_09:00:00 -l ER -o errors/errors_09.txt",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Временные параметры (взаимоисключающие группы)
    time_group = parser.add_argument_group("временные параметры (обязательно указать один из вариантов)")
    time_group.add_argument(
        "--datetime", "-dt",
        help="Комбинированная дата и время в формате ГГГГ-ММ-ДД_ЧЧ:ММ:СС"
    )
    time_group.add_argument(
        "--date", "-d",
        help="Дата в формате ГГГГ-ММ-ДД (время по умолчанию 00:00:00)"
    )
    time_group.add_argument(
        "--time", "-t",
        help="Время в формате ЧЧ:ММ:СС или относительное ('10 min ago', '9 hours')"
    )
    
    # Параметры фильтрации
    parser.add_argument(
        "--level", "-l",
        required=True,
        help="Уровень логов: all (A), warning (WE), error (ER)"
    )
    
    # Пути ввода/вывода
    parser.add_argument(
        "--input", "-i",
        default=".",
        help="Путь к директории с логами (по умолчанию текущая директория)"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Путь к выходному файлу(ам)"
    )
    
    # Ограничения
    parser.add_argument(
        "--mlength",
        type=float,
        help="Максимальный размер выходного файла в МБ (дробление при превышении)"
    )
    
    # Прочее
    parser.add_argument(
        "--version",
        action="version",
        version="log_collector 1.0.0"
    )
    
    return parser


def parse_cli_args() -> CLIArguments:
    """
    Парсит аргументы командной строки и возвращает валидированный объект.
    
    Returns
    -------
    CLIArguments
        Валидированные аргументы.
    
    Raises
    ------
    SystemExit
        При ошибках парсинга или валидации.
    """
    parser = setup_argument_parser()
    
    try:
        args = parser.parse_args()
        return CLIArguments(args)
    except ValueError as e:
        print(f"Ошибка валидации аргументов: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка при обработке аргументов: {e}", file=sys.stderr)
        sys.exit(1)
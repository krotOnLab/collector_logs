"""CLI интерфейс утилиты для сбора логов с поддержкой конфигурации."""

import argparse
import sys
import traceback as tb
from datetime import datetime, time
from pathlib import Path
from typing import Any

from log_collector.config import ConfigError, ConfigLoader
from log_collector.utils import (
    mb_to_bytes,
    parse_relative_time,
)


class CLIArguments:
    """
    Обрабатывает и валидирует аргументы командной строки.
    
    Инкапсулирует логику объединения параметров и их валидации
    """
    
    LEVEL_ALIASES = {
        "A": "all",
        "WE": "warning",
        "ER": "error",
        "all": "all",
        "warning": "warning",
        "error": "error",
    }
    
    def __init__(self, args_dict: dict[str, Any]) -> None:
        """
        Инициализирует аргументы после объединения CLI и конфига.
        
        Parameters
        ----------
        args_dict : Dict[str, Any]
            Объединённые параметры из CLI и конфигурации.
        
        Raises
        ------
        ValueError
            При некорректных значениях параметров.
        """
        self._validate_datetime_args(args_dict)
        self.start_time = self._determine_start_time(args_dict)
        self.end_time = self._determine_end_time(args_dict)  # Для будущего шага 2
        self.level = self._normalize_level(args_dict.get("level"))
        self.input_dir = Path(args_dict.get("input", "."))
        self.output_path = Path(args_dict.get("output", "collected_logs.txt"))
        self.max_file_size = self._parse_max_file_size(args_dict.get("mlength"))
        self.config_path = args_dict.get("config")  # Для информационных сообщений
    
    def _validate_datetime_args(self, args: dict[str, Any]) -> None:
        """Валидирует комбинацию временных параметров."""
        has_datetime = args.get("datetime") is not None
        has_date = args.get("date") is not None
        has_time = args.get("time") is not None
        
        if not (has_datetime or has_date):
            raise ValueError(
                "Обязательно должен быть указан один из параметров: "
                "--datetime ИЛИ --date (с опциональным --time)"
                "Проверьте конфигурационный файл или аргументы CLI."
            )
        
        if has_datetime and (has_date or has_time):
            raise ValueError(
                "Параметр --datetime не может использоваться одновременно "
                "с --date или --time"
                "Проверьте конфигурационный файл или аргументы CLI."
            )
    
    def _determine_start_time(self, args: dict[str, Any]) -> datetime:
        """Определяет начальное время фильтрации на основе аргументов."""
        if args.get("datetime"):
            # Формат: %Y-%m-%d_%H:%M:%S
            try:
                return datetime.strptime(args["datetime"], "%Y-%m-%d_%H:%M:%S")
            except ValueError as e:
                raise ValueError(
                    f"Некорректный формат --datetime: '{args['datetime']}'. "
                    f"Ожидается формат: ГГГГ-ММ-ДД_ЧЧ:ММ:СС"
                ) from e
        
        # Используем --date (обязательный) и --time (опциональный)
        try:
            base_date = datetime.strptime(args["date"], "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Некорректный формат --date: '{args.get('date')}'. "
                f"Ожидается формат: ГГГГ-ММ-ДД"
            ) from e
        
        time_str = args.get("time")
        # Если время не указано, используем начало дня
        if not time_str:
            return datetime.combine(base_date, time(0, 0, 0))
        
        # Парсим время: сначала пробуем абсолютный формат %H:%M:%S
        
        time_value = self._parse_time_argument(time_str, base_date)
        return datetime.combine(base_date, time_value)
    
    def _determine_end_time(self, args: dict[str, Any]) -> datetime | None:
        """
        Определяет конечное время фильтрации (пока всегда None для шага 1).
        
        В будущем (шаг 2) будет поддерживать --end-datetime, --end-date + --end-time.
        """
        return None  # Для шага 1 всегда фильтруем до текущего момента
    
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
    
    def _normalize_level(self, level_arg: str | None) -> str:
        """Нормализует уровень логов к каноническому виду."""
        if not level_arg:
            raise ValueError("Параметр --level (или -l) является обязательным")
        
        normalized = self.LEVEL_ALIASES.get(level_arg.upper(), None)
        if normalized is None:
            valid = ", ".join(set(self.LEVEL_ALIASES.values()))
            raise ValueError(
                f"Некорректный уровень логов: '{level_arg}'. "
                f"Допустимые значения: {valid} (или сокращения: A, WE, ER)"
            )
        return normalized
    
    def _parse_max_file_size(self, mlength: float | None) -> int | None:
        """Конвертирует размер в МБ в байты."""
        return mb_to_bytes(mlength) if mlength is not None else None


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
               "  collect_log -c config.yaml\n"
               "  collect_log -c config.json --date 2026-02-10  # переопределение из CLI"
               "  collect_log --datetime 2026-02-09_09:00:00 -l ER -o errors/errors_09.txt",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Группа конфигурации
    config_group = parser.add_argument_group("конфигурация")
    config_group.add_argument(
        "--config", "-c",
        type=Path,
        help="Путь к конфигурационному файлу (JSON или YAML)"
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
        # required=True,
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
        # required=True,
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
    Парсит аргументы командной строки с поддержкой конфигурации.
    
    Returns
    -------
    CLIArguments
        Валидированные и объединённые аргументы.
    
    Raises
    ------
    SystemExit
        При ошибках парсинга или валидации.
    """
    # Сначала парсим только --config для загрузки конфига
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", "-c", type=Path, required=False)
    pre_args, _ = pre_parser.parse_known_args()
    
    # Загружаем конфиг, если указан
    config_loader = ConfigLoader(pre_args.config) if pre_args.config else ConfigLoader()
    
    # Теперь парсим все аргументы
    parser = setup_argument_parser()
    cli_namespace = parser.parse_args()
    
    # Преобразуем Namespace в словарь для объединения
    cli_dict = {
        k: v for k, v in vars(cli_namespace).items()
        if v is not None or k in ("input", "config")  # сохраняем пустые пути
    }
    
    # Объединяем с конфигом
    try:
        merged_args = config_loader.get_merged_args(cli_dict)
    except ConfigError as e:
        print(f"Ошибка конфигурации: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Валидация и создание объекта аргументов
    try:
        return CLIArguments(merged_args)
    except ValueError as e:
        print(f"Ошибка валидации аргументов: {e}", file=sys.stderr)
        
        # Помощь при отсутствии обязательных параметров
        if "обязательно" in str(e).lower() or "required" in str(e).lower():
            print("\nПодсказка: укажите параметры через CLI или в конфигурационном файле.", file=sys.stderr)
            if config_loader.config_path:
                print(f"Проверьте конфигурационный файл: {config_loader.config_path}", file=sys.stderr)
                
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка при обработке аргументов: {e}", file=sys.stderr)
        print(tb.format_exc())
        sys.exit(1)
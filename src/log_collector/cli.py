"""CLI интерфейс утилиты для сбора логов с поддержкой конфигурации."""

import argparse
# import sys
# import traceback as tb
from datetime import datetime, time#, date
from pathlib import Path
from typing import Any

from log_collector.config import  ConfigLoader #ConfigError,
from log_collector.utils import (
    mb_to_bytes,
    # parse_relative_time,
    parse_time_string,
)

from log_collector.timestamp_parser import TimestampParser, TimestampParserError
from log_collector.instance_filter import InstanceFilter

class CLIArguments:
    """
    Валидированные аргументы после объединения CLI + конфиг + глобальных дефолтов.
    
    Значения по умолчанию применяются ТОЛЬКО если параметр отсутствует везде.
    """
    
    LEVEL_ALIASES = {
        "A": "all",
        "WE": "warning",
        "ER": "error",
        "ALL": "all",
        "WARNING": "warning",
        "ERROR": "error",
    }
    
    # Глобальные значения по умолчанию (применяются только если нет ни в CLI, ни в конфиге)
    GLOBAL_DEFAULTS = {
        "input": ".",
        # "time": "00:00:00",
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
        
        # Применяем глобальные дефолты только для отсутствующих параметров
        for key, default_value in self.GLOBAL_DEFAULTS.items():
            if args_dict.get(key) is None:
                args_dict[key] = default_value
        
        print(f"CLIArguments init - {args_dict}")
        self._validate_datetime_args(args_dict)
        self.start_time = self._determine_start_time(args_dict)
        self.end_time = self._determine_end_time(args_dict)
        self._validate_time_range()
        self.level = self._normalize_level(args_dict.get("level"))
        self.input_dir = Path(args_dict.get("input", "."))
        self.output_path = Path(args_dict.get("output", "collected_logs.txt"))
        self.max_file_size = self._parse_max_file_size(args_dict.get("mlength"))
        self.config_path = args_dict.get("config")  # Для информационных сообщений
        
        self.timestamp_parser = self._create_timestamp_parser(args_dict)
        
        # Создаём фильтр экземпляров
        self.instance_filter = self._create_instance_filter(args_dict)
    
    def _create_timestamp_parser(self, args: dict[str, Any]) -> TimestampParser:
        """Создаёт парсер временных меток на основе параметров."""
        preset = args.get("timestamp_preset")
        pattern = args.get("timestamp_pattern")
        format_str = args.get("timestamp_format")
        
        try:
            return TimestampParser(
                pattern=pattern,
                format_str=format_str,
                preset=preset
            )
        except TimestampParserError as e:
            raise ValueError(f"Ошибка конфигурации парсера временных меток: {e}") from e
    
    def _create_instance_filter(self, args: dict[str, Any]) -> InstanceFilter:
        """Создаёт фильтр экземпляров на основе параметров."""
        # Парсим списки экземпляров из строки (через запятую)
        def parse_instance_list(value: str | None) -> list[int] | None:
            if not value:
                return None
            try:
                # Разделяем по запятым, удаляем пробелы, конвертируем в int
                return [int(x.strip()) for x in value.split(",") if x.strip()]
            except ValueError as e:
                raise ValueError(
                    f"Ошибка парсинга списка экземпляров '{value}': {e}. "
                    f"Ожидается список чисел через запятую, например: '100,101,205'"
                ) from e
        
        allow_instances = parse_instance_list(args.get("allow_instances"))
        deny_instances = parse_instance_list(args.get("deny_instances"))
        allow_regex = args.get("allow_regex")
        deny_regex = args.get("deny_regex")
        
        return InstanceFilter(
            allow_instances=allow_instances,
            deny_instances=deny_instances,
            allow_regex=allow_regex,
            deny_regex=deny_regex
        )
    
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
        # Случай 1: комбинированный параметр datetime
        if args.get("datetime"):
            # Формат: %Y-%m-%d_%H:%M:%S
            try:
                return datetime.strptime(args["datetime"], "%Y-%m-%d_%H:%M:%S")
            except ValueError as e:
                raise ValueError(
                    f"Некорректный формат --datetime: '{args['datetime']}'. "
                    f"Ожидается формат: ГГГГ-ММ-ДД_ЧЧ:ММ:СС"
                ) from e
        
        # Случай 2: раздельные параметры дата + время
        try:
            base_date = datetime.strptime(args["date"], "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(
                f"Некорректный формат --date: '{args.get('date')}'. "
                f"Ожидается формат: ГГГГ-ММ-ДД"
            ) from e
        
        time_str = args.get("time", "00:00:00")
        
        # Парсим время: сначала пробуем абсолютный формат %H:%M:%S
        
        time_value, is_relative = parse_time_string(time_str, base_date)
        
        if is_relative and not isinstance(time_value, time):
            # Относительное время возвращает полную дату-время — используем как есть
            return time_value
        else:
            # Абсолютное время комбинируем с датой из --date
            
            return datetime.combine(base_date, time_value) if not isinstance(time_value, datetime) else time_value
    
    def _determine_end_time(self, args: dict[str, Any]) -> datetime | None:
        """
        Определяет конечное время фильтрации.
        
        Если не задано — возвращаем None (фильтрация до конца лога).
        """
        # Проверяем комбинированный параметр
        if args.get("end_datetime"):
            try:
                return datetime.strptime(args["end_datetime"], "%Y-%m-%d_%H:%M:%S")
            except ValueError as e:
                raise ValueError(
                    f"Некорректный формат --end-datetime: '{args['end_datetime']}'. "
                    f"Ожидается: ГГГГ-ММ-ДД_ЧЧ:ММ:СС"
                ) from e
        
        # Проверяем раздельные параметры даты и времени
        end_date_str = args.get("end_date")
        end_time_str = args.get("end_time")
        
        if not end_date_str and not end_time_str:
            return None  # Не задано конечное время
        
        # if not end_date_str:
        #     raise ValueError(
        #         "Параметр --end-time требует указания --end-date"
        #     )
        if end_time_str and not end_date_str:
            # Пробуем взять дату из начальных параметров
            if args.get("date"):
                end_date_str = args["date"]
            elif args.get("datetime"):
                # Извлекаем дату из строки datetime (формат: "ГГГГ-ММ-ДД_ЧЧ:ММ:СС")
                try:
                    date_part = args["datetime"].split("_")[0]
                    # Валидируем формат даты
                    datetime.strptime(date_part, "%Y-%m-%d")
                    end_date_str = date_part
                except (ValueError, IndexError):
                    # Если не удалось извлечь, используем текущую дату
                    end_date_str = datetime.now().strftime("%Y-%m-%d")
            else:
                # Если начальная дата не указана — используем текущую дату
                end_date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Парсим дату окончания
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(
                f"Некорректный формат --end-date: '{end_date_str}'. "
                f"Ожидается: ГГГГ-ММ-ДД"
            ) from e
        
        # Если время не указано — используем конец дня (23:59:59.999999)
        if not end_time_str:
            return datetime.combine(end_date, time(23, 59, 59, 999999))
        
        end_time_value, is_relative = parse_time_string(end_time_str, base_date=end_date)
        if is_relative and not isinstance(end_time_value, time):
            return end_time_value
        else:
            return datetime.combine(end_date, end_time_value) if not isinstance(end_time_value, datetime) else end_time_value

    def _validate_time_range(self) -> None:
        """Валидирует корректность временного диапазона."""
        if self.end_time and self.end_time < self.start_time:
            raise ValueError(
                f"Конечное время ({self.end_time}) раньше начального ({self.start_time}). "
                f"Временной диапазон должен быть корректным: начало <= конец."
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
               "  collect_log --datetime 2026-02-09_09:00:00 -l ER -o errors/errors_09.txt"
               "  collect_log -c config.yaml --end-date 2026-02-10  # переопределение из CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Группа конфигурации
    config_group = parser.add_argument_group("конфигурация")
    config_group.add_argument(
        "--config", "-c",
        type=Path,
        help="Путь к конфигурационному файлу (JSON или YAML)"
    )
    
    # Временные параметры — начало диапазона
    start_group = parser.add_argument_group("начало временного диапазона (обязательно)")
    start_group.add_argument(
        "--datetime", "-dt",
        help="Дата и время начала в формате ГГГГ-ММ-ДД_ЧЧ:ММ:СС"
    )
    start_group.add_argument(
        "--date", "-d",
        help="Дата начала в формате ГГГГ-ММ-ДД (время по умолчанию 00:00:00)"
    )
    start_group.add_argument(
        "--time", "-t",
        help="Время начала в формате ЧЧ[:ММ[:СС]] или относительное ('10 min ago'). По умолчанию: 00:00:00"
    )
    
    # Временные параметры — конец диапазона
    end_group = parser.add_argument_group("конец временного диапазона (опционально)")
    end_group.add_argument(
        "--end-datetime", "-edt",
        help="Дата и время окончания в формате ГГГГ-ММ-ДД_ЧЧ:ММ:СС"
    )
    end_group.add_argument(
        "--end-date", "-ed",
        help="Дата окончания в формате ГГГГ-ММ-ДД"
    )
    end_group.add_argument(
        "--end-time", "-et",
        help="Время окончания в формате ЧЧ[:ММ[:СС]] или относительное ('10 min ago'). "
             "Если указан только --end-date, время устанавливается в 23:59:59.999999"
    )
    
    # Настройка формата временной метки
    timestamp_group = parser.add_argument_group("формат временной метки (опционально)")
    timestamp_group.add_argument(
        "--timestamp-preset",
        choices=["default", "syslog", "iso8601", "nginx", "rfc3339"],
        help="Предустановленный профиль формата временной метки"
    )
    timestamp_group.add_argument(
        "--timestamp-pattern",
        help="Регулярное выражение для обнаружения начала записи в логе"
    )
    timestamp_group.add_argument(
        "--timestamp-format",
        help="Формат даты/времени для парсинга (strftime). Пример: '%%Y-%%m-%%d %%H:%%M:%%S,%%f'"
    )
    
    # Параметры фильтрации
    parser.add_argument(
        "--level", "-l",
        # required=True,
        help="Уровень логов: all (A), warning (WE), error (ER)"
    )
    
    # Фильтрация экземпляров
    filter_group = parser.add_argument_group("фильтрация экземпляров (опционально)")
    filter_group.add_argument(
        "--allow-instances",
        help="Список разрешённых экземпляров через запятую (например: 100,101,205)"
    )
    filter_group.add_argument(
        "--deny-instances",
        help="Список запрещённых экземпляров через запятую (например: 500,501)"
    )
    filter_group.add_argument(
        "--allow-regex",
        help="Регулярное выражение для разрешённых экземпляров (проверяется по ID)"
    )
    filter_group.add_argument(
        "--deny-regex",
        help="Регулярное выражение для запрещённых экземпляров (проверяется по ID)"
    )
    
    # Пути ввода/вывода
    parser.add_argument(
        "--input", "-i",
        type=Path,
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
        version="log_collector 1.1.0"
    )
    
    return parser


def parse_cli_args() -> CLIArguments:
    """
    Парсит аргументы с корректной семантикой приоритетов:
        CLI (явно указано) > конфигурация > глобальные значения по умолчанию
    
    Алгоритм:
        1. Первый парсинг: извлекаем только --config
        2. Загружаем конфигурацию
        3. Второй парсинг: устанавливаем значения из конфига как дефолты через set_defaults()
        4. Применяем глобальные дефолты только для отсутствующих параметров
    """
    # Шаг 1: Парсим только --config для загрузки конфигурации
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", "-c", type=Path, required=False)
    config_args, remaining_args = pre_parser.parse_known_args()
    
    # Шаг 2: Загружаем конфигурацию, если указан путь
    config_loader = ConfigLoader(config_args.config) if config_args.config else ConfigLoader()
    
    # Шаг 3: Создаём основной парсер и устанавливаем дефолты ИЗ КОНФИГА
    parser = setup_argument_parser()
    
    # Критически важный шаг: значения из конфига становятся дефолтами,
    # но будут перекрыты любым явным указанием в CLI
    if config_loader.has_config:
        parser.set_defaults(**config_loader.raw_config)
    
    # Шаг 4: Парсим оставшиеся аргументы (всё кроме --config)
    args = parser.parse_args(remaining_args)
    args_dict = vars(args)
    
    # Шаг 5: Применяем ГЛОБАЛЬНЫЕ дефолты только для параметров, отсутствующих везде
    # (например, 'input' будет "." только если не задан ни в CLI, ни в конфиге)
    return CLIArguments(args_dict)
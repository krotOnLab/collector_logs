"""Парсер временных меток с поддержкой кастомных форматов."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from re import Pattern
import sys


class TimestampParserError(Exception):
    """Ошибка при работе с парсером временных меток."""
    pass


class TimestampParser:
    """
    Парсит временные метки из строк лога по настраиваемому формату.
    
    Поддерживает:
    - Произвольные регулярные выражения для обнаружения начала записи
    - Произвольные форматы даты/времени (strftime)
    - Предустановленные профили для популярных форматов
    
    Attributes
    ----------
    pattern : Pattern
        Скомпилированный регулярный выражение для обнаружения начала записи.
    format_str : str
        Формат даты/времени для парсинга (strftime).
    """
    
    # Предустановленные профили форматов
    PRESETS: dict[str, dict[str, str]] = {
        "default": {
            "pattern": r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}",
            "format": "%Y-%m-%d %H:%M:%S,%f"
        },
        "syslog": {
            "pattern": r"^[A-Z][a-z]{2} {1,2}\d{1,2} \d{2}:\d{2}:\d{2}",
            "format": "%b %d %H:%M:%S"
        },
        "iso8601": {
            "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z",
            "format": "%Y-%m-%dT%H:%M:%S.%fZ"
        },
        "nginx": {
            "pattern": r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}",
            "format": "%Y/%m/%d %H:%M:%S"
        },
        "rfc3339": {
            "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}",
            "format": "%Y-%m-%dT%H:%M:%S%z"
        }
    }
    
    def __init__(
        self,
        pattern: str | None = None,
        format_str: str | None = None,
        preset: str | None = None
    ) -> None:
        """
        Инициализирует парсер временных меток.
        
        Параметры задаются в порядке приоритета:
        1. Явно указанные pattern и format_str
        2. Предустановленный профиль (preset)
        3. Значения по умолчанию (default)
        
        Parameters
        ----------
        pattern : str | None
            Регулярное выражение для обнаружения начала записи.
        format_str : str | None
            Формат даты/времени для парсинга (strftime).
        preset : str | None
            Имя предустановленного профиля (default, syslog, iso8601, nginx, rfc3339).
        
        Raises
        ------
        TimestampParserError
            При ошибках валидации параметров или несуществующем профиле.
        """
        # Определяем источник конфигурации
        if pattern and format_str:
            self.pattern_str = pattern
            self.format_str = format_str
        elif preset:
            if preset not in self.PRESETS:
                valid_presets = ", ".join(self.PRESETS.keys())
                raise TimestampParserError(
                    f"Неизвестный профиль временной метки: '{preset}'. "
                    f"Допустимые значения: {valid_presets}"
                )
            config = self.PRESETS[preset]
            self.pattern_str = config["pattern"]
            self.format_str = config["format"]
        else:
            # Значения по умолчанию
            default_config = self.PRESETS["default"]
            self.pattern_str = default_config["pattern"]
            self.format_str = default_config["format"]
        
        # Компилируем регулярное выражение
        try:
            self.pattern: Pattern = re.compile(self.pattern_str)
        except re.error as e:
            raise TimestampParserError(
                f"Ошибка компиляции регулярного выражения '{self.pattern_str}': {e}"
            ) from e
    
    def is_line_start(self, line: str) -> bool:
        """
        Проверяет, начинается ли строка с временной метки.
        
        Удаляет ведущие пробелы и BOM-символы для устойчивости к разному форматированию.
        
        Parameters
        ----------
        line : str
            Строка для проверки.
        
        Returns
        -------
        bool
            True, если строка начинается с временной метки.
        """
        # Удаляем ведущие пробельные символы (пробелы, табы) и BOM
        stripped_line = line.lstrip('\ufeff \t')
        return bool(self.pattern.match(stripped_line))
    
    def parse_timestamp(self, line: str) -> datetime:
        """
        Извлекает и парсит временную метку из строки.
        
        Parameters
        ----------
        line : str
            Строка, начинающаяся с временной метки.
        
        Returns
        -------
        datetime
            Распарсенная временная метка.
        
        Raises
        ------
        TimestampParserError
            Если строка не содержит временную метку или формат не распознан.
        """
        # Удаляем ведущие символы для корректного матчинга
        stripped_line = line.lstrip('\ufeff \t')
    
        match = self.pattern.match(stripped_line)
        if not match:
            raise TimestampParserError(
                f"Строка не начинается с временной метки (паттерн: {self.pattern_str}): "
                f"{line[:60]}..."
            )
        
        # Извлекаем полную совпавшую временную метку
        timestamp_str = match.group(0)
        
        # === КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ ===
        # Сначала проверяем, требует ли формат специальной обработки (без года)
        if self._requires_year_inference():
            return self._handle_syslog_timestamp(timestamp_str)
        
        # Стандартный парсинг для форматов с годом
        try:
            return datetime.strptime(timestamp_str, self.format_str)
        except ValueError as e:
            raise TimestampParserError(
                f"Не удалось распарсить временную метку '{timestamp_str}' "
                f"по формату '{self.format_str}': {e}"
            ) from e
    
    def _is_syslog_format(self) -> bool:
        """Проверяет, является ли формат похожим на syslog (без года)."""
        print(f'DEBUG - - - _is_syslog_format = {"syslog" in self.format_str.lower() or (
            "%b" in self.format_str and 
            "%Y" not in self.format_str and 
            "%y" not in self.format_str
        )}')
        return "syslog" in self.format_str.lower() or (
            "%b" in self.format_str and 
            "%Y" not in self.format_str and 
            "%y" not in self.format_str
        )
        
    def _requires_year_inference(self) -> bool:
        """
        Проверяет, требует ли формат определения года (отсутствует %Y или %y в формате).
        
        Returns
        -------
        bool
            True, если формат не содержит года и требует инференса.
        """
        # Формат содержит год напрямую
        if "%Y" in self.format_str or "%y" in self.format_str:
            return False
        
        # Явный признак syslog-формата
        if "syslog" in self.format_str.lower():
            return True
        
        # Эвристика: формат с месяцем (%b, %B, %m) но без года
        has_month = any(x in self.format_str for x in ["%b", "%B", "%m"])
        return has_month
    
    def _handle_syslog_timestamp(self, timestamp_str: str) -> datetime:
        """
        Обрабатывает временные метки без года (syslog и подобные).
        
        Стратегия:
        1. Генерирует кандидатов для нескольких лет (прошлый, текущий, следующий)
        2. Выбирает ближайшую дату к текущему моменту, но не в будущем
        3. Гарантирует, что возвращаемая дата не позже текущего момента
        
        Parameters
        ----------
        timestamp_str : str
            Строка временной метки без года (например, "Feb 14 16:12:22").
        
        Returns
        -------
        datetime
            Распарсенная временная метка с корректным годом.
        """
        now = datetime.now()
        candidates = []
        
        # Пробуем 3 года для надёжности
        for year_offset in (-1, 0, 1):
            year = now.year + year_offset
            try:
                candidate_str = f"{year} {timestamp_str}"
                candidate_format = f"%Y {self.format_str}"
                candidate = datetime.strptime(candidate_str, candidate_format)
                candidates.append(candidate)
            except ValueError:
                continue
        
        if not candidates:
            raise TimestampParserError(
                f"Не удалось распарсить временную метку без года '{timestamp_str}' "
                f"для любого из ближайших лет"
            )
        
        # Фильтруем будущие даты
        past_candidates = [c for c in candidates if c <= now]
        
        if past_candidates:
            # Ближайшая дата из прошлого
            return min(past_candidates, key=lambda c: (now - c).total_seconds())
        
        # Все кандидаты в будущем — берём самую раннюю
        return min(candidates)
    
    def __repr__(self) -> str:
        return f"TimestampParser(pattern={self.pattern_str!r}, format={self.format_str!r})"
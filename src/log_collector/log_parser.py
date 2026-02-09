"""Модуль для парсинга содержимого лог-файлов и фильтрации записей по времени."""

from collections.abc import Generator
from datetime import datetime
from pathlib import Path

from log_collector.utils import is_log_line_start


class LogEntry:
    """
    Представляет одну запись в логе (может занимать несколько строк).
    
    Атрибуты
    --------
    timestamp : datetime
        Временная метка записи.
    content : str
        Полное содержимое записи (включая все строки трейсбека).
    """
    
    def __init__(self, timestamp: datetime, content: str) -> None:
        self.timestamp = timestamp
        self.content = content
    
    def __repr__(self) -> str:
        return f"LogEntry({self.timestamp}, {len(self.content)} chars)"


class LogParser:
    """
    Парсит лог-файлы и извлекает записи с фильтрацией по времени.
    
    Отвечает за:
    - Чтение файлов с корректной обработкой многострочных записей
    - Парсинг временных меток
    - Фильтрацию записей по временному диапазону
    """
    
    def __init__(self, start_time: datetime) -> None:
        """
        Инициализирует парсер с указанием начального времени фильтрации.
        
        Parameters
        ----------
        start_time : datetime
            Минимальная временная метка для включения записи в результат.
        """
        self.start_time = start_time
    
    def parse_file(self, file_path: Path) -> Generator[LogEntry, None, None]:
        """
        Парсит лог-файл и возвращает записи, удовлетворяющие временному фильтру.
        
        Parameters
        ----------
        file_path : Path
            Путь к файлу лога.
        
        Yields
        ------
        LogEntry
            Записи лога, начиная с указанного времени.
        
        Notes
        -----
        Многострочные записи (например, трейсбеки) обрабатываются корректно:
        запись продолжается до тех пор, пока не встретится новая строка
        с временной меткой или не закончится файл.
        """
        current_entry: list[str] = []
        current_timestamp: datetime | None = None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    # Проверяем, начинается ли строка с временной метки
                    if is_log_line_start(line):
                        # Сохраняем предыдущую запись, если она есть и проходит фильтр
                        if current_entry and current_timestamp:
                            if current_timestamp >= self.start_time:
                                yield LogEntry(current_timestamp, "".join(current_entry))
                        
                        # Начинаем новую запись
                        current_timestamp = self._parse_timestamp(line)
                        current_entry = [line]
                    else:
                        # Продолжение текущей записи (трейсбек, дополнительные данные)
                        if current_entry:  # Защита от случая, когда файл начинается не с временной метки
                            current_entry.append(line)
                
                # Не забываем сохранить последнюю запись в файле
                if current_entry and current_timestamp:
                    if current_timestamp >= self.start_time:
                        yield LogEntry(current_timestamp, "".join(current_entry))
        
        except UnicodeDecodeError:
            # Пропускаем файлы с некорректной кодировкой, логируем предупреждение
            print(f"Предупреждение: невозможно прочитать файл {file_path} (ошибка кодировки). Пропущен.")
        except Exception as e:
            print(f"Ошибка при чтении файла {file_path}: {e}. Пропущен.")
    
    def _parse_timestamp(self, line: str) -> datetime:
        """
        Извлекает временную метку из первой строки лога.
        
        Parameters
        ----------
        line : str
            Первая строка записи лога.
        
        Returns
        -------
        datetime
            Распарсенная временная метка.
        
        Raises
        ------
        ValueError
            Если формат временной метки некорректен.
        """
        # Формат: "2026-02-09 09:23:04,623"
        try:
            date_str = line[:23]  # "2026-02-09 09:23:04,623"
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S,%f")
        except (ValueError, IndexError) as e:
            raise ValueError(f"Некорректный формат временной метки в строке: {line[:30]}...") from e
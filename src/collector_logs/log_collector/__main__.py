"""Точка входа утилиты для сбора логов."""

import sys

from collector_logs.log_collector.cli import CLIArguments, parse_cli_args
from collector_logs.log_collector.filesystem import LogFileFinder
from collector_logs.log_collector.formatter import LogFormatter
from collector_logs.log_collector.log_parser import LogEntry, LogParser


class LogCollector:
    """
    Основной класс утилиты для сбора логов.
    
    Координирует работу всех компонентов:
    - Поиск файлов логов
    - Парсинг и фильтрация записей
    - Форматирование результата
    - Запись в выходные файлы с учетом ограничений по размеру
    """
    
    def __init__(self, args: CLIArguments) -> None:
        """
        Инициализирует сборщик логов.
        
        Parameters
        ----------
        args : CLIArguments
            Валидированные аргументы командной строки.
        """
        self.args = args
        self.finder = LogFileFinder(self.args.input_dir)
        self.parser = LogParser(self.args.start_time)
        self.formatter = LogFormatter()
    
    def collect(self) -> int:
        """
        Выполняет сбор логов согласно параметрам.
        
        Returns
        -------
        int
            Код возврата: 0 при успехе, 1 при ошибке.
        """
        try:
            # 1. Находим файлы логов для всех экземпляров
            instance_files = self.finder.find_log_files(self.args.level)
            if not instance_files:
                print(f"Внимание: не найдено файлов логов уровня '{self.args.level}' "
                      f"в директории {self.args.input_dir}", file=sys.stderr)
                return 0
            
            # 2. Собираем и фильтруем записи для каждого экземпляра
            instance_entries: list[tuple[int, list[LogEntry]]] = []
            total_entries = 0
            
            for instance_id in sorted(instance_files.keys()):
                entries: list[LogEntry] = []
                for file_path in instance_files[instance_id]:
                    for entry in self.parser.parse_file(file_path):
                        entries.append(entry)
                
                if entries:
                    instance_entries.append((instance_id, entries))
                    total_entries += len(entries)
            
            if not instance_entries:
                print(f"Информация: найдены файлы логов, но нет записей после "
                      f"{self.args.start_time}", file=sys.stderr)
                return 0
            
            # 3. Форматируем и записываем результат
            self._write_output(instance_entries, total_entries)
            
            print(f"Успешно собрано {total_entries} записей от {len(instance_entries)} "
                  f"экземпляров в {self.args.output_path}")
            return 0
        
        except Exception as e:
            print(f"Ошибка при сборе логов: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1
    
    def _write_output(self, instance_entries: list[tuple[int, list[LogEntry]]], total_entries: int) -> None:
        """
        Записывает отформатированные логи в выходной файл(ы).
        
        Parameters
        ----------
        instance_entries : List[Tuple[int, List[LogEntry]]]
            Список кортежей (ID экземпляра, записи лога).
        total_entries : int
            Общее количество записей (для информационного сообщения).
        
        Notes
        -----
        При указании --mlength выполняется дробление на несколько файлов
        с сохранением целостности записей одного экземпляра.
        """
        # Создаем родительские директории для выходного файла
        self.args.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.args.max_file_size:
            # Простой случай: один файл
            self._write_to_single_file(instance_entries)
            return
        
        # Сложный случай: дробление на файлы с ограничением по размеру
        self._write_with_size_limit(instance_entries)
    
    def _write_to_single_file(self, instance_entries: list[tuple[int, list[LogEntry]]]) -> None:
        """Записывает все логи в один файл."""
        with open(self.args.output_path, "w", encoding="utf-8") as f:
            for idx, (instance_id, entries) in enumerate(instance_entries):
                f.write(self.formatter.format_instance_logs(instance_id, entries))
                if idx < len(instance_entries) - 1:
                    f.write(self.formatter.format_next_marker())
    
    def _write_with_size_limit(self, instance_entries: list[tuple[int, list[LogEntry]]]) -> None:
        """
        Записывает логи в несколько файлов с ограничением максимального размера.
        
        Каждый файл содержит целые экземпляры (нельзя разбивать один экземпляр между файлами).
        """
        assert self.args.max_file_size is not None, "max_file_size must be set for size-limited writing"
        max_size_bytes = self.args.max_file_size
        
        base_path = self.args.output_path
        base_stem = base_path.stem
        suffix = base_path.suffix or ".txt"
        parent_dir = base_path.parent
        
        current_file_index = 1
        current_file_path = parent_dir / f"{base_stem}_{current_file_index}{suffix}"
        current_size = 0
        
        with open(current_file_path, "w", encoding="utf-8") as f:
            for idx, (instance_id, entries) in enumerate(instance_entries):
                # Форматируем записи текущего экземпляра
                formatted = self.formatter.format_instance_logs(instance_id, entries)
                if idx < len(instance_entries) - 1:
                    formatted += self.formatter.format_next_marker()
                
                formatted_size = len(formatted.encode("utf-8"))
                
                # Проверяем, поместится ли экземпляр в текущий файл
                if current_size + formatted_size > max_size_bytes:
                    # Закрываем текущий файл и начинаем новый
                    f.close()
                    current_file_index += 1
                    current_file_path = parent_dir / f"{base_stem}_{current_file_index}{suffix}"
                    f = open(current_file_path, "w", encoding="utf-8")
                    current_size = 0
                    print(f"Создан новый файл из-за ограничения размера: {current_file_path}")
                
                # Записываем экземпляр в текущий файл
                f.write(formatted)
                current_size += formatted_size
        
        print(f"Результат разделен на {current_file_index} файл(ов) из-за ограничения "
              f"размера {max_size_bytes / (1024 * 1024):.1f} МБ")


def main() -> int:
    """
    Точка входа утилиты.
    
    Returns
    -------
    int
        Код возврата программы.
    """
    args = parse_cli_args()
    collector = LogCollector(args)
    return collector.collect()


if __name__ == "__main__":
    sys.exit(main())
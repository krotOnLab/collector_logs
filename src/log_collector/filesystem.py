"""Модуль для поиска и работы с файлами логов в файловой системе."""

import re
from pathlib import Path

from collector_logs.log_collector.utils import extract_instance_id


class LogFileFinder:
    """
    Класс для поиска файлов логов в указанной директории.
    
    Отвечает за обнаружение всех файлов логов для экземпляров,
    включая ротированные версии файлов.
    """
    
    # Паттерны имен файлов для разных уровней логирования
    LOG_PATTERNS = {
        "all": re.compile(r"^instance\s+\d+\.log$", re.IGNORECASE),
        "warning": re.compile(r"^instance\s+\d+_warning\.log$", re.IGNORECASE),
        "error": re.compile(r"^instance\s+\d+_error\.log$", re.IGNORECASE),
    }
    
    def __init__(self, log_directory: Path) -> None:
        """
        Инициализирует поиск логов в указанной директории.
        
        Parameters
        ----------
        log_directory : Path
            Путь к директории с логами.
        
        Raises
        ------
        ValueError
            Если директория не существует или не является директорией.
        """
        if not log_directory.exists():
            raise ValueError(f"Директория не существует: {log_directory}")
        if not log_directory.is_dir():
            raise ValueError(f"Путь не является директорией: {log_directory}")
        
        self.log_directory = log_directory
    
    def find_log_files(self, level: str) -> dict[int, list[Path]]:
        """
        Находит все файлы логов указанного уровня для всех экземпляров.
        
        Parameters
        ----------
        level : str
            Уровень логов: "all", "warning" или "error".
        
        Returns
        -------
        Dict[int, List[Path]]
            Словарь, где ключ - ID экземпляра, значение - список путей к файлам логов
            (включая ротированные версии), отсортированный по времени модификации.
        
        Notes
        -----
        Ротированные файлы обычно имеют суффиксы вида ".2026-02-09" или ".1".
        Все найденные файлы для одного экземпляра сортируются по времени модификации
        для корректного чтения хронологически.
        """
        if level not in self.LOG_PATTERNS:
            raise ValueError(f"Некорректный уровень логов: {level}. "
                           f"Допустимые значения: {list(self.LOG_PATTERNS.keys())}")
        
        pattern = self.LOG_PATTERNS[level]
        instance_files: dict[int, list[Path]] = {}
        
        # Проходим по всем поддиректориям (каждая поддиректория = экземпляр)
        for subdir in self.log_directory.iterdir():
            if not subdir.is_dir():
                continue
            
            # Ищем файлы логов в поддиректории
            for file_path in subdir.iterdir():
                if file_path.is_file() and pattern.match(file_path.name):
                    instance_id = extract_instance_id(file_path.name)
                    if instance_id is not None:
                        instance_files.setdefault(instance_id, []).append(file_path)
        
        # Сортируем файлы для каждого экземпляра по времени модификации (старые -> новые)
        for instance_id in instance_files:
            instance_files[instance_id].sort(key=lambda p: p.stat().st_mtime)
        
        return instance_files
"""Загрузка и объединение конфигурации из файлов и CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class ConfigError(Exception):
    """Ошибка при работе с конфигурацией."""
    pass


class ConfigLoader:
    """
    Загружает и объединяет параметры из конфигурационного файла и CLI.
    
    Приоритет параметров:
        1. Явно указанные в CLI (не None)
        2. Значения из конфигурационного файла
        3. Значения по умолчанию (в коде)
    
    Examples
    --------
    >>> loader = ConfigLoader(Path("config.yaml"))
    >>> cli_args = {"date": "2026-02-10", "output": "new.txt"}
    >>> merged = loader.get_merged_args(cli_args)
    >>> merged["date"]  # CLI имеет приоритет
    '2026-02-10'
    """
    
    SUPPORTED_EXTENSIONS = {".json", ".yaml", ".yml"}
    
    def __init__(self, config_path: str| Path | None = None) -> None:
        """
        Инициализирует загрузчик конфигурации.
        
        Parameters
        ----------
        config_path : str | Path | None
            Путь к конфигурационному файлу. Если None — конфиг не загружается.
        
        Raises
        ------
        ConfigError
            При ошибках загрузки или неподдерживаемом формате файла.
        """
        self.config_path: Path | None = Path(config_path) if config_path else None
        self.raw_config: dict[str, Any] = {}
        
        if self.config_path:
            self._load_config()
    
    def _load_config(self) -> None:
        """Загружает конфигурацию из файла."""
        if self.config_path is None:
            raise ConfigError("Config path is None")
        
        if not self.config_path.exists():
            raise ConfigError(f"Конфигурационный файл не найден: {self.config_path}")
        
        if not self.config_path.is_file():
            raise ConfigError(f"Путь не является файлом: {self.config_path}")
        
        ext = self.config_path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(self.SUPPORTED_EXTENSIONS))
            raise ConfigError(
                f"Неподдерживаемый формат файла '{ext}'. "
                f"Поддерживаются: {supported}"
            )
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                if ext == ".json":
                    self.raw_config = json.load(f)
                else:  # .yaml, .yml
                    if not HAS_YAML:
                        raise ConfigError(
                            "Для работы с YAML требуется установка pyyaml: "
                            "pip install pyyaml"
                        )
                    self.raw_config = yaml.safe_load(f) or {}
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ConfigError(f"Ошибка парсинга конфигурации: {e}") from e
        except Exception as e:
            raise ConfigError(f"Ошибка чтения конфигурации: {e}") from e
    
    def get_merged_args(self, cli_args: dict[str, Any]) -> dict[str, Any]:
        """
        Объединяет параметры из CLI и конфигурации.
        
        Параметры из CLI перекрывают значения из конфига, если они явно заданы (не None).
        
        Parameters
        ----------
        cli_args : Dict[str, Any]
            Словарь аргументов из командной строки.
        
        Returns
        -------
        Dict[str, Any]
            Объединённые параметры.
        """
        # Копируем конфиг, чтобы не модифицировать оригинал
        merged = self.raw_config.copy()
        
        # CLI имеет приоритет над конфигом
        for key, value in cli_args.items():
            # Только явно заданные значения из CLI (не None и не пустая строка для путей)
            if value is not None and value != "":
                merged[key] = value
        
        return merged
    
    @property
    def has_config(self) -> bool:
        """Проверяет, был ли загружен конфигурационный файл."""
        return bool(self.raw_config)
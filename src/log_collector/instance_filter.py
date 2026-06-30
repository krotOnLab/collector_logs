"""Фильтрация экземпляров по спискам и регулярным выражениям."""

import re


class InstanceFilter:
    """
    Фильтрует экземпляры по спискам и регулярным выражениям.
    
    Приоритет правил:
        1. Запрет (deny) имеет высший приоритет
        2. Если есть разрешающие правила (allow) — проверяем их
        3. По умолчанию разрешаем всё (если нет правил)
    
    Примеры использования:
        # Только экземпляры 100-199
        InstanceFilter(allow_regex=r"^1\d{2}$")
        
        # Все кроме 500-599
        InstanceFilter(deny_regex=r"^5\d{2}$")
        
        # Конкретные экземпляры
        InstanceFilter(allow_instances=[100, 101, 205])
    """
    
    def __init__(
        self,
        allow_instances: list[int] | None = None,
        deny_instances: list[int] | None= None,
        allow_regex: str | None = None,
        deny_regex: str | None = None
    ):
        """
        Инициализирует фильтр экземпляров.
        
        Parameters
        ----------
        allow_instances : list[int] | None
            Список разрешённых ID экземпляров. Если указан — только эти экземпляры разрешены.
        deny_instances : list[int] | None
            Список запрещённых ID экземпляров. Имеет приоритет над разрешениями.
        allow_regex : str | None
            Регулярное выражение для разрешённых экземпляров (проверяется по строковому представлению ID).
        deny_regex : str | None
            Регулярное выражение для запрещённых экземпляров. Имеет приоритет над разрешениями.
        """
        # Преобразуем списки в множества для быстрого поиска
        self.allow_instances: set[int] | None = set(allow_instances) if allow_instances else None
        self.deny_instances: set[int] | None = set(deny_instances) if deny_instances else None
        
        # Компилируем регулярные выражения
        self.allow_pattern: re.Pattern | None = re.compile(allow_regex) if allow_regex else None
        self.deny_pattern: re.Pattern| None = re.compile(deny_regex) if deny_regex else None
    
    def is_allowed(self, instance_id: int) -> bool:
        """
        Проверяет, разрешён ли экземпляр согласно правилам фильтрации.
        
        Parameters
        ----------
        instance_id : int
            ID экземпляра для проверки.
        
        Returns
        -------
        bool
            True, если экземпляр разрешён к обработке.
        
        Приоритет проверки:
            1. Если экземпляр в списке запрещённых — отклоняем
            2. Если экземпляр совпадает с запрещающим регексом — отклоняем
            3. Если есть разрешающие правила:
                - Если экземпляр в списке разрешённых — разрешаем
                - Если экземпляр совпадает с разрешающим регексом — разрешаем
                - Иначе отклоняем
            4. Если нет разрешающих правил — разрешаем всё
        """
        id_str = str(instance_id)
        
        # 1. Проверка запретов (высший приоритет)
        if self.deny_instances and instance_id in self.deny_instances:
            return False
        if self.deny_pattern and self.deny_pattern.search(id_str):
            return False
        
        # 2. Если есть разрешающие правила — проверяем их
        if self.allow_instances is not None or self.allow_pattern is not None:
            # Проверяем список разрешённых
            if self.allow_instances is not None and instance_id in self.allow_instances:
                return True
            # Проверяем регекс разрешённых
            if self.allow_pattern and self.allow_pattern.search(id_str):
                return True
            # Не прошёл ни один из разрешающих фильтров
            return False
        
        # 3. По умолчанию разрешаем всё (если нет разрешающих правил)
        return True
    
    def __repr__(self) -> str:
        parts = []
        if self.allow_instances:
            parts.append(f"allow_instances={sorted(self.allow_instances)}")
        if self.deny_instances:
            parts.append(f"deny_instances={sorted(self.deny_instances)}")
        if self.allow_pattern:
            parts.append(f"allow_regex={self.allow_pattern.pattern}")
        if self.deny_pattern:
            parts.append(f"deny_regex={self.deny_pattern.pattern}")
        return f"InstanceFilter({', '.join(parts)})"
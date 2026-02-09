"""Модуль для форматирования результатов сбора логов в читаемый вид."""

from log_collector.log_parser import LogEntry


class LogFormatter:
    """
    Форматирует собранные логи в структурированный вывод с разделителями.
    
    Генерирует вывод в формате:
    ===================================   100   =================================================
    [содержимое логов экземпляра 100]
    ===================================   100 (END)   =================================================
    """
    
    SEPARATOR_LENGTH = 100
    
    def format_instance_logs(self, instance_id: int, entries: list[LogEntry]) -> str:
        """
        Форматирует логи одного экземпляра с разделителями.
        
        Parameters
        ----------
        instance_id : int
            ID экземпляра.
        entries : List[LogEntry]
            Список записей лога для экземпляра.
        
        Returns
        -------
        str
            Отформатированная строка с логами экземпляра и разделителями.
        
        Notes
        -----
        Если для экземпляра нет записей, возвращается пустая строка.
        """
        if not entries:
            return ""
        
        id_str = f"   {instance_id}   "
        separator = self._create_separator(id_str)
        end_separator = self._create_separator(f"   {instance_id} (END)   ")
        
        content = "\n".join(entry.content.rstrip("\n") for entry in entries)
        
        return f"{separator}\n{content}\n{end_separator}\n\n"
    
    def format_next_marker(self) -> str:
        """
        Создает маркер перехода к следующему экземпляру.
        
        Returns
        -------
        str
            Строка-маркер "===================================   NEXT   =================================================".
        """
        return self._create_separator("   NEXT   ") + "\n\n"
    
    def _create_separator(self, center_text: str) -> str:
        """
        Создает разделительную строку с центрированным текстом.
        
        Parameters
        ----------
        center_text : str
            Текст для центрирования в разделителе.
        
        Returns
        -------
        str
            Строка-разделитель заданной длины.
        """
        available_space = self.SEPARATOR_LENGTH - len(center_text)
        left_pad = available_space // 2
        right_pad = available_space - left_pad
        
        return "=" * left_pad + center_text + "=" * right_pad
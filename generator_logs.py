#!/usr/bin/env python3
"""
Генератор тестовых логов для проверки всех форматов временных меток.
Создаёт структуру директорий и файлов, имитирующую реальные логи сервиса.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import string


def random_string(length=20):
    """Генерирует случайную строку для имитации данных."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_default_format(base_dir: Path):
    """Генерирует логи в стандартном формате: 2026-02-14 09:23:04,623"""
    log_dir = base_dir / "default_format" / "instance_100"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    entries = [
        ("2026-02-13 23:50:00,123", "INFO", "Сервис запущен", []),
        ("2026-02-13 23:55:30,456", "WARNING", "[DB] Медленный запрос к таблице users", []),
        ("2026-02-14 00:05:15,789", "ERROR", "[Model_updated] Ошибка в ModelInstance.Process: [Errno 2] No such file or directory: ''", [
            "Traceback (most recent call last):",
            "  File \"/opt/service/core/model.py\", line 145, in process",
            "    with open(filepath, 'r') as f:",
            "FileNotFoundError: [Errno 2] No such file or directory: ''"
        ]),
        ("2026-02-14 00:10:22,012", "ERROR", "[API] Таймаут подключения к внешнему сервису", [
            "Traceback (most recent call last):",
            "  File \"/opt/service/api/client.py\", line 88, in call_external",
            "    response = requests.get(url, timeout=5)",
            "requests.exceptions.Timeout: Request timed out"
        ]),
        ("2026-02-14 00:15:45,345", "INFO", "Плановое обслуживание завершено", []),
    ]
    
    _write_log_files(log_dir, "100", entries)


def generate_syslog_format(base_dir: Path):
    """Генерирует логи в формате syslog: Feb 14 09:23:04"""
    log_dir = base_dir / "syslog_format" / "instance_101"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Используем текущую дату для корректной обработки syslog (без года)
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)
    
    # Форматируем даты как в syslog: "Feb 14 09:23:04" (без года, с ведущим пробелом для дней < 10)
    def syslog_time(dt: datetime) -> str:
        return dt.strftime("%b %d %H:%M:%S").replace(f" {dt.day} ", f" {dt.day:2d} ")  # Ведущий пробел для дней < 10
    
    entries = [
        (syslog_time(two_days_ago), "service[123]", f"INFO Started service v2.1.0 on {random_string(8)}", []),
        (syslog_time(yesterday.replace(hour=23, minute=55)), "service[123]", "WARNING High memory usage: 85%", []),
        (syslog_time(now.replace(hour=0, minute=5)), "service[123]", "ERROR Failed to connect to database: Connection refused", [
            "Traceback:",
            "  File \"db.py\", line 42, in connect",
            "    raise ConnectionError(\"Connection refused\")",
            "ConnectionError: Connection refused"
        ]),
        (syslog_time(now.replace(hour=0, minute=10)), "service[123]", "ERROR Permission denied: /var/log/app/data.log", [
            "IOError: [Errno 13] Permission denied: '/var/log/app/data.log'"
        ]),
        (syslog_time(now.replace(hour=0, minute=15)), "service[123]", "INFO Daily cleanup completed successfully", []),
    ]
    
    # Для syslog формата структура записи другая: "<время> <хост> <процесс>: <сообщение>"
    syslog_entries = []
    for time_str, process, msg, traceback_lines in entries:
        base_line = f"{time_str} localhost {process}: {msg}"
        syslog_entries.append((time_str, "SYSLOG", base_line, traceback_lines))
    
    _write_log_files(log_dir, "101", syslog_entries, is_syslog=True)


def generate_iso8601_format(base_dir: Path):
    """Генерирует логи в формате ISO 8601: 2026-02-14T09:23:04.623Z"""
    log_dir = base_dir / "iso8601_format" / "instance_102"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    entries = [
        ("2026-02-13T23:50:00.123Z", "INFO", "[INIT] Service starting up", []),
        ("2026-02-13T23:55:30.456Z", "WARN", "[CACHE] Cache miss rate increased to 40%", []),
        ("2026-02-14T00:05:15.789Z", "ERROR", "[STORAGE] Failed to write data block", [
            "com.storage.WriteException: Disk full",
            "\tat com.storage.BlockWriter.write(BlockWriter.java:112)",
            "\tat com.service.DataProcessor.process(DataProcessor.java:45)"
        ]),
        ("2026-02-14T00:10:22.012Z", "ERROR", "[NETWORK] Connection reset by peer", [
            "java.net.SocketException: Connection reset",
            "\tat java.net.SocketInputStream.read(SocketInputStream.java:210)"
        ]),
        ("2026-02-14T00:15:45.345Z", "INFO", "[HEALTH] All systems operational", []),
    ]
    
    _write_log_files(log_dir, "102", entries)


def generate_nginx_format(base_dir: Path):
    """Генерирует логи в формате nginx: 2026/02/14 09:23:04"""
    log_dir = base_dir / "nginx_format" / "instance_103"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    entries = [
        ("2026/02/13 23:50:00", "[info]", "Starting nginx worker process", []),
        ("2026/02/13 23:55:30", "[warn]", "*1 an upstream response is buffered to a temporary file", []),
        ("2026/02/14 00:05:15", "[error]", "*3 open() \"/usr/share/nginx/html/favicon.ico\" failed (2: No such file or directory)", []),
        ("2026/02/14 00:10:22", "[error]", "*5 connect() failed (111: Connection refused) while connecting to upstream", [
            "upstream: \"http://127.0.0.1:8080/api\"",
            "client: 192.168.1.100, server: example.com, request: \"GET /api/data HTTP/1.1\""
        ]),
        ("2026/02/14 00:15:45", "[info]", "Successfully reloaded configuration", []),
    ]
    
    _write_log_files(log_dir, "103", entries)


def generate_rfc3339_format(base_dir: Path):
    """Генерирует логи в формате RFC3339 с временной зоной: 2026-02-14T09:23:04+03:00"""
    log_dir = base_dir / "rfc3339_format" / "instance_104"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    entries = [
        ("2026-02-13T23:50:00+03:00", "INFO", "Application started", []),
        ("2026-02-13T23:55:30+03:00", "WARNING", "High CPU usage detected (92%)", []),
        ("2026-02-14T00:05:15+03:00", "ERROR", "Database connection lost", [
            "org.postgresql.util.PSQLException: Connection to localhost:5432 refused",
            "\tat org.postgresql.core.v3.ConnectionFactoryImpl.openConnectionInternal(ConnectionFactoryImpl.java:312)"
        ]),
        ("2026-02-14T00:10:22+03:00", "ERROR", "Failed to process payment", [
            "com.payment.GatewayException: Invalid API key",
            "\tat com.payment.Gateway.validate(Gateway.java:78)"
        ]),
        ("2026-02-14T00:15:45+03:00", "INFO", "Scheduled task completed", []),
    ]
    
    _write_log_files(log_dir, "104", entries)


def generate_custom_format(base_dir: Path):
    """Генерирует логи в кастомном формате: [2026-02-14 09:23:04]"""
    log_dir = base_dir / "custom_format" / "instance_105"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    entries = [
        ("[2026-02-13 23:50:00]", "DEBUG", "Loading configuration from /etc/app/config.yaml", []),
        ("[2026-02-13 23:55:30]", "WARN", "Deprecated API endpoint called: /v1/old-endpoint", []),
        ("[2026-02-14 00:05:15]", "ERROR", "File upload failed: disk quota exceeded", [
            "Traceback (most recent call last):",
            "  File \"uploader.py\", line 120, in save_file",
            "    raise DiskQuotaExceededError(\"User quota: 100MB\")",
            "DiskQuotaExceededError: User quota: 100MB"
        ]),
        ("[2026-02-14 00:10:22]", "ERROR", "Authentication failed for user 'admin'", [
            "InvalidCredentialsError: Password mismatch",
            "IP: 192.168.1.50, Attempt: 3/5"
        ]),
        ("[2026-02-14 00:15:45]", "INFO", "Backup completed successfully", []),
    ]
    
    _write_log_files(log_dir, "105", entries)


def _write_log_files(log_dir: Path, instance_id: str, entries: list, is_syslog: bool = False):
    """
    Записывает логи в файлы: .log, _warning.log, _error.log
    
    Parameters
    ----------
    log_dir : Path
        Директория для файлов логов
    instance_id : str
        ID экземпляра (для имени файла)
    entries : list
        Список записей в формате (время, уровень, сообщение, трейсбек)
    is_syslog : bool
        Флаг для особой обработки syslog формата
    """
    # Основные файлы
    all_log = log_dir / f"instance {instance_id}.log"
    warn_log = log_dir / f"instance {instance_id}_warning.log"
    error_log = log_dir / f"instance {instance_id}_error.log"
    
    # Ротированные файлы (для проверки обработки ротации)
    rotated_all = log_dir / f"instance {instance_id}.log.2026-02-13"
    rotated_error = log_dir / f"instance {instance_id}_error.log.1"
    
    # Собираем содержимое для каждого файла
    all_lines = []
    warn_lines = []
    error_lines = []
    
    for time_str, level, msg, traceback_lines in entries:
        # Для syslog формата время уже включено в сообщение
        if is_syslog:
            base_line = msg  # msg уже содержит полную строку с временем
        else:
            base_line = f"{time_str} - {level} - {msg}"
        
        # Формируем полную запись
        full_entry = [base_line]
        if traceback_lines:
            full_entry.extend(traceback_lines)
        full_entry.append("")  # Пустая строка между записями
        
        # Добавляем во все файлы
        all_lines.extend(full_entry)
        
        # В файл предупреждений: WARNING и ERROR
        if "WARN" in level or "ERROR" in level or "CRITICAL" in level:
            warn_lines.extend(full_entry)
        
        # В файл ошибок: только ERROR и выше
        if "ERROR" in level or "CRITICAL" in level:
            error_lines.extend(full_entry)
    
    # Записываем файлы
    all_log.write_text("\n".join(all_lines), encoding="utf-8")
    warn_log.write_text("\n".join(warn_lines), encoding="utf-8")
    error_log.write_text("\n".join(error_lines), encoding="utf-8")
    
    # Создаём ротированные файлы (копируем часть записей)
    if len(all_lines) > 5:
        rotated_all.write_text("\n".join(all_lines[:3]), encoding="utf-8")
    if len(error_lines) > 3:
        rotated_error.write_text("\n".join(error_lines[:2]), encoding="utf-8")


def generate_config_files(base_dir: Path):
    """Генерирует примеры конфигурационных файлов для тестирования."""
    configs = {
        "config_default.yaml": {
            "date": "2026-02-14",
            "time": "00:00:00",
            "end_time": "00:12:00",
            "level": "error",
            "input": str(base_dir / "default_format"),
            "output": "test_output/default_errors.txt",
            "mlength": 10
        },
        "config_syslog.yaml": {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": "00:00:00",
            "level": "error",
            "input": str(base_dir / "syslog_format"),
            "output": "test_output/syslog_errors.txt",
            "timestamp_preset": "syslog"
        },
        "config_iso8601.yaml": {
            "datetime": "2026-02-14_00:00:00",
            "end_datetime": "2026-02-14_00:12:00",
            "level": "error",
            "input": str(base_dir / "iso8601_format"),
            "output": "test_output/iso8601_errors.txt",
            "timestamp_preset": "iso8601"
        },
        "config_custom.yaml": {
            "date": "2026-02-14",
            "time": "00:00:00",
            "level": "all",
            "input": str(base_dir / "custom_format"),
            "output": "test_output/custom_all.txt",
            "timestamp_pattern": "^\\[\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}\\]",
            "timestamp_format": "[%Y-%m-%d %H:%M:%S]"
        },
        "config_nginx.json": {
            "date": "2026-02-14",
            "time": "00:05:00",
            "end_time": "00:11:00",
            "level": "error",
            "input": str(base_dir / "nginx_format"),
            "output": "test_output/nginx_errors.txt",
            "timestamp_preset": "nginx"
        }
    }
    
    config_dir = base_dir / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    import yaml
    import json
    
    for filename, config in configs.items():
        filepath = config_dir / filename
        if filename.endswith(".yaml"):
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, sort_keys=False)
        elif filename.endswith(".json"):
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)


def main():
    """Основная функция генерации тестовых данных."""
    base_dir = Path("test_logs")
    base_dir.mkdir(exist_ok=True)
    
    print(f"Генерация тестовых логов в директорию: {base_dir.absolute()}")
    
    try:
        generate_default_format(base_dir)
        print("✓ Стандартный формат (default)")
        
        generate_syslog_format(base_dir)
        print("✓ Syslog формат")
        
        generate_iso8601_format(base_dir)
        print("✓ ISO8601 формат")
        
        generate_nginx_format(base_dir)
        print("✓ Nginx формат")
        
        generate_rfc3339_format(base_dir)
        print("✓ RFC3339 формат")
        
        generate_custom_format(base_dir)
        print("✓ Кастомный формат")
        
        generate_config_files(base_dir)
        print("✓ Конфигурационные файлы")
        
        print("\n✅ Генерация завершена успешно!")
        print(f"\nСтруктура созданных данных:")
        print(f"  {base_dir}/")
        print(f"    ├── default_format/")
        print(f"    ├── syslog_format/")
        print(f"    ├── iso8601_format/")
        print(f"    ├── nginx_format/")
        print(f"    ├── rfc3339_format/")
        print(f"    ├── custom_format/")
        print(f"    └── configs/")
        print(f"\nПримеры использования:")
        print(f"  # Тест стандартного формата")
        print(f"  collect_log -c test_logs/configs/config_default.yaml")
        print(f"\n  # Тест syslog формата")
        print(f"  collect_log -c test_logs/configs/config_syslog.yaml")
        print(f"\n  # Тест кастомного формата")
        print(f"  collect_log -c test_logs/configs/config_custom.yaml")
        print(f"\n  # Тест с явным указанием параметров")
        print(f"  collect_log --date 2026-02-14 --time 00:00:00 --end-time 00:12:00 \\")
        print(f"              --level error --input test_logs/nginx_format \\")
        print(f"              --timestamp-preset nginx -o /tmp/nginx_test.txt")
        
    except Exception as e:
        print(f"\n❌ Ошибка при генерации: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
# sysadmin_core/logging_audit.py
"""
Модуль для логирования и аудита действий в приложении.

Особенности:
- Логирование в консоль, файл и базу данных SQLite.
- Использование RotatingFileHandler для ротации лог-файлов.
- Маскирование чувствительных данных (паролей) в логах.
"""
import logging
import logging.handlers
import sqlite3
import os
import re
from typing import Optional

DB_DIR = "db"
AUDIT_DB_PATH = os.path.join(DB_DIR, "audit.db")
LOG_DIR = "logs"
LOG_FILE_PATH = os.path.join(LOG_DIR, "sysadmin_assistant.log")

class AuditLogger:
    """
    Обеспечивает комплексное логирование действий пользователя.
    """
    def __init__(self, logger_name: str = "SysAdminAudit", db_path: str = AUDIT_DB_PATH):
        """
        Инициализирует логгер.

        Args:
            logger_name: Имя для экземпляра логгера.
            db_path: Путь к файлу базы данных аудита.
        """
        self._ensure_dirs()
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        # Предотвращение дублирования обработчиков при повторной инициализации
        if not self.logger.handlers:
            # 1. Консольный обработчик
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            
            # 2. Файловый обработчик с ротацией
            # 1MB на файл, храним 5 старых файлов
            file_handler = logging.handlers.RotatingFileHandler(
                LOG_FILE_PATH, maxBytes=1024*1024, backupCount=5, encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - User: %(user)s - Intent: %(intent)s - Params: %(params)s - Result: %(result)s'))
            
            # 3. Обработчик для записи в SQLite
            self.db_path = db_path
            self._db_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._db_cursor = self._db_conn.cursor()
            self._create_audit_table()
            db_handler = self.SQLiteHandler(self)

            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
            self.logger.addHandler(db_handler)
        
        print("AuditLogger initialized.")

    def _ensure_dirs(self):
        """Убеждается, что директории для БД и логов существуют."""
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)

    def _create_audit_table(self):
        """Создает таблицу для логов аудита, если она не существует."""
        self._db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT,
                username TEXT,
                intent TEXT,
                params TEXT,
                result TEXT,
                message TEXT
            )
        """)
        self._db_conn.commit()

    def _mask_passwords(self, message: str) -> str:
        """
        Маскирует пароли и другие чувствительные данные в строке.
        """
        # Маскирует 'password': 'some_value' -> 'password': '***'
        message = re.sub(r"(['\"]password['\"]:\s*['\"])(.*?)(['\"])", r"\1***\3", message, flags=re.IGNORECASE)
        # Маскирует кортежи ('admin', 'pass123') -> ('admin', '***')
        message = re.sub(r"(\(\s*['\"].*?['\"]\s*,\s*['\"])(.*?)(['\"]\s*\))", r"\1***\3", message)
        return message

    def log(self, level: int, user: str, intent: Optional[str], params: Optional[dict], result: str):
        """
        Основной метод для записи лога.

        Args:
            level: Уровень логирования (например, logging.INFO).
            user: Имя пользователя, выполнившего действие.
            intent: Выполненный интент.
            params: Параметры, с которыми был выполнен интент.
            result: Результат выполнения (успех, ошибка, вывод команды).
        """
        params_str = self._mask_passwords(str(params))
        result_str = self._mask_passwords(result)
        
        extra_info = {
            "user": user,
            "intent": str(intent),
            "params": params_str,
            "result": result_str,
        }
        message = f"User '{user}' executed '{intent}' with result: {result_str[:100]}..."
        self.logger.log(level, self._mask_passwords(message), extra=extra_info)

    def info(self, user: str, intent: str, params: dict, result: str):
        self.log(logging.INFO, user, intent, params, result)

    def warning(self, user: str, intent: str, params: dict, result: str):
        self.log(logging.WARNING, user, intent, params, result)

    def error(self, user: str, intent: str, params: dict, result: str):
        self.log(logging.ERROR, user, intent, params, result)

    def close(self):
        """Закрывает соединение с базой данных аудита."""
        if self._db_conn:
            self._db_conn.close()
            print("AuditLogger database connection closed.")

    class SQLiteHandler(logging.Handler):
        """
        Пользовательский обработчик для записи логов в базу данных SQLite.
        """
        def __init__(self, logger_instance: 'AuditLogger'):
            super().__init__()
            self.logger_instance = logger_instance

        def emit(self, record):
            # Маскируем сообщение еще раз на всякий случай
            message = self.logger_instance._mask_passwords(self.format(record))
            
            # Получаем данные из 'extra'
            user = getattr(record, 'user', 'system')
            intent = getattr(record, 'intent', 'N/A')
            params = getattr(record, 'params', '{}')
            result = getattr(record, 'result', 'N/A')
            
            try:
                cursor = self.logger_instance._db_cursor
                conn = self.logger_instance._db_conn
                cursor.execute("""
                    INSERT INTO audit_log (level, username, intent, params, result, message)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (record.levelname, user, intent, str(params), str(result), message))
                conn.commit()
            except Exception as e:
                # В случае ошибки выводим в консоль, чтобы не потерять лог
                print(f"CRITICAL: Failed to write to audit database: {e}")


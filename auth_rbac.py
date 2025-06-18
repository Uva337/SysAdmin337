# sysadmin_core/auth_rbac.py
"""
Модуль для аутентификации пользователей и управления доступом на основе ролей (RBAC).

Использует:
- SQLite для хранения данных пользователей.
- bcrypt для хэширования паролей.
- cryptography (AES-256) для шифрования дополнительных данных.
"""
import sqlite3
import os
import bcrypt
from enum import Enum
from typing import Optional, Tuple
from cryptography.fernet import Fernet

DB_DIR = "db"
AUTH_DB_PATH = os.path.join(DB_DIR, "auth.db")

class Role(Enum):
    """Перечисление для ролей пользователей."""
    OPERATOR = "operator"
    ADMIN = "admin"

class AuthManager:
    """
    Управляет пользователями, аутентификацией и проверкой прав доступа.
    """
    def __init__(self, db_path: str = AUTH_DB_PATH, secret_key: Optional[bytes] = None):
        """
        Инициализирует менеджер аутентификации.

        Args:
            db_path: Путь к файлу базы данных SQLite.
            secret_key: Ключ для шифрования (32-байтный). Если не предоставлен,
                        генерируется и сохраняется новый.
        """
        self.db_path = db_path
        self._ensure_db_dir()
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._create_table()

        # Управление ключом шифрования
        key_file = os.path.join(DB_DIR, "secret.key")
        if secret_key:
            self.fernet = Fernet(secret_key)
        elif os.path.exists(key_file):
            with open(key_file, "rb") as f:
                self.fernet = Fernet(f.read())
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            self.fernet = Fernet(key)
            print("New secret key generated and saved.")
        
        self._add_default_user_if_needed()
        print("AuthManager initialized.")
    
    def _ensure_db_dir(self):
        """Убеждается, что директория для БД существует."""
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)
            print(f"Directory '{DB_DIR}' created.")

    def _create_table(self):
        """Создает таблицу пользователей, если она не существует."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                encrypted_data BLOB
            )
        """)
        self.conn.commit()

    def _add_default_user_if_needed(self):
        """Добавляет пользователя admin по умолчанию, если в БД нет пользователей."""
        self.cursor.execute("SELECT COUNT(*) FROM users")
        if self.cursor.fetchone()[0] == 0:
            print("No users found. Creating default 'admin' user...")
            self.add_user("admin", "password123", Role.ADMIN, {"info": "Default administrator account"})
            print("Default user 'admin' with password 'password123' created.")

    def add_user(self, username: str, password: str, role: Role, extra_data: Optional[dict] = None):
        """
        Добавляет нового пользователя в базу данных.

        Args:
            username: Имя пользователя.
            password: Пароль в открытом виде.
            role: Роль пользователя (объект Role).
            extra_data: Дополнительные данные для шифрования.
        """
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        encrypted_data = None
        if extra_data:
            data_str = str(extra_data)
            encrypted_data = self.fernet.encrypt(data_str.encode('utf-8'))
            
        try:
            self.cursor.execute(
                "INSERT INTO users (username, password_hash, role, encrypted_data) VALUES (?, ?, ?, ?)",
                (username, password_hash.decode('utf-8'), role.value, encrypted_data)
            )
            self.conn.commit()
            print(f"User '{username}' added with role '{role.value}'.")
        except sqlite3.IntegrityError:
            print(f"User '{username}' already exists.")

    def verify_user(self, username: str, password: str) -> Optional[Role]:
        """
        Проверяет логин и пароль пользователя.

        Args:
            username: Имя пользователя.
            password: Пароль для проверки.

        Returns:
            Роль пользователя (Role) в случае успеха, иначе None.
        """
        self.cursor.execute("SELECT password_hash, role FROM users WHERE username = ?", (username,))
        result = self.cursor.fetchone()
        
        if result:
            password_hash, role_str = result
            if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                print(f"User '{username}' authenticated successfully.")
                return Role(role_str)
        
        print(f"Authentication failed for user '{username}'.")
        return None

    def is_allowed(self, role: Role, required_role: Role) -> bool:
        """
        Проверяет, имеет ли данная роль достаточные права.
        Предполагается, что ADMIN имеет больше прав, чем OPERATOR.

        Args:
            role: Текущая роль пользователя.
            required_role: Требуемая роль для выполнения действия.

        Returns:
            True, если доступ разрешен, иначе False.
        """
        if role == Role.ADMIN:
            return True
        if role == Role.OPERATOR and required_role == Role.OPERATOR:
            return True
        return False

    def get_user_data(self, username: str) -> Optional[dict]:
        """
        Получает и расшифровывает дополнительные данные пользователя.
        """
        self.cursor.execute("SELECT encrypted_data FROM users WHERE username = ?", (username,))
        result = self.cursor.fetchone()

        if result and result[0]:
            try:
                decrypted_data_bytes = self.fernet.decrypt(result[0])
                # Безопасное преобразование строки в dict
                data = eval(decrypted_data_bytes.decode('utf-8'))
                return data
            except Exception as e:
                print(f"Failed to decrypt or parse data for user '{username}': {e}")
        return None

    def close(self):
        """Закрывает соединение с базой данных."""
        if self.conn:
            self.conn.close()
            print("AuthManager database connection closed.")


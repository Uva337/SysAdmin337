# sysadmin_core/command_templates.py
"""
Модуль для управления шаблонами команд.

Содержит классы для описания параметров, интентов и загрузки
конфигурации из JSON-файла.
"""
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class ParamSpec:
    """
    Описывает спецификацию одного параметра для команды.

    Attributes:
        type: Тип параметра (например, 'ip', 'port', 'string', 'choice').
        required: Является ли параметр обязательным.
        default: Значение по умолчанию, если параметр не обязателен и не предоставлен.
        choices: Список возможных значений (для типа 'choice').
        example: Пример значения для подсказки пользователю.
    """
    type: str
    required: bool = False
    default: Optional[Any] = None
    choices: Optional[List[str]] = field(default=None)
    example: Optional[str] = field(default=None)


@dataclass
class IntentTemplate:
    """
    Описывает полный шаблон для одного интента.

    Attributes:
        intent: Уникальный идентификатор интента (например, "network.ping_host").
        description: Человекочитаемое описание интента.
        phrases: Список ключевых фраз для распознавания этого интента.
        params: Словарь спецификаций параметров, где ключ - имя параметра.
        templates: Словарь с шаблонами команд для разных ОС ('win', 'astro').
    """
    intent: str
    description: str = ""
    phrases: List[str] = field(default_factory=list)
    params: Dict[str, ParamSpec] = field(default_factory=dict)
    templates: Dict[str, str] = field(default_factory=dict)

class CommandTemplates:
    """
    Класс для загрузки, хранения и управления шаблонами команд из файла.
    """
    def __init__(self):
        """Инициализирует пустой контейнер для шаблонов."""
        self.intents: Dict[str, IntentTemplate] = {}
        print("CommandTemplates initialized.")

    def load_from_json(self, file_path: str) -> None:
        """
        Загружает определения интентов из JSON-файла.

        Args:
            file_path: Путь к JSON-файлу с определениями команд.
        
        Raises:
            FileNotFoundError: Если файл не найден.
            json.JSONDecodeError: Если файл имеет неверный JSON-формат.
            KeyError: Если в JSON отсутствуют обязательные поля.
        """
        print(f"Attempting to load command templates from '{file_path}'...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.intents.clear()
            for intent_key, intent_data in data.items():
                params = {
                    name: ParamSpec(**spec)
                    for name, spec in intent_data.get("params", {}).items()
                }
                
                template = IntentTemplate(
                    intent=intent_key,
                    description=intent_data.get("description", ""),
                    phrases=intent_data.get("phrases", []),
                    params=params,
                    templates=intent_data.get("templates", {})
                )
                self.intents[intent_key] = template
            
            print(f"Successfully loaded {len(self.intents)} intent templates.")

        except FileNotFoundError:
            print(f"ERROR: Command definitions file not found at '{file_path}'")
            raise
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to decode JSON from '{file_path}': {e}")
            raise
        except (KeyError, TypeError) as e:
            print(f"ERROR: Invalid format in command definitions file: {e}")
            raise

    def get_intent_template(self, intent: str) -> Optional[IntentTemplate]:
        """
        Возвращает шаблон для указанного интента.

        Args:
            intent: Идентификатор интента.

        Returns:
            Объект IntentTemplate или None, если интент не найден.
        """
        return self.intents.get(intent)

    def render_command(self, intent: str, os_type: str, params: Dict[str, Any]) -> str:
        """
        Генерирует финальную команду из шаблона, подставляя параметры.

        Args:
            intent: Идентификатор интента.
            os_type: Тип операционной системы ('win' или 'astro').
            params: Словарь с параметрами для подстановки.

        Returns:
            Готовая к выполнению строка команды.
            
        Raises:
            KeyError: Если интент или шаблон для ОС не найден.
            ValueError: Если отсутствуют обязательные параметры.
        """
        template_obj = self.get_intent_template(intent)
        if not template_obj:
            raise KeyError(f"Intent '{intent}' not found in templates.")

        command_template = template_obj.templates.get(os_type)
        if not command_template:
            raise KeyError(f"Command template for OS '{os_type}' not found for intent '{intent}'.")

        # Заполняем параметры значениями по умолчанию, если они не предоставлены
        final_params = {}
        for param_name, param_spec in template_obj.params.items():
            if param_name in params:
                final_params[param_name] = params[param_name]
            elif param_spec.default is not None:
                final_params[param_name] = param_spec.default
            elif param_spec.required:
                raise ValueError(f"Missing required parameter '{param_name}' for intent '{intent}'.")
            else:
                # Для необязательных параметров без default подставляем пустую строку,
                # чтобы .format не выдавал ошибку.
                final_params[param_name] = ""

        try:
            return command_template.format(**final_params)
        except KeyError as e:
            raise ValueError(f"Parameter '{e}' is required for template but was not provided.")

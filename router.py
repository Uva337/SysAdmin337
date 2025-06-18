# sysadmin_core/router.py
"""
Модуль содержит класс IntentRouter для маршрутизации интентов.
"""
from typing import Callable, Dict, Any, Optional

class IntentRouter:
    """
    Маршрутизатор для сопоставления строковых интентов с функциями-обработчиками.

    Позволяет регистрировать обработчики для интентов и вызывать их
    с передачей параметров.
    """
    def __init__(self):
        """Инициализирует пустой словарь маршрутов."""
        self._routes: Dict[str, Callable] = {}
        print("IntentRouter initialized.")

    def register(self, intent: str, handler: Callable) -> None:
        """
        Регистрирует функцию-обработчик для заданного интента.

        Args:
            intent: Строковый идентификатор интента (например, "network.ping").
            handler: Функция, которая будет вызвана для обработки интента.
        
        Raises:
            ValueError: Если интент уже зарегистрирован.
        """
        if intent in self._routes:
            raise ValueError(f"Intent '{intent}' is already registered.")
        self._routes[intent] = handler
        print(f"Handler for intent '{intent}' registered.")

    def route(self, intent: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Находит и вызывает обработчик для заданного интента.

        Args:
            intent: Интент для обработки.
            params: Словарь с параметрами для передачи в обработчик.

        Returns:
            Результат выполнения функции-обработчика.

        Raises:
            KeyError: Если обработчик для интента не найден.
        """
        if params is None:
            params = {}
            
        handler = self._routes.get(intent)
        if not handler:
            raise KeyError(f"No handler registered for intent '{intent}'.")
        
        print(f"Routing intent '{intent}' with params: {params}")
        return handler(intent=intent, params=params)


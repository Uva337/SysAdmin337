# sysadmin_core/plugin_api.py
"""
Модуль для реализации системы плагинов.
"""
import importlib
import os
from typing import List, Type

class PluginBase:
    """
    Базовый класс для всех плагинов.
    
    Каждый плагин должен наследоваться от этого класса и реализовывать
    свои методы.
    """
    def __init__(self, app_context=None):
        """
        Инициализация плагина.
        
        Args:
            app_context: Контекст приложения, который может содержать
                         ссылки на основные компоненты (роутер, логгер и т.д.).
        """
        self.app_context = app_context
        print(f"Plugin '{self.__class__.__name__}' initialized.")

    def activate(self):
        """Метод, вызываемый при активации плагина."""
        raise NotImplementedError("Each plugin must implement the 'activate' method.")

    def deactivate(self):
        """Метод, вызываемый при деактивации плагина."""
        raise NotImplementedError("Each plugin must implement the 'deactivate' method.")

class PluginManager:
    """
    Управляет жизненным циклом плагинов: загрузкой, активацией и перезагрузкой.
    """
    def __init__(self, plugin_dir: str = "plugins", app_context=None):
        """
        Инициализация менеджера плагинов.
        
        Args:
            plugin_dir: Директория, в которой находятся плагины.
            app_context: Контекст приложения для передачи в плагины.
        """
        self.plugin_dir = plugin_dir
        self.app_context = app_context
        self.plugins: List[PluginBase] = []
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)
            print(f"Plugin directory '{self.plugin_dir}' created.")

    def load_plugins(self):
        """
        Сканирует директорию плагинов, импортирует их и активирует.
        """
        print(f"Loading plugins from '{self.plugin_dir}'...")
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = f"{self.plugin_dir}.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    for item_name in dir(module):
                        item = getattr(module, item_name)
                        if isinstance(item, Type) and issubclass(item, PluginBase) and item is not PluginBase:
                            plugin_instance = item(self.app_context)
                            self.plugins.append(plugin_instance)
                            plugin_instance.activate()
                            print(f"Plugin '{item.__name__}' activated.")
                except Exception as e:
                    print(f"Failed to load or activate plugin from '{filename}': {e}")
        print(f"Finished loading plugins. Total active: {len(self.plugins)}.")

    def reload_plugins(self):
        """
        Деактивирует все текущие плагины и загружает их заново.
        """
        print("Reloading all plugins...")
        # Деактивация
        for plugin in self.plugins:
            try:
                plugin.deactivate()
                print(f"Plugin '{plugin.__class__.__name__}' deactivated.")
            except Exception as e:
                print(f"Error deactivating plugin '{plugin.__class__.__name__}': {e}")
        
        self.plugins.clear()
        
        # Загрузка заново
        self.load_plugins()

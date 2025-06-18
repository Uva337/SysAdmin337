# sysadmin_core/__init__.py
"""
Инициализирующий файл для пакета sysadmin_core.

Этот файл делает основные классы пакета доступными для импорта
из `sysadmin_core`, упрощая их использование в других частях приложения.
"""

from .router import IntentRouter
from .command_templates import CommandTemplates, IntentTemplate, ParamSpec
from .plugin_api import PluginBase, PluginManager
from .macro_engine import MacroEngine
from .auth_rbac import AuthManager, Role
from .logging_audit import AuditLogger
from .utils import AdvancedNLUParser

__all__ = [
    'IntentRouter',
    'CommandTemplates',
    'IntentTemplate',
    'ParamSpec',
    'PluginBase',
    'PluginManager',
    'MacroEngine',
    'AuthManager',
    'Role',
    'AuditLogger',
    'AdvancedNLUParser',
]

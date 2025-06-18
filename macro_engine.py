# sysadmin_core/macro_engine.py
"""
Модуль для реализации движка макросов.
Позволяет записывать и воспроизводить последовательности действий.
"""

from typing import List, Dict, Any, Callable
import time
import json

class MacroEngine:
    """
    Класс для записи и воспроизведения макросов (последовательностей команд).
    """
    def __init__(self, action_executor: Callable):
        """
        Инициализация движка макросов.

        Args:
            action_executor: Функция, которая будет выполнять одно действие.
                             Она должна принимать `intent` и `params`.
        """
        self.is_recording: bool = False
        self.recorded_macro: List[Dict[str, Any]] = []
        self.action_executor = action_executor
        print("MacroEngine initialized.")

    def start_recording(self):
        """Начинает запись макроса."""
        if self.is_recording:
            print("Already recording a macro.")
            return
        self.is_recording = True
        self.recorded_macro = []
        print("Macro recording started.")

    def stop_recording(self):
        """Останавливает запись макроса."""
        if not self.is_recording:
            print("Not currently recording.")
            return
        self.is_recording = False
        print(f"Macro recording stopped. {len(self.recorded_macro)} actions recorded.")

    def record_action(self, intent: str, params: Dict[str, Any]):
        """
        Записывает одно действие в текущий макрос, если запись активна.

        Args:
            intent: Интент действия.
            params: Параметры действия.
        """
        if self.is_recording:
            action = {
                "timestamp": time.time(),
                "intent": intent,
                "params": params
            }
            self.recorded_macro.append(action)
            print(f"Action recorded: {intent}")

    def play_macro(self, macro: List[Dict[str, Any]]):
        """
        Воспроизводит заданный макрос.

        Args:
            macro: Список действий для воспроизведения.
        """
        if self.is_recording:
            print("Cannot play a macro while recording.")
            return

        print(f"Playing macro with {len(macro)} actions...")
        for i, action in enumerate(macro):
            intent = action.get("intent")
            params = action.get("params")
            if not intent or not isinstance(params, dict):
                print(f"Skipping invalid action at index {i}.")
                continue
            
            print(f"Executing action {i+1}/{len(macro)}: {intent} with params {params}")
            try:
                self.action_executor(intent=intent, params=params)
                # Можно добавить задержку между действиями
                time.sleep(0.5)
            except Exception as e:
                print(f"Error executing action {intent}: {e}")
                # Можно добавить логику прерывания макроса при ошибке
                break
        print("Macro playback finished.")

    def save_macro_to_file(self, file_path: str):
        """
        Сохраняет записанный макрос в JSON-файл.

        Args:
            file_path: Путь к файлу для сохранения.
        """
        if self.is_recording:
            print("Stop recording before saving the macro.")
            return
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.recorded_macro, f, indent=4, ensure_ascii=False)
        print(f"Macro saved to '{file_path}'.")

    def load_macro_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Загружает макрос из JSON-файла.

        Args:
            file_path: Путь к файлу с макросом.

        Returns:
            Список действий, представляющий макрос.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            macro = json.load(f)
        print(f"Macro loaded from '{file_path}'.")
        return macro

# sysadmin_core/utils.py
"""
Модуль содержит NLU-парсер и другие вспомогательные утилиты.
"""
import re
from typing import Dict, Any, Optional, List

# --- Опциональные зависимости ---
try:
    from pymorphy2 import MorphAnalyzer
    PYMORPHY_AVAILABLE = True
except ImportError:
    PYMORPHY_AVAILABLE = False
    print("Warning: pymorphy2 not found. Lemmatization will be disabled.")

try:
    from rapidfuzz import process, fuzz
    RAPIDFuzz_AVAILABLE = True
except ImportError:
    RAPIDFuzz_AVAILABLE = False
    print("Warning: rapidfuzz not found. Fuzzy search will be disabled.")

# --- Основной класс NLU ---

class AdvancedNLUParser:
    """
    Класс для разбора команд на естественном языке.
    - Лемматизирует текст (если доступен pymorphy2).
    - Использует нечеткий поиск для определения интента (если доступен rapidfuzz).
    - Извлекает параметры с помощью регулярных выражений.
    """
    
    # Расширенные шаблоны для извлечения параметров
    PARAM_REGEX = {
        "ip": r"\b\d{1,3}(?:\.\d{1,3}){3}\b",
        "ip_mask": r"(?:\b\d{1,3}(?:\.\d{1,3}){3}\b|/\d{1,2}\b)",
        "hostname": r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,63}\b",
        "hostname_or_ip": r"\b(?:\d{1,3}(?:\.\d{1,3}){3}|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,63})\b",
        "port": r"\b\d{1,5}\b",
        "pid_or_name": r"\b(?:[a-zA-Z.-][a-zA-Z0-9.-]*|\d+)\b",
        "username": r"(?:user|пользовател[ья])\s+([a-zA-Z0-9_.-]+)",
        "filepath": r"([a-zA-Z]:(?:\\(?:[^\\/:*?\"<>|\r\n]+))+|/(?:[^/]+/)*[^/]+)",
        "password": r"(?:пароль|password)\s*[:=]?\s*['\"]?(\S+)['\"]?",
        "number": r"\b\d+\b",
        "string": r"['\"]([^'\"]+)['\"]", # Для явных строк в кавычках
    }
    
    def __init__(self, command_templates):
        """
        Инициализирует парсер.

        Args:
            command_templates (CommandTemplates): Экземпляр класса с загруженными
                                                  шаблонами команд.
        """
        self.command_templates = command_templates
        self.morph: Optional[MorphAnalyzer] = MorphAnalyzer() if PYMORPHY_AVAILABLE else None
        
        # Подготовка данных для нечеткого поиска
        self.intent_phrases_map: Dict[str, str] = {}
        self.prepare_intent_data()
        print("AdvancedNLUParser initialized.")

    def prepare_intent_data(self):
        """Готовит словарь 'фраза -> интент' для быстрого поиска."""
        self.intent_phrases_map = {}
        for intent, template in self.command_templates.intents.items():
            for phrase in template.phrases:
                lemmatized_phrase = self._lemmatize_text(phrase)
                # Проверяем на дубликаты, чтобы избежать перезаписи
                if lemmatized_phrase not in self.intent_phrases_map:
                    self.intent_phrases_map[lemmatized_phrase] = intent
                else:
                    print(f"Warning: Duplicate lemmatized phrase '{lemmatized_phrase}' for intent '{intent}'. "
                          f"It's already mapped to '{self.intent_phrases_map[lemmatized_phrase]}'.")
        print(f"Prepared {len(self.intent_phrases_map)} unique phrases for NLU matching.")

    def _lemmatize_text(self, text: str) -> str:
        """
        Приводит слова в тексте к их нормальной форме (лемме).
        """
        if not self.morph:
            return text.lower()
        
        words = re.findall(r'[a-zа-я0-9]+', text.lower())
        lemmas = [self.morph.parse(word)[0].normal_form for word in words]
        return " ".join(lemmas)

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Основной метод, выполняющий полный разбор текста команды.
        """
        lemmatized_input = self._lemmatize_text(text)
        
        intent = self._find_intent(lemmatized_input)
        
        if not intent:
            return {"intent": None, "params": {}}
            
        params = self._extract_params(text, intent)
        
        # Специальная логика для команд, где параметр может быть частью фразы
        if intent == "network.toggle_firewall":
            if "включи" in text or " on" in text:
                params['state'] = 'on'
            elif "выключи" in text or " off" in text:
                params['state'] = 'off'
        
        return {"intent": intent, "params": params}

    def _find_intent(self, lemmatized_input: str) -> Optional[str]:
        """
        Находит наиболее подходящий интент для лемматизированного ввода.
        """
        if not RAPIDFuzz_AVAILABLE:
            # Простой, но менее надежный поиск
            for phrase, intent in self.intent_phrases_map.items():
                if all(word in lemmatized_input for word in phrase.split()):
                    return intent
            return None

        # Нечеткий поиск с высоким порогом
        choices = list(self.intent_phrases_map.keys())
        # Используем WRatio, который хорошо справляется с разным порядком слов
        best_match = process.extractOne(lemmatized_input, choices, scorer=fuzz.WRatio, score_cutoff=88)
        
        if best_match:
            best_phrase, score, _ = best_match
            print(f"NLU match: '{best_phrase}' with score {score:.2f} for input '{lemmatized_input}'")
            return self.intent_phrases_map[best_phrase]
            
        print(f"NLU: No intent found with sufficient score for '{lemmatized_input}'")
        return None

    def _extract_params(self, text: str, intent: str) -> Dict[str, Any]:
        """
        Извлекает параметры из текста на основе спецификации интента.
        """
        params: Dict[str, Any] = {}
        template = self.command_templates.get_intent_template(intent)
        
        if not template:
            return params
            
        text_to_parse = text
        for param_name, param_spec in template.params.items():
            regex = self.PARAM_REGEX.get(param_spec.type)
            if not regex:
                continue

            match = re.search(regex, text_to_parse, re.IGNORECASE)
            if match:
                # Если у регулярки есть группа, берем ее, иначе - все совпадение
                value = match.group(1) if match.groups() else match.group(0)
                params[param_name] = value
                # Удаляем найденный параметр из строки, чтобы не найти его снова
                text_to_parse = text_to_parse[:match.start()] + text_to_parse[match.end():]

        print(f"Extracted params for intent '{intent}': {params}")
        return params

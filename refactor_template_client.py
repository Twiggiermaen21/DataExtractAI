import re

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\template\service.py', 'r', encoding='utf-8') as f:
    code = f.read()

client_code = '''import json
import logging
from typing import Any, Dict, Mapping
from app.prompts.template_prompts import TEMPLATE_FIELD_RESPONSE_SCHEMA, TEMPLATE_ANALYSIS_SYSTEM_PROMPT
from .exceptions import InvalidLLMResponseError
from .http_utils import _strip_json_code_fence

log = logging.getLogger(__name__)

class TemplateLLMClient:
    def __init__(self, api_url: str, model_name: str, max_tokens: int):
        self.api_url = api_url
        self.model_name = model_name
        self.max_tokens = max_tokens

    def build_payload(self, source_text: str) -> Dict[str, Any]:
        return {
            'model': self.model_name,
            'messages': [
                {'role': 'system', 'content': TEMPLATE_ANALYSIS_SYSTEM_PROMPT},
                {'role': 'user', 'content': source_text},
            ],
            'temperature': 0.0,
            'max_tokens': self.max_tokens,
            'response_format': TEMPLATE_FIELD_RESPONSE_SCHEMA,
            'stream': False,
        }

    def read_llm_payload(self, response_body: bytes) -> Mapping[str, Any]:
        try:
            body_text = response_body.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise InvalidLLMResponseError('Odpowiedz LLM nie jest poprawnym UTF-8') from exc

        try:
            parsed = json.loads(body_text)
        except json.JSONDecodeError as exc:
            raise InvalidLLMResponseError('Odpowiedz LLM nie jest poprawnym JSON') from exc

        if not isinstance(parsed, dict) or 'choices' not in parsed:
            raise InvalidLLMResponseError('Odpowiedz LLM nie zawiera oczekiwanej struktury choices')

        choices = parsed.get('choices')
        if not isinstance(choices, list) or not choices:
            raise InvalidLLMResponseError('Odpowiedz LLM ma pusta tablice choices')

        first_choice = choices[0]
        if not isinstance(first_choice, dict) or 'message' not in first_choice:
            raise InvalidLLMResponseError('Odpowiedz LLM nie ma obiektu message w pierwszym wyborze')

        message = first_choice.get('message')
        if not isinstance(message, dict) or 'content' not in message:
            raise InvalidLLMResponseError('Odpowiedz LLM nie ma pola content w message')

        content = message.get('content')
        if not isinstance(content, str):
            raise InvalidLLMResponseError('Pole content w odpowiedzi LLM nie jest stringiem')

        stripped = _strip_json_code_fence(content)

        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise InvalidLLMResponseError('Pole content LLM nie jest poprawnym JSON') from exc

        if not isinstance(payload, dict):
            raise InvalidLLMResponseError('Pole content LLM nie zwraca glownego obiektu JSON')

        if 'fields' not in payload:
            raise InvalidLLMResponseError('Odpowiedz LLM nie zawiera klucza fields')

        return payload
'''

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\template\llm_client.py', 'w', encoding='utf-8') as f:
    f.write(client_code)

# Replace usage in service.py
code = code.replace("from app.prompts.template_prompts import TEMPLATE_FIELD_RESPONSE_SCHEMA, TEMPLATE_ANALYSIS_SYSTEM_PROMPT", "from .llm_client import TemplateLLMClient")
code = re.sub(r'    def _build_payload\(self.*?return payload', '', code, flags=re.DOTALL)
code = re.sub(r'    def _read_llm_payload\(self.*?return payload', '', code, flags=re.DOTALL)

# Delete the orphaned read_limited_response_body logic
code = re.sub(r'def _read_limited_response_body.*?return b\'\'\.join\(chunks\)\n', '', code, flags=re.DOTALL)

# Add client init
code = code.replace("self._api_url = api_url_arg", "self._api_url = api_url_arg\n        self._llm_client = TemplateLLMClient(self._api_url, self._model_name, self._llm_max_tokens)")

# Update analyze method to use client
code = code.replace("payload = self._build_payload(source_text)", "payload = self._llm_client.build_payload(source_text)")
code = code.replace("llm_payload = self._read_llm_payload(response_body)", "llm_payload = self._llm_client.read_llm_payload(response_body)")

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\template\service.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Updated template service to use LLMClient!")

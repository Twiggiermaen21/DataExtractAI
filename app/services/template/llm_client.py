import json
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
                {'role': 'user', 'content': json.dumps({'document_text': source_text}, ensure_ascii=False)},
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

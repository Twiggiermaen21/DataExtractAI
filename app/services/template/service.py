from __future__ import annotations

import io
import json
import logging
import os
import re
import unicodedata
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import requests

from app.dto.iusfully_template import (
    DTOValidationError,
    DetectedTemplateFieldDTO,
    TemplateAnalysisRequestDTO,
    TemplateAnalysisResponseDTO,
    TemplateFormFieldDTO,
)
from app.utils.ocr_utils import get_llm_api_url, llm_post, normalize_llm_api_url

from .exceptions import (
    TemplateAnalysisConfigurationError,
    LLMUnavailableError,
    LLMTimeoutError,
    LLMUpstreamError,
    InvalidLLMResponseError,
    UnprocessableTemplateFileError,
)
from .normalizers import _normalize_field_value, _source_replacement_expression
from decimal import InvalidOperation
from .http_utils import _strip_json_code_fence, _close_http_response, _is_stream_read_timeout, _read_limited_response_body

from .llm_client import TemplateLLMClient

from .parser import _positive_int_from_env, _positive_int_argument

log = logging.getLogger(__name__)

DEFAULT_LLM_TIMEOUT_SECONDS = 600
DEFAULT_LLM_MAX_TOKENS = 4000
DEFAULT_MAX_LLM_RESPONSE_BYTES = 1024 * 1024
MAX_DETECTED_FIELDS = 50

PLACEHOLDER_IN_TEXT_PATTERN = re.compile(r'\{\{[a-z][a-z0-9_]{0,63}\}\}')





def _read_limited_response_body(response: Any, max_bytes: int) -> bytes:
    headers = getattr(response, 'headers', {}) or {}
    declared_length = headers.get('Content-Length')
    if declared_length:
        try:
            if int(declared_length) > max_bytes:
                raise InvalidLLMResponseError('Odpowiedz LLM przekracza limit rozmiaru')
        except ValueError:
            pass
    if callable(getattr(response, 'iter_content', None)):
        body = bytearray()
        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            body.extend(chunk)
            if len(body) > max_bytes:
                raise InvalidLLMResponseError('Odpowiedz LLM przekracza limit rozmiaru')
        return bytes(body)
    content = getattr(response, 'content', None)
    if content is None:
        content = (getattr(response, 'text', '') or '').encode('utf-8')
    elif isinstance(content, str):
        content = content.encode('utf-8')
    if not isinstance(content, bytes):
        raise InvalidLLMResponseError('Odpowiedz LLM ma niepoprawny format binarny')
    if len(content) > max_bytes:
        raise InvalidLLMResponseError('Odpowiedz LLM przekracza limit rozmiaru')
    return content

class IusfullyTemplateAnalysisService:
    """Finds dynamic fields with an LLM and renders the template deterministically."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_tokens: Optional[int] = None,
        max_response_bytes: Optional[int] = None,
        post_func: Optional[Callable[..., Any]] = None,
    ):
        configured_url = api_url or get_llm_api_url()
        if not isinstance(configured_url, str) or not configured_url.strip():
            raise TemplateAnalysisConfigurationError(
                'LLM_API_URL nie jest skonfigurowany'
            )
        try:
            self.api_url = normalize_llm_api_url(configured_url)
        except ValueError as exc:
            raise TemplateAnalysisConfigurationError(str(exc)) from exc

        configured_model = model or os.environ.get('LLM_MODEL') or 'default'
        if not isinstance(configured_model, str) or not configured_model.strip():
            raise TemplateAnalysisConfigurationError('LLM_MODEL jest niepoprawny')
        self.model = configured_model.strip()

        if timeout_seconds is None:
            if os.environ.get('IUSFULLY_TEMPLATE_LLM_TIMEOUT_SECONDS', '').strip():
                self.timeout_seconds = _positive_int_from_env(
                    'IUSFULLY_TEMPLATE_LLM_TIMEOUT_SECONDS',
                    DEFAULT_LLM_TIMEOUT_SECONDS,
                )
            else:
                self.timeout_seconds = _positive_int_from_env(
                    'LLM_TIMEOUT_SECONDS',
                    DEFAULT_LLM_TIMEOUT_SECONDS,
                )
        else:
            self.timeout_seconds = _positive_int_argument(
                'timeout_seconds',
                timeout_seconds,
            )

        if max_tokens is None:
            self.max_tokens = _positive_int_from_env(
                'IUSFULLY_TEMPLATE_LLM_MAX_TOKENS',
                DEFAULT_LLM_MAX_TOKENS,
            )
        else:
            self.max_tokens = _positive_int_argument('max_tokens', max_tokens)

        if max_response_bytes is None:
            self.max_response_bytes = _positive_int_from_env(
                'IUSFULLY_TEMPLATE_MAX_LLM_RESPONSE_BYTES',
                DEFAULT_MAX_LLM_RESPONSE_BYTES,
            )
        else:
            self.max_response_bytes = _positive_int_argument(
                'max_response_bytes',
                max_response_bytes,
            )
        self.api_key = os.environ.get('LLM_API_KEY', '').strip()
        self._post = post_func or llm_post
        self._llm_client = TemplateLLMClient(self.api_url, self.model, self.max_tokens)

    def analyze(
        self,
        analysis_request: TemplateAnalysisRequestDTO,
    ) -> TemplateAnalysisResponseDTO:
        if PLACEHOLDER_IN_TEXT_PATTERN.search(analysis_request.source_text):
            raise UnprocessableTemplateFileError(
                'Dokument zawiera juz zarezerwowana skladnie {{placeholder}}'
            )

        payload = self._llm_client.build_payload(analysis_request.source_text)
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        log.info(
            'Iusfully template LLM request: chars=%s model=%s timeout=%s',
            len(analysis_request.source_text),
            self.model,
            self.timeout_seconds,
        )

        try:
            response = self._post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
                stream=True,
            )
        except requests.exceptions.Timeout as exc:
            raise LLMTimeoutError('Przekroczono czas oczekiwania na odpowiedz LLM') from exc
        except requests.exceptions.RequestException as exc:
            raise LLMUnavailableError('Nie mozna polaczyc sie z serwerem LLM') from exc

        response_headers = getattr(response, 'headers', {}) or {}
        log.info(
            'Iusfully template LLM response: status=%s declared_bytes=%s',
            response.status_code,
            response_headers.get('Content-Length'),
        )

        if response.status_code == 429 or response.status_code >= 500:
            _close_http_response(response)
            raise LLMUnavailableError('Serwer LLM jest chwilowo niedostepny')
        if response.status_code < 200 or response.status_code >= 300:
            _close_http_response(response)
            raise LLMUpstreamError('Serwer LLM odrzucil zadanie analizy')

        try:
            response_body = _read_limited_response_body(
                response,
                self.max_response_bytes,
            )
        except requests.exceptions.RequestException as exc:
            if _is_stream_read_timeout(exc):
                raise LLMTimeoutError(
                    'Przekroczono czas odczytu odpowiedzi LLM'
                ) from exc
            raise LLMUnavailableError('Polaczenie z LLM zostalo przerwane') from exc
        finally:
            _close_http_response(response)

        llm_payload = self._llm_client.read_llm_payload(response_body)
        detected_fields = self._validate_detected_fields(
            llm_payload,
            analysis_request.source_text,
        )
        response_dto = self._render_response(analysis_request, detected_fields)

        log.info(
            'Iusfully template analysis done: fields=%s template_chars=%s',
            len(response_dto.form_fields),
            len(response_dto.template_text),
        )
        return response_dto


    @staticmethod
    def _read_llm_payload(response_body: bytes) -> Mapping[str, Any]:
        try:
            response_payload = json.loads(response_body.decode('utf-8'))
            message = response_payload['choices'][0]['message']
            content = message.get('content')
            if content is None and isinstance(message.get('parsed'), Mapping):
                parsed = message['parsed']
            elif isinstance(content, Mapping):
                parsed = content
            elif isinstance(content, str):
                parsed = json.loads(_strip_json_code_fence(content))
            else:
                raise TypeError('Brak tekstowej odpowiedzi modelu')
        except (KeyError, IndexError, TypeError, ValueError, UnicodeDecodeError) as exc:
            raise InvalidLLMResponseError(
                'LLM zwrocil odpowiedz w niepoprawnym formacie'
            ) from exc

        if not isinstance(parsed, Mapping):
            raise InvalidLLMResponseError('Odpowiedz LLM musi byc obiektem JSON')
        return parsed

    @staticmethod
    def _validate_detected_fields(
        payload: Mapping[str, Any],
        source_text: str,
    ) -> List[DetectedTemplateFieldDTO]:
        if set(payload.keys()) != {'fields'} or not isinstance(payload.get('fields'), list):
            raise InvalidLLMResponseError('LLM zwrocil niepoprawny schemat odpowiedzi')
        if len(payload['fields']) > MAX_DETECTED_FIELDS:
            raise InvalidLLMResponseError('LLM zwrocil zbyt wiele pol szablonu')

        detected_fields: List[DetectedTemplateFieldDTO] = []
        seen_keys = set()
        source_to_key: Dict[str, str] = {}

        for raw_field in payload['fields']:
            try:
                field = DetectedTemplateFieldDTO.from_mapping(raw_field)
            except DTOValidationError as exc:
                raise InvalidLLMResponseError(
                    'LLM zwrocil niepoprawna definicje pola'
                ) from exc

            if field.key in seen_keys:
                raise InvalidLLMResponseError('LLM zwrocil zduplikowany klucz pola')
            seen_keys.add(field.key)

            normalized_fragments = []
            for fragment in field.source_fragments:
                if fragment not in source_text:
                    raise InvalidLLMResponseError(
                        'LLM wskazal fragment nieobecny w dokumencie'
                    )
                previous_key = source_to_key.get(fragment)
                if previous_key is not None and previous_key != field.key:
                    raise InvalidLLMResponseError(
                        'Ten sam fragment zostal przypisany do wielu pol'
                    )
                source_to_key[fragment] = field.key
                try:
                    normalized_fragments.append(
                        _normalize_field_value(fragment, field.type, field.key)
                    )
                except (ValueError, InvalidOperation) as exc:
                    raise InvalidLLMResponseError(
                        'Nie mozna znormalizowac fragmentu wskazanego przez LLM'
                    ) from exc

            try:
                normalized_extracted_value = _normalize_field_value(
                    field.extracted_value,
                    field.type,
                    field.key,
                )
            except (ValueError, InvalidOperation) as exc:
                raise InvalidLLMResponseError(
                    'LLM zwrocil niepoprawna wartosc pola'
                ) from exc

            if any(value != normalized_fragments[0] for value in normalized_fragments):
                raise InvalidLLMResponseError(
                    'Fragmenty jednego pola reprezentuja rozne wartosci'
                )
            if normalized_extracted_value != normalized_fragments[0]:
                raise InvalidLLMResponseError(
                    'Wyodrebniona wartosc nie odpowiada fragmentowi dokumentu'
                )

            detected_fields.append(
                DetectedTemplateFieldDTO(
                    key=field.key,
                    source_fragments=field.source_fragments,
                    label=field.label,
                    type=field.type,
                    extracted_value=normalized_fragments[0],
                )
            )

        detected_fields.sort(
            key=lambda field: min(source_text.find(fragment) for fragment in field.source_fragments)
        )
        return detected_fields

    @staticmethod
    def _render_response(
        analysis_request: TemplateAnalysisRequestDTO,
        fields: Sequence[DetectedTemplateFieldDTO],
    ) -> TemplateAnalysisResponseDTO:
        if not fields:
            return TemplateAnalysisResponseDTO(
                original_filename=analysis_request.original_filename,
                template_text=analysis_request.source_text,
                form_fields=(),
            )

        source_to_replacement = {
            fragment: (field.placeholder, field.type)
            for field in fields
            for fragment in field.source_fragments
        }
        sources = sorted(source_to_replacement, key=len, reverse=True)
        replacement_pattern = re.compile('|'.join(
            _source_replacement_expression(
                source,
                source_to_replacement[source][1],
            )
            for source in sources
        ))
        template_text = replacement_pattern.sub(
            lambda match: source_to_replacement[match.group(0)][0],
            analysis_request.source_text,
        )

        form_fields: Tuple[TemplateFormFieldDTO, ...] = tuple(
            field.to_form_field()
            for field in fields
        )
        expected_placeholders = {field.placeholder for field in form_fields}
        actual_placeholders = set(PLACEHOLDER_IN_TEXT_PATTERN.findall(template_text))
        if actual_placeholders != expected_placeholders:
            raise InvalidLLMResponseError(
                'Nie mozna jednoznacznie utworzyc szablonu z odpowiedzi LLM'
            )

        return TemplateAnalysisResponseDTO(
            original_filename=analysis_request.original_filename,
            template_text=template_text,
            form_fields=form_fields,
        )

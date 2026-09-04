import re
import requests
from typing import Any, List

from .exceptions import InvalidLLMResponseError

def _strip_json_code_fence(content: str) -> str:
    stripped = content.strip()
    match = re.fullmatch(r'`(?:json)?\s*(.*?)\s*`', stripped, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else stripped

def _close_http_response(response: Any) -> None:
    close = getattr(response, 'close', None)
    if callable(close):
        try:
            close()
        except Exception:
            pass

def _is_stream_read_timeout(exc: BaseException) -> bool:
    pending: List[BaseException] = [exc]
    visited: set[int] = set()
    while pending:
        candidate = pending.pop()
        candidate_id = id(candidate)
        if candidate_id in visited:
            continue
        visited.add(candidate_id)
        if isinstance(candidate, requests.exceptions.Timeout):
            return True
        candidate_type = type(candidate)
        if (
            candidate_type.__name__ == 'ReadTimeoutError'
            and (
                candidate_type.__module__ == 'urllib3.exceptions'
                or candidate_type.__module__.endswith('.urllib3.exceptions')
            )
        ):
            return True
        for nested in (
            getattr(candidate, '__cause__', None),
            getattr(candidate, '__context__', None),
            *getattr(candidate, 'args', ()),
        ):
            if isinstance(nested, BaseException):
                pending.append(nested)
    return False

def _read_limited_response_body(response: Any, max_bytes: int) -> bytes:
    headers = getattr(response, 'headers', {}) or {}
    declared_length = headers.get('Content-Length')
    if declared_length:
        try:
            if int(declared_length) > max_bytes:
                raise InvalidLLMResponseError('Odpowiedz LLM przekracza limit rozmiaru')
        except ValueError:
            pass
    chunks = []
    read_bytes = 0
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            chunks.append(chunk)
            read_bytes += len(chunk)
            if read_bytes > max_bytes:
                raise InvalidLLMResponseError('Odpowiedz LLM przekracza limit rozmiaru')
    return b''.join(chunks)

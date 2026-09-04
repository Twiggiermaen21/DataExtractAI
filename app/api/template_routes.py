import os
import logging
from threading import BoundedSemaphore
from flask import jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from app.api.auth import require_auth
from app.api.endpoints import api_bp
from app.utils.api_utils import _request_id
from app.services.template import (
    EmptyTemplateFileError,
    InvalidLLMResponseError,
    IusfullyTemplateAnalysisService,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMUpstreamError,
    TemplateAnalysisConfigurationError,
    TemplateFileTooLargeError,
    UnprocessableTemplateFileError,
    UnsupportedTemplateFileError,
    UploadedTextFileParser,
)

log = logging.getLogger(__name__)

def _configured_template_concurrency_limit():
    raw_value = os.environ.get('IUSFULLY_TEMPLATE_MAX_CONCURRENT_REQUESTS', '2')
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError('IUSFULLY_TEMPLATE_MAX_CONCURRENT_REQUESTS must be an integer') from exc
    if value <= 0:
        raise RuntimeError('IUSFULLY_TEMPLATE_MAX_CONCURRENT_REQUESTS must be positive')
    return value

_TEMPLATE_ANALYSIS_SLOTS = BoundedSemaphore(_configured_template_concurrency_limit())

def _template_error(message, error_code, status_code, rid=None):
    prefix = f"[{rid}] " if rid else ""
    log.warning("%sIusfully template analysis error (%s - %s): %s", prefix, status_code, error_code, message)
    return jsonify({'success': False, 'error': message, 'error_code': error_code}), status_code

@api_bp.route('/api/iusfully/templates/analyze', methods=['POST'])
@require_auth
def analyze_text_template():
    """Turns an uploaded document (.txt, .pdf, .docx, .doc, .rtf, .odt) into a dynamic form template."""
    rid = _request_id()
    log.info(
        "[%s] analyze_text_template incoming request: remote=%s content_length=%s mimetype=%s",
        rid,
        request.headers.get('X-Forwarded-For', request.remote_addr),
        request.content_length,
        request.mimetype,
    )

    try:
        file_parser = UploadedTextFileParser()
    except TemplateAnalysisConfigurationError:
        log.exception("[%s] Invalid Iusfully template upload configuration", rid)
        return _template_error(
            'Konfiguracja analizy szablonow jest niepoprawna',
            'configuration_error',
            503,
            rid=rid,
        )

    if request.mimetype != 'multipart/form-data':
        return _template_error(
            'Content-Type musi miec wartosc multipart/form-data',
            'unsupported_media_type',
            415,
            rid=rid,
        )

    # Check the whole multipart body before request.files triggers form parsing.
    max_request_bytes = file_parser.max_file_bytes + (64 * 1024)
    request.max_content_length = max_request_bytes
    if request.content_length is not None and request.content_length > max_request_bytes:
        return _template_error(
            f'Plik przekracza limit {file_parser.max_file_bytes} bajtow',
            'file_too_large',
            413,
            rid=rid,
        )

    try:
        uploaded_files = request.files.getlist('file')
        uploaded_file_count = sum(
            len(file_list)
            for _, file_list in request.files.lists()
        )
    except RequestEntityTooLarge:
        return _template_error(
            f'Plik przekracza limit {file_parser.max_file_bytes} bajtow',
            'file_too_large',
            413,
            rid=rid,
        )
    if not uploaded_files:
        return _template_error(
            'Brak pliku w polu file',
            'missing_file',
            400,
            rid=rid,
        )
    if len(uploaded_files) != 1 or uploaded_file_count != 1:
        return _template_error(
            'Nalezy przeslac dokladnie jeden plik',
            'multiple_files',
            400,
            rid=rid,
        )

    uploaded_file = uploaded_files[0]
    log.info(
        "[%s] analyze_text_template processing uploaded file: filename='%s', content_type='%s'",
        rid,
        uploaded_file.filename,
        uploaded_file.mimetype,
    )

    analysis_slot_acquired = False
    try:
        analysis_request = file_parser.parse(
            filename=uploaded_file.filename or '',
            stream=uploaded_file.stream,
            mime_type=uploaded_file.mimetype,
        )
        if not _TEMPLATE_ANALYSIS_SLOTS.acquire(blocking=False):
            return _template_error(
                'Usluga analizy szablonow jest chwilowo zajeta',
                'too_many_requests',
                429,
                rid=rid,
            )
        analysis_slot_acquired = True
        result = IusfullyTemplateAnalysisService().analyze(analysis_request)
        log.info(
            "[%s] analyze_text_template completed successfully: original_filename='%s', form_fields_count=%d",
            rid,
            result.original_filename,
            len(result.form_fields),
        )
        return jsonify(result.to_dict()), 200

    except EmptyTemplateFileError as exc:
        return _template_error(str(exc), 'empty_file', 400, rid=rid)
    except TemplateFileTooLargeError as exc:
        return _template_error(str(exc), 'file_too_large', 413, rid=rid)
    except UnsupportedTemplateFileError as exc:
        return _template_error(str(exc), 'unsupported_file', 415, rid=rid)
    except UnprocessableTemplateFileError as exc:
        return _template_error(str(exc), 'unprocessable_file', 422, rid=rid)
    except TemplateAnalysisConfigurationError:
        log.exception("[%s] Invalid Iusfully template LLM configuration", rid)
        return _template_error(
            'Usluga analizy szablonow nie jest skonfigurowana',
            'service_not_configured',
            503,
            rid=rid,
        )
    except LLMTimeoutError as exc:
        log.warning("[%s] Iusfully template LLM timeout: %s", rid, exc)
        return _template_error(str(exc), 'llm_timeout', 504, rid=rid)
    except LLMUnavailableError as exc:
        log.warning("[%s] Iusfully template LLM unavailable: %s", rid, exc)
        return _template_error(str(exc), 'llm_unavailable', 503, rid=rid)
    except LLMUpstreamError:
        log.warning("[%s] Iusfully template LLM rejected the request", rid)
        return _template_error(
            'Zewnetrzna usluga LLM odrzucila zadanie analizy',
            'llm_upstream_error',
            502,
            rid=rid,
        )
    except InvalidLLMResponseError:
        log.warning("[%s] Iusfully template LLM returned an invalid response", rid)
        return _template_error(
            'Nie udalo sie poprawnie przeanalizowac dokumentu',
            'invalid_llm_response',
            502,
            rid=rid,
        )
    except Exception as exc:
        log.exception("[%s] Unexpected Iusfully template analysis error: %s", rid, exc)
        return _template_error(
            'Wystapil nieoczekiwany blad analizy dokumentu',
            'internal_error',
            500,
            rid=rid,
        )
    finally:
        if analysis_slot_acquired:
            _TEMPLATE_ANALYSIS_SLOTS.release()



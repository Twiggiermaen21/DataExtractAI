import json
import logging
import os
import time
from threading import BoundedSemaphore

from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from app.auth import require_auth
from app.routes.ocr import _fields_summary, _file_size, _request_id
from app.services.iusfully_template_service import (
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
from app.services.ocr_pipeline import get_pipeline, unload_pipeline


log = logging.getLogger(__name__)

iusfully_bp = Blueprint('iusfully', __name__)


def _configured_template_concurrency_limit():
    raw_value = os.environ.get('IUSFULLY_TEMPLATE_MAX_CONCURRENT_REQUESTS', '2')
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            'IUSFULLY_TEMPLATE_MAX_CONCURRENT_REQUESTS must be an integer'
        ) from exc
    if value <= 0:
        raise RuntimeError(
            'IUSFULLY_TEMPLATE_MAX_CONCURRENT_REQUESTS must be positive'
        )
    return value


_TEMPLATE_ANALYSIS_SLOTS = BoundedSemaphore(
    _configured_template_concurrency_limit()
)


def _template_error(message, error_code, status_code):
    return jsonify({
        'success': False,
        'error': message,
        'error_code': error_code,
    }), status_code


@iusfully_bp.route('/api/iusfully/templates/analyze', methods=['POST'])
@require_auth
def analyze_text_template():
    """Turns one UTF-8 .txt document into a dynamic form template."""
    try:
        file_parser = UploadedTextFileParser()
    except TemplateAnalysisConfigurationError:
        log.exception('Invalid Iusfully template upload configuration')
        return _template_error(
            'Konfiguracja analizy szablonow jest niepoprawna',
            'configuration_error',
            503,
        )

    if request.mimetype != 'multipart/form-data':
        return _template_error(
            'Content-Type musi miec wartosc multipart/form-data',
            'unsupported_media_type',
            415,
        )

    # Check the whole multipart body before request.files triggers form parsing.
    max_request_bytes = file_parser.max_file_bytes + (64 * 1024)
    request.max_content_length = max_request_bytes
    if request.content_length is not None and request.content_length > max_request_bytes:
        return _template_error(
            f'Plik przekracza limit {file_parser.max_file_bytes} bajtow',
            'file_too_large',
            413,
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
        )
    if not uploaded_files:
        return _template_error(
            'Brak pliku w polu file',
            'missing_file',
            400,
        )
    if len(uploaded_files) != 1 or uploaded_file_count != 1:
        return _template_error(
            'Nalezy przeslac dokladnie jeden plik',
            'multiple_files',
            400,
        )

    uploaded_file = uploaded_files[0]

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
            )
        analysis_slot_acquired = True
        result = IusfullyTemplateAnalysisService().analyze(analysis_request)
        return jsonify(result.to_dict()), 200

    except EmptyTemplateFileError as exc:
        return _template_error(str(exc), 'empty_file', 400)
    except TemplateFileTooLargeError as exc:
        return _template_error(str(exc), 'file_too_large', 413)
    except UnsupportedTemplateFileError as exc:
        return _template_error(str(exc), 'unsupported_file', 415)
    except UnprocessableTemplateFileError as exc:
        return _template_error(str(exc), 'unprocessable_file', 422)
    except TemplateAnalysisConfigurationError:
        log.exception('Invalid Iusfully template LLM configuration')
        return _template_error(
            'Usluga analizy szablonow nie jest skonfigurowana',
            'service_not_configured',
            503,
        )
    except LLMTimeoutError as exc:
        log.warning('Iusfully template LLM timeout')
        return _template_error(str(exc), 'llm_timeout', 504)
    except LLMUnavailableError as exc:
        log.warning('Iusfully template LLM unavailable')
        return _template_error(str(exc), 'llm_unavailable', 503)
    except LLMUpstreamError:
        log.warning('Iusfully template LLM rejected the request')
        return _template_error(
            'Zewnetrzna usluga LLM odrzucila zadanie analizy',
            'llm_upstream_error',
            502,
        )
    except InvalidLLMResponseError:
        log.warning('Iusfully template LLM returned an invalid response')
        return _template_error(
            'Nie udalo sie poprawnie przeanalizowac dokumentu',
            'invalid_llm_response',
            502,
        )
    except Exception:
        log.exception('Unexpected Iusfully template analysis error')
        return _template_error(
            'Wystapil nieoczekiwany blad analizy dokumentu',
            'internal_error',
            500,
        )
    finally:
        if analysis_slot_acquired:
            _TEMPLATE_ANALYSIS_SLOTS.release()


@iusfully_bp.route('/api/process_ocr_iusfully', methods=['POST'])
@require_auth
def process_ocr_iusfully():
    """OCR - przetwarza pliki i zwraca wyekstrahowane dane na podstawie pol z requestu."""
    rid = _request_id()
    started_at = time.monotonic()
    log.info(
        "[%s] process_ocr_iusfully start: remote=%s content_length=%s form_keys=%s file_keys=%s",
        rid,
        request.headers.get('X-Forwarded-For', request.remote_addr),
        request.content_length,
        list(request.form.keys()),
        list(request.files.keys()),
    )

    if 'files' not in request.files:
        log.warning("[%s] process_ocr_iusfully rejected: missing files field", rid)
        return jsonify({'success': False, 'error': 'Brak plikow'}), 400

    files = request.files.getlist('files')
    incoming_files = [
        {
            'filename': file.filename,
            'content_type': file.content_type,
            'content_length': getattr(file, 'content_length', None),
        }
        for file in files
    ]
    log.info("[%s] process_ocr_iusfully incoming files: count=%s files=%s", rid, len(files), incoming_files)

    if not files or files[0].filename == '':
        log.warning("[%s] process_ocr_iusfully rejected: empty files list or empty filename", rid)
        return jsonify({'success': False, 'error': 'Nie wybrano plikow'}), 400

    # Get fields from request form data
    fields_raw = request.form.get('fields')
    fields = []
    if fields_raw:
        try:
            fields = json.loads(fields_raw)
            if not isinstance(fields, list):
                fields = [fields]
        except Exception:
            fields = [fields_raw]
    else:
        fields = request.form.getlist('fields') or request.form.getlist('fields[]')

    # Clean and filter fields
    fields = [str(f).strip() for f in fields if f and str(f).strip()]

    if not fields:
        log.warning("[%s] process_ocr_iusfully rejected: missing fields", rid)
        return jsonify({'success': False, 'error': 'Brak pol do ekstrakcji'}), 400

    model_name = request.form.get('model')
    log.info(
        "[%s] process_ocr_iusfully config: fields_count=%s fields=%s model=%s upload_folder=%s output_folder=%s",
        rid,
        len(fields),
        fields[:40],
        model_name or '<env/default>',
        current_app.config['UPLOAD_FOLDER'],
        current_app.config['OUTPUT_FOLDER'],
    )

    try:
        pipeline = get_pipeline(model=model_name)
        if pipeline is None:
            log.error("[%s] process_ocr_iusfully pipeline unavailable", rid)
            return jsonify({'success': False, 'error': 'Nie mozna polaczyc z LM Studio'}), 500

        # Set custom fields in the pipeline instance
        pipeline.fields = fields

        log.info(
            "[%s] process_ocr_iusfully pipeline ready: class=%s model=%s api_url=%s fields_count=%s",
            rid,
            pipeline.__class__.__name__,
            getattr(pipeline, 'model', None),
            getattr(pipeline, 'api_url', None),
            len(pipeline.fields),
        )
    except Exception as e:
        log.exception("[%s] process_ocr_iusfully pipeline init error", rid)
        return jsonify({'success': False, 'error': f'Blad: {str(e)}'}), 500

    processed_files = []
    documents = []
    errors = []

    for index, file in enumerate(files, start=1):
        if file.filename == '':
            log.warning("[%s] process_ocr_iusfully skip empty filename at index=%s", rid, index)
            continue

        original_filename = file.filename
        filename = secure_filename(original_filename) or f'upload_{index}'
        original_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file_started_at = time.monotonic()
        log.info(
            "[%s] file %s/%s start: original=%s stored=%s content_type=%s path=%s",
            rid,
            index,
            len(files),
            original_filename,
            filename,
            file.content_type,
            original_path,
        )

        try:
            save_started_at = time.monotonic()
            file.save(original_path)
            log.info(
                "[%s] file saved: filename=%s size=%s save_ms=%d",
                rid,
                filename,
                _file_size(original_path),
                int((time.monotonic() - save_started_at) * 1000),
            )

            predict_started_at = time.monotonic()
            ocr_output = pipeline.predict(original_path)
            log.info(
                "[%s] pipeline.predict done: filename=%s results=%s predict_ms=%d",
                rid,
                filename,
                len(ocr_output) if ocr_output is not None else None,
                int((time.monotonic() - predict_started_at) * 1000),
            )

            has_data = False
            for result_index, res in enumerate(ocr_output or [], start=1):
                extracted = getattr(res, 'extracted_data', None)
                log.info(
                    "[%s] OCR result: filename=%s result=%s text_chars=%s extracted=%s",
                    rid,
                    filename,
                    result_index,
                    len(getattr(res, 'text', '') or ''),
                    _fields_summary(extracted),
                )

                saved = res.save_to_json(save_path=current_app.config['OUTPUT_FOLDER'])
                if saved:
                    saved_name = os.path.basename(saved)
                    processed_files.append(saved_name)
                    log.info("[%s] OCR result saved: filename=%s json=%s size=%s", rid, filename, saved_name, _file_size(saved))
                else:
                    log.warning("[%s] OCR result save failed: filename=%s result=%s", rid, filename, result_index)

                if extracted:
                    documents.append({'filename': filename, 'fields': extracted})
                    has_data = True

            if not has_data:
                error = f'Model nie zwrocil danych dla pliku: {filename}'
                log.warning("[%s] file no extracted data: filename=%s", rid, filename)
                errors.append({'file': filename, 'error': error})

            log.info("[%s] file done: filename=%s has_data=%s elapsed_ms=%d", rid, filename, has_data, int((time.monotonic() - file_started_at) * 1000))

        except Exception as e:
            log.exception("[%s] OCR error for %s", rid, filename)
            errors.append({'file': filename, 'error': str(e)})

    unload_pipeline()
    log.info("[%s] process_ocr_iusfully pipeline unloaded", rid)

    success = len(documents) > 0
    status_code = 200 if success else 422
    message = f'Przetworzono {len(processed_files)} plikow'
    error_details = '; '.join(
        f"{item.get('file', 'plik')}: {item.get('error', 'brak danych')}"
        for item in errors
    )
    error_message = None if success else (
        error_details or 'OCR nie zwrocil danych dla zadnego pliku.'
    )

    response_payload = {
        'success': success,
        'processed': processed_files,
        'documents': documents,
        'errors': errors,
        'message': message,
        'error': error_message,
    }
    log.info(
        "[%s] process_ocr_iusfully response: status=%s success=%s processed=%s documents=%s errors=%s elapsed_ms=%d",
        rid,
        status_code,
        success,
        len(processed_files),
        len(documents),
        errors,
        int((time.monotonic() - started_at) * 1000),
    )
    log.debug("[%s] process_ocr_iusfully response payload: %s", rid, json.dumps(response_payload, ensure_ascii=False, default=str))

    return jsonify(response_payload), status_code

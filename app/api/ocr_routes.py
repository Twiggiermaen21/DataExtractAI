import os
import time
import json
import logging
from flask import current_app, jsonify, request
from werkzeug.utils import secure_filename

from app.core.auth import require_auth
from app.api.endpoints import api_bp
from app.utils.api_utils import _request_id, _file_size, _fields_summary
from app.services.ocr_pipeline import get_pipeline, unload_pipeline

log = logging.getLogger(__name__)

@api_bp.route('/api/process_ocr_iusfully', methods=['POST'])
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

        # Set custom fields in the pipeline instance using the new method
        if hasattr(pipeline, 'set_fields'):
            pipeline.set_fields(fields)
        else:
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

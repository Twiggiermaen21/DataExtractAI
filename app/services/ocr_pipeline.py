import logging

log = logging.getLogger(__name__)

_pipeline = None


def get_pipeline(template_path=None, model=None, selected_columns=None):
    global _pipeline

    if _pipeline is None:
        try:
            from app.services.ocr_llm_service import OCRService
            _pipeline = OCRService(model=model, selected_columns=selected_columns)
        except Exception as e:
            log.error("Nie udało się utworzyć OCRService: %s", e)
            return None
    else:
        # Aktualizuj schemat jeśli zmienił się wybór kolumn
        if selected_columns is not None and selected_columns != _pipeline.selected_columns:
            from app.services.ocr_llm_service import build_response_schema
            _pipeline.selected_columns = selected_columns
            _pipeline.response_schema = build_response_schema(selected_columns)

    if template_path:
        _pipeline.set_template(template_path)

    return _pipeline


def unload_pipeline():
    global _pipeline
    _pipeline = None
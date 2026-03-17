import logging

log = logging.getLogger(__name__)

_pipeline = None


def get_pipeline(template_path=None, model=None):
    global _pipeline

    if _pipeline is None:
        try:
            from app.services.ocr_llm_service import OCRService
            _pipeline = OCRService(model=model)
        except Exception as e:
            log.error("Nie udało się utworzyć OCRService: %s", e)
            return None
    elif model and _pipeline.model != model:
        _pipeline.model = model

    if template_path:
        _pipeline.set_template(template_path)

    return _pipeline


def unload_pipeline():
    global _pipeline
    _pipeline = None
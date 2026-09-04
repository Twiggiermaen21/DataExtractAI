import logging

log = logging.getLogger(__name__)

_pipeline = None


def get_pipeline(template_path=None, model=None, custom_fields=None):
    global _pipeline

    if _pipeline is None:
        try:
            from app.services.ocr import OCRService
            _pipeline = OCRService(model=model)
        except Exception as e:
            log.error("Nie udało się utworzyć OCRService: %s", e)
            return None
    elif model and _pipeline.model != model:
        _pipeline.model = model

    # custom_fields z frontendu mają priorytet nad szablonem
    if custom_fields:
        _pipeline.set_fields(custom_fields)
        log.info("Pipeline: custom fields set from frontend: count=%s", len(custom_fields))
    elif template_path:
        _pipeline.set_template(template_path)

    return _pipeline


def unload_pipeline():
    global _pipeline
    _pipeline = None
_pipeline = None

def get_pipeline(template_path=None, model=None):
    print("Wywołano funkcję: get_pipeline")
    global _pipeline
    
    if _pipeline is None:
        try:
            from app.services.ocr_llm_service import OCRService
            _pipeline = OCRService(model=model)
        except Exception as e:
            pass  # usuniety print
            return None
    else:
        if model and _pipeline.model != model:
            _pipeline.model = model
            pass  # usuniety print
    
    # Ustaw szablon jeśli podano
    if template_path:
        _pipeline.set_template(template_path)
    
    return _pipeline

def unload_pipeline():
    print("Wywołano funkcję: unload_pipeline")
    global _pipeline
    if _pipeline is not None:
        _pipeline.unload_model()
        _pipeline = None
_pipeline = None

def get_pipeline(template_path=None, model=None):
    global _pipeline
    
    if _pipeline is None:
        try:
            from app.services.ocr_llm_service import OCRService
            _pipeline = OCRService(model=model)
        except Exception as e:
            print(f"⚠️ Błąd ładowania OCR: {e}")
            return None
    else:
        if model and _pipeline.model != model:
            _pipeline.model = model
            print(f"🔄 Zaktualizowano model OCR na: {model}")
    
    # Ustaw szablon jeśli podano
    if template_path:
        _pipeline.set_template(template_path)
    
    return _pipeline

def unload_pipeline():
    global _pipeline
    if _pipeline is not None:
        _pipeline.unload_model()
        _pipeline = None
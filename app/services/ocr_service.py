_pipeline = None

def get_pipeline(template_path=None):
    global _pipeline
    
    if _pipeline is None:
        try:
            from app.services.ocr_lightOCR2 import GemmaOCRService
            _pipeline = GemmaOCRService()
        except Exception as e:
            print(f"⚠️ Błąd ładowania OCR: {e}")
            return None
    
    # Ustaw szablon jeśli podano
    if template_path:
        _pipeline.set_template(template_path)
    
    return _pipeline

def unload_pipeline():
    global _pipeline
    if _pipeline is not None:
        _pipeline.unload_model()
        _pipeline = None
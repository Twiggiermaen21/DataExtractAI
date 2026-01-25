"""
Serwis OCR z lazy loading modelu.
Model ładowany jest dopiero przy pierwszym użyciu i pozostaje w pamięci.
"""

_pipeline = None

def _ensure_dynamic_mode():
    """Wymusza tryb dynamiczny PaddlePaddle przed predykcją."""
    try:
        import paddle
        if not paddle.in_dynamic_mode():
            paddle.disable_static()
    except Exception:
        pass

def get_pipeline():
    """Ładuje model OCR jeśli nie jest załadowany."""
    global _pipeline
    
    # Zawsze upewnij się że jesteśmy w trybie dynamicznym
    # _ensure_dynamic_mode() # Not needed for LightOCR/Transformers?
    
    if _pipeline is None:
        try:
            from app.services.ocr_lightOCR2 import LightOCRService
            print("⏳ Ładowanie modelu LightOCR...")
            _pipeline = LightOCRService()
            print("✅ Model LightOCR zainicjalizowany (lazy loading).")
        except ImportError:
            print("⚠️ Błąd importu LightOCRService.")
            return None
        except Exception as e:
            print(f"⚠️ Błąd ładowania serwisu OCR: {e}")
            return None
    return _pipeline

def unload_pipeline():
    """Zwalnia model z pamięci."""
    global _pipeline
    if _pipeline is not None:
        print("🔄 Zwalnianie modelu OCR z pamięci...")
        try:
            if hasattr(_pipeline, 'unload_model'):
                _pipeline.unload_model()
            elif hasattr(_pipeline, 'unload'): # Fallback if naming changes
                 _pipeline.unload()
        except Exception as e:
            print(f"⚠️ Błąd podczas zwalniania modelu: {e}")
            
        del _pipeline
        _pipeline = None
        
        # Wymuś garbage collection
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass
        print("✅ Model OCR zwolniony.")
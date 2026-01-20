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
    _ensure_dynamic_mode()
    
    if _pipeline is None:
        try:
            from paddleocr import PaddleOCRVL
            print("⏳ Ładowanie modelu PaddleOCR...")
            _pipeline = PaddleOCRVL()
            print("✅ Model PaddleOCR załadowany.")
        except ImportError:
            print("⚠️ Brak biblioteki paddleocr.")
            return None
        except Exception as e:
            print(f"⚠️ Błąd ładowania modelu: {e}")
            return None
    return _pipeline

def unload_pipeline():
    """Zwalnia model z pamięci."""
    global _pipeline
    if _pipeline is not None:
        print("🔄 Zwalnianie modelu OCR z pamięci...")
        del _pipeline
        _pipeline = None
        # Wymuś garbage collection
        import gc
        gc.collect()
        try:
            import paddle
            paddle.device.cuda.empty_cache()
        except:
            pass
        print("✅ Model OCR zwolniony.")
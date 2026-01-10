try:
    from paddleocr import PaddleOCRVL
    _pipeline = PaddleOCRVL()
    print("✅ Model PaddleOCR załadowany.")
except ImportError:
    print("⚠️ Brak biblioteki paddleocr. Tryb demo.")
    _pipeline = None
except Exception as e:
    print(f"⚠️ Błąd modelu: {e}")
    _pipeline = None

def get_pipeline():
    return _pipeline
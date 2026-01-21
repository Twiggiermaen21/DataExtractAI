import cv2
import numpy as np
import os

def enhance_image_for_ocr(image_path, scale_factor=2):
    """
    Powiększa i czyści zdjęcie faktury, aby OCR lepiej radził sobie z tekstem.
    Zapisuje przetworzony plik tymczasowy i zwraca jego ścieżkę.
    """
    
    # 1. Wczytanie obrazu
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Nie znaleziono pliku: {image_path}")
    
    # Użyj numpy.fromfile + imdecode zamiast imread
    # To obsługuje polskie znaki i specjalne ścieżki na Windows
    try:
        img_array = np.fromfile(image_path, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    except Exception as e:
        raise ValueError(f"Nie można zdekodować obrazu: {image_path}. Błąd: {e}")
    
    if img is None:
        raise ValueError(f"Nie można wczytać obrazu: {image_path}. Sprawdź czy plik jest prawidłowym obrazem (JPG, PNG).")
    
    # --- ETAP 1: UPSCALING (Powiększanie) ---
    # Jeśli faktura jest mała (np. mała rozdzielczość skanu), powiększamy ją.
    # Używamy INTER_CUBIC lub INTER_LANCZOS4 (wolniejszy, ale lepszy do tekstu)
    
    width = int(img.shape[1] * scale_factor)
    height = int(img.shape[0] * scale_factor)
    dim = (width, height)
    
    # Upscaling
    upscaled = cv2.resize(img, dim, interpolation=cv2.INTER_LANCZOS4)
    
    # --- ETAP 2: PRZETWARZANIE WSTĘPNE (Preprocessing) ---
    
    # Konwersja na skalę szarości (OCR działa najlepiej na szarościach)
    gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
    
    # Opcjonalnie: Lekkie odszumianie (ostrożnie, żeby nie rozmazać liter)
    # h=10 to siła odszumiania
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    
    # --- ETAP 3: BINARYZACJA (Czarny tekst, białe tło) ---
    # Metoda Otsu automatycznie znajduje idealny próg odcięcia czerni od bieli.
    # To jest KLUCZOWE dla faktur ze słabym kontrastem lub kolorowym tłem.
    
    # binaryzacja adaptacyjna (lepsza jeśli na fakturze są cienie)
    binary = cv2.adaptiveThreshold(
        denoised, 
        255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        11, # wielkość bloku sąsiedztwa (musi być nieparzysta)
        2   # stała odejmowana od średniej
    )
    
    # --- ZAPIS WYNIKU ---
    # Tworzymy folder "ulepszone_zdjecia" w katalogu output
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    enhanced_dir = os.path.join(project_root, "output", "ulepszone_zdjecia")
    
    # Upewniamy się, że folder istnieje
    os.makedirs(enhanced_dir, exist_ok=True)
    
    filename = os.path.basename(image_path)
    new_filename = f"ulepszone_{filename}"
    output_path = os.path.join(enhanced_dir, new_filename)
    
    # Użyj imencode + tofile zamiast imwrite (obsługuje polskie znaki)
    ext = os.path.splitext(filename)[1]
    is_success, encoded_img = cv2.imencode(ext, binary)
    if is_success:
        encoded_img.tofile(output_path)
    else:
        raise ValueError(f"Nie można zakodować obrazu: {output_path}")
    
    print(f"Ulepszone zdjęcie zapisano: {output_path}")
    
    return output_path

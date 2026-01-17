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
        
    img = cv2.imread(image_path)
    
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
    # Tworzymy nazwę dla pliku tymczasowego
    base_dir = os.path.dirname(image_path)
    filename = os.path.basename(image_path)
    new_filename = f"ocr_ready_{filename}"
    output_path = os.path.join(base_dir, new_filename)
    
    cv2.imwrite(output_path, binary)
    
    return output_path

# --- TESTOWANIE ---
if __name__ == "__main__":
    # Test ręczny
    input_file = "twoja_slaba_faktura.jpg" # Upewnij się, że masz taki plik
    try:
        better_file = enhance_image_for_ocr(input_file, scale_factor=3) # 3x powiększenie
        print(f"Sukces! Przetworzony plik zapisano jako: {better_file}")
    except Exception as e:
        print(f"Błąd: {e}")
import os
from paddleocr import PaddleOCRVL

# Konfiguracja folderów
UPLOAD_FOLDER = "input"
OUTPUT_FOLDER = "output"

# 1. Upewnij się, że folder wyjściowy istnieje
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 2. Inicjalizacja modelu
pipeline = PaddleOCRVL()

# 3. Pętla przez pliki w folderze input
print(f"Rozpoczynam przetwarzanie plików z folderu: {UPLOAD_FOLDER}")

for filename in os.listdir(UPLOAD_FOLDER):
    # Sprawdzenie rozszerzenia (żeby nie próbował czytać np. plików systemowych)
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.pdf')):
        
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        print(f"--> Przetwarzanie: {filename}")
        
        try:
            # Wykonanie OCR
            output = pipeline.predict(file_path)

            for res in output:
                # Opcjonalnie: wypisz w konsoli (możesz zakomentować, jeśli plików jest dużo)
                # res.print() 
                
                # Zapis wyników do folderu output
                # PaddleOCRVL zazwyczaj automatycznie używa nazwy pliku źródłowego do nazwania wyniku
                res.save_to_json(save_path=OUTPUT_FOLDER)
                res.save_to_markdown(save_path=OUTPUT_FOLDER)
                
        except Exception as e:
            print(f"!!! Błąd przy pliku {filename}: {e}")

print("Zakończono przetwarzanie wszystkich plików.")
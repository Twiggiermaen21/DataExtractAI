from paddleocr import PaddleOCRVL
import os

def przetworz_dokument(sciezka_do_pliku, folder_wynikowy="output"):
    """
    Przetwarza dokument przy użyciu PaddleOCRVL i zapisuje wyniki.
    
    Args:
        sciezka_do_pliku (str): Ścieżka do pliku obrazu (np. "FAKTURA.jpg").
        folder_wynikowy (str): Folder, gdzie zapisać JSON i Markdown (domyślnie "output_faktura").
        model (PaddleOCRVL, optional): Załadowana instancja modelu. Jeśli None, model zostanie załadowany wewnątrz funkcji.
    
    Returns:
        output: Obiekt z wynikami lub None w przypadku błędu.
    """
    model= PaddleOCRVL()
    # 1. Sprawdzenie czy plik istnieje
    if not os.path.exists(sciezka_do_pliku):
        print(f"!!! BŁĄD: Nie widzę pliku '{sciezka_do_pliku}' w tym folderze.")
        return None

    try:
        # 2. Inicjalizacja modelu (jeśli nie został podany)
        # Uwaga: Dla wydajności lepiej załadować model raz poza funkcją i go przekazywać.
        if model is None:
            print(">>> Inicjalizacja modelu PaddleOCRVL...")
            model = PaddleOCRVL()

        print(f">>> Przetwarzam plik: {sciezka_do_pliku}")
        
        # 3. Predykcja
        output = model.predict(sciezka_do_pliku)

        # 4. Zapis wyników
        for res in output:
            # Wyświetl w terminalu (opcjonalne, można zakomentować dla czytelności przy wielu plikach)
            res.print()
            
            # Zapisz wyniki
            res.save_to_json(save_path=folder_wynikowy)
            res.save_to_markdown(save_path=folder_wynikowy)
            
        print(f">>> Sukces. Zapisano wyniki w folderze '{folder_wynikowy}'")
        return output

    except Exception as e:
        print(f"!!! Wystąpił nieoczekiwany błąd podczas przetwarzania '{sciezka_do_pliku}': {e}")
        return None


    # 3. Przykład dla innego pliku (bez ponownego ładowania modelu!)
    # przetworz_dokument("PARAGON.png", folder_wynikowy="wyniki_paragonow", model=moj_pipeline)
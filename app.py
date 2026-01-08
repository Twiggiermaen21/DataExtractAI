from paddleocr import PaddleOCRVL
import os
pipeline = PaddleOCRVL()
# output = pipeline.predict("https://paddle-model-ecology.bj.bcebos.com/paddlex/imgs/demo_image/paddleocr_vl_demo.png")
plik_lokalny = "FAKTURA.jpg"

if os.path.exists(plik_lokalny):
    print(f">>> Przetwarzam plik: {plik_lokalny}")
    
    # Tu podajemy nazwę pliku zamiast linku WWW
    output = pipeline.predict(plik_lokalny)

    for res in output:
        # Wyświetl w terminalu
        res.print()
        
        # Zapisz wyniki
        res.save_to_json(save_path="output_faktura")
        res.save_to_markdown(save_path="output_faktura")
        print(">>> Zapisano wyniki w folderze 'output_faktura'")
else:
    print(f"!!! BŁĄD: Nie widzę pliku '{plik_lokalny}' w tym folderze.")
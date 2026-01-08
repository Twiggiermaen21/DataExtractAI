import os
import sys
import paddle
from paddleocr import PPStructure, save_structure_res

# ==========================================
# KONFIGURACJA: TRYB GPU (RTX 3050 Ti)
# ==========================================
# Odblokowujemy widoczność karty graficznej
if "CUDA_VISIBLE_DEVICES" in os.environ:
    del os.environ["CUDA_VISIBLE_DEVICES"]

# Fix dla bibliotek systemowych na Windowsie
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
# Mniej logów w terminalu
os.environ["GLOG_minloglevel"] = "2"

def run_invoice_parser_gpu():
    # Sprawdzenie czy Python widzi Twoją kartę
    gpu_dostepne = paddle.device.is_compiled_with_cuda()
    nazwa_urzadzenia = paddle.device.get_device()
    
    print(f"\n" + "="*50)
    print(f" STATUS GPU: {'✅ AKTYWNE' if gpu_dostepne else '❌ NIEAKTYWNE'}")
    print(f" Urządzenie: {nazwa_urzadzenia}")
    print("="*50)

    if not gpu_dostepne:
        print("!!! UWAGA: Nie wykryto bibliotek CUDA. Upewnij się, że masz zainstalowane sterowniki CUDA i cuDNN.")
        print("!!! Próba uruchomienia na CPU jako fallback...")
        uzyj_gpu = False
    else:
        print(">>> Uruchamiam silnik PP-Structure na karcie RTX 3050 Ti...")
        uzyj_gpu = True

    # Plik do przetworzenia
    img_path = "FAKTURA.jpg"
    if not os.path.exists(img_path):
        print("!!! Brak pliku FAKTURA.jpg w folderze!")
        return

    try:
        # Inicjalizacja silnika z włączonym GPU
        # lang='pl' -> polski model językowy
        engine = PPStructure(
            table=True, 
            ocr=True, 
            show_log=True, 
            lang='pl', 
            use_gpu=uzyj_gpu,
            gpu_mem=3000  # Ograniczamy zużycie do 3GB (Twoja karta ma 4GB)
        )

        print(f">>> Analizuję fakturę: {img_path}")
        result = engine(img_path)

        # Zapis wyników
        save_folder = './wyniki_gpu'
        os.makedirs(save_folder, exist_ok=True)
        save_structure_res(result, save_folder, os.path.basename(img_path).split('.')[0])

        print("\n" + "="*50)
        print(" SUKCES! PRZETWORZONO NA GPU 🚀 ")
        print("="*50)
        print(f">>> Wyniki zapisano w folderze: {save_folder}")

    except Exception as e:
        print(f"\n!!! BŁĄD: {e}")
        # Jeśli błąd dotyczy cuDNN/cublas
        if "dll" in str(e).lower() or "cublas" in str(e).lower():
            print("\nWSKAZÓWKA: Wygląda na brak bibliotek 'cuDNN' w systemie Windows.")
            print("Pobierz je ze strony Nvidii i wrzuć do folderu bin w C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\...")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_invoice_parser_gpu()
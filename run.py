import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

import webview
import time
import urllib.request
import urllib.error
import threading
import sys
import subprocess
import atexit
from app import create_app
class Api:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def save_file(self, base64_data, filename):
        """Otwiera dialog zapisu pliku i zapisuje dane base64."""
        if not self._window:
            return {'success': False, 'error': 'Window not initialized'}
        
        # Filtry plików dla dialogu zapisu
        file_types = ('Excel files (*.xlsx)', 'All files (*.*)')
        save_path = self._window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory=os.path.expanduser('~'), 
            save_filename=filename,
            file_types=file_types
        )
        
        if save_path and len(save_path) > 0:
            actual_path = save_path[0]
            import base64
            try:
                # Usunięcie nagłówka data URI jeśli obecny
                if ',' in base64_data:
                    base64_data = base64_data.split(',')[1]
                
                with open(actual_path, 'wb') as f:
                    f.write(base64.b64decode(base64_data))
                
                print(f"[API] Plik zapisany pomyślnie: {actual_path}")
                return {'success': True, 'path': actual_path}
            except Exception as e:
                print(f"[API] BŁĄD zapisu pliku: {e}")
                return {'success': False, 'error': str(e)}
        
        return {'success': False, 'error': 'Cancelled'}

app = create_app()
api = Api()

# Zmienna przechowująca nasz niewidzialny proces C++
_llama_process = None

def start_background_server():
    global _llama_process
    if _llama_process is not None:
        return
    
    # Magiczny trik dla PyInstallera - szuka pliku w tymczasowym folderze po spakowaniu
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    # Ścieżki synchronizowane z .env
    server_exe = os.path.join(base_path, "llama", "llama-server.exe")
    
    # Pobieranie nazw plików modeli z .env
    model_file = os.environ.get("LLM_MODEL_FILE", "Qwen3.5-2B.gguf")
    mmproj_file = os.environ.get("LLM_MMPROJ_FILE", "mmproj-Qwen3.5-2B.gguf")

    model_path = os.path.join(base_path, "model", model_file)
    mmproj_path = os.path.join(base_path, "model", mmproj_file)

    print("[OCR] Próbuję uruchomić serwer AI w tle...")
    
    cmd = [
    server_exe,
    "-m", model_path,
    "--mmproj", mmproj_path,
    "--port", "8080",
    "-c", "20000",       # Zwiększamy do 8k - masz 16GB VRAM, wejdzie bez problemu, a obsłuży długie faktury
    "-ngl", "99",       # Przerzucenie wszystkiego na GPU
    "-fa", "on",       # Flash Attention - MUSISZ to mieć. Przyspiesza analizę obrazu i oszczędza VRAM
    "--temp", "0.0",    # Temperatura 0.0 - eliminuje "kreatywność" modelu, wymusza faktyczne dane z obrazu
    "-t", "12",         # Wykorzystanie 12 wątków CPU do zadań pomocniczych (ładowanie, obsługa HTTP)
    "--ubatch-size", "512", # Optymalny rozmiar paczek dla serii RTX 50
    "--host", "127.0.0.1"   # Bezpieczeństwo - serwer dostępny tylko lokalnie
]
    
    # Odpalamy jako proces z własnym widocznym oknem konsoli
    creationflags = 0
    if os.name == 'nt':
        creationflags = subprocess.CREATE_NO_WINDOW

    try:
        _llama_process = subprocess.Popen(
            cmd, 
            creationflags=creationflags,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Krótka weryfikacja czy proces nie "wywalił się" natychmiast
        time.sleep(1)
        if _llama_process.poll() is not None:
            stdout, stderr = _llama_process.communicate()
            error_msg = stderr.decode('utf-8', errors='ignore')
            print(f"BŁĄD: Serwer C++ zamknął się tuż po starcie:\n{error_msg}")
            _llama_process = None
        else:
            print("SUKCES: Serwer pomyślnie uruchomiony.")
            
    except FileNotFoundError:
        print(f"BŁĄD KRYTYCZNY: Nie znaleziono pliku llama-server.exe pod ścieżką: {server_exe}")
    except Exception as e:
        print(f"NIEOCZEKIWANY BŁĄD podczas próby startu: {e}")

# Zabezpieczenie: Gdy wyłączasz swoją aplikację, zabijamy serwer w tle
@atexit.register
def cleanup_server():
    global _llama_process
    if _llama_process:
        _llama_process.terminate()
        _llama_process = None

def wait_and_redirect(window, port=5000):
    print("[RUN] Oczekiwanie na start serwera C++...")
    start_background_server()
    
    server_ready = False
    for _ in range(240): # Maksymalnie 4 minuty na załadowanie modelu do RAM
        try:
            req = urllib.request.Request("http://127.0.0.1:8080/health")
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    server_ready = True
                    break
        except urllib.error.URLError:
            pass
        time.sleep(1)
        
    if server_ready:
        print("[RUN] Serwer gotowy. Przekierowanie do głównej aplikacji.")
        window.load_url(f'http://localhost:{port}')
    else:
        print("[RUN] Serwer nie odpowiedział.")

if __name__ == '__main__':
    loading_html = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'templates', 'loading.html')
    
    window = webview.create_window('iusfully', f'file://{loading_html}', width=1200, height=800, js_api=api)
    api.set_window(window)
    
    def start_flask():
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

    threading.Thread(target=start_flask, daemon=True).start()
    threading.Thread(target=wait_and_redirect, args=(window, 5000), daemon=True).start()
    
    webview.start(private_mode=False)
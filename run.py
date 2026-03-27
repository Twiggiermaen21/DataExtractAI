import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

import time
import urllib.request
import urllib.error
import threading
import sys
import subprocess
import atexit
import webbrowser
from app import create_app

app = create_app()

# Proces llama-server
_llama_process = None


def start_background_server():
    global _llama_process
    if _llama_process is not None:
        return

    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    server_exe = os.path.join(base_path, "llama", "llama-server.exe")
    model_file = os.environ.get("MODEL_FILE", "Qwen3VL-4B-Instruct-Q8_0.gguf")
    mmproj_file = os.environ.get("MMPROJ_FILE", "mmproj-Qwen3VL-4B-Instruct-Q8_0.gguf")
    max_tokens = os.environ.get("LLAMA_CONTEXT_SIZE", "8000")

    model_path = os.path.join(base_path, "model", model_file)
    mmproj_path = os.path.join(base_path, "model", mmproj_file)

    if not os.path.exists(server_exe):
        logging.error("Nie znaleziono llama-server.exe: %s", server_exe)
        return

    if not os.path.exists(model_path):
        logging.error("Nie znaleziono pliku modelu: %s", model_path)
        return

    logging.info("Uruchamianie serwera AI w tle...")

    cmd = [
        server_exe,
        "-m", model_path,
        "--mmproj", mmproj_path,
        "--port", "8080",
        "-c", max_tokens,
        "-ngl", "99",
        "-fa", "on",
        "--temp", "0.0",
        "-t", "12",
        "--ubatch-size", "512",
        "--host", "127.0.0.1",
    ]

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

    try:
        _llama_process = subprocess.Popen(
            cmd,
            creationflags=creationflags,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        time.sleep(1)
        if _llama_process.poll() is not None:
            _, stderr = _llama_process.communicate()
            logging.error("Serwer AI zamknął się tuż po starcie:\n%s",
                          stderr.decode('utf-8', errors='ignore'))
            _llama_process = None
        else:
            logging.info("Serwer AI uruchomiony (PID %d).", _llama_process.pid)

    except Exception:
        logging.exception("Błąd podczas uruchamiania llama-server")


@atexit.register
def cleanup_server():
    global _llama_process
    if _llama_process:
        logging.info("Zatrzymywanie serwera AI...")
        _llama_process.terminate()
        _llama_process = None


def wait_for_llama(port=8080, timeout=240):
    """Czeka aż llama-server odpowie na /health."""
    url = f"http://127.0.0.1:{port}/health"
    for _ in range(timeout):
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    logging.info("Serwer AI gotowy.")
                    return True
        except Exception:
            pass
        time.sleep(1)
    logging.warning("Serwer AI nie odpowiedział w ciągu %d sekund.", timeout)
    return False


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))

    # Start llama-server w tle
    llama_thread = threading.Thread(target=start_background_server, daemon=True)
    llama_thread.start()

    # Otwórz przeglądarkę po chwili (Flask musi zdążyć się uruchomić)
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}")

    threading.Thread(target=open_browser, daemon=True).start()

    logging.info("Aplikacja dostępna pod adresem: http://localhost:%d", port)
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

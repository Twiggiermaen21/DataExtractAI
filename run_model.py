"""
Uruchamia llama-server (model AI) na localhost.
Port i parametry konfigurowane przez .env lub zmienne środowiskowe.

Użycie:
    python run_model.py
"""
import os
import sys
import time
import logging
import subprocess
import atexit
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

log = logging.getLogger("run_model")

_llama_process = None


def start():
    global _llama_process

    base_path = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

    server_exe  = os.path.join(base_path, "llama", "llama-server.exe")
    model_file  = os.environ.get("MODEL_FILE",        "Qwen3VL-4B-Instruct-Q8_0.gguf")
    mmproj_file = os.environ.get("MMPROJ_FILE",       "mmproj-Qwen3VL-4B-Instruct-Q8_0.gguf")
    host        = os.environ.get("LLAMA_HOST",        "127.0.0.1")
    port        = os.environ.get("LLAMA_PORT",        "8080")
    ctx_size    = os.environ.get("LLAMA_CONTEXT_SIZE", "8000")
    n_gpu       = os.environ.get("LLAMA_GPU_LAYERS",   "99")
    threads     = os.environ.get("LLAMA_THREADS",      "12")
    ubatch      = os.environ.get("LLAMA_UBATCH_SIZE",  "512")
    temperature = os.environ.get("LLAMA_TEMP",         "0.0")

    model_path  = os.path.join(base_path, "model", model_file)
    mmproj_path = os.path.join(base_path, "model", mmproj_file)

    if not os.path.exists(server_exe):
        log.error("Nie znaleziono llama-server.exe: %s", server_exe)
        sys.exit(1)

    if not os.path.exists(model_path):
        log.error("Nie znaleziono pliku modelu: %s", model_path)
        sys.exit(1)

    cmd = [
        server_exe,
        "-m",            model_path,
        "--mmproj",      mmproj_path,
        "--host",        host,
        "--port",        port,
        "-c",            ctx_size,
        "-ngl",          n_gpu,
        "-fa",           "on",
        "--temp",        temperature,
        "-t",            threads,
        "--ubatch-size", ubatch,
    ]

    log.info("Uruchamianie modelu AI...")
    log.info("  Model:  %s", model_file)
    log.info("  Adres:  http://%s:%s", host, port)

    creationflags = 0
    if os.name == 'nt':
        # Pokaż okno konsoli żeby widać było postęp ładowania modelu
        creationflags = subprocess.CREATE_NEW_CONSOLE

    stderr_pipe = None if creationflags else subprocess.PIPE

    try:
        _llama_process = subprocess.Popen(cmd, creationflags=creationflags, stderr=stderr_pipe)

        time.sleep(2)
        if _llama_process.poll() is not None:
            log.error("Serwer AI zamknął się tuż po starcie (kod: %d).", _llama_process.returncode)
            if stderr_pipe is not None:
                stderr_out = _llama_process.stderr.read().decode(errors="replace").strip()
                if stderr_out:
                    log.error("Błąd z llama-server:\n%s", stderr_out)
            sys.exit(1)

        log.info("Serwer AI uruchomiony (PID %d). Ładowanie modelu...", _llama_process.pid)

    except FileNotFoundError:
        log.error("Nie można uruchomić llama-server.exe — plik nie istnieje: %s", server_exe)
        sys.exit(1)
    except PermissionError as e:
        log.error("Brak uprawnień do uruchomienia llama-server.exe: %s", e)
        sys.exit(1)
    except Exception as e:
        log.exception("Nieoczekiwany błąd podczas uruchamiania llama-server: %s", e)
        sys.exit(1)


@atexit.register
def _cleanup():
    global _llama_process
    if _llama_process and _llama_process.poll() is None:
        log.info("Zatrzymywanie serwera AI...")
        _llama_process.terminate()


def wait_until_ready(timeout=300):
    host = os.environ.get("LLAMA_HOST", "127.0.0.1")
    port = os.environ.get("LLAMA_PORT", "8080")
    url  = f"http://{host}:{port}/health"

    log.info("Oczekiwanie na gotowość modelu (max %d s)...", timeout)
    last_error = None
    for elapsed in range(timeout):
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    log.info("Model gotowy po %d s.", elapsed)
                    return True
        except urllib.error.URLError as e:
            last_error = str(e.reason)
            log.debug("Próba %d/%d — serwer jeszcze nie gotowy: %s", elapsed + 1, timeout, e.reason)
        except Exception as e:
            last_error = str(e)
            log.debug("Próba %d/%d — błąd: %s", elapsed + 1, timeout, e)
        time.sleep(1)

    log.warning("Model nie odpowiedział w ciągu %d sekund.", timeout)
    if last_error:
        log.warning("Ostatni błąd połączenia: %s", last_error)
    return False


if __name__ == '__main__':
    start()
    ready = wait_until_ready()
    if ready:
        log.info("Serwer AI działa. Możesz teraz uruchomić aplikację: python run.py")
    else:
        log.warning("Serwer AI działa, ale nie potwierdził gotowości. Sprawdź okno konsoli modelu.")

    # Czekaj aż proces zakończy się lub użytkownik przerwie (Ctrl+C)
    try:
        _llama_process.wait()
    except KeyboardInterrupt:
        log.info("Przerwano przez użytkownika.")

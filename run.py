import os
import logging
import webbrowser
import threading
import time
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))

    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}")

    threading.Thread(target=open_browser, daemon=True).start()

    logging.info("Aplikacja dostępna pod adresem: http://localhost:%d", port)
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

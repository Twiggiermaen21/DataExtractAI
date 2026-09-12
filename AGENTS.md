# AGENTS.md — Ekstrakcja i OCR (DataExtractAI-dev)

Ten dokument definiuje standardy pracy i zasady weryfikacji dla mikroserwisu **`DataExtractAI-dev`**.

---

## 1. Odpowiedzialność Serwisu

Mikroserwis odpowiada za przetwarzanie, analizę strukturalną oraz ekstrakcję tekstu i pól dynamicznych z dokumentów prawnych przesyłanych w formatach:
- PDF (przez `PyMuPDF` / `fitz`)
- DOCX (`python-docx`)
- RTF (`striprtf`)
- ODF (`odfpy`)
- TXT

---

## 2. Standardy i Dobre Praktyki

1. **Defensywne parsowanie (Fault Tolerance):**
   - Pliki wejściowe mogą być uszkodzone, spreparowane lub niekompletne.
   - Wszelkie operacje wejścia/wyjścia na plikach muszą być opakowane w obsługę wyjątków i zwracać czytelne błędy HTTP (np. `422 Unprocessable Entity` z kodem błędu, a nie surowy błąd `500`).
2. **Ochrona prywatności i tajemnicy zawodowej:**
   - Nie loguj pełnej zawartości dokumentów ani danych osobowych (RODO).
   - W przypadku błędów parsowania do logów trafia jedynie typ błędu i ew. bezpieczny hash/długość pliku.
3. **Rejestracja tras we Flask:**
   - Trasy podpinane do blueprintów (`api_bp`) muszą być importowane w `app/api/endpoints.py` przed wywołaniem `app.register_blueprint()`.

---

## 3. Pętla Weryfikacji dla Agenta

Przed ukończeniem zadania w `DataExtractAI-dev` wykonaj:

```bash
# 1. Aktywacja środowiska:
source .venv/bin/activate

# 2. Szybki linter Ruff:
ruff check .

# 3. Testy jednostkowe:
pytest
```
Wszystkie 34+ testy muszą przejść z kodem wyjścia 0.

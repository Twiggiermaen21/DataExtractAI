# Iusfully AI - DataExtractAI

Usługa backendowa (Flask) do analizy dokumentów tekstowych oraz ekstrakcji danych z plików i skanów (OCR) przy pomocy modeli LLM.

## Wymagania
- Python 3.10+
- Docker i docker-compose (do uruchomienia bazy Postgres)
- Klucze API do usługi LLM (skonfigurowane w pliku .env)

## Konfiguracja
Skopiuj plik .env.example (jeśli istnieje) lub upewnij się, że posiadasz plik .env w głównym katalogu, z poprawnymi danymi (LLM_API_URL, LLM_API_KEY, klucze autoryzacyjne bazy danych itp.).

## Uruchamianie (Docker)
Aplikację można uruchomić kontenerowo używając docker-compose:
\\\ash
docker-compose up -d --build
\\\
Usługa uruchomi się domyślnie na porcie 40107. Posiada wbudowany healthcheck na endpointcie /healthz.

## Endpointy

### Autoryzacja
Autoryzacja odbywa się przez tokeny JWT.
- **POST** /api/auth/login - Zwraca token dostępowy (ccess_token) dla poprawnych danych logowania.
- **POST** /api/auth/refresh - Odświeża token dostępowy.
- **GET** /api/auth/me - Zwraca informacje o aktualnie zalogowanym użytkowniku. Wymaga nagłówka Authorization: Bearer <token>.

### Analiza Szablonów (Iusfully)
- **POST** /api/iusfully/templates/analyze 
  Zmienia przesłany plik dokumentu w formularz z polami wejściowymi dla platformy Iusfully.
  - Wymaga nagłówka Authorization: Bearer <token>.
  - Content-Type: multipart/form-data
  - Body: Plik przesłany w polu ile (wspierane: .txt, .pdf, .docx, .doc, .rtf, .odt).
  - Zwraca listę dynamicznie rozpoznanych zmiennych dokumentu w formacie JSON.

### Wyodrębnianie Danych (OCR)
- **POST** /api/process_ocr_iusfully 
  Wyciąga wartości kluczowych pól z dokumentu (np. faktury), aby automatycznie uzupełnić wezwanie do zapłaty lub inny formularz.
  - Wymaga nagłówka Authorization: Bearer <token>.
  - Content-Type: multipart/form-data
  - Body: Plik przesłany w polu ile, definicje pól w ciele żądania.
  - Zwraca ustrukturyzowany JSON (zgodny ze zdefiniowanym schematem pól) ze znalezionymi wartościami OCR.
  
### Inne
- **GET** /healthz - Zwraca status 200 OK, używany głównie jako dockerowy healthcheck.

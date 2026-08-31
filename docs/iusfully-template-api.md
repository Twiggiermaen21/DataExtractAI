# Iusfully — analiza tekstu do dynamicznego szablonu

## Endpoint

`POST /api/iusfully/templates/analyze`

Endpoint wymaga tokenu JWT oraz żądania `multipart/form-data` z dokładnie jednym
plikiem w polu `file`. Akceptowane są pliki `.txt` zakodowane w UTF-8 lub UTF-8
z BOM. Plik jest analizowany w pamięci i nie jest zapisywany na dysku.

```bash
curl -X POST http://localhost:5000/api/iusfully/templates/analyze \
  -H "Authorization: Bearer <token>" \
  -F "file=@wezwanie.txt;type=text/plain"
```

Przykładowa odpowiedź `200`:

```json
{
  "original_filename": "wezwanie.txt",
  "template_text": "Wezwanie dla {{klient_nazwa}} na kwotę {{kwota_do_zaplaty}} zł.",
  "form_fields": [
    {
      "placeholder": "{{klient_nazwa}}",
      "label": "Nazwa klienta",
      "type": "text",
      "extracted_value": "Jan Kowalski Sp. z o.o."
    },
    {
      "placeholder": "{{kwota_do_zaplaty}}",
      "label": "Kwota do zapłaty",
      "type": "number",
      "extracted_value": "1500.50"
    }
  ]
}
```

Typ `number` zawiera wartość dziesiętną jako tekst z kropką. Typ `date` zawiera
datę ISO `YYYY-MM-DD`. Identyfikatory, takie jak NIP, KRS, rachunek bankowy lub
numer faktury, zawsze mają typ `text`.

## Konfiguracja

Serwis korzysta z istniejącego klienta HTTP i API zgodnego z OpenAI Chat
Completions. `LLM_API_URL` musi wskazywać pełny endpoint, na przykład
`http://localhost:8080/v1/chat/completions`. Serwer musi obsługiwać
`response_format.type=json_schema`.

```dotenv
LLM_API_URL=http://localhost:8080/v1/chat/completions
LLM_MODEL=your-model
LLM_API_KEY=
IUSFULLY_TEMPLATE_MAX_FILE_BYTES=65536
IUSFULLY_TEMPLATE_LLM_TIMEOUT_SECONDS=120
IUSFULLY_TEMPLATE_LLM_MAX_TOKENS=4000
IUSFULLY_TEMPLATE_MAX_LLM_RESPONSE_BYTES=1048576
IUSFULLY_TEMPLATE_MAX_CONCURRENT_REQUESTS=2
```

Nie są potrzebne nowe biblioteki: endpoint używa Flaska, `requests` i DTO na
standardowych `dataclass`. Dla zewnętrznego dostawcy można ustawić
`LLM_API_KEY`; dla lokalnego serwera wartość pozostaje pusta.

## Błędy

Błędy walidacji pliku i komunikacji z LLM mają postać:

```json
{
  "success": false,
  "error": "Opis błędu",
  "error_code": "machine_readable_code"
}
```

| Status | Znaczenie |
|---|---|
| `400` | Brak pliku, wiele plików, pusta nazwa lub pusty plik |
| `401` / `403` | Błąd autoryzacji |
| `413` | Przekroczony limit rozmiaru |
| `415` | Plik inny niż `.txt`, błędne UTF-8 lub dane binarne |
| `422` | Brak treści do analizy lub konflikt składni placeholderów |
| `429` | Limit równoległych analiz w procesie został osiągnięty |
| `502` | Niepoprawna odpowiedź albo odrzucenie żądania przez LLM |
| `503` | Brak konfiguracji, limit dostawcy lub niedostępny LLM |
| `504` | Przekroczony czas oczekiwania na LLM |

Błędy `401` i `403` pochodzą ze wspólnej warstwy autoryzacji aplikacji i
zachowują jej dotychczasowy kontrakt `{ "success": false, "error": "..." }`
bez pola `error_code`.

W środowisku produkcyjnym limit żądania należy dodatkowo ustawić w reverse
proxy. Treści dokumentów i wartości pól nie powinny trafiać do logów.
Frontend powinien przypisywać `label`, `template_text` i `extracted_value` jako
tekst lub właściwość `value`, nigdy wstawiać ich bezpośrednio przez `innerHTML`.
Limit równoległości działa osobno w każdym procesie Gunicorna. Reverse proxy lub
API gateway powinien dodatkowo wymuszać rate limit per użytkownik.

## Testy

Testy nie wymagają działającego modelu — odpowiedzi LLM są mockowane:

```bash
python -m unittest discover -s tests -v
```

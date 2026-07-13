# Wdrozenie Docker/VPS

Aplikacja jest przygotowana pod uruchomienie bezposrednio na porcie VPS:

```text
http://srv59.mikr.us:40107
```

W kontenerze Gunicorn slucha na `0.0.0.0:5000`, a Docker wystawia port hosta `40107` na port kontenera `5000`. Bez podanego host IP Docker moze pokazac bind dla IPv4 i IPv6, np. `0.0.0.0:40107->5000/tcp, [::]:40107->5000/tcp`.

## Start na VPS

1. Wejdz do katalogu projektu:

```bash
cd DataExtractAI
```

2. Utworz konfiguracje, jesli jeszcze jej nie ma:

```bash
cp .env.example .env
```

3. Ustaw w `.env` adres serwera LLM. Jesli `llama-server` dziala na tym samym VPS poza Dockerem:

```bash
LLM_API_URL=http://host.docker.internal:8080/v1/chat/completions
LLM_MODEL=default
```

Jesli LLM dziala jako drugi kontener w tej samej sieci Compose, uzyj nazwy uslugi, np.:

```bash
LLM_API_URL=http://llm:8080/v1/chat/completions
```

4. Zbuduj i uruchom aplikacje:

```bash
docker compose up -d --build
```

5. Sprawdz status:

```bash
docker compose ps
docker compose logs -f app
curl http://127.0.0.1:40107/healthz
```

Publicznie aplikacja powinna byc dostepna pod:

```text
http://srv59.mikr.us:40107
```

## Dane trwale

Te katalogi sa montowane do kontenera:

- `input/`
- `output/`
- `saved/`

Dzieki temu pliki uzytkownika i wygenerowane dokumenty zostaja na VPS po restarcie lub przebudowie kontenera.

## Aktualizacja

```bash
git pull
docker compose up -d --build
docker image prune -f
```
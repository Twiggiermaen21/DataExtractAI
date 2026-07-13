# Wdrozenie Docker/VPS

## Lokalnie przez Docker Compose

1. Skopiuj konfiguracje:

```bash
cp .env.example .env
```

2. Ustaw w `.env` adres serwera LLM:

```bash
LLM_API_URL=http://host.docker.internal:8080/v1/chat/completions
LLM_MODEL=default
```

3. Zbuduj i uruchom:

```bash
docker compose up -d --build
```

4. Sprawdz logi i healthcheck:

```bash
docker compose logs -f app
curl http://127.0.0.1:5000/healthz
```

## VPS

1. Zainstaluj Docker i plugin Compose.
2. Wgraj projekt na serwer, wejdz do katalogu `DataExtractAI`.
3. Utworz `.env` z `.env.example` i ustaw produkcyjny `LLM_API_URL`.
4. Uruchom aplikacje:

```bash
docker compose up -d --build
```

Compose wystawia aplikacje tylko na `127.0.0.1:5000`, wiec publiczny ruch powinien isc przez Nginx.

## Nginx

1. Skopiuj `deploy/nginx.conf` do `/etc/nginx/sites-available/dataextractai`.
2. Zmien `server_name example.com www.example.com;` na swoja domene.
3. Wlacz konfiguracje:

```bash
sudo ln -s /etc/nginx/sites-available/dataextractai /etc/nginx/sites-enabled/dataextractai
sudo nginx -t
sudo systemctl reload nginx
```

4. Dla HTTPS najprosciej uzyc Certbota:

```bash
sudo certbot --nginx -d twoja-domena.pl
```

## LLM na VPS

Jesli `llama-server` dziala bezposrednio na tym samym VPS poza Dockerem, ustaw:

```bash
LLM_API_URL=http://host.docker.internal:8080/v1/chat/completions
```

W `docker-compose.yml` dodano `host.docker.internal:host-gateway`, zeby kontener mogl laczyc sie z uslugami na hoscie Linuksa.

Jesli LLM dziala jako drugi kontener w tej samej sieci Compose, ustaw adres na nazwe uslugi, np.:

```bash
LLM_API_URL=http://llm:8080/v1/chat/completions
```

## Dane trwale

Te katalogi sa montowane jako wolumeny bind:

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
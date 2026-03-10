FROM python:3.10-slim

# Ustawienie katalogu roboczego
WORKDIR /app

# Skopiowanie plików serwisu
COPY requirements.txt .

# Instalacja zależności Pythona
RUN pip install --no-cache-dir -r requirements.txt

# Skopiowanie całego kodu źródłowego
COPY . .

# Wystawienie portu
EXPOSE 5000

# Komenda startowa
CMD ["python", "run.py"]

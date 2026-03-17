FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Tworzenie folderów danych (nie kopiowanych z hosta)
RUN mkdir -p input output saved

# Non-root user
RUN adduser --disabled-password --no-create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# Gunicorn: 4 workery, timeout 600s (długie zapytania LLM)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "600", "run:app"]

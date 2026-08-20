FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Porta convenzionale Fly.io — distinta dalla 8000/dinamica usata dall'app
# desktop via Electron (electron/main.js), che resta invariata.
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

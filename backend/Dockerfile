FROM python:3.12-slim

# Senza questa variabile, lo stdout di Python dentro il container è
# bufferizzato a blocchi (non è un terminale, è una pipe verso i log di
# Fly): i `print()` di telegram_bot.py possono restare invisibili in
# `fly logs` molto a lungo invece di comparire subito.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Porta convenzionale Fly.io — distinta dalla 8000/dinamica usata dall'app
# desktop via Electron (electron/main.js), che resta invariata.
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

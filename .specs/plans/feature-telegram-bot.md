# Feature: Bot Telegram

## Obiettivo

Registrare spese e consultare i totali dal telefono via Telegram, scrivendo in
linguaggio naturale, senza aprire l'app desktop. I dati finiscono nello stesso
database Turso già usato da desktop e backend hosted.

## Dipendenze

- Backend FastAPI hosted su Fly.io (`financed-backend`, issue-mobile-1) — già in prod
- Turso configurato come database condiviso — già fatto
- Chiave gratuita Google AI Studio (`GEMINI_API_KEY`) come secret Fly.io
- Un bot creato su @BotFather (token) + il proprio `chat_id`

## Stack

- Webhook come route del backend FastAPI esistente (`routes/telegram.py`),
  **non** un'app Fly.io separata come ipotizzato nell'ADR originale: quel piano
  precede il backend hosted attuale. Un solo deploy, riusa `database.py` e il
  client Turso HTTP.
- Chiamate alla Bot API di Telegram con `requests` (no `python-telegram-bot`).
- Parsing dei messaggi con **Gemini Flash** (SDK `google-genai`), structured
  output JSON con schema imposto. Modello configurabile via
  `TELEGRAM_PARSER_MODEL` (default `gemini-2.5-flash`; `gemini-2.5-flash-lite`
  più leggero). Chiave gratuita da Google AI Studio (`GEMINI_API_KEY`).
  - Prima iterazione fatta con Claude (`anthropic`, function-calling):
    abbandonata quando l'utente ha realizzato che l'API Anthropic è a consumo
    (credito prepagato, ~480 msg con 5 $ su Opus 5). Gemini Flash gratis era
    già l'idea dell'ADR originale.
- Auth: il webhook verifica `X-Telegram-Bot-Api-Secret-Token`
  (`TELEGRAM_WEBHOOK_SECRET`); il bot risponde solo a `TELEGRAM_CHAT_ID`.
- Il path `/api/telegram/webhook` è esente dal middleware `X-API-Token` in
  `main.py` (Telegram non può mandare header custom).

## Comandi

- testo libero → registra spesa (importo negativo, `source='telegram'`) o
  corregge l'ultima (`era 12 non 8`, `mettila in Svago`)
- `/oggi` `/settimana` `/mese` — spese per categoria + totale
- `/budget` — budget del mese (da `monthly_budgets`) vs speso
- `/ultima` — ultima spesa registrata dal bot
- `/cancella` — cancella l'ultima
- `/aiuto` `/start` — istruzioni

## File

```
backend/telegram_bot.py        ← logica bot: comandi, parsing Gemini, accesso DB
backend/routes/telegram.py     ← webhook + helper set-webhook/info/delete-webhook
backend/main.py                ← include router + esenzione middleware
backend/requirements.txt       ← + google-genai
backend/.env.example           ← nuovo, documenta tutte le env var
```

## Setup (una tantum)

1. @BotFather → `/newbot` → copia il token
2. Chiave Gemini gratuita su https://aistudio.google.com/app/apikey
3. `fly secrets set TELEGRAM_BOT_TOKEN=... GEMINI_API_KEY=... TELEGRAM_WEBHOOK_SECRET=... --app financed-backend`
4. Scrivi un messaggio al bot, poi `https://api.telegram.org/bot<TOKEN>/getUpdates` → copia `message.chat.id` (o usa @userinfobot)
5. `fly secrets set TELEGRAM_CHAT_ID=... --app financed-backend`
6. `fly deploy` (dalla cartella `backend/`)
7. Registra il webhook (una riga sola, niente `\`):
   `curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://financed-backend.fly.dev/api/telegram/webhook&secret_token=<TELEGRAM_WEBHOOK_SECRET>"`
   (in alternativa `POST /api/telegram/set-webhook` col body `{"base_url":"..."}` e header `X-API-Token`, che imposta anche il menu comandi)

## Output atteso

Scrivendo «€8 bar boulevard» al bot, compare una transazione da -8,00 €
categoria "Bar & Ristoranti" in Turso, visibile subito nell'app desktop.

## Status

[x] Codice scritto e testato in locale (import, round-trip DB con RETURNING id,
    webhook + esenzione middleware via TestClient, formattazione comandi,
    costruzione del config Gemini con lo schema). Parsing Gemini non ancora
    verificato dal vivo (serve `GEMINI_API_KEY`).
[x] Bot creato su @BotFather, deploy su Fly.io fatto, webhook registrato
    (`getWebhookInfo` OK, 0 pending, nessun errore). Catena Telegram → webhook
    → bot → LLM verificata (l'errore che si vedeva era solo la chiave LLM).
[~] Swap Claude → Gemini in corso: serve `fly secrets set GEMINI_API_KEY=...`
    + `fly deploy` (requirements cambiati: `anthropic` → `google-genai`).
    Rimuovere il vecchio secret: `fly secrets unset ANTHROPIC_API_KEY`.
[ ] Verifica end-to-end da telefono con Gemini
[ ] Merge in `dev`

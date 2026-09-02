# Feature: Bot Telegram

## Obiettivo

Registrare spese e consultare i totali dal telefono via Telegram, scrivendo in
linguaggio naturale, senza aprire l'app desktop. I dati finiscono nello stesso
database Turso già usato da desktop e backend hosted.

## Dipendenze

- Backend FastAPI hosted su Fly.io (`financed-backend`, issue-mobile-1) — già in prod
- Turso configurato come database condiviso — già fatto
- Chiave API Anthropic (`ANTHROPIC_API_KEY`) come secret Fly.io
- Un bot creato su @BotFather (token) + il proprio `chat_id`

## Stack

- Webhook come route del backend FastAPI esistente (`routes/telegram.py`),
  **non** un'app Fly.io separata come ipotizzato nell'ADR originale: quel piano
  precede il backend hosted attuale. Un solo deploy, riusa `database.py` e il
  client Turso HTTP.
- Chiamate alla Bot API di Telegram con `requests` (no `python-telegram-bot`).
- Parsing dei messaggi con Claude (SDK `anthropic`), non Gemini: la chiave
  Anthropic è già prevista nella config del progetto. Modello configurabile via
  `TELEGRAM_PARSER_MODEL` (default `claude-opus-5`; `claude-haiku-4-5` per
  tagliare i costi).
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
backend/telegram_bot.py        ← logica bot: comandi, parsing Claude, accesso DB
backend/routes/telegram.py     ← webhook + helper set-webhook/info/delete-webhook
backend/main.py                ← include router + esenzione middleware
backend/requirements.txt       ← + anthropic
backend/.env.example           ← nuovo, documenta tutte le env var
```

## Setup (una tantum)

1. @BotFather → `/newbot` → copia il token
2. `fly secrets set TELEGRAM_BOT_TOKEN=... ANTHROPIC_API_KEY=... TELEGRAM_WEBHOOK_SECRET=... --app financed-backend`
3. Scrivi un messaggio al bot, poi `https://api.telegram.org/bot<TOKEN>/getUpdates` → copia `message.chat.id`
4. `fly secrets set TELEGRAM_CHAT_ID=... --app financed-backend`
5. `fly deploy` (dalla cartella `backend/`)
6. Registra il webhook:
   `curl -X POST https://financed-backend.fly.dev/api/telegram/set-webhook -H "X-API-Token: <API_ACCESS_TOKEN>" -H "Content-Type: application/json" -d '{"base_url":"https://financed-backend.fly.dev"}'`

## Output atteso

Scrivendo «€8 bar boulevard» al bot, compare una transazione da -8,00 €
categoria "Bar & Ristoranti" in Turso, visibile subito nell'app desktop.

## Status

[ ] Non iniziata
[x] Codice scritto e testato in locale (import, round-trip DB con RETURNING id,
    webhook + esenzione middleware, formattazione comandi). Parsing Claude non
    verificato dal vivo: nessuna chiave Anthropic nell'ambiente di sviluppo.
[ ] Setup BotFather + secret Fly.io + deploy + registrazione webhook (utente)
[ ] Verifica end-to-end da telefono

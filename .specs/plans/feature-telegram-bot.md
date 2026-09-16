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
  `TELEGRAM_PARSER_MODEL` (default `gemini-3.6-flash`; `gemini-3.6-flash-lite`
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
  corregge l'ultima (`era 12 non 8`, `mettila in Svago`, `era di ieri`)
- messaggio che inizia per `+` → registra un'**entrata** (`+50 stipendio`),
  importo positivo, categoria `Entrata`/`Rimborso ricevuto`
- data diversa da oggi in linguaggio naturale (`ieri 20 euro benzina`, `il 3
  settembre 15 al cinema`) — Gemini la risolve rispetto a "oggi" (iniettato nel
  prompt ad ogni chiamata) e la restituisce in `YYYY-MM-DD`, validata con
  `date.fromisoformat` prima di scrivere
- `/oggi` `/settimana` `/mese` — spese per categoria + totale
- `/budget` — budget del mese (da `monthly_budgets`) vs speso
- `/ultima` — ultima registrazione (spesa o entrata) del bot
- `/cancella` — cancella l'ultima
- `/coda` — messaggi in attesa di essere ritentati
- `/aiuto` `/start` — istruzioni

## Coda dei messaggi (issue-telegram-2)

Se `_interpret()` fallisce (rete, quota Gemini, modello ritirato — è già
successo con `gemini-2.5-flash`) il messaggio **non viene scartato**: finisce
in `telegram_pending` (tabella creata al volo da `telegram_bot.py`, non serve
una migrazione a parte) e un task asyncio (`queue_worker_loop`, avviato da
`main.py` — `asyncio.create_task` nello startup event, gira anche in sviluppo)
lo ritenta ogni 60s (`_QUEUE_INTERVAL_S`) fino a `_QUEUE_MAX_ATTEMPTS` (8, poi
l'utente viene avvisato e il messaggio scartato). Il primo fallimento avvisa
subito l'utente ("⏳ ... l'ho messo in coda"); i ritentativi successivi sono
silenziosi finché non c'è un esito (successo o scarto finale) — altrimenti un
outage di qualche minuto significherebbe un messaggio "⏳" ogni minuto.
`_interpret()` ha anche un timeout di 12s + 1 retry automatico lato SDK
(`http_options`), per non tenere un thread del threadpool bloccato a
oltranza su un problema di rete prima ancora di arrivare alla coda.

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
    costruzione del config Gemini con lo schema).
[x] Bot creato su @BotFather, deploy su Fly.io fatto, webhook registrato
    (`getWebhookInfo` OK, 0 pending, nessun errore).
[x] Swap Claude → Gemini fatto e deployato. `gemini-2.5-flash` era già ritirato
    per i progetti nuovi → default portato a `gemini-3.6-flash` (nome suggerito
    dall'API stessa nel 404).
[x] Verifica end-to-end da telefono con Gemini: OK, spesa registrata.
[x] Merge in `dev`, poi fast-forward in `main` (issue-telegram-1)
[x] issue-telegram-2: entrate con `+`, data personalizzabile (registrazione +
    correzione), coda con retry automatico. Testato in locale con `_interpret`
    monkeypatchata (round-trip entrata/spesa/data/correzione, coda:
    fallimento→attempts++, successo→rimossa, max tentativi→scartata e
    utente avvisato). Non verificato dal vivo contro Gemini reale.
[ ] Deploy + verifica end-to-end di issue-telegram-2 da telefono
[ ] Merge issue-telegram-2 in `dev`

# Feature: revisione mirata di telegram_bot.py — issue-audit-3

## Obiettivo

Dall'audit del repo (30/09/2026, commit `3b56e4f`, vedi `AUDIT.md`):
`backend/telegram_bot.py` (773 righe) è il file backend più grande del
progetto. È tipicamente dove si annidano edge case: parsing dei messaggi con
Gemini, retry della coda, gestione errori di rete. Non è un problema
confermato, ma un'area a rischio che merita un'occhiata mirata, soprattutto
dopo le modifiche recenti (`issue-telegram-2`, `issue-telegram-3`: webhook che
risponde subito con dedup su `update_id`, coda con retry, entrate con "+" e
data personalizzabile).

## Dipendenze

- Nessuna. Attività di revisione, non di feature.

## Stack

- Backend FastAPI + python-telegram-bot/webhook + Gemini per il parsing,
  coerente con l'ADR.

## Output atteso

- Revisione riga per riga di `telegram_bot.py` con focus su:
  - parsing Gemini: cosa succede se la risposta non è nel formato atteso o
    Gemini è irraggiungibile/lento;
  - coda con retry: comportamento su fallimento permanente (dead letter? log?
    messaggio perso silenziosamente?), idempotenza dei retry;
  - gestione errori di rete verso Telegram e verso il backend/DB;
  - eventuali race condition tra webhook e processamento della coda.
- Documento (o commento nello spec) con l'elenco di edge case trovati,
  ciascuno classificato come "già gestito", "minore" o "da sistemare".
- Per gli edge case classificati "da sistemare": fix mirati, senza refactoring
  più ampio del file (quello è fuori scope qui).
- Verifica: test manuale dei casi critici trovati (es. messaggio malformato,
  Gemini offline, Telegram che ritorna errore) su bot di test.

## Status

[ ] Da fare

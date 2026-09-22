"""Webhook Telegram + helper per registrarlo.

`POST /api/telegram/webhook` è l'endpoint che Telegram chiama a ogni messaggio.
È esente dal middleware `X-API-Token` (vedi `main.py`) perché Telegram non può
mandare quell'header — al suo posto verifica un segreto condiviso passato da
Telegram nell'header `X-Telegram-Bot-Api-Secret-Token` (impostato quando si
registra il webhook con `secret_token`).

Gli altri endpoint qui (`set-webhook`, `info`, `delete-webhook`) sono strumenti
di configurazione una-tantum e restano protetti dal normale `X-API-Token`.
"""
import asyncio
import os

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

import telegram_bot

router = APIRouter()

_WEBHOOK_PATH = "/api/telegram/webhook"


@router.post("/webhook")
async def telegram_webhook(request: Request):
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        raise HTTPException(status_code=403, detail="Secret token non valido")

    update = await request.json()

    # Rispondere PRIMA di elaborare, non dopo — visto dal vivo: elaborare
    # significa una chiamata a Gemini (fino a ~25s tra timeout e retry
    # dell'SDK, vedi telegram_bot._interpret) più l'invio su Telegram. Se
    # aspettavamo tutto questo prima di rispondere 200, Telegram considerava
    # la consegna appesa/fallita e RIMANDAVA lo stesso update — da qui
    # l'orologio che gira sul telefono, poi il messaggio segnato come non
    # inviato, e messaggi doppi che si accavallano in corsa fra loro quando
    # la copia rimandata arrivava mentre la prima stava ancora elaborando.
    # Ora rispondiamo subito e l'elaborazione vera gira in background — vedi
    # anche il controllo su update_id in handle_update, seconda rete di
    # sicurezza se Telegram rimanda comunque lo stesso update per altri motivi
    # (bug lato loro, riavvio della macchina Fly a metà elaborazione, ecc.).
    asyncio.create_task(_process_in_background(update))
    return {"ok": True}


async def _process_in_background(update: dict) -> None:
    try:
        await run_in_threadpool(telegram_bot.handle_update, update)
    except Exception as e:
        print("[telegram] errore elaborazione update in background:", repr(e))


class SetWebhookIn(BaseModel):
    # Es. "https://financed-backend.fly.dev" — senza slash finale.
    base_url: str


def _require_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN non impostato sul server")
    return token


@router.post("/set-webhook")
def set_webhook(payload: SetWebhookIn):
    """Registra il webhook presso Telegram e imposta il menu comandi."""
    token = _require_token()
    api = f"https://api.telegram.org/bot{token}"
    url = payload.base_url.rstrip("/") + _WEBHOOK_PATH

    body = {"url": url, "allowed_updates": ["message"]}
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if secret:
        body["secret_token"] = secret

    r = requests.post(f"{api}/setWebhook", json=body, timeout=15)
    set_result = r.json()

    commands = [
        {"command": "oggi", "description": "Spese di oggi"},
        {"command": "settimana", "description": "Spese degli ultimi 7 giorni"},
        {"command": "mese", "description": "Spese dal 1° del mese"},
        {"command": "budget", "description": "Budget del mese e quanto resta"},
        {"command": "ultima", "description": "Ultima spesa registrata"},
        {"command": "cancella", "description": "Cancella l'ultima spesa"},
        {"command": "aiuto", "description": "Come si usa il bot"},
    ]
    requests.post(f"{api}/setMyCommands", json={"commands": commands}, timeout=15)

    return {"webhook_url": url, "telegram": set_result, "chat_id_configurato": bool(os.getenv("TELEGRAM_CHAT_ID"))}


@router.get("/info")
def webhook_info():
    token = _require_token()
    r = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=15)
    return r.json()


@router.post("/delete-webhook")
def delete_webhook():
    token = _require_token()
    r = requests.post(
        f"https://api.telegram.org/bot{token}/deleteWebhook",
        json={"drop_pending_updates": True},
        timeout=15,
    )
    return r.json()

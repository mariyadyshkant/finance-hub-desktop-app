"""Bot Telegram personale per registrare spese e consultare i totali dal telefono.

Non gira come processo a sé: è un modulo importato dal backend FastAPI
(`routes/telegram.py` espone il webhook). Telegram consegna gli update via
HTTPS a `POST /api/telegram/webhook`, quel route chiama `handle_update()` qui.

Scelte (vedi ADR.md → "Integrazione Telegram Bot"):
- Nessuna libreria `python-telegram-bot`: sono due sole chiamate HTTP alla Bot
  API (`sendMessage`, `setWebhook`), fatte con `requests` — già una dipendenza.
  Stessa filosofia di `turso_client.py` (client HTTP fatto in casa, zero build
  native).
- Parsing dei messaggi in linguaggio naturale con Gemini Flash (SDK
  `google-genai`), piano gratuito di Google AI Studio: costo zero per un bot
  personale.
- Il bot risponde SOLO a `TELEGRAM_CHAT_ID`: chiunque altro conosca il nome del
  bot riceve un rifiuto secco.
- Le spese sono salvate con importo NEGATIVO, come fa l'app desktop per le
  spese manuali (`frontend/.../Transazioni.svelte`: default -10). Entrate e
  rimborsi restano positivi.
"""
import json
import os
from datetime import date, timedelta

import requests

import database as db
from importers.helpers import CATEGORIES

# ─── Config da ambiente ──────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
# Modello Gemini per il parsing: abbondante per estrarre importo/descrizione/
# categoria da una frase. Google ritira i modelli vecchi in fretta (i `2.5-*`
# non sono più disponibili ai nuovi progetti da set. 2026) — se l'API risponde
# 404 dicendo di aggiornare, mettere il nome suggerito in TELEGRAM_PARSER_MODEL
# (secret Fly) senza aspettare una modifica al codice.
# `or` e non il default di getenv: la env var può essere presente ma vuota.
PARSER_MODEL = os.getenv("TELEGRAM_PARSER_MODEL") or "gemini-3.6-flash"

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Categorie che non hanno senso per una spesa registrata al volo dal telefono
# (sono entrate/rimborsi, gestite dall'app desktop).
_EXPENSE_CATEGORIES = [c for c in CATEGORIES if c not in ("Entrata", "Rimborso ricevuto")]

_MESI_IT = [
    "gen", "feb", "mar", "apr", "mag", "giu",
    "lug", "ago", "set", "ott", "nov", "dic",
]

_LAST_TX_KEY = "telegram:last_tx_id"


def is_configured() -> bool:
    return bool(BOT_TOKEN and ALLOWED_CHAT_ID)


# ─── Telegram Bot API ────────────────────────────────────────────────────────

def send_message(chat_id, text: str) -> None:
    if not BOT_TOKEN:
        print("[telegram] TELEGRAM_BOT_TOKEN non impostato, messaggio non inviato")
        return
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=15,
        ).raise_for_status()
    except requests.RequestException as e:
        print("[telegram] invio messaggio fallito:", repr(e))


# ─── Accesso dati ────────────────────────────────────────────────────────────

def _rows(sql: str, params=()):
    conn = db.get_conn()
    cur = conn.execute(sql, params)
    cols = [d[0] for d in cur.description]
    out = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return out


def _today_iso() -> str:
    return date.today().isoformat()


def _fmt_date_it(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{int(d)} {_MESI_IT[int(m) - 1]} {y}"


def _fmt_eur(value: float) -> str:
    return f"€{value:,.2f}".replace(",", "·").replace(".", ",").replace("·", ".")


def _spent_between(start_iso: str, end_iso: str) -> float:
    """Totale speso (valore positivo) tra due date incluse."""
    rows = _rows(
        "SELECT COALESCE(-SUM(amount), 0) AS spent FROM transactions "
        "WHERE date BETWEEN ? AND ? AND amount < 0",
        (start_iso, end_iso),
    )
    return float(rows[0]["spent"]) if rows else 0.0


def _spent_in_month(month: str) -> float:
    rows = _rows(
        "SELECT COALESCE(-SUM(amount), 0) AS spent FROM transactions "
        "WHERE strftime('%Y-%m', date) = ? AND amount < 0",
        (month,),
    )
    return float(rows[0]["spent"]) if rows else 0.0


def _breakdown(sql_where: str, params) -> list[tuple[str, float]]:
    rows = _rows(
        f"SELECT category, -SUM(amount) AS amt FROM transactions "
        f"WHERE {sql_where} AND amount < 0 GROUP BY category ORDER BY amt DESC",
        params,
    )
    return [(r["category"], float(r["amt"])) for r in rows]


def _insert_expense(description: str, amount_abs: float, category: str) -> int:
    """Inserisce una spesa (importo negativo) e ritorna l'id della nuova riga.

    RETURNING è supportato sia da SQLite locale (>= 3.35) sia da libsql/Turso —
    evita di dover indovinare l'id con un SELECT successivo, che con il client
    HTTP di Turso girerebbe su una connessione diversa (last_insert_rowid = 0).
    """
    today = _today_iso()
    conn = db.get_conn()
    cur = conn.execute(
        "INSERT INTO transactions (date, description, amount, category, source, note) "
        "VALUES (?,?,?,?,?,?) RETURNING id",
        (today, description, -abs(amount_abs), category, "telegram", ""),
    )
    row = cur.fetchone()
    conn.commit()
    conn.close()
    return int(row[0])


# ─── Interpretazione messaggi (Gemini) ─────────────────────────────────────
# Gemini Flash sul piano gratuito di Google AI Studio (1M token/giorno, nessuna
# carta): costo zero per un bot personale. Si usa la "structured output" di
# Gemini (JSON con schema imposto) invece del function-calling: un solo schema
# piatto, output deterministico, mapping banale sul resto del codice.

_NO_FIELD = "nessuno"

_SYSTEM_PROMPT = (
    "Sei l'assistente di un bot Telegram personale per registrare spese in "
    "italiano. Ogni messaggio dell'utente è di uno di questi tipi:\n"
    "- una NUOVA spesa: '€8 bar boulevard', 'ho pagato 45 dal dentista', "
    "'5 euro caffè contanti' → azione = registra_spesa, con importo (sempre "
    "positivo), una descrizione breve e pulita, e la categoria più adatta.\n"
    "- una CORREZIONE dell'ultima spesa: 'era 54 non 45', 'mettila in Persona', "
    "'la descrizione è sbagliata, è X' → azione = correggi_ultima, indicando "
    "campo_correzione e il nuovo valore (nuovo_numero per l'importo, "
    "nuovo_testo per categoria o descrizione).\n"
    "- nient'altro → azione = non_pertinente.\n"
    "Non inventare spese se il messaggio non ne contiene una. Riempi sempre "
    f"tutti i campi: usa 0, stringa vuota o '{_NO_FIELD}' per quelli non pertinenti."
)


def _response_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "azione": {
                "type": "string",
                "enum": ["registra_spesa", "correggi_ultima", "non_pertinente"],
            },
            "descrizione": {"type": "string"},
            "importo": {"type": "number"},
            "categoria": {"type": "string", "enum": _EXPENSE_CATEGORIES},
            "campo_correzione": {
                "type": "string",
                "enum": ["importo", "categoria", "descrizione", _NO_FIELD],
            },
            "nuovo_testo": {"type": "string"},
            "nuovo_numero": {"type": "number"},
        },
        "required": [
            "azione", "descrizione", "importo", "categoria",
            "campo_correzione", "nuovo_testo", "nuovo_numero",
        ],
        "propertyOrdering": [
            "azione", "descrizione", "importo", "categoria",
            "campo_correzione", "nuovo_testo", "nuovo_numero",
        ],
    }


def _interpret(text: str, last_tx: dict | None) -> dict:
    """Ritorna {'tool': <nome>, 'input': {...}} oppure {'tool': 'errore', ...}.

    I nomi 'tool' nel valore di ritorno sono storici (prima si usava il
    function-calling): il resto del modulo li usa come chiavi di dispatch.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return {"tool": "errore", "messaggio": "SDK google-genai non installato sul server."}

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"tool": "errore", "messaggio": "GEMINI_API_KEY non impostata sul server."}

    user_content = text
    if last_tx:
        user_content = (
            f"[Ultima spesa registrata: {last_tx['description']} "
            f"{_fmt_eur(abs(last_tx['amount']))} · {last_tx['category']}]\n\n{text}"
        )

    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=PARSER_MODEL,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0,
                response_mime_type="application/json",
                response_schema=_response_schema(),
            ),
        )
        data = json.loads(resp.text)
    except Exception as e:  # google.genai.errors.APIError, JSON non valido, ...
        return {"tool": "errore", "messaggio": f"Errore Gemini: {e}"}

    azione = data.get("azione")

    if azione == "registra_spesa":
        return {
            "tool": "registra_spesa",
            "input": {
                "descrizione": data.get("descrizione", ""),
                "importo": data.get("importo", 0),
                "categoria": data.get("categoria", ""),
            },
        }

    if azione == "correggi_ultima" and last_tx:
        campo = data.get("campo_correzione")
        if campo not in ("importo", "categoria", "descrizione"):
            return {"tool": "non_pertinente", "input": {"motivo": "correzione senza campo"}}
        return {
            "tool": "correggi_ultima",
            "input": {
                "campo": campo,
                "nuovo_importo": data.get("nuovo_numero", 0),
                "nuova_categoria": data.get("nuovo_testo", "") if campo == "categoria" else "",
                "nuova_descrizione": data.get("nuovo_testo", "") if campo == "descrizione" else "",
            },
        }

    return {"tool": "non_pertinente", "input": {"motivo": "non è una spesa"}}


# ─── Comandi ────────────────────────────────────────────────────────────────

_HELP = (
    "FinanceD — bot spese\n\n"
    "Scrivi una spesa in linguaggio naturale:\n"
    "  «€8 bar boulevard»\n"
    "  «ho pagato 45 dal dentista»\n\n"
    "Comandi:\n"
    "/oggi — spese di oggi\n"
    "/settimana — ultimi 7 giorni\n"
    "/mese — dal 1° del mese\n"
    "/budget — budget del mese e quanto resta\n"
    "/ultima — ultima spesa registrata\n"
    "/cancella — cancella l'ultima spesa\n"
    "/aiuto — questo messaggio"
)


def _cmd_oggi(chat_id):
    today = _today_iso()
    items = _breakdown("date = ?", (today,))
    if not items:
        send_message(chat_id, "Oggi nessuna spesa registrata.")
        return
    total = sum(a for _, a in items)
    lines = [f"Spese di oggi — {_fmt_eur(total)}", ""]
    lines += [f"  {c}: {_fmt_eur(a)}" for c, a in items]
    send_message(chat_id, "\n".join(lines))


def _cmd_settimana(chat_id):
    end = date.today()
    start = end - timedelta(days=6)
    items = _breakdown("date BETWEEN ? AND ?", (start.isoformat(), end.isoformat()))
    if not items:
        send_message(chat_id, "Ultimi 7 giorni: nessuna spesa.")
        return
    total = sum(a for _, a in items)
    lines = [f"Ultimi 7 giorni — {_fmt_eur(total)}", ""]
    lines += [f"  {c}: {_fmt_eur(a)}" for c, a in items]
    send_message(chat_id, "\n".join(lines))


def _cmd_mese(chat_id):
    month = _today_iso()[:7]
    items = _breakdown("strftime('%Y-%m', date) = ?", (month,))
    if not items:
        send_message(chat_id, f"{month}: nessuna spesa registrata.")
        return
    total = sum(a for _, a in items)
    lines = [f"Spese di {month}", ""]
    lines += [f"  {c}: {_fmt_eur(a)}" for c, a in items]
    lines += ["", f"Totale: {_fmt_eur(total)}"]
    send_message(chat_id, "\n".join(lines))


def _cmd_budget(chat_id):
    month = _today_iso()[:7]
    budget = db.get_monthly_budget(month)
    spent = _spent_in_month(month)
    if not budget or budget.get("total") is None:
        send_message(
            chat_id,
            f"Nessun budget impostato per {month}.\n"
            f"Speso finora: {_fmt_eur(spent)}\n"
            f"Imposta il budget dall'app desktop (sezione Pianificazione).",
        )
        return
    total = float(budget["total"])
    left = total - spent
    verdict = "ancora disponibili" if left >= 0 else "OLTRE il budget di"
    send_message(
        chat_id,
        f"Budget {month}\n\n"
        f"  Impostato: {_fmt_eur(total)}\n"
        f"  Speso: {_fmt_eur(spent)}\n"
        f"  {verdict}: {_fmt_eur(abs(left))}",
    )


def _cmd_ultima(chat_id):
    raw = db.get_setting(_LAST_TX_KEY)
    tx = _get_tx(int(raw)) if raw else None
    if not tx:
        send_message(chat_id, "Nessuna spesa registrata di recente dal bot.")
        return
    send_message(
        chat_id,
        f"Ultima spesa: {tx['description']} {_fmt_eur(abs(tx['amount']))} · "
        f"{tx['category']} · {_fmt_date_it(tx['date'])}\n\n"
        f"Per correggerla scrivi ad es. «era 12 non 8» oppure «mettila in Svago». "
        f"Per cancellarla: /cancella",
    )


def _cmd_cancella(chat_id):
    raw = db.get_setting(_LAST_TX_KEY)
    tx = _get_tx(int(raw)) if raw else None
    if not tx:
        send_message(chat_id, "Niente da cancellare.")
        return
    db.delete_transaction(tx["id"])
    db.set_setting(_LAST_TX_KEY, "")
    send_message(
        chat_id,
        f"Cancellata — {tx['description']} {_fmt_eur(abs(tx['amount']))} · {tx['category']}",
    )


def _get_tx(tx_id: int) -> dict | None:
    rows = _rows("SELECT * FROM transactions WHERE id = ?", (tx_id,))
    return rows[0] if rows else None


# ─── Testo libero: spesa o correzione ──────────────────────────────────────

def _handle_text(chat_id, text: str):
    raw = db.get_setting(_LAST_TX_KEY)
    last_tx = _get_tx(int(raw)) if raw else None

    result = _interpret(text, last_tx)
    tool = result.get("tool")

    if tool == "errore":
        send_message(chat_id, f"Non riesco a interpretare il messaggio.\n{result['messaggio']}")
        return

    if tool == "registra_spesa":
        data = result["input"]
        desc = str(data["descrizione"]).strip() or "Spesa"
        amount = abs(float(data["importo"]))
        category = data["categoria"] if data["categoria"] in _EXPENSE_CATEGORIES else "Altro"
        new_id = _insert_expense(desc, amount, category)
        db.set_setting(_LAST_TX_KEY, str(new_id))

        today = _today_iso()
        today_total = _spent_between(today, today)
        month_total = _spent_in_month(today[:7])
        send_message(
            chat_id,
            f"Registrato — {desc} {_fmt_eur(amount)} · {category} · {_fmt_date_it(today)}\n"
            f"Oggi: {_fmt_eur(today_total)} · Questo mese: {_fmt_eur(month_total)}",
        )
        return

    if tool == "correggi_ultima":
        if not last_tx:
            send_message(chat_id, "Non c'è un'ultima spesa da correggere.")
            return
        data = result["input"]
        campo = data["campo"]
        if campo == "importo":
            new_amount = abs(float(data.get("nuovo_importo") or 0))
            if new_amount <= 0:
                send_message(chat_id, "Importo non valido.")
                return
            db.update_transaction(last_tx["id"], amount=-new_amount)
            send_message(
                chat_id,
                f"Corretto — {last_tx['description']} {_fmt_eur(new_amount)} · {last_tx['category']}",
            )
        elif campo == "categoria":
            new_cat = data.get("nuova_categoria") or ""
            if new_cat not in _EXPENSE_CATEGORIES:
                send_message(chat_id, "Categoria non riconosciuta.")
                return
            db.update_transaction(last_tx["id"], category=new_cat)
            send_message(chat_id, f"Categoria aggiornata → {new_cat}")
        elif campo == "descrizione":
            new_desc = (data.get("nuova_descrizione") or "").strip()
            if not new_desc:
                send_message(chat_id, "Descrizione non valida.")
                return
            db.update_transaction(last_tx["id"], description=new_desc)
            send_message(chat_id, f"Descrizione aggiornata → {new_desc}")
        return

    # non_pertinente
    send_message(
        chat_id,
        "Non sembra una spesa. Scrivi ad es. «€8 bar boulevard» oppure /aiuto per i comandi.",
    )


# ─── Entry point ────────────────────────────────────────────────────────────

_COMMANDS = {
    "/start": lambda cid: send_message(cid, _HELP),
    "/aiuto": lambda cid: send_message(cid, _HELP),
    "/help": lambda cid: send_message(cid, _HELP),
    "/oggi": _cmd_oggi,
    "/settimana": _cmd_settimana,
    "/mese": _cmd_mese,
    "/budget": _cmd_budget,
    "/ultima": _cmd_ultima,
    "/cancella": _cmd_cancella,
}


def handle_update(update: dict) -> None:
    """Gestisce un update Telegram. Non solleva: logga e basta."""
    message = update.get("message") or update.get("edited_message")
    if not message or "text" not in message:
        return

    chat = message.get("chat", {})
    chat_id = chat.get("id")

    # Sicurezza: solo il proprietario. Confronto come stringa perché la env var
    # è sempre stringa e chat_id è int.
    if str(chat_id) != str(ALLOWED_CHAT_ID):
        send_message(chat_id, "Questo bot è personale e non risponde a questo account.")
        print(f"[telegram] messaggio ignorato da chat_id non autorizzato: {chat_id}")
        return

    text = message["text"].strip()
    if not text:
        return

    if text.startswith("/"):
        cmd = text.split()[0].split("@")[0].lower()
        handler = _COMMANDS.get(cmd)
        if handler:
            handler(chat_id)
        else:
            send_message(chat_id, "Comando sconosciuto. /aiuto per la lista.")
        return

    _handle_text(chat_id, text)

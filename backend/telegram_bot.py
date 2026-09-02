"""Bot Telegram personale per registrare spese e consultare i totali dal telefono.

Non gira come processo a sé: è un modulo importato dal backend FastAPI
(`routes/telegram.py` espone il webhook). Telegram consegna gli update via
HTTPS a `POST /api/telegram/webhook`, quel route chiama `handle_update()` qui.

Scelte (vedi ADR.md → "Integrazione Telegram Bot"):
- Nessuna libreria `python-telegram-bot`: sono due sole chiamate HTTP alla Bot
  API (`sendMessage`, `setWebhook`), fatte con `requests` — già una dipendenza.
  Stessa filosofia di `turso_client.py` (client HTTP fatto in casa, zero build
  native).
- Parsing dei messaggi in linguaggio naturale con Claude (SDK `anthropic`), non
  Gemini: la chiave API Anthropic è già prevista nella config del progetto.
- Il bot risponde SOLO a `TELEGRAM_CHAT_ID`: chiunque altro conosca il nome del
  bot riceve un rifiuto secco.
- Le spese sono salvate con importo NEGATIVO, come fa l'app desktop per le
  spese manuali (`frontend/.../Transazioni.svelte`: default -10). Entrate e
  rimborsi restano positivi.
"""
import os
from datetime import date, timedelta

import requests

import database as db
from importers.helpers import CATEGORIES

# ─── Config da ambiente ──────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
# Default esplicito su Opus 5. Per un parser di frasi brevi è sovradimensionato:
# `claude-haiku-4-5` costa una frazione e basta e avanza — impostare
# TELEGRAM_PARSER_MODEL per cambiarlo senza toccare il codice.
PARSER_MODEL = os.getenv("TELEGRAM_PARSER_MODEL", "claude-opus-5")

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


# ─── Interpretazione messaggi (Claude) ──────────────────────────────────────

_TOOLS = [
    {
        "name": "registra_spesa",
        "description": "Registra una nuova spesa personale descritta nel messaggio.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "descrizione": {
                    "type": "string",
                    "description": "Descrizione breve della spesa, es. 'Bar Boulevard', 'Caffè', 'Dentista'.",
                },
                "importo": {
                    "type": "number",
                    "description": "Importo speso in euro, sempre positivo.",
                },
                "categoria": {"type": "string", "enum": _EXPENSE_CATEGORIES},
            },
            "required": ["descrizione", "importo", "categoria"],
        },
    },
    {
        "name": "correggi_ultima",
        "description": (
            "Corregge un campo dell'ultima spesa registrata. Usare quando il "
            "messaggio si riferisce chiaramente a una correzione (es. 'era 54 "
            "non 45', 'mettila in Persona', 'la descrizione è sbagliata')."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "campo": {"type": "string", "enum": ["importo", "categoria", "descrizione"]},
                "nuovo_importo": {
                    "type": "number",
                    "description": "Nuovo importo positivo in euro, se campo = importo. Altrimenti 0.",
                },
                "nuova_categoria": {
                    "type": "string",
                    "enum": _EXPENSE_CATEGORIES + [""],
                    "description": "Nuova categoria, se campo = categoria. Altrimenti stringa vuota.",
                },
                "nuova_descrizione": {
                    "type": "string",
                    "description": "Nuova descrizione, se campo = descrizione. Altrimenti stringa vuota.",
                },
            },
            "required": ["campo", "nuovo_importo", "nuova_categoria", "nuova_descrizione"],
        },
    },
    {
        "name": "non_pertinente",
        "description": "Il messaggio non è né una spesa né una correzione.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"motivo": {"type": "string"}},
            "required": ["motivo"],
        },
    },
]

_SYSTEM_PROMPT = (
    "Sei l'assistente di un bot Telegram personale per registrare spese in "
    "italiano. Ogni messaggio dell'utente è o una nuova spesa ('€8 bar "
    "boulevard', 'ho pagato 45 dal dentista', '5 euro caffè contanti') o una "
    "correzione dell'ultima spesa ('era 54 non 45', 'mettila in Persona'). "
    "Scegli sempre esattamente uno strumento. Per le spese: estrai importo "
    "(sempre positivo), una descrizione breve e pulita, e la categoria più "
    "adatta tra quelle disponibili. Non inventare spese se il messaggio non ne "
    "contiene una."
)


def _interpret(text: str, last_tx: dict | None) -> dict:
    """Ritorna {'tool': <nome>, 'input': {...}} oppure {'tool': 'errore', ...}."""
    try:
        import anthropic
    except ImportError:
        return {"tool": "errore", "messaggio": "SDK anthropic non installato sul server."}

    if not os.getenv("ANTHROPIC_API_KEY"):
        return {"tool": "errore", "messaggio": "ANTHROPIC_API_KEY non impostata sul server."}

    tools = [t for t in _TOOLS if t["name"] != "correggi_ultima" or last_tx]
    user_content = text
    if last_tx:
        user_content = (
            f"[Ultima spesa registrata: {last_tx['description']} "
            f"{_fmt_eur(abs(last_tx['amount']))} · {last_tx['category']}]\n\n{text}"
        )

    try:
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=PARSER_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            tools=tools,
            # `auto` (non `any`): compatibile con ogni modello, incluse le
            # famiglie che rifiutano il tool_choice forzato. Con 3 strumenti che
            # coprono tutti i casi e il system prompt, il modello ne sceglie
            # sempre uno.
            tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": user_content}],
        )
    except anthropic.APIError as e:
        return {"tool": "errore", "messaggio": f"Errore Claude: {e}"}

    for block in resp.content:
        if block.type == "tool_use":
            # Gli input dei tool possono arrivare con escaping JSON particolare:
            # affidarsi a block.input (già deserializzato dall'SDK).
            return {"tool": block.name, "input": dict(block.input)}
    return {"tool": "non_pertinente", "input": {"motivo": "nessuno strumento scelto"}}


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

import re
import io
import pandas as pd
from datetime import datetime

CATEGORIES = [
    "Bar & Ristoranti",
    "Spesa",
    "Trasporti",
    "Auto",
    "Abbonamenti",
    "Utenze",
    "Affitto",
    "Salute",
    "Persona",
    "Svago",
    "Shopping",
    "Riparazioni",
    "Sigarette",
    "Regali",
    "Vacanza",
    "Entrata",
    "Rimborso ricevuto",
    "Altro",
]

# Palette allineata al wireframe (tema chiaro, frontend/dist/assets/): ogni
# colore è la tinta "satura" del badge — il frontend calcola lo sfondo
# pastello applicando una bassa opacità a questo stesso colore, così le 18
# categorie condividono lo stesso trattamento visivo dei 6-7 esempi nel
# wireframe (badge chiaro + testo colorato) senza dover mantenere due valori
# per categoria.
CAT_COLORS = {
    "Bar & Ristoranti":  "#c2410c",  # orange-700
    "Spesa":             "#4d7c0f",  # lime-700
    "Trasporti":         "#0369a1",  # sky-700
    "Auto":              "#4338ca",  # indigo-700
    "Abbonamenti":       "#1d4ed8",  # blue-700
    "Utenze":            "#b45309",  # amber-700
    "Affitto":           "#44403c",  # stone-700
    "Salute":            "#15803d",  # green-700
    "Persona":           "#be123c",  # rose-700
    "Svago":             "#6d28d9",  # violet-700
    "Shopping":          "#be185d",  # pink-700
    "Riparazioni":       "#334155",  # slate-700
    "Sigarette":         "#b91c1c",  # red-700
    "Regali":            "#a21caf",  # fuchsia-700
    "Vacanza":           "#7e22ce",  # purple-700
    "Entrata":           "#047857",  # emerald-700
    "Rimborso ricevuto": "#0f766e",  # teal-700
    "Altro":             "#0e7490",  # cyan-700
}

def categorize(desc: str, amount: float) -> str:
    if amount > 0:
        return "Entrata"
    d = desc.lower()

    # Prelievo contanti — non categorizzare (usato per bollette/affitto in contanti)
    if re.search(r"prelievo di contanti", d):
        return "Altro"

    # Abbonamenti
    if re.search(r"netflix|spotify|prime|disney|claude|chatgpt|nordvpn|google one|icloud|apple\.com|apple com|apple|dazn|now tv|hbo|fastweb|tim |vodafone|wind|tre |iliad|macpaw|paddle|teaming|fundaci", d):
        return "Abbonamenti"

    # Utenze
    if re.search(r"enel|eni energia|edison|hera|luce |gas |acqua |affitto|condominio|enercoop", d):
        return "Utenze"

    # Auto
    if re.search(r"easypark|parcheggio|parking|benzina|carburante|ip italiana|q8|tamoil|vega carburanti|autostrade|telepass|agip|esso|sara assicurazioni|assicuraz|boso.parcheggio|p073", d):
        return "Auto"

    # Trasporti
    if re.search(r"tper|trenitalia|italo|taxi|uber|bolt|atm |atc |bus |treno|metro|frecciarossa|freccia|flixbus|autobus|ryanair|easyjet|wizz|vueling|ita airways|kiwi\.com|cotabo|blablacar", d):
        return "Trasporti"

    # Salute
    if re.search(r"farmacia|dottore|dentista|medico|salute|visita|esame |laboratorio|analisi|ottico|fisioterapia|ospedale", d):
        return "Salute"

    # Sigarette — prima di Persona
    if re.search(r"svapo|vape|sigarett|tabacch|smoke", d):
        return "Sigarette"

    # Persona
    if re.search(r"parrucchier|barbiere|manicure|pedicure|estetista|nail|beauty|psicologo|psicolog|palestra|gym |wellness|spa |profumeria|kurva ink|tattoo|tatuaggi", d):
        return "Persona"

    # Spesa
    if re.search(r"conad|coop|esselunga|pam |lidl|aldi|carrefour|eurospin|penny|tigros|supermercato|market|iper|simply|bennet|caab|agroalimentare|latterie|panini|gastronomia", d):
        return "Spesa"

    # Bar & Ristoranti
    if re.search(r"ristorante|trattoria|osteria|pizzeria|sushi|burger|mcdonalds|kfc|bar |caffe|cafe |bistrot|gelateria|pasticceria|lunch|brunch|just eat|deliveroo|glovo|uber eat|food|taverna|locanda|brasserie|pub |griglia|braceria|cremeria|ananasso|bodega|boulevard|asia fusion|miro |effea|buonristoro|provenzano|antonio prov", d):
        return "Bar & Ristoranti"

    # Svago
    if re.search(r"cinema|teatro|concert|museum|museo|libro|steam|playstation|xbox|gioco|ticketmaster|ticketone|bowling|escape room|waynabox|holidu|airbnb|booking\.com|hostel|hotel", d):
        return "Svago"

    # Riparazioni
    if re.search(r"lavanderia|sartoria|sarta|riparazione|calzolaio|idraulico|elettricista|fabbro|pulizie", d):
        return "Riparazioni"

    # Shopping
    if re.search(r"zara|h&m|primark|amazon|zalando|shein|decathlon|ikea|tiger|oysho|pull.bear|bershka|mango|stradivarius|footlocker|nike|adidas|calzedonia|leroy merlin|action|1\+1|mio sas", d):
        return "Shopping"

    # Regali / trasferimenti personali
    if re.search(r"paypal \*|laura.castellano|anna montanaro|gift|regalo", d):
        return "Regali"

    return "Altro"


# ─── Revolut PDF parser ──────────────────────────────────────────────────────

MONTHS_IT = {
    "gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
    "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12
}

_SKIP = re.compile(
    r"prelievo da pocket|accredita eur .+ da eur|a eur conto deposito"
    r"|da eur conto deposito|interessi netti pagati",
    re.IGNORECASE
)
_STIPENDIO = re.compile(r"italian break", re.IGNORECASE)
_KEEP_CONTO = re.compile(
    r"prelievo di contanti|pagamento da parte di|pagamento da (?!italian break)",
    re.IGNORECASE
)

def _parse_amt(s):
    if not s:
        return None
    try:
        return float(s.replace(".", "").replace(",", ".").replace("€", "").strip())
    except Exception:
        return None

def _parse_date_it(s):
    m = re.match(r"(\d{1,2})\s+(\w{3})\s+(\d{4})", s.strip(), re.IGNORECASE)
    if not m:
        return None
    day, mon, year = m.groups()
    month = MONTHS_IT.get(mon.lower())
    if not month:
        return None
    return f"{year}-{month:02d}-{int(day):02d}"

def parse_revolut_pdf(file_bytes: bytes) -> list[dict]:
    try:
        import pdfplumber, io as _io
        with pdfplumber.open(_io.BytesIO(file_bytes)) as pdf:
            full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except ImportError:
        return []

    lines = full_text.splitlines()
    records = []
    seen_ids = set()
    current_section = None

    for i, line in enumerate(lines):
        line = line.strip()

        if "Transazioni dei Pocket" in line:
            current_section = "pocket"
            continue
        elif "Transazioni del conto" in line and "Pocket" not in line:
            current_section = "conto"
            continue
        elif "Transazioni deposito" in line:
            current_section = "deposito"
            continue

        if current_section == "deposito":
            continue

        date_m = re.match(
            r"^(\d{1,2}\s+(?:gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)\s+\d{4})\s+(.+)",
            line, re.IGNORECASE
        )
        if not date_m:
            continue

        date_str, rest = date_m.group(1), date_m.group(2)
        parsed_date = _parse_date_it(date_str)
        if not parsed_date:
            continue

        amounts = re.findall(r"[\d\.]+,\d{2}€", rest)
        desc = re.sub(r"[\d\.]+,\d{2}€", "", rest).strip()
        desc = re.sub(r"\s+", " ", desc).strip()

        tx_id = None
        for j in range(i+1, min(i+4, len(lines))):
            id_m = re.search(r"ID transazione:\s*([a-f0-9\-]+)", lines[j])
            if id_m:
                tx_id = id_m.group(1)
                break

        if tx_id and tx_id in seen_ids:
            continue
        if tx_id:
            seen_ids.add(tx_id)

        if _SKIP.search(desc):
            continue

        if current_section == "conto":
            if not _STIPENDIO.search(desc) and not _KEEP_CONTO.search(desc):
                continue

        if len(amounts) < 2:
            continue

        amt_val = _parse_amt(amounts[0])
        if not amt_val:
            continue

        is_entrata = bool(
            _STIPENDIO.search(desc)
            or re.search(r"pagamento da parte di|pagamento da paypal", desc, re.IGNORECASE)
        )
        amount = amt_val if is_entrata else -amt_val

        if not desc or amount == 0:
            continue

        records.append({
            "date":        parsed_date,
            "description": desc,
            "amount":      round(amount, 2),
            "category":    categorize(desc, amount),
            "source":      "revolut_pdf",
        })

    return records


def parse_revolut_csv(file_bytes: bytes) -> list[dict]:
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")

    df = pd.read_csv(io.StringIO(text))
    df.columns = [c.strip() for c in df.columns]

    col_aliases = {
        "date": ["Data di completamento", "Data di inizio", "Completed Date", "Started Date", "Date"],
        "description": ["Descrizione", "Description", "Merchant"],
        "amount": ["Importo", "Amount"],
    }

    col_map = {}
    for key, aliases in col_aliases.items():
        for alias in aliases:
            if alias in df.columns:
                col_map[key] = alias
                break

    if not all(k in col_map for k in ["date", "description", "amount"]):
        return []

    records = []
    for _, row in df.iterrows():
        try:
            raw_date = str(row[col_map["date"]]).strip()
            parsed_date = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    parsed_date = datetime.strptime(raw_date[:19], fmt).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
            if not parsed_date:
                continue

            desc   = str(row[col_map["description"]]).strip()
            amount = float(str(row[col_map["amount"]]).replace(",", ".").replace(" ", ""))

            stato = str(row.get("State", row.get("Stato", ""))).upper()
            if stato and stato not in ("COMPLETATO", "COMPLETED", "REVERTATO", "REVERTED"):
                continue

            records.append({
                "date":        parsed_date,
                "description": desc,
                "amount":      amount,
                "category":    categorize(desc, amount),
                "source":      "revolut",
            })
        except Exception:
            continue

    return records


# ─── Note parser for work shifts ─────────────────────────────────────────────

def parse_note_shifts(text: str) -> list[dict]:
    shifts = []
    current_year = datetime.now().year

    pattern = re.compile(
        r"(\d{1,2}[./]\d{1,2})"
        r"\s+"
        r"(\d{1,2}:\d{2})"
        r"\s*[-–]\s*"
        r"(\d{1,2}(?::\d{2})?)"
        r"(?:\s*\(([^)]+)\))?"
    )

    for line in text.splitlines():
        m = pattern.search(line)
        if not m:
            continue
        date_str, start, end_raw, dur_str = m.groups()

        end = end_raw if ":" in end_raw else end_raw + ":00"

        sep = "." if "." in date_str else "/"
        try:
            day, month = map(int, date_str.split(sep))
            parsed_date = datetime(current_year, month, day).strftime("%Y-%m-%d")
        except Exception:
            continue

        try:
            sh, sm = map(int, start.split(":"))
            eh, em = map(int, end.split(":"))
            hours = ((eh * 60 + em) - (sh * 60 + sm)) / 60
            if hours < 0:
                hours += 24
            hours = round(hours, 2)
        except Exception:
            hours = 0.0

        if hours <= 0:
            continue

        shifts.append({
            "date":       parsed_date,
            "start_time": start,
            "end_time":   end,
            "hours":      hours,
            "note":       dur_str or "",
        })

    return shifts

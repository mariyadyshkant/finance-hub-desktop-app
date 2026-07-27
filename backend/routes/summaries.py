import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

import database as db

router = APIRouter()

# Mapping categorie Notion → categorie app (vedi BRIEF.md)
NOTION_MAP = {
    "bar/ristoranti/eventi": "Bar & Ristoranti",
    "bar/ristoranti": "Bar & Ristoranti",
    "svago": "Svago",
    "trasporti": "Trasporti",
    "utenze/tasse": "Utenze",
    "utenze": "Utenze",
    "spesa": "Spesa",
    "salute": "Salute",
    "shopping": "Shopping",
    "vacanze": "Vacanza",
    "vacanza": "Vacanza",
    "auto/bici": "Auto",
    "auto": "Auto",
    "persona": "Persona",
    "regali": "Regali",
    "abbonamenti": "Abbonamenti",
    "riparazioni": "Riparazioni",
    "sigarette": "Sigarette",
}

SKIP_KEYS = {
    "senza affitto", "mensile", "evitabile", "spese che potevo evitare",
    "mese", "totale", "affitto",
}


def parse_notion_md(text: str):
    """Parse l'export markdown di Notion in {mese, {categoria: importo}}."""
    result = {}
    month_str = None

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.lower().startswith("mese:"):
            raw = line.split(":", 1)[1].strip()
            for fmt in ("%B %d, %Y", "%d %B %Y", "%Y-%m-%d"):
                try:
                    month_str = datetime.strptime(raw, fmt).strftime("%Y-%m")
                    break
                except ValueError:
                    continue
            continue

        m = re.match(r"^(.+?):\s*[€$]?([\d,\.]+)", line)
        if not m:
            continue

        key = m.group(1).strip().lower()
        if key in SKIP_KEYS:
            continue

        try:
            amt_str = m.group(2).replace(",", "")
            if re.search(r"\d\.\d{3}", m.group(2)):
                amt_str = m.group(2).replace(".", "").replace(",", ".")
            amount = float(amt_str)
        except ValueError:
            continue

        if amount == 0:
            continue

        mapped = NOTION_MAP.get(key)
        if mapped:
            result[mapped] = amount

    return month_str, result


class ParseIn(BaseModel):
    text: str


class SummaryIn(BaseModel):
    month: str
    category: str
    amount: float
    source: str = "notion"


@router.get("")
def list_summaries(month: Optional[str] = None):
    return db.get_monthly_summaries(month)


@router.get("/months")
def list_summary_months():
    return db.get_summary_months()


@router.post("/parse")
def parse_notion_export(payload: ParseIn):
    month_str, categories = parse_notion_md(payload.text)
    return {"month": month_str, "categories": categories}


@router.post("")
def upsert_summary(s: SummaryIn):
    db.upsert_monthly_summary(s.month, s.category, s.amount, s.source)
    return {"ok": True}


@router.delete("/{month}")
def delete_summary_month(month: str):
    db.delete_monthly_summary_month(month)
    return {"ok": True}

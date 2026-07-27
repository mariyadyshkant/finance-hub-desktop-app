from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

import database as db
from importers.helpers import parse_revolut_pdf, parse_revolut_csv

router = APIRouter()


class TransactionIn(BaseModel):
    date: str
    description: str
    amount: float
    category: str
    source: str = "manual"
    note: str = ""


class TransactionUpdate(BaseModel):
    date: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    note: Optional[str] = None


@router.get("")
def list_transactions(month: Optional[str] = None):
    return db.get_transactions(month)


@router.get("/months")
def list_months():
    return db.get_available_months()


@router.post("")
def create_transaction(tx: TransactionIn):
    db.add_transaction(tx.date, tx.description, tx.amount, tx.category, tx.source, tx.note)
    return {"ok": True}


@router.put("/{tx_id}")
def edit_transaction(tx_id: int, tx: TransactionUpdate):
    fields = {k: v for k, v in tx.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Nessun campo da aggiornare")
    db.update_transaction(tx_id, **fields)
    return {"ok": True}


@router.delete("/{tx_id}")
def remove_transaction(tx_id: int):
    db.delete_transaction(tx_id)
    return {"ok": True}


@router.post("/import")
def import_transactions(records: list[TransactionIn]):
    inserted = db.import_transactions_bulk([r.model_dump() for r in records])
    return {"inserted": inserted}


@router.post("/parse-revolut")
async def parse_revolut(file: UploadFile):
    file_bytes = await file.read()
    if file.filename.endswith(".pdf"):
        records = parse_revolut_pdf(file_bytes)
    else:
        records = parse_revolut_csv(file_bytes)
    return {"records": records}

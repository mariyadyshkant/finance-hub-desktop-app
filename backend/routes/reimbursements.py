from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import database as db

router = APIRouter()


class ReimbursementIn(BaseModel):
    date: str
    description: str
    amount: float
    from_person: str
    note: str = ""
    transaction_id: Optional[int] = None


class ReimbursementUpdate(BaseModel):
    date: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    from_person: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


@router.get("")
def list_reimbursements(status: Optional[str] = None):
    return db.get_reimbursements(status)


@router.post("")
def create_reimbursement(r: ReimbursementIn):
    db.add_reimbursement(r.date, r.description, r.amount, r.from_person, r.note, r.transaction_id)
    return {"ok": True}


@router.put("/{r_id}")
def edit_reimbursement(r_id: int, r: ReimbursementUpdate):
    fields = {k: v for k, v in r.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Nessun campo da aggiornare")
    db.update_reimbursement(r_id, **fields)
    return {"ok": True}


@router.delete("/{r_id}")
def remove_reimbursement(r_id: int):
    db.delete_reimbursement(r_id)
    return {"ok": True}

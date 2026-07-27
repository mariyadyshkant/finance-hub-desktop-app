from fastapi import APIRouter
from pydantic import BaseModel

import database as db

router = APIRouter()


class SavingsIn(BaseModel):
    date: str
    amount: float
    label: str = ""
    note: str = ""


@router.get("")
def list_savings():
    return db.get_savings()


@router.post("")
def create_savings_entry(s: SavingsIn):
    db.add_savings_entry(s.date, s.amount, s.label, s.note)
    return {"ok": True}


@router.delete("/{s_id}")
def remove_savings_entry(s_id: int):
    db.delete_savings_entry(s_id)
    return {"ok": True}

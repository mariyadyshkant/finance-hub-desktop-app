from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

import database as db
from importers.helpers import parse_note_shifts

router = APIRouter()


class ShiftIn(BaseModel):
    date: str
    hours: float
    start_time: str = ""
    end_time: str = ""
    note: str = ""


class ShiftText(BaseModel):
    text: str


@router.get("")
def list_shifts(month: Optional[str] = None):
    return db.get_shifts(month)


@router.post("")
def create_shift(s: ShiftIn):
    db.add_shift(s.date, s.hours, s.start_time, s.end_time, s.note)
    return {"ok": True}


@router.delete("/{shift_id}")
def remove_shift(shift_id: int):
    db.delete_shift(shift_id)
    return {"ok": True}


@router.post("/parse")
def parse_shifts_text(payload: ShiftText):
    return {"shifts": parse_note_shifts(payload.text)}


@router.post("/import")
def import_shifts(shifts: list[ShiftIn]):
    db.add_shifts_bulk([s.model_dump() for s in shifts])
    return {"inserted": len(shifts)}

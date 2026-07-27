import os

import requests
from fastapi import APIRouter, HTTPException

router = APIRouter()

BASE_URL = "https://secure.splitwise.com/api/v3.0"


def _headers():
    api_key = os.getenv("SPLITWISE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="SPLITWISE_API_KEY non configurata in backend/.env")
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _sw_get(endpoint: str):
    try:
        r = requests.get(BASE_URL + endpoint, headers=_headers(), timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Errore di connessione a Splitwise: {e}")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail="Chiave API non valida o errore Splitwise")
    return r.json()


@router.get("/user")
def get_current_user():
    return _sw_get("/get_current_user").get("user", {})


@router.get("/friends")
def get_friends():
    return _sw_get("/get_friends").get("friends", [])


@router.get("/groups")
def get_groups():
    groups = _sw_get("/get_groups").get("groups", [])
    return [g for g in groups if g.get("id") != 0]


@router.get("/expenses")
def get_expenses(limit: int = 20):
    expenses = _sw_get(f"/get_expenses?limit={limit}").get("expenses", [])
    return [e for e in expenses if not e.get("deleted_at")]

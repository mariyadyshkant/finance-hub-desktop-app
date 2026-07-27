"""Client minimale per l'API HTTP di Turso (protocollo Hrana su /v2/pipeline).

Espone la stessa interfaccia usata da database.py per sqlite3.Connection/Cursor
(execute, executemany, fetchall, fetchone, description, commit, close) così il
resto del codice non deve sapere se sta parlando con SQLite locale o Turso.

Nessuna dipendenza nuova: solo `requests`, già usata per Splitwise. Evita
libsql_experimental, la cui build da sorgente richiede un toolchain Rust che
su macOS fallisce senza GNU coreutils installati (vedi ADR.md).
"""
import base64

import requests


def _encode_value(v):
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": str(int(v))}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    if isinstance(v, (bytes, bytearray)):
        return {"type": "blob", "base64": base64.b64encode(v).decode()}
    return {"type": "text", "value": str(v)}


def _decode_value(v):
    t = v.get("type")
    if t == "null":
        return None
    if t == "integer":
        return int(v["value"])
    if t == "float":
        return float(v["value"])
    if t == "blob":
        return base64.b64decode(v["base64"])
    return v.get("value")


class TursoCursor:
    def __init__(self, result=None):
        result = result or {}
        cols = result.get("cols", [])
        self.description = [(c["name"],) for c in cols]
        self._rows = [
            tuple(_decode_value(v) for v in row) for row in result.get("rows", [])
        ]
        self._pos = 0

    def fetchall(self):
        rows = self._rows[self._pos:]
        self._pos = len(self._rows)
        return rows

    def fetchone(self):
        if self._pos >= len(self._rows):
            return None
        row = self._rows[self._pos]
        self._pos += 1
        return row


class TursoConnection:
    def __init__(self, url, auth_token, timeout=15):
        http_url = url.replace("libsql://", "https://", 1)
        self._pipeline_url = f"{http_url}/v2/pipeline"
        self._headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        self._timeout = timeout

    def _pipeline(self, steps):
        body = {"requests": steps + [{"type": "close"}]}
        resp = requests.post(
            self._pipeline_url, headers=self._headers, json=body, timeout=self._timeout
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for step in data.get("results", []):
            if step.get("type") == "error":
                raise RuntimeError(f"Turso error: {step.get('error')}")
            response = step.get("response") or {}
            if response.get("type") == "execute":
                results.append(response.get("result", {}))
        return results

    def execute(self, sql, params=()):
        step = {"type": "execute", "stmt": {"sql": sql, "args": [_encode_value(p) for p in params]}}
        results = self._pipeline([step])
        return TursoCursor(results[0] if results else None)

    def executemany(self, sql, seq_of_params):
        steps = [
            {"type": "execute", "stmt": {"sql": sql, "args": [_encode_value(p) for p in params]}}
            for params in seq_of_params
        ]
        if steps:
            self._pipeline(steps)
        return TursoCursor()

    def commit(self):
        # Ogni chiamata a /v2/pipeline è già atomica e persistita lato server —
        # nessuna transazione esplicita da chiudere lato client.
        pass

    def close(self):
        pass

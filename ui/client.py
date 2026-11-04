"""Client HTTP pour l'API — utilisé par l'interface Streamlit."""
from __future__ import annotations

from typing import Any

import httpx

API_URL = "http://127.0.0.1:8000"
TIMEOUT = 10.0


def _get(endpoint: str) -> dict[str, Any]:
    try:
        r = httpx.get(f"{API_URL}{endpoint}", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        raise ConnectionError("API injoignable — lancez d'abord : uvicorn api.main:app --reload")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Erreur API {e.response.status_code} : {e.response.text}")


def _post(endpoint: str, data: dict) -> dict[str, Any]:
    try:
        r = httpx.post(f"{API_URL}{endpoint}", json=data, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        raise ConnectionError("API injoignable — lancez d'abord : uvicorn api.main:app --reload")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Erreur API {e.response.status_code} : {e.response.text}")


def health() -> dict:
    return _get("/health")

def etat_usine() -> dict:
    return _get("/usine/etat")

def analyser_usine() -> dict:
    return _get("/usine/analyser")

def lister_agents() -> dict:
    return _get("/agents")

def rapport_agent(nom: str) -> dict:
    return _get(f"/agents/{nom}")

def analyser_agent(nom: str) -> dict:
    return _get(f"/agents/{nom}/analyser")

def historique_messages(n: int = 50) -> dict:
    return _get(f"/messages?n={n}")

def historique_alertes(n: int = 50) -> dict:
    return _get(f"/alertes?n={n}")

def historique_decisions(n: int = 20) -> dict:
    return _get(f"/decisions?n={n}")

def commande_machine(machine_id: str, action: str, raison: str) -> dict:
    return _post("/machines/commande", {
        "machine_id": machine_id,
        "action": action,
        "raison": raison
    })

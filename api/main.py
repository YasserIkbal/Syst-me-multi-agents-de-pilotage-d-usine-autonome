"""API FastAPI — Système Multi-Agents Usine Autonome.

Endpoints :
    GET  /health                   → santé de l'API
    GET  /usine/etat               → état complet de l'usine
    GET  /usine/analyser           → déclenche une analyse immédiate
    GET  /agents                   → liste tous les agents
    GET  /agents/{nom}             → rapport détaillé d'un agent
    GET  /agents/{nom}/analyser    → analyse immédiate d'un agent
    GET  /messages                 → historique des messages inter-agents
    GET  /alertes                  → historique des alertes
    GET  /decisions                → historique des décisions superviseur
    POST /machines/commande        → commande manuelle sur une machine
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    HealthReponse, EtatUsineReponse, RapportAgentReponse,
    AnalyseDemandeReponse, MessageHistorique, CommandeManuelle, CommandeReponse
)
from app import __version__

MODELS = Path(__file__).resolve().parents[1] / "models"


def _orchestrateur():
    """Retourne l'orchestrateur initialisé (erreur claire si les modèles manquent)."""
    if not (MODELS / "metrics.json").exists():
        raise HTTPException(
            status_code=503,
            detail="Modèles ML absents. Lancez : python scripts/generate_data.py && python scripts/train_models.py"
        )
    from app.orchestrator import Orchestrateur
    orch = Orchestrateur.instance()
    if not orch._demarre:
        orch.demarrer()
    return orch


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Gestion du cycle de vie : démarrage et arrêt propre des agents."""
    # Démarrage
    try:
        _orchestrateur()
    except HTTPException:
        pass  # Les données seront générées par l'utilisateur
    yield
    # Arrêt
    try:
        from app.orchestrator import Orchestrateur
        if Orchestrateur._instance:
            Orchestrateur._instance.arreter()
    except Exception:
        pass


app = FastAPI(
    title="Usine Autonome — API Multi-Agents",
    description="API de pilotage du système multi-agents de l'usine autonome.",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS pour l'interface Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ──────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthReponse, tags=["Système"])
def health() -> HealthReponse:
    """Vérifie que l'API est opérationnelle."""
    try:
        orch = _orchestrateur()
        nb_actifs = sum(1 for a in orch.agents.values() if a._actif)
    except HTTPException:
        nb_actifs = 0
    return HealthReponse(
        statut="OK",
        version=__version__,
        agents_actifs=nb_actifs,
        systeme="Usine Autonome — Système Multi-Agents"
    )


# ─── Usine ───────────────────────────────────────────────────────────────────

@app.get("/usine/etat", tags=["Usine"])
def etat_usine() -> dict[str, Any]:
    """Retourne l'état complet de l'usine (snapshot temps réel)."""
    orch = _orchestrateur()
    return orch.etat_usine()


@app.get("/usine/analyser", tags=["Usine"])
def analyser_usine() -> dict[str, Any]:
    """Déclenche une analyse immédiate de tous les agents et retourne les résultats."""
    orch = _orchestrateur()
    resultats = orch.analyser_tous()
    return {
        "horodatage": datetime.now().isoformat(),
        "resultats": resultats,
        "superviseur": resultats.get("SupervisorAgent", {})
    }


# ─── Agents ──────────────────────────────────────────────────────────────────

@app.get("/agents", tags=["Agents"])
def lister_agents() -> dict[str, Any]:
    """Liste tous les agents avec leur statut courant."""
    orch = _orchestrateur()
    return {
        "agents": [
            {
                "nom": nom,
                "actif": agent._actif,
                "cycles": agent._compteur_cycles,
                "statut": agent._derniere_analyse.get("statut", "EN_ATTENTE"),
                "horodatage": agent._derniere_analyse.get("horodatage", "")
            }
            for nom, agent in orch.agents.items()
        ]
    }


@app.get("/agents/{nom}", tags=["Agents"])
def rapport_agent(nom: str) -> dict[str, Any]:
    """Rapport détaillé d'un agent spécifique."""
    orch = _orchestrateur()
    try:
        return orch.rapport_agent(nom)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/agents/{nom}/analyser", tags=["Agents"])
def analyser_agent(nom: str) -> dict[str, Any]:
    """Déclenche une analyse immédiate d'un agent spécifique."""
    orch = _orchestrateur()
    agent = orch.agents.get(nom)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{nom}' introuvable")
    try:
        resultat = agent.analyser()
        return {"agent": nom, "horodatage": datetime.now().isoformat(), "resultat": resultat}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur analyse {nom} : {e}")


# ─── Messages & Historique ───────────────────────────────────────────────────

@app.get("/messages", tags=["Communication"])
def historique_messages(n: int = Query(default=50, ge=1, le=500)) -> dict[str, Any]:
    """Historique des messages échangés entre agents (traçabilité)."""
    orch = _orchestrateur()
    messages = orch.historique_messages(n)
    return {"total": len(messages), "messages": messages}


@app.get("/alertes", tags=["Communication"])
def historique_alertes(n: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    """Historique des alertes émises par tous les agents."""
    orch = _orchestrateur()
    superviseur = orch.agents["SupervisorAgent"]
    alertes = superviseur.historique_alertes(n)
    return {"total": len(alertes), "alertes": alertes}


@app.get("/decisions", tags=["Communication"])
def historique_decisions(n: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    """Historique des décisions prises par l'agent superviseur."""
    orch = _orchestrateur()
    superviseur = orch.agents["SupervisorAgent"]
    decisions = superviseur.historique_decisions(n)
    return {"total": len(decisions), "decisions": decisions}


# ─── Commandes manuelles ─────────────────────────────────────────────────────

@app.post("/machines/commande", response_model=CommandeReponse, tags=["Machines"])
def commande_machine(commande: CommandeManuelle) -> CommandeReponse:
    """Envoie une commande manuelle à une machine (simulation)."""
    orch = _orchestrateur()
    # Publier la commande sur le bus pour que les agents la reçoivent
    from agents.base import Message
    orch.bus.publier(Message(
        expediteur="API_OPERATEUR",
        destinataire="TOUS",
        type_message="COMMANDE",
        contenu={
            "machine": commande.machine_id,
            "action": commande.action,
            "raison": commande.raison
        },
        priorite=2 if commande.action in ("ARRETER", "MAINTENANCE") else 1
    ))
    return CommandeReponse(
        succes=True,
        machine_id=commande.machine_id,
        action=commande.action,
        message=f"Commande {commande.action} envoyée à {commande.machine_id}",
        horodatage=datetime.now().isoformat()
    )

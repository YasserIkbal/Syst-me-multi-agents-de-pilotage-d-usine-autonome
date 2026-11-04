"""Schémas Pydantic — contrats d'entrée/sortie de l'API."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

StatutUsine = Literal["OK", "ALERTE", "CRITIQUE", "INCONNU", "EN_ATTENTE"]
DecisionUsine = Literal[
    "FONCTIONNEMENT_NORMAL", "ACTION_PLANIFIEE",
    "SURVEILLANCE_RENFORCEE", "INTERVENTION_IMMEDIATE",
    "ARRET_D_URGENCE", "EN_ATTENTE"
]


class SanteUsine(BaseModel):
    score_global: float = Field(ge=0, le=100, description="Score de santé 0–100")
    niveau: str
    scores_par_agent: dict[str, float] = {}


class EtatUsineReponse(BaseModel):
    horodatage: str
    systeme_actif: bool
    nb_agents: int
    sante_usine: SanteUsine | dict
    decision_courante: DecisionUsine | str
    message_decision: str
    statuts: dict[str, str]
    alertes_recentes: list[dict] = []
    bus_stats: dict[str, Any] = {}


class RapportAgentReponse(BaseModel):
    agent: str
    actif: bool
    cycles: int
    horodatage: str
    derniere_analyse: dict[str, Any] = {}
    indicateurs: dict[str, Any] = {}
    recommandations: list[dict] = []


class AnalyseDemandeReponse(BaseModel):
    horodatage: str
    resultats: dict[str, Any]
    superviseur: dict[str, Any] = {}


class MessageHistorique(BaseModel):
    horodatage: str
    expediteur: str
    destinataire: str
    type: str
    priorite: int
    contenu: dict[str, Any]


class CommandeManuelle(BaseModel):
    machine_id: str = Field(..., pattern=r"^M\d{3}$", description="ID machine ex: M001")
    action: Literal["DEMARRER", "ARRETER", "MAINTENANCE", "REINITIALISER"]
    raison: str = Field(..., min_length=5, max_length=200)


class CommandeReponse(BaseModel):
    succes: bool
    machine_id: str
    action: str
    message: str
    horodatage: str


class HealthReponse(BaseModel):
    statut: str
    version: str
    agents_actifs: int
    systeme: str

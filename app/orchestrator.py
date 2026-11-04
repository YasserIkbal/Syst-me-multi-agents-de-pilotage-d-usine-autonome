"""Orchestrateur — instancie et démarre tous les agents de l'usine.

C'est le point d'entrée principal du système multi-agents.
L'API et l'interface passent par l'orchestrateur pour interroger les agents.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any

from agents.base import MessageBus
from agents.production import ProductionAgent
from agents.maintenance import MaintenanceAgent
from agents.quality import QualityAgent
from agents.inventory import InventoryAgent
from agents.energy import EnergyAgent
from agents.supervisor import SupervisorAgent


class Orchestrateur:
    """Gère le cycle de vie de tous les agents et expose leur état à l'API."""

    # Singleton partagé entre l'API et l'interface
    _instance: "Orchestrateur | None" = None
    _verrou = threading.Lock()

    def __init__(self) -> None:
        self.bus = MessageBus()
        # Instanciation des 6 agents
        self.agents: dict[str, Any] = {
            "ProductionAgent":  ProductionAgent(self.bus),
            "MaintenanceAgent": MaintenanceAgent(self.bus),
            "QualityAgent":     QualityAgent(self.bus),
            "InventoryAgent":   InventoryAgent(self.bus),
            "EnergyAgent":      EnergyAgent(self.bus),
            "SupervisorAgent":  SupervisorAgent(self.bus),
        }
        self._demarre = False

    @classmethod
    def instance(cls) -> "Orchestrateur":
        """Retourne l'instance singleton (créée au premier appel)."""
        with cls._verrou:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def demarrer(self, intervalle: float = 10.0) -> None:
        """Démarre tous les agents en mode fond."""
        if self._demarre:
            return
        # Le superviseur tourne plus vite pour collecter rapidement
        self.agents["SupervisorAgent"].demarrer(intervalle=5.0)
        for nom, agent in self.agents.items():
            if nom != "SupervisorAgent":
                agent.demarrer(intervalle=intervalle)
        self._demarre = True

    def arreter(self) -> None:
        """Arrête tous les agents proprement."""
        for agent in self.agents.values():
            agent.arreter()
        self._demarre = False

    def analyser_tous(self) -> dict[str, Any]:
        """Déclenche une analyse immédiate de tous les agents (mode synchrone pour l'API)."""
        resultats = {}
        for nom, agent in self.agents.items():
            if nom != "SupervisorAgent":
                try:
                    resultats[nom] = agent.analyser()
                except Exception as e:
                    resultats[nom] = {"statut": "ERREUR", "erreur": str(e)}
        # Le superviseur analyse en dernier pour avoir tous les rapports
        try:
            resultats["SupervisorAgent"] = self.agents["SupervisorAgent"].analyser()
        except Exception as e:
            resultats["SupervisorAgent"] = {"statut": "ERREUR", "erreur": str(e)}
        return resultats

    def etat_usine(self) -> dict[str, Any]:
        """Snapshot de l'état complet de l'usine pour le dashboard."""
        superviseur = self.agents["SupervisorAgent"]
        return {
            "horodatage": datetime.now().isoformat(),
            "systeme_actif": self._demarre,
            "nb_agents": len(self.agents),
            "sante_usine": superviseur._derniere_analyse.get("sante_usine", {}),
            "decision_courante": superviseur._derniere_analyse.get("decision", "EN_ATTENTE"),
            "message_decision": superviseur._derniere_analyse.get("message_decision", ""),
            "statuts": {
                nom: agent._derniere_analyse.get("statut", "EN_ATTENTE")
                for nom, agent in self.agents.items()
            },
            "alertes_recentes": superviseur.historique_alertes(10),
            "bus_stats": self.bus.statistiques()
        }

    def rapport_agent(self, nom: str) -> dict[str, Any]:
        """Rapport détaillé d'un agent spécifique."""
        agent = self.agents.get(nom)
        if not agent:
            raise KeyError(f"Agent '{nom}' introuvable. Agents disponibles : {list(self.agents.keys())}")
        return agent.rapport()

    def historique_messages(self, n: int = 50) -> list[dict]:
        """Historique des messages du bus pour la traçabilité."""
        messages = self.bus.historique(n)
        return [
            {
                "horodatage": m.horodatage,
                "expediteur": m.expediteur,
                "destinataire": m.destinataire,
                "type": m.type_message,
                "priorite": m.priorite,
                "contenu": m.contenu
            }
            for m in messages
        ]

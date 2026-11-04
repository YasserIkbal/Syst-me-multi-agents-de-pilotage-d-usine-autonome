"""Agent Superviseur — coordonne tous les agents, centralise les décisions globales.

Responsabilités :
- Collecter les rapports de tous les agents
- Détecter les conflits entre décisions
- Prioriser les actions selon la criticité
- Générer des décisions globales pour l'usine
- Maintenir l'historique des événements
"""
from __future__ import annotations

import threading
from collections import deque
from datetime import datetime
from typing import Any

from agents.base import BaseAgent, Message, MessageBus

# Poids de criticité pour prioriser les décisions
POIDS_CRITICITE = {
    "CRITIQUE": 3,
    "ALERTE": 2,
    "OK": 1,
    "DONNEES_MANQUANTES": 0
}


class SupervisorAgent(BaseAgent):
    """Agent coordinateur — cerveau central de l'usine autonome."""

    def __init__(self, bus: MessageBus) -> None:
        super().__init__("SupervisorAgent", bus)
        self._rapports: dict[str, dict] = {}          # dernier rapport par agent
        self._alertes: deque[dict] = deque(maxlen=200)  # historique des alertes
        self._decisions: deque[dict] = deque(maxlen=100)  # décisions prises
        self._verrou = threading.Lock()

    def _traiter_message(self, message: Message) -> None:
        """Traite les messages reçus des agents spécialisés."""
        with self._verrou:
            if message.type_message == "RAPPORT":
                self._rapports[message.expediteur] = message.contenu
            elif message.type_message == "ALERTE":
                alerte = {
                    "horodatage": message.horodatage,
                    "agent": message.expediteur,
                    "priorite": message.priorite,
                    "contenu": message.contenu
                }
                self._alertes.append(alerte)

    def _detecter_conflits(self) -> list[dict]:
        """Détecte les conflits entre décisions des agents."""
        conflits = []

        # Conflit : Maintenance veut arrêter M003 mais Production veut l'utiliser
        maint = self._rapports.get("MaintenanceAgent", {})
        prod = self._rapports.get("ProductionAgent", {})

        if maint and prod:
            interventions = maint.get("interventions_recommandees", [])
            machines_urgentes = {i["machine"] for i in interventions if i.get("urgence") == "IMMEDIATE"}
            machine_critique_prod = prod.get("machine_la_plus_problematique")

            if machines_urgentes and machine_critique_prod in machines_urgentes:
                conflits.append({
                    "type": "MAINTENANCE_VS_PRODUCTION",
                    "machine": machine_critique_prod,
                    "description": f"Maintenance immédiate requise sur {machine_critique_prod} "
                                   f"mais production en retard",
                    "resolution": "MAINTENANCE_PRIORITAIRE"
                })

        # Conflit : Qualité alerte M002 mais Énergie la signale critique
        qual = self._rapports.get("QualityAgent", {})
        energy = self._rapports.get("EnergyAgent", {})
        if qual and energy:
            m_qual = set(qual.get("machines_critiques", []))
            m_energy = set(energy.get("machines_critiques", []))
            double_critique = m_qual & m_energy
            if double_critique:
                conflits.append({
                    "type": "QUALITE_ET_ENERGIE_CRITIQUE",
                    "machines": list(double_critique),
                    "description": f"Machines {double_critique} critiques sur qualité ET énergie",
                    "resolution": "ARRET_PROGRAMME"
                })

        return conflits

    def _prioriser_actions(self) -> list[dict]:
        """Trie et priorise toutes les actions recommandées par les agents."""
        toutes_actions = []

        # Collecter depuis tous les agents
        sources = {
            "MaintenanceAgent": ("interventions_recommandees", "maintenance"),
            "QualityAgent": ("actions_correctives", "qualite"),
            "InventoryAgent": ("commandes_urgentes", "inventaire"),
            "EnergyAgent": ("optimisations", "energie"),
            "ProductionAgent": ("recommandations", "production"),
        }

        for agent, (cle, categorie) in sources.items():
            rapport = self._rapports.get(agent, {})
            actions = rapport.get(cle, [])
            for action in actions[:5]:  # max 5 par agent
                action_enrichie = dict(action)
                action_enrichie["agent_source"] = agent
                action_enrichie["categorie"] = categorie
                urgence = action.get("urgence", "PLANIFIEE")
                action_enrichie["score"] = {"IMMEDIATE": 3, "PLANIFIEE": 2, "NON_URGENTE": 1}.get(urgence, 1)
                toutes_actions.append(action_enrichie)

        # Trier par score décroissant
        toutes_actions.sort(key=lambda x: x["score"], reverse=True)
        return toutes_actions[:20]  # top 20

    def _calculer_sante_usine(self) -> dict[str, Any]:
        """Calcule un score global de santé de l'usine (0-100)."""
        scores_agents = {}
        for agent, rapport in self._rapports.items():
            statut = rapport.get("statut", "DONNEES_MANQUANTES")
            scores_agents[agent] = {
                "OK": 100, "ALERTE": 60, "CRITIQUE": 20, "DONNEES_MANQUANTES": 50
            }.get(statut, 50)

        if not scores_agents:
            return {"score_global": 0, "scores_par_agent": {}, "niveau": "INCONNU"}

        score_global = round(sum(scores_agents.values()) / len(scores_agents), 1)
        niveau = "EXCELLENT" if score_global >= 90 else (
            "BON" if score_global >= 70 else (
                "DEGRADE" if score_global >= 40 else "CRITIQUE"
            )
        )
        return {
            "score_global": score_global,
            "scores_par_agent": scores_agents,
            "niveau": niveau
        }

    def analyser(self) -> dict[str, Any]:
        """Synthèse globale et décision superviseur."""
        # Lire tous les messages en attente
        for msg in self.lire_messages():
            self._traiter_message(msg)

        conflits = self._detecter_conflits()
        actions_priorisees = self._prioriser_actions()
        sante = self._calculer_sante_usine()

        # Résumé des statuts des agents
        statuts = {agent: rapport.get("statut", "INCONNU")
                   for agent, rapport in self._rapports.items()}

        # Décision globale
        nb_critiques = sum(1 for s in statuts.values() if s == "CRITIQUE")
        nb_alertes = sum(1 for s in statuts.values() if s == "ALERTE")

        if nb_critiques >= 2:
            decision = "ARRET_D_URGENCE"
            message_decision = f"{nb_critiques} agents en état critique — arrêt recommandé"
        elif nb_critiques == 1:
            decision = "INTERVENTION_IMMEDIATE"
            agent_crit = next((a for a, s in statuts.items() if s == "CRITIQUE"), "?")
            message_decision = f"Intervention immédiate requise : {agent_crit}"
        elif nb_alertes >= 2:
            decision = "SURVEILLANCE_RENFORCEE"
            message_decision = f"{nb_alertes} alertes actives — surveillance renforcée"
        elif nb_alertes == 1:
            decision = "ACTION_PLANIFIEE"
            message_decision = "1 alerte — action planifiée"
        else:
            decision = "FONCTIONNEMENT_NORMAL"
            message_decision = "Tous les systèmes nominaux"

        # Enregistrer la décision
        decision_obj = {
            "horodatage": datetime.now().isoformat(),
            "decision": decision,
            "message": message_decision,
            "statuts_agents": statuts,
            "conflits": conflits,
            "sante_usine": sante
        }
        with self._verrou:
            self._decisions.append(decision_obj)

        resultat = {
            "statut": "CRITIQUE" if nb_critiques >= 2 else ("ALERTE" if nb_alertes >= 1 else "OK"),
            "decision": decision,
            "message_decision": message_decision,
            "sante_usine": sante,
            "statuts_agents": statuts,
            "conflits_detectes": conflits,
            "actions_priorisees": actions_priorisees,
            "nb_alertes_actives": len(list(self._alertes)),
            "rapports_recus": list(self._rapports.keys()),
            "horodatage": datetime.now().isoformat()
        }
        return resultat

    def historique_alertes(self, n: int = 50) -> list[dict]:
        with self._verrou:
            return list(self._alertes)[-n:]

    def historique_decisions(self, n: int = 20) -> list[dict]:
        with self._verrou:
            return list(self._decisions)[-n:]

    def rapport(self) -> dict[str, Any]:
        base = super().rapport()
        base["sante_usine"] = self._derniere_analyse.get("sante_usine", {})
        base["decision_courante"] = self._derniere_analyse.get("decision", "INCONNU")
        base["nb_alertes"] = len(list(self._alertes))
        return base

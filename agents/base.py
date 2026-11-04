"""Classe de base pour tous les agents et bus de communication.

Chaque agent hérite de BaseAgent et implémente :
- analyser() : traite les données et produit une décision
- rapport()  : résume l'état actuel pour le superviseur
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from collections import deque


@dataclass
class Message:
    """Un message échangé entre agents."""
    expediteur: str
    destinataire: str        # nom de l'agent cible, ou "TOUS" pour broadcast
    type_message: str        # "ALERTE", "RAPPORT", "COMMANDE", "INFO"
    contenu: dict[str, Any]
    horodatage: str = field(default_factory=lambda: datetime.now().isoformat())
    priorite: int = 0        # 0 = normale, 1 = haute, 2 = critique

    def __lt__(self, other: "Message") -> bool:
        return self.priorite > other.priorite  # plus haute priorité d'abord


class MessageBus:
    """Bus de messages central — tous les agents s'y abonnent.

    Thread-safe : les agents tournent en parallèle et peuvent publier/lire
    en même temps. Conserve les 500 derniers messages pour l'historique.
    """

    def __init__(self) -> None:
        self._verrou = threading.Lock()
        self._files: dict[str, deque] = {}          # file par agent
        self._historique: deque[Message] = deque(maxlen=500)
        self._abonnes: dict[str, list[Callable]] = {}

    def enregistrer(self, agent_nom: str) -> None:
        """Enregistre un agent dans le bus."""
        with self._verrou:
            if agent_nom not in self._files:
                self._files[agent_nom] = deque(maxlen=100)

    def publier(self, message: Message) -> None:
        """Publie un message vers un destinataire (ou tous)."""
        with self._verrou:
            self._historique.append(message)
            if message.destinataire == "TOUS":
                for file in self._files.values():
                    file.append(message)
            elif message.destinataire in self._files:
                self._files[message.destinataire].append(message)

    def lire(self, agent_nom: str) -> list[Message]:
        """Récupère et vide la file de messages d'un agent."""
        with self._verrou:
            if agent_nom not in self._files:
                return []
            messages = list(self._files[agent_nom])
            self._files[agent_nom].clear()
            return messages

    def historique(self, n: int = 50) -> list[Message]:
        """Retourne les n derniers messages de tous les agents."""
        with self._verrou:
            return list(self._historique)[-n:]

    def statistiques(self) -> dict[str, Any]:
        """Statistiques du bus pour le dashboard."""
        with self._verrou:
            return {
                "total_messages": len(self._historique),
                "agents_enregistres": list(self._files.keys()),
                "messages_en_attente": {k: len(v) for k, v in self._files.items()}
            }


class BaseAgent:
    """Classe de base pour tous les agents de l'usine.

    Chaque agent :
    1. S'enregistre sur le bus de messages
    2. Lit les données de simulation
    3. Applique son modèle ML ou sa logique métier
    4. Produit une décision et la publie
    5. Répond aux messages des autres agents
    """

    def __init__(self, nom: str, bus: MessageBus) -> None:
        self.nom = nom
        self.bus = bus
        self._actif = False
        self._thread: threading.Thread | None = None
        self._derniere_analyse: dict[str, Any] = {}
        self._compteur_cycles = 0
        bus.enregistrer(nom)

    def publier(self, type_message: str, contenu: dict,
                destinataire: str = "SupervisorAgent", priorite: int = 0) -> None:
        """Raccourci pour publier un message depuis cet agent."""
        self.bus.publier(Message(
            expediteur=self.nom,
            destinataire=destinataire,
            type_message=type_message,
            contenu=contenu,
            priorite=priorite
        ))

    def publier_alerte(self, description: str, donnees: dict, critique: bool = False) -> None:
        """Publie une alerte vers le superviseur et tous les agents."""
        priorite = 2 if critique else 1
        self.publier("ALERTE", {"description": description, **donnees},
                     destinataire="SupervisorAgent", priorite=priorite)
        self.publier("ALERTE", {"description": description, **donnees},
                     destinataire="TOUS", priorite=priorite)

    def lire_messages(self) -> list[Message]:
        """Lit les messages en attente pour cet agent."""
        return self.bus.lire(self.nom)

    def analyser(self) -> dict[str, Any]:
        """À implémenter par chaque agent spécialisé."""
        raise NotImplementedError

    def rapport(self) -> dict[str, Any]:
        """Résumé de l'état actuel de cet agent pour le superviseur."""
        return {
            "agent": self.nom,
            "actif": self._actif,
            "cycles": self._compteur_cycles,
            "derniere_analyse": self._derniere_analyse,
            "horodatage": datetime.now().isoformat()
        }

    def _boucle(self, intervalle: float) -> None:
        """Boucle principale de l'agent (tourne dans un thread séparé)."""
        while self._actif:
            try:
                self._compteur_cycles += 1
                self._derniere_analyse = self.analyser()
                # Traiter les messages reçus
                for msg in self.lire_messages():
                    self._traiter_message(msg)
            except Exception as e:
                self.publier("ERREUR", {"agent": self.nom, "erreur": str(e)},
                             destinataire="SupervisorAgent", priorite=2)
            time.sleep(intervalle)

    def _traiter_message(self, message: Message) -> None:
        """Traitement par défaut des messages reçus (peut être surchargé)."""
        pass  # Les agents spécialisés gèrent leurs propres messages

    def demarrer(self, intervalle: float = 5.0) -> None:
        """Démarre l'agent dans un thread de fond."""
        self._actif = True
        self._thread = threading.Thread(target=self._boucle, args=(intervalle,), daemon=True)
        self._thread.start()

    def arreter(self) -> None:
        """Arrête l'agent proprement."""
        self._actif = False
        if self._thread:
            self._thread.join(timeout=3.0)

"""Agents IA de l'usine autonome.

Six agents spécialisés qui communiquent via un bus de messages partagé :
- ProductionAgent  : surveille les objectifs de production
- MaintenanceAgent : anticipe les pannes machines
- QualityAgent     : contrôle la qualité des lots
- InventoryAgent   : gère les stocks de matières premières
- EnergyAgent      : optimise la consommation énergétique
- SupervisorAgent  : coordonne et prend les décisions globales
"""

from agents.base import BaseAgent, MessageBus, Message

__all__ = ["BaseAgent", "MessageBus", "Message"]

"""Tests de l'orchestrateur — coordination des agents."""
import pytest
from unittest.mock import patch, MagicMock


def test_orchestrateur_singleton():
    """L'orchestrateur est un singleton."""
    from app.orchestrator import Orchestrateur
    Orchestrateur._instance = None  # reset
    o1 = Orchestrateur.instance()
    o2 = Orchestrateur.instance()
    assert o1 is o2
    Orchestrateur._instance = None  # cleanup


def test_orchestrateur_six_agents():
    """L'orchestrateur instancie exactement 6 agents."""
    from app.orchestrator import Orchestrateur
    Orchestrateur._instance = None
    o = Orchestrateur()
    assert len(o.agents) == 6
    noms_attendus = {"ProductionAgent", "MaintenanceAgent", "QualityAgent",
                     "InventoryAgent", "EnergyAgent", "SupervisorAgent"}
    assert set(o.agents.keys()) == noms_attendus


def test_orchestrateur_etat_usine():
    """etat_usine() retourne un dict avec les champs obligatoires."""
    from app.orchestrator import Orchestrateur
    Orchestrateur._instance = None
    o = Orchestrateur()
    etat = o.etat_usine()
    assert "horodatage" in etat
    assert "systeme_actif" in etat
    assert "nb_agents" in etat
    assert etat["nb_agents"] == 6


def test_orchestrateur_rapport_agent_inexistant():
    """rapport_agent() lève KeyError pour un agent inconnu."""
    from app.orchestrator import Orchestrateur
    Orchestrateur._instance = None
    o = Orchestrateur()
    with pytest.raises(KeyError):
        o.rapport_agent("AgentFantome")


def test_orchestrateur_rapport_agent_existant():
    """rapport_agent() retourne un dict pour un agent connu."""
    from app.orchestrator import Orchestrateur
    Orchestrateur._instance = None
    o = Orchestrateur()
    rapport = o.rapport_agent("ProductionAgent")
    assert "agent" in rapport
    assert rapport["agent"] == "ProductionAgent"


def test_orchestrateur_historique_messages():
    """historique_messages() retourne une liste."""
    from app.orchestrator import Orchestrateur
    Orchestrateur._instance = None
    o = Orchestrateur()
    hist = o.historique_messages(10)
    assert isinstance(hist, list)

"""Tests du bus de messages et de la classe BaseAgent."""
import time
import pytest
from agents.base import BaseAgent, MessageBus, Message


@pytest.fixture
def bus():
    return MessageBus()


class AgentTest(BaseAgent):
    """Agent minimal pour les tests."""
    def analyser(self):
        return {"statut": "OK", "test": True}


# ── Bus de messages ────────────────────────────────────────────────────────────

def test_bus_enregistrement(bus):
    """Un agent enregistré apparaît dans les stats du bus."""
    bus.enregistrer("AgentA")
    stats = bus.statistiques()
    assert "AgentA" in stats["agents_enregistres"]


def test_bus_publication_destinataire(bus):
    """Un message vers un destinataire précis n'arrive que chez lui."""
    bus.enregistrer("AgentA")
    bus.enregistrer("AgentB")
    msg = Message("Emetteur", "AgentA", "INFO", {"val": 1})
    bus.publier(msg)
    assert len(bus.lire("AgentA")) == 1
    assert len(bus.lire("AgentB")) == 0


def test_bus_broadcast(bus):
    """Un message TOUS arrive chez tous les agents enregistrés."""
    bus.enregistrer("AgentA")
    bus.enregistrer("AgentB")
    bus.enregistrer("AgentC")
    msg = Message("Emetteur", "TOUS", "ALERTE", {"urgence": True})
    bus.publier(msg)
    assert len(bus.lire("AgentA")) == 1
    assert len(bus.lire("AgentB")) == 1
    assert len(bus.lire("AgentC")) == 1


def test_bus_historique(bus):
    """L'historique conserve les messages publiés."""
    bus.enregistrer("AgentA")
    for i in range(5):
        bus.publier(Message("X", "AgentA", "INFO", {"i": i}))
    hist = bus.historique(3)
    assert len(hist) == 3


def test_bus_vider_file(bus):
    """Après lecture, la file est vidée."""
    bus.enregistrer("AgentA")
    bus.publier(Message("X", "AgentA", "INFO", {}))
    bus.lire("AgentA")
    assert bus.lire("AgentA") == []


def test_bus_thread_safe(bus):
    """Plusieurs threads peuvent publier simultanément sans corruption."""
    import threading
    bus.enregistrer("AgentA")
    erreurs = []

    def publier_plusieurs():
        try:
            for i in range(20):
                bus.publier(Message("Thread", "AgentA", "INFO", {"i": i}))
        except Exception as e:
            erreurs.append(e)

    threads = [threading.Thread(target=publier_plusieurs) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(erreurs) == 0


# ── BaseAgent ─────────────────────────────────────────────────────────────────

def test_agent_enregistrement(bus):
    """Un agent s'enregistre automatiquement sur le bus à la création."""
    agent = AgentTest("AgentTest", bus)
    stats = bus.statistiques()
    assert "AgentTest" in stats["agents_enregistres"]


def test_agent_analyser(bus):
    """analyser() retourne un dict avec au moins 'statut'."""
    agent = AgentTest("AgentTest", bus)
    resultat = agent.analyser()
    assert isinstance(resultat, dict)
    assert "statut" in resultat


def test_agent_publier(bus):
    """Un agent peut publier un message sur le bus."""
    bus.enregistrer("SupervisorAgent")
    agent = AgentTest("AgentTest", bus)
    agent.publier("RAPPORT", {"donnee": 42}, destinataire="SupervisorAgent")
    messages = bus.lire("SupervisorAgent")
    assert len(messages) == 1
    assert messages[0].contenu["donnee"] == 42


def test_agent_rapport(bus):
    """rapport() contient les champs attendus."""
    agent = AgentTest("AgentTest", bus)
    r = agent.rapport()
    assert "agent" in r
    assert "actif" in r
    assert "cycles" in r
    assert r["agent"] == "AgentTest"


def test_agent_demarrer_arreter(bus):
    """Un agent peut démarrer et s'arrêter proprement."""
    agent = AgentTest("AgentTest", bus)
    agent.demarrer(intervalle=0.1)
    time.sleep(0.3)
    assert agent._actif is True
    assert agent._compteur_cycles >= 1
    agent.arreter()
    assert agent._actif is False


def test_agent_alerte_priorite(bus):
    """Une alerte critique a la priorité 2."""
    bus.enregistrer("SupervisorAgent")
    bus.enregistrer("TOUS")
    agent = AgentTest("AgentTest", bus)
    agent.publier_alerte("Test critique", {}, critique=True)
    messages = bus.historique(10)
    alertes = [m for m in messages if m.type_message == "ALERTE" and m.priorite == 2]
    assert len(alertes) >= 1

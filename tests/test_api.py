"""Tests de l'API FastAPI — contrats d'entrée/sortie et comportements."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pathlib import Path


@pytest.fixture
def models_presents(tmp_path):
    """Crée un fichier metrics.json pour simuler des modèles entraînés."""
    import json
    metrics = {
        "anomaly_detector": {"modele": "IsolationForest", "rappel_anomalies": 0.85},
        "failure_predictor": {"modele": "RandomForest", "f1_macro": 0.90},
        "quality_classifier": {"modele": "GradientBoosting", "f1_macro": 0.88},
        "energy_forecaster": {"modele": "LinearRegression", "mae_kwh": 2.1}
    }
    (tmp_path / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    return tmp_path


@pytest.fixture
def client_api(models_presents):
    """Client de test avec l'orchestrateur mocké."""
    mock_orch = MagicMock()
    mock_orch._demarre = True
    mock_orch.agents = {
        "ProductionAgent": MagicMock(_actif=True, _compteur_cycles=5,
                                      _derniere_analyse={"statut": "OK"}),
        "MaintenanceAgent": MagicMock(_actif=True, _compteur_cycles=5,
                                       _derniere_analyse={"statut": "OK"}),
        "SupervisorAgent": MagicMock(_actif=True, _compteur_cycles=5,
                                      _derniere_analyse={"statut": "OK",
                                                          "decision": "FONCTIONNEMENT_NORMAL",
                                                          "message_decision": "Nominal",
                                                          "sante_usine": {"score_global": 95, "niveau": "EXCELLENT"}},
                                      historique_alertes=MagicMock(return_value=[]),
                                      historique_decisions=MagicMock(return_value=[])),
    }
    mock_orch.etat_usine.return_value = {
        "horodatage": "2026-11-04T10:00:00",
        "systeme_actif": True,
        "nb_agents": 6,
        "sante_usine": {"score_global": 95, "niveau": "EXCELLENT", "scores_par_agent": {}},
        "decision_courante": "FONCTIONNEMENT_NORMAL",
        "message_decision": "Nominal",
        "statuts": {"ProductionAgent": "OK"},
        "alertes_recentes": [],
        "bus_stats": {}
    }
    mock_orch.analyser_tous.return_value = {
        "ProductionAgent": {"statut": "OK"},
        "SupervisorAgent": {"statut": "OK", "decision": "FONCTIONNEMENT_NORMAL"}
    }
    mock_orch.historique_messages.return_value = []
    mock_orch.rapport_agent.return_value = {
        "agent": "ProductionAgent", "actif": True, "cycles": 5,
        "horodatage": "2026-11-04T10:00:00", "derniere_analyse": {}
    }

    with patch("api.main.MODELS", models_presents), \
         patch("api.main._orchestrateur", return_value=mock_orch):
        from api.main import app
        yield TestClient(app)


# ── /health ───────────────────────────────────────────────────────────────────

def test_health_ok(client_api):
    """GET /health retourne 200 avec statut OK."""
    r = client_api.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["statut"] == "OK"
    assert "version" in data
    assert "systeme" in data


def test_health_contient_version(client_api):
    """La version est une chaîne non vide."""
    r = client_api.get("/health")
    assert r.json()["version"] != ""


# ── /usine/etat ───────────────────────────────────────────────────────────────

def test_etat_usine_ok(client_api):
    """GET /usine/etat retourne 200 avec les champs attendus."""
    r = client_api.get("/usine/etat")
    assert r.status_code == 200
    data = r.json()
    assert "horodatage" in data
    assert "statuts" in data
    assert "decision_courante" in data


def test_etat_usine_sante(client_api):
    """Le score de santé est entre 0 et 100."""
    r = client_api.get("/usine/etat")
    sante = r.json().get("sante_usine", {})
    score = sante.get("score_global", -1)
    assert 0 <= score <= 100


# ── /usine/analyser ───────────────────────────────────────────────────────────

def test_analyser_usine(client_api):
    """GET /usine/analyser retourne les résultats de tous les agents."""
    r = client_api.get("/usine/analyser")
    assert r.status_code == 200
    data = r.json()
    assert "resultats" in data
    assert "horodatage" in data


# ── /agents ───────────────────────────────────────────────────────────────────

def test_lister_agents(client_api):
    """GET /agents retourne la liste des agents."""
    r = client_api.get("/agents")
    assert r.status_code == 200
    data = r.json()
    assert "agents" in data
    assert isinstance(data["agents"], list)


def test_rapport_agent_existant(client_api):
    """GET /agents/{nom} retourne le rapport d'un agent existant."""
    r = client_api.get("/agents/ProductionAgent")
    assert r.status_code == 200
    data = r.json()
    assert "agent" in data or "cycles" in data


def test_rapport_agent_inexistant(client_api):
    """GET /agents/AgentInexistant retourne 404."""
    from unittest.mock import patch
    with patch("api.main._orchestrateur") as mock_orch:
        mock_orch.return_value.rapport_agent.side_effect = KeyError("Agent introuvable")
        r = client_api.get("/agents/AgentInexistant")
    assert r.status_code == 404


# ── /messages ─────────────────────────────────────────────────────────────────

def test_messages_ok(client_api):
    """GET /messages retourne l'historique."""
    r = client_api.get("/messages")
    assert r.status_code == 200
    data = r.json()
    assert "messages" in data
    assert "total" in data


def test_messages_param_n(client_api):
    """GET /messages?n=10 accepte le paramètre n."""
    r = client_api.get("/messages?n=10")
    assert r.status_code == 200


def test_messages_param_invalide(client_api):
    """GET /messages?n=0 retourne 422."""
    r = client_api.get("/messages?n=0")
    assert r.status_code == 422


# ── /machines/commande ────────────────────────────────────────────────────────

def test_commande_machine_valide(client_api):
    """POST /machines/commande avec données valides retourne 200."""
    from unittest.mock import patch, MagicMock
    mock_bus = MagicMock()
    with patch("api.main._orchestrateur") as mock_orch:
        mock_orch.return_value.bus = mock_bus
        mock_orch.return_value._demarre = True
        r = client_api.post("/machines/commande", json={
            "machine_id": "M001",
            "action": "MAINTENANCE",
            "raison": "Maintenance préventive planifiée"
        })
    assert r.status_code == 200
    data = r.json()
    assert data["succes"] is True
    assert data["machine_id"] == "M001"


def test_commande_machine_id_invalide(client_api):
    """POST /machines/commande avec machine_id invalide retourne 422."""
    r = client_api.post("/machines/commande", json={
        "machine_id": "MACHINE_INVALIDE",
        "action": "DEMARRER",
        "raison": "Test"
    })
    assert r.status_code == 422


def test_commande_raison_trop_courte(client_api):
    """POST /machines/commande avec raison < 5 chars retourne 422."""
    r = client_api.post("/machines/commande", json={
        "machine_id": "M001",
        "action": "DEMARRER",
        "raison": "AB"
    })
    assert r.status_code == 422


def test_commande_action_invalide(client_api):
    """POST /machines/commande avec action inconnue retourne 422."""
    r = client_api.post("/machines/commande", json={
        "machine_id": "M001",
        "action": "EXPLOSER",
        "raison": "Action invalide test"
    })
    assert r.status_code == 422

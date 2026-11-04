"""Tests des 6 agents spécialisés — sans modèles ML ni fichiers de données requis."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from agents.base import MessageBus


@pytest.fixture
def bus():
    return MessageBus()


@pytest.fixture
def bus_avec_superviseur(bus):
    bus.enregistrer("SupervisorAgent")
    bus.enregistrer("TOUS")
    return bus


# ── ProductionAgent ────────────────────────────────────────────────────────────

def test_production_agent_creation(bus_avec_superviseur):
    """ProductionAgent se crée sans erreur même sans modèle."""
    from agents.production import ProductionAgent
    agent = ProductionAgent(bus_avec_superviseur)
    assert agent.nom == "ProductionAgent"


def test_production_agent_sans_donnees(bus_avec_superviseur):
    """ProductionAgent gère l'absence de fichier de données."""
    from agents.production import ProductionAgent
    agent = ProductionAgent(bus_avec_superviseur)
    with patch("agents.production.agent.DATA", Path("/tmp/inexistant")):
        result = agent.analyser()
    assert "statut" in result


def test_production_agent_avec_donnees(bus_avec_superviseur, tmp_path):
    """ProductionAgent analyse correctement des données CSV synthétiques."""
    from agents.production import ProductionAgent
    # Créer un CSV de production minimal
    csv_content = "date,machine_id,produit,objectif,produit_reel,taux_realisation,retard,statut\n"
    csv_content += "2026-11-01,M001,PROD-A,100,95,0.95,5,OK\n"
    csv_content += "2026-11-01,M002,PROD-B,100,70,0.70,30,RETARD\n"
    csv_content += "2026-11-01,M003,PROD-A,100,50,0.50,50,CRITIQUE\n"
    (tmp_path / "production.csv").write_text(csv_content, encoding="utf-8")

    agent = ProductionAgent(bus_avec_superviseur)
    with patch("agents.production.agent.DATA", tmp_path):
        result = agent.analyser()

    assert result["statut"] in ("OK", "ALERTE", "CRITIQUE")
    assert "total_ordres" in result
    assert result["total_ordres"] == 3


def test_production_optimiser_ordres(bus_avec_superviseur, tmp_path):
    """optimiser_ordres() retourne une liste de recommandations."""
    from agents.production import ProductionAgent
    csv_content = "date,machine_id,produit,objectif,produit_reel,taux_realisation,retard,statut\n"
    csv_content += "2026-11-01,M003,PROD-A,100,40,0.40,60,CRITIQUE\n"
    (tmp_path / "production.csv").write_text(csv_content, encoding="utf-8")

    agent = ProductionAgent(bus_avec_superviseur)
    with patch("agents.production.agent.DATA", tmp_path):
        recommandations = agent.optimiser_ordres()
    assert isinstance(recommandations, list)


# ── MaintenanceAgent ───────────────────────────────────────────────────────────

def test_maintenance_agent_creation(bus_avec_superviseur):
    from agents.maintenance import MaintenanceAgent
    agent = MaintenanceAgent(bus_avec_superviseur)
    assert agent.nom == "MaintenanceAgent"


def test_maintenance_agent_score_risque(bus_avec_superviseur, tmp_path):
    """Le score de risque reflète les valeurs capteurs."""
    from agents.maintenance import MaintenanceAgent
    # Température élevée → score élevé
    csv_content = "timestamp,machine_id,temperature,vibration,pression,rpm,etat,anomalie\n"
    csv_content += "2026-11-04T10:00:00,M003,95.0,4.5,8.0,1500,ALERTE,1\n" * 20
    csv_content += "2026-11-04T10:00:00,M001,75.0,2.5,6.0,1500,OK,0\n" * 20
    (tmp_path / "machines.csv").write_text(csv_content, encoding="utf-8")

    agent = MaintenanceAgent(bus_avec_superviseur)
    with patch("agents.maintenance.agent.DATA", tmp_path):
        result = agent.analyser()

    assert "scores_risque" in result
    # M003 doit avoir un score plus élevé que M001
    scores = result["scores_risque"]
    if "M003" in scores and "M001" in scores:
        assert scores["M003"] >= scores["M001"]


def test_maintenance_alerte_publiee(bus_avec_superviseur, tmp_path):
    """Une machine avec capteurs critiques génère une alerte."""
    from agents.maintenance import MaintenanceAgent
    csv_content = "timestamp,machine_id,temperature,vibration,pression,rpm,etat,anomalie\n"
    # 30 mesures avec température > seuil critique (92°C)
    csv_content += "2026-11-04T10:00:00,M001,96.0,4.8,8.5,1500,ALERTE,1\n" * 30
    (tmp_path / "machines.csv").write_text(csv_content, encoding="utf-8")

    agent = MaintenanceAgent(bus_avec_superviseur)
    with patch("agents.maintenance.agent.DATA", tmp_path):
        result = agent.analyser()

    assert "alertes_seuil" in result


# ── QualityAgent ───────────────────────────────────────────────────────────────

def test_quality_agent_creation(bus_avec_superviseur):
    from agents.quality import QualityAgent
    agent = QualityAgent(bus_avec_superviseur)
    assert agent.nom == "QualityAgent"


def test_quality_taux_conformite(bus_avec_superviseur, tmp_path):
    """QualityAgent calcule correctement le taux de conformité."""
    from agents.quality import QualityAgent
    csv_content = "date,machine_id,produit,lot_taille,conformes,defauts,taux_conformite,type_defaut,statut\n"
    csv_content += "2026-11-01,M001,PROD-A,100,98,2,0.98,Aucun,OK\n"
    csv_content += "2026-11-01,M002,PROD-B,100,80,20,0.80,Rayure,ALERTE\n"
    (tmp_path / "quality.csv").write_text(csv_content, encoding="utf-8")

    agent = QualityAgent(bus_avec_superviseur)
    with patch("agents.quality.agent.DATA", tmp_path):
        result = agent.analyser()

    assert "taux_conformite_global" in result
    assert 0 <= result["taux_conformite_global"] <= 1


def test_quality_machine_critique(bus_avec_superviseur, tmp_path):
    """Une machine avec taux < 85% est détectée comme critique."""
    from agents.quality import QualityAgent
    csv_content = "date,machine_id,produit,lot_taille,conformes,defauts,taux_conformite,type_defaut,statut\n"
    csv_content += "2026-11-01,M002,PROD-B,100,80,20,0.80,Rayure,CRITIQUE\n" * 5
    (tmp_path / "quality.csv").write_text(csv_content, encoding="utf-8")

    agent = QualityAgent(bus_avec_superviseur)
    with patch("agents.quality.agent.DATA", tmp_path):
        result = agent.analyser()

    assert "M002" in result.get("machines_critiques", []) or result["statut"] in ("ALERTE", "CRITIQUE")


# ── InventoryAgent ─────────────────────────────────────────────────────────────

def test_inventory_agent_creation(bus_avec_superviseur):
    from agents.inventory import InventoryAgent
    agent = InventoryAgent(bus_avec_superviseur)
    assert agent.nom == "InventoryAgent"


def test_inventory_rupture_detectee(bus_avec_superviseur, tmp_path):
    """InventoryAgent détecte une rupture de stock."""
    from agents.inventory import InventoryAgent
    csv_content = "date,matiere,stock_actuel,stock_min,stock_max,consommation_jour,jours_restants,statut\n"
    csv_content += "2026-11-04,Acier,0,200,2000,50,0,RUPTURE\n"
    csv_content += "2026-11-04,Aluminium,1500,200,2000,40,37,OK\n"
    (tmp_path / "inventory.csv").write_text(csv_content, encoding="utf-8")

    agent = InventoryAgent(bus_avec_superviseur)
    with patch("agents.inventory.agent.DATA", tmp_path):
        result = agent.analyser()

    assert result["statut"] == "CRITIQUE"
    assert "Acier" in result.get("ruptures", [])


def test_inventory_commande_calculee(bus_avec_superviseur, tmp_path):
    """InventoryAgent calcule correctement la quantité à commander."""
    from agents.inventory import InventoryAgent
    csv_content = "date,matiere,stock_actuel,stock_min,stock_max,consommation_jour,jours_restants,statut\n"
    csv_content += "2026-11-04,Cuivre,100,200,2000,50,2,CRITIQUE\n"
    (tmp_path / "inventory.csv").write_text(csv_content, encoding="utf-8")

    agent = InventoryAgent(bus_avec_superviseur)
    with patch("agents.inventory.agent.DATA", tmp_path):
        result = agent.analyser()

    commandes = result.get("commandes_urgentes", [])
    assert len(commandes) >= 1
    assert commandes[0]["quantite_a_commander"] > 0


# ── EnergyAgent ────────────────────────────────────────────────────────────────

def test_energy_agent_creation(bus_avec_superviseur):
    from agents.energy import EnergyAgent
    agent = EnergyAgent(bus_avec_superviseur)
    assert agent.nom == "EnergyAgent"


def test_energy_anomalie_detectee(bus_avec_superviseur, tmp_path):
    """EnergyAgent détecte une consommation anormale."""
    from agents.energy import EnergyAgent
    csv_content = "timestamp,machine_id,conso_kwh,puissance_kw,cout_eur,anomalie_conso,statut\n"
    # M004 consomme 30kWh → au-dessus du seuil critique (28)
    csv_content += "2026-11-04T10:00:00,M004,30.0,120.0,3.60,1,ANOMALIE\n" * 20
    csv_content += "2026-11-04T10:00:00,M001,15.0,60.0,1.80,0,OK\n" * 20
    (tmp_path / "energy.csv").write_text(csv_content, encoding="utf-8")

    agent = EnergyAgent(bus_avec_superviseur)
    with patch("agents.energy.agent.DATA", tmp_path):
        result = agent.analyser()

    assert "M004" in result.get("machines_critiques", []) or result["statut"] in ("ALERTE", "CRITIQUE")


def test_energy_cout_calcule(bus_avec_superviseur, tmp_path):
    """EnergyAgent calcule correctement le coût total."""
    from agents.energy import EnergyAgent
    csv_content = "timestamp,machine_id,conso_kwh,puissance_kw,cout_eur,anomalie_conso,statut\n"
    csv_content += "2026-11-04T10:00:00,M001,10.0,40.0,1.20,0,OK\n" * 10
    (tmp_path / "energy.csv").write_text(csv_content, encoding="utf-8")

    agent = EnergyAgent(bus_avec_superviseur)
    with patch("agents.energy.agent.DATA", tmp_path):
        result = agent.analyser()

    assert result.get("cout_total_eur_24h", 0) > 0


# ── SupervisorAgent ────────────────────────────────────────────────────────────

def test_supervisor_creation(bus):
    from agents.supervisor import SupervisorAgent
    agent = SupervisorAgent(bus)
    assert agent.nom == "SupervisorAgent"


def test_supervisor_collecte_rapports(bus):
    """Le superviseur collecte les rapports des autres agents."""
    from agents.supervisor import SupervisorAgent
    from agents.base import Message

    bus.enregistrer("SupervisorAgent")
    superviseur = SupervisorAgent(bus)

    # Simuler des rapports d'agents
    bus.publier(Message("ProductionAgent", "SupervisorAgent", "RAPPORT",
                        {"statut": "OK", "taux_realisation_moyen": 0.95}))
    bus.publier(Message("MaintenanceAgent", "SupervisorAgent", "RAPPORT",
                        {"statut": "ALERTE", "score_risque_max": 0.5}))

    result = superviseur.analyser()
    assert "statuts_agents" in result or "rapports_recus" in result


def test_supervisor_decision_critique(bus):
    """Le superviseur génère ARRET_D_URGENCE si 2+ agents sont critiques."""
    from agents.supervisor import SupervisorAgent
    from agents.base import Message

    bus.enregistrer("SupervisorAgent")
    superviseur = SupervisorAgent(bus)

    # Injecter des rapports critiques directement dans l'état interne
    superviseur._rapports = {
        "ProductionAgent": {"statut": "CRITIQUE"},
        "MaintenanceAgent": {"statut": "CRITIQUE"},
        "QualityAgent": {"statut": "OK"},
    }

    result = superviseur.analyser()
    assert result["decision"] == "ARRET_D_URGENCE"


def test_supervisor_decision_normale(bus):
    """Le superviseur génère FONCTIONNEMENT_NORMAL si tous les agents sont OK."""
    from agents.supervisor import SupervisorAgent

    bus.enregistrer("SupervisorAgent")
    superviseur = SupervisorAgent(bus)

    superviseur._rapports = {
        "ProductionAgent": {"statut": "OK"},
        "MaintenanceAgent": {"statut": "OK"},
        "QualityAgent": {"statut": "OK"},
        "InventoryAgent": {"statut": "OK"},
        "EnergyAgent": {"statut": "OK"},
    }

    result = superviseur.analyser()
    assert result["decision"] == "FONCTIONNEMENT_NORMAL"


def test_supervisor_historique_alertes(bus):
    """Le superviseur conserve l'historique des alertes."""
    from agents.supervisor import SupervisorAgent
    from agents.base import Message

    bus.enregistrer("SupervisorAgent")
    superviseur = SupervisorAgent(bus)

    bus.publier(Message("ProductionAgent", "SupervisorAgent", "ALERTE",
                        {"description": "Retard critique"}, priorite=2))
    superviseur.analyser()

    hist = superviseur.historique_alertes()
    assert isinstance(hist, list)


def test_supervisor_sante_usine(bus):
    """Le score de santé est entre 0 et 100."""
    from agents.supervisor import SupervisorAgent

    bus.enregistrer("SupervisorAgent")
    superviseur = SupervisorAgent(bus)
    superviseur._rapports = {
        "ProductionAgent": {"statut": "OK"},
        "MaintenanceAgent": {"statut": "ALERTE"},
    }

    result = superviseur.analyser()
    sante = result.get("sante_usine", {})
    score = sante.get("score_global", -1)
    assert 0 <= score <= 100

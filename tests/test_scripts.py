"""Tests des scripts utilitaires — génération de données et entraînement."""
import pytest
from pathlib import Path


def test_generate_data_cree_fichiers(tmp_path):
    """generate_data.py crée tous les fichiers CSV attendus."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.generate_data import (
        generer_machines, generer_production, generer_qualite,
        generer_inventaire, generer_energie, generer_evenements
    )
    from unittest.mock import patch

    with patch("scripts.generate_data.DATA", tmp_path):
        generer_machines(2)
        generer_production(2)
        generer_qualite(2)
        generer_inventaire(2)
        generer_energie(2)
        generer_evenements(2)

    assert (tmp_path / "machines.csv").exists()
    assert (tmp_path / "production.csv").exists()
    assert (tmp_path / "quality.csv").exists()
    assert (tmp_path / "inventory.csv").exists()
    assert (tmp_path / "energy.csv").exists()
    assert (tmp_path / "events.csv").exists()


def test_generate_data_machines_contenu(tmp_path):
    """Le CSV machines contient les bonnes colonnes."""
    import csv
    from scripts.generate_data import generer_machines
    from unittest.mock import patch

    with patch("scripts.generate_data.DATA", tmp_path):
        generer_machines(1)

    with open(tmp_path / "machines.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        colonnes = reader.fieldnames
        premiere_ligne = next(reader)

    assert "timestamp" in colonnes
    assert "machine_id" in colonnes
    assert "temperature" in colonnes
    assert "vibration" in colonnes
    assert "anomalie" in colonnes
    assert premiere_ligne["machine_id"] in ["M001", "M002", "M003", "M004", "M005"]


def test_generate_data_production_contenu(tmp_path):
    """Le CSV production contient les bonnes colonnes."""
    import csv
    from scripts.generate_data import generer_production
    from unittest.mock import patch

    with patch("scripts.generate_data.DATA", tmp_path):
        generer_production(1)

    with open(tmp_path / "production.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        colonnes = reader.fieldnames

    assert "taux_realisation" in colonnes
    assert "statut" in colonnes
    assert "objectif" in colonnes


def test_generate_data_valeurs_realistes(tmp_path):
    """Les températures générées sont dans une plage réaliste."""
    import csv
    from scripts.generate_data import generer_machines
    from unittest.mock import patch

    with patch("scripts.generate_data.DATA", tmp_path):
        generer_machines(1)

    temperatures = []
    with open(tmp_path / "machines.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            temperatures.append(float(row["temperature"]))

    # La plage normale est 40-120°C ; M003 peut légèrement dépasser sous dégradation simulée
    assert all(20 <= t <= 200 for t in temperatures), "Températures hors plage physiquement possible"
    assert any(60 <= t <= 100 for t in temperatures), "Aucune température dans la plage nominale"
    assert len(temperatures) > 0

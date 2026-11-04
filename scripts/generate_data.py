#!/usr/bin/env python
"""Génère les données de simulation pour l'usine autonome.

Usage :
    python scripts/generate_data.py
    python scripts/generate_data.py --jours 30
"""
import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path
import csv

RACINE = Path(__file__).resolve().parents[1]
DATA = RACINE / "data"

MACHINES = ["M001", "M002", "M003", "M004", "M005"]
PRODUITS = ["PROD-A", "PROD-B", "PROD-C"]
MATIERES = ["Acier", "Aluminium", "Plastique", "Caoutchouc", "Cuivre"]

random.seed(42)


def horodatages(jours: int):
    """Génère des horodatages toutes les 15 minutes sur `jours` jours."""
    debut = datetime.now() - timedelta(days=jours)
    t = debut
    while t <= datetime.now():
        yield t
        t += timedelta(minutes=15)


def generer_machines(jours: int) -> None:
    """Données capteurs pour chaque machine : température, vibration, pression, état."""
    fichier = DATA / "machines.csv"
    with open(fichier, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "machine_id", "temperature", "vibration",
                         "pression", "rpm", "etat", "anomalie"])
        for ts in horodatages(jours):
            for machine in MACHINES:
                # Simulation de dégradation progressive pour M003
                facteur = 1.0
                if machine == "M003" and ts > datetime.now() - timedelta(days=5):
                    facteur = 1.0 + (ts - (datetime.now() - timedelta(days=5))).total_seconds() / 86400 * 0.1

                temp = round(random.gauss(75, 5) * facteur, 1)
                vib = round(random.gauss(2.5, 0.3) * facteur, 3)
                pression = round(random.gauss(6.0, 0.4) * facteur, 2)
                rpm = int(random.gauss(1500, 50))
                anomalie = temp > 90 or vib > 3.5 or pression > 7.5
                etat = "ALERTE" if anomalie else "OK"
                writer.writerow([ts.isoformat(), machine, temp, vib, pression, rpm, etat, int(anomalie)])
    print(f"  machines.csv : {sum(1 for _ in horodatages(jours)) * len(MACHINES)} lignes")


def generer_production(jours: int) -> None:
    """Ordres de fabrication, quantités produites vs objectifs."""
    fichier = DATA / "production.csv"
    with open(fichier, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "machine_id", "produit", "objectif", "produit_reel",
                         "taux_realisation", "retard", "statut"])
        for i in range(jours * 3):
            date = (datetime.now() - timedelta(days=jours) + timedelta(days=i // 3)).date()
            machine = random.choice(MACHINES)
            produit = random.choice(PRODUITS)
            objectif = random.randint(80, 150)
            retard_facteur = 0.7 if machine == "M003" and i > jours * 2 else 1.0
            produit_reel = int(random.gauss(objectif * retard_facteur, 10))
            taux = round(produit_reel / objectif, 3)
            retard = max(0, objectif - produit_reel)
            statut = "OK" if taux >= 0.95 else ("RETARD" if taux >= 0.80 else "CRITIQUE")
            writer.writerow([date, machine, produit, objectif, produit_reel, taux, retard, statut])
    print(f"  production.csv : {jours * 3} lignes")


def generer_qualite(jours: int) -> None:
    """Contrôles qualité : taux de conformité, défauts détectés."""
    fichier = DATA / "quality.csv"
    with open(fichier, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "machine_id", "produit", "lot_taille",
                         "conformes", "defauts", "taux_conformite", "type_defaut", "statut"])
        defauts_types = ["Rayure", "Deformation", "Inclusion", "Porosite", "Aucun"]
        for i in range(jours * 3):
            date = (datetime.now() - timedelta(days=jours) + timedelta(days=i // 3)).date()
            machine = random.choice(MACHINES)
            produit = random.choice(PRODUITS)
            lot = random.randint(50, 200)
            # M002 a un problème de qualité simulé
            taux_defaut = 0.15 if machine == "M002" else 0.03
            defauts = int(lot * taux_defaut * random.gauss(1, 0.2))
            conformes = lot - defauts
            taux = round(conformes / lot, 3)
            type_defaut = random.choice(defauts_types[:-1]) if defauts > 0 else "Aucun"
            statut = "OK" if taux >= 0.95 else ("ALERTE" if taux >= 0.85 else "CRITIQUE")
            writer.writerow([date, machine, produit, lot, conformes, defauts, taux, type_defaut, statut])
    print(f"  quality.csv : {jours * 3} lignes")


def generer_inventaire(jours: int) -> None:
    """Niveaux de stock des matières premières."""
    fichier = DATA / "inventory.csv"
    with open(fichier, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "matiere", "stock_actuel", "stock_min",
                         "stock_max", "consommation_jour", "jours_restants", "statut"])
        stocks = {m: random.randint(500, 2000) for m in MATIERES}
        for i in range(jours):
            date = (datetime.now() - timedelta(days=jours - i)).date()
            for matiere in MATIERES:
                conso = random.randint(30, 80)
                stocks[matiere] = max(0, stocks[matiere] - conso + random.randint(0, 50))
                stock = stocks[matiere]
                stock_min = 200
                stock_max = 2000
                jours_restants = stock // conso if conso > 0 else 99
                statut = "RUPTURE" if stock <= 0 else (
                    "CRITIQUE" if stock < stock_min else (
                        "BAS" if jours_restants < 7 else "OK"
                    )
                )
                writer.writerow([date, matiere, stock, stock_min, stock_max,
                                  conso, jours_restants, statut])
    print(f"  inventory.csv : {jours * len(MATIERES)} lignes")


def generer_energie(jours: int) -> None:
    """Consommation énergétique par machine."""
    fichier = DATA / "energy.csv"
    with open(fichier, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "machine_id", "conso_kwh", "puissance_kw",
                         "cout_eur", "anomalie_conso", "statut"])
        for ts in horodatages(jours):
            for machine in MACHINES:
                # M004 consomme anormalement
                facteur = 1.5 if machine == "M004" and ts.hour in range(8, 18) else 1.0
                conso = round(random.gauss(15, 2) * facteur, 2)
                puissance = round(conso * 4, 1)
                cout = round(conso * 0.12, 3)
                anomalie = conso > 25
                statut = "ANOMALIE" if anomalie else "OK"
                writer.writerow([ts.isoformat(), machine, conso, puissance, cout, int(anomalie), statut])
    print(f"  energy.csv : généré")


def generer_evenements(jours: int) -> None:
    """Journal des événements de l'usine."""
    fichier = DATA / "events.csv"
    types = ["PANNE", "MAINTENANCE", "PRODUCTION_STOP", "QUALITE_ALERTE",
             "STOCK_BAS", "ENERGIE_ANOMALIE", "REPRISE"]
    agents = ["ProductionAgent", "MaintenanceAgent", "QualityAgent",
              "InventoryAgent", "EnergyAgent", "SupervisorAgent"]
    with open(fichier, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "type", "machine_id", "agent", "severite",
                         "description", "action_prise", "resolu"])
        for i in range(jours * 2):
            ts = datetime.now() - timedelta(days=jours) + timedelta(hours=i * 12)
            machine = random.choice(MACHINES)
            type_evt = random.choice(types)
            agent = random.choice(agents)
            severite = random.choice(["INFO", "AVERTISSEMENT", "CRITIQUE"])
            desc = f"Événement {type_evt} détecté sur {machine}"
            action = f"Intervention planifiée par {agent}"
            writer.writerow([ts.isoformat(), type_evt, machine, agent,
                              severite, desc, action, random.randint(0, 1)])
    print(f"  events.csv : {jours * 2} lignes")


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère les données de simulation de l'usine")
    parser.add_argument("--jours", type=int, default=30, help="Nombre de jours d'historique")
    args = parser.parse_args()

    DATA.mkdir(exist_ok=True)
    print(f"Génération de {args.jours} jours de données...")
    generer_machines(args.jours)
    generer_production(args.jours)
    generer_qualite(args.jours)
    generer_inventaire(args.jours)
    generer_energie(args.jours)
    generer_evenements(args.jours)
    print("Données générées avec succès dans data/")


if __name__ == "__main__":
    main()

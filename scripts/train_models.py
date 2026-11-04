#!/usr/bin/env python
"""Entraîne les modèles ML pour les agents de l'usine autonome.

Usage :
    python scripts/train_models.py
    python scripts/train_models.py --force

Modèles produits dans models/ :
    - anomaly_detector.joblib   : détection d'anomalies machines (IsolationForest)
    - failure_predictor.joblib  : prédiction de pannes (RandomForest)
    - quality_classifier.joblib : classification qualité (GradientBoosting)
    - energy_forecaster.joblib  : prédiction consommation (LinearRegression)
    - metrics.json              : métriques de tous les modèles
"""
import argparse
import json
from pathlib import Path

import numpy as np
import joblib
from sklearn.ensemble import IsolationForest, RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

RACINE = Path(__file__).resolve().parents[1]
DATA = RACINE / "data"
MODELS = RACINE / "models"


def charger_donnees_machines() -> tuple:
    """Charge et prépare les données capteurs pour la détection d'anomalies."""
    import csv
    X, y = [], []
    fichier = DATA / "machines.csv"
    if not fichier.exists():
        raise FileNotFoundError(f"Lancez d'abord : python scripts/generate_data.py")
    with open(fichier, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            X.append([float(row["temperature"]), float(row["vibration"]),
                       float(row["pression"]), float(row["rpm"])])
            y.append(int(row["anomalie"]))
    return np.array(X), np.array(y)


def charger_donnees_production() -> tuple:
    """Charge les données de production pour la prédiction de pannes."""
    import csv
    X, y = [], []
    fichier = DATA / "production.csv"
    if not fichier.exists():
        raise FileNotFoundError("Lancez d'abord : python scripts/generate_data.py")
    statut_map = {"OK": 0, "RETARD": 1, "CRITIQUE": 2}
    with open(fichier, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            X.append([float(row["objectif"]), float(row["produit_reel"]),
                       float(row["taux_realisation"]), float(row["retard"])])
            y.append(statut_map.get(row["statut"], 0))
    return np.array(X), np.array(y)


def charger_donnees_qualite() -> tuple:
    """Charge les données qualité pour la classification."""
    import csv
    X, y = [], []
    fichier = DATA / "quality.csv"
    if not fichier.exists():
        raise FileNotFoundError("Lancez d'abord : python scripts/generate_data.py")
    statut_map = {"OK": 0, "ALERTE": 1, "CRITIQUE": 2}
    with open(fichier, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            X.append([float(row["lot_taille"]), float(row["conformes"]),
                       float(row["defauts"]), float(row["taux_conformite"])])
            y.append(statut_map.get(row["statut"], 0))
    return np.array(X), np.array(y)


def charger_donnees_energie() -> tuple:
    """Charge les données d'énergie pour la prévision de consommation."""
    import csv
    from datetime import datetime
    X, y = [], []
    fichier = DATA / "energy.csv"
    if not fichier.exists():
        raise FileNotFoundError("Lancez d'abord : python scripts/generate_data.py")
    machine_map = {m: i for i, m in enumerate(["M001", "M002", "M003", "M004", "M005"])}
    with open(fichier, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = datetime.fromisoformat(row["timestamp"])
            machine_id = machine_map.get(row["machine_id"], 0)
            X.append([ts.hour, ts.weekday(), machine_id, float(row["puissance_kw"])])
            y.append(float(row["conso_kwh"]))
    return np.array(X), np.array(y)


def entrainer_detecteur_anomalies(X: np.ndarray, y: np.ndarray) -> dict:
    """IsolationForest pour détecter les comportements anormaux des machines."""
    print("  Entraînement du détecteur d'anomalies (IsolationForest)...")
    modele = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", IsolationForest(n_estimators=100, contamination=0.05, random_state=42))
    ])
    modele.fit(X)
    predictions = modele.predict(X)
    # IsolationForest : -1 = anomalie, 1 = normal → convertir
    pred_binaire = (predictions == -1).astype(int)
    # Calcul du taux de détection vs labels réels
    vrais_positifs = int(np.sum((pred_binaire == 1) & (y == 1)))
    total_anomalies = int(np.sum(y == 1))
    rappel = vrais_positifs / total_anomalies if total_anomalies > 0 else 0
    joblib.dump(modele, MODELS / "anomaly_detector.joblib")
    metriques = {
        "modele": "IsolationForest",
        "n_echantillons": len(X),
        "n_anomalies_detectees": int(np.sum(pred_binaire)),
        "n_anomalies_reelles": total_anomalies,
        "rappel_anomalies": round(rappel, 3)
    }
    print(f"    Anomalies détectées : {metriques['n_anomalies_detectees']} / {total_anomalies} réelles")
    return metriques


def entrainer_predicteur_pannes(X: np.ndarray, y: np.ndarray) -> dict:
    """RandomForest pour prédire l'état de production (OK/RETARD/CRITIQUE)."""
    print("  Entraînement du prédicteur de pannes (RandomForest)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    modele = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(n_estimators=100, random_state=42))
    ])
    modele.fit(X_train, y_train)
    y_pred = modele.predict(X_test)
    f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
    joblib.dump(modele, MODELS / "failure_predictor.joblib")
    metriques = {
        "modele": "RandomForest",
        "n_train": len(X_train),
        "n_test": len(X_test),
        "f1_macro": round(float(f1), 3)
    }
    print(f"    F1 macro : {f1:.3f}")
    return metriques


def entrainer_classificateur_qualite(X: np.ndarray, y: np.ndarray) -> dict:
    """GradientBoosting pour classifier la qualité des lots."""
    print("  Entraînement du classificateur qualité (GradientBoosting)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    modele = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(n_estimators=100, random_state=42))
    ])
    modele.fit(X_train, y_train)
    y_pred = modele.predict(X_test)
    f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
    joblib.dump(modele, MODELS / "quality_classifier.joblib")
    metriques = {
        "modele": "GradientBoosting",
        "n_train": len(X_train),
        "n_test": len(X_test),
        "f1_macro": round(float(f1), 3)
    }
    print(f"    F1 macro : {f1:.3f}")
    return metriques


def entrainer_predicteur_energie(X: np.ndarray, y: np.ndarray) -> dict:
    """Régression linéaire pour prédire la consommation énergétique."""
    print("  Entraînement du prédicteur d'énergie (LinearRegression)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    modele = Pipeline([
        ("scaler", StandardScaler()),
        ("reg", LinearRegression())
    ])
    modele.fit(X_train, y_train)
    y_pred = modele.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    joblib.dump(modele, MODELS / "energy_forecaster.joblib")
    metriques = {
        "modele": "LinearRegression",
        "n_train": len(X_train),
        "n_test": len(X_test),
        "mae_kwh": round(float(mae), 3)
    }
    print(f"    MAE : {mae:.3f} kWh")
    return metriques


def main() -> None:
    parser = argparse.ArgumentParser(description="Entraîne les modèles ML de l'usine")
    parser.add_argument("--force", action="store_true", help="Ré-entraîner même si les modèles existent")
    args = parser.parse_args()

    MODELS.mkdir(exist_ok=True)

    if not args.force and (MODELS / "metrics.json").exists():
        print("Modèles déjà entraînés. Utilisez --force pour ré-entraîner.")
        return

    print("Entraînement des modèles ML...")
    toutes_metriques = {}

    X_m, y_m = charger_donnees_machines()
    toutes_metriques["anomaly_detector"] = entrainer_detecteur_anomalies(X_m, y_m)

    X_p, y_p = charger_donnees_production()
    toutes_metriques["failure_predictor"] = entrainer_predicteur_pannes(X_p, y_p)

    X_q, y_q = charger_donnees_qualite()
    toutes_metriques["quality_classifier"] = entrainer_classificateur_qualite(X_q, y_q)

    X_e, y_e = charger_donnees_energie()
    toutes_metriques["energy_forecaster"] = entrainer_predicteur_energie(X_e, y_e)

    metrics_path = MODELS / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(toutes_metriques, f, indent=2, ensure_ascii=False)

    print(f"\nModèles sauvegardés dans models/")
    print(f"Métriques : {metrics_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Diagnostic de l'environnement — vérifie que tout est en place avant de démarrer.

Usage :
    python scripts/check_setup.py
"""
import sys
import importlib
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
ERREURS = []
AVERTISSEMENTS = []


def verifier(condition: bool, ok_msg: str, err_msg: str, avert: bool = False) -> None:
    if condition:
        print(f"  ✓  {ok_msg}")
    else:
        print(f"  {'⚠' if avert else '✗'}  {err_msg}")
        if avert:
            AVERTISSEMENTS.append(err_msg)
        else:
            ERREURS.append(err_msg)


def main() -> int:
    print(f"\n{'='*60}")
    print("  Diagnostic — Usine Autonome")
    print(f"{'='*60}\n")

    # Python
    print("[ Python ]")
    v = sys.version_info
    verifier(v >= (3, 11), f"Python {v.major}.{v.minor}.{v.micro}",
             f"Python 3.11+ requis (actuel : {v.major}.{v.minor})")

    # Dépendances Python
    print("\n[ Dépendances ]")
    deps = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("pydantic", "Pydantic"),
        ("sklearn", "scikit-learn"),
        ("joblib", "joblib"),
        ("numpy", "NumPy"),
        ("streamlit", "Streamlit"),
        ("pandas", "Pandas"),
        ("plotly", "Plotly"),
        ("httpx", "httpx"),
    ]
    for module, nom in deps:
        try:
            importlib.import_module(module)
            verifier(True, f"{nom} installé", "")
        except ImportError:
            verifier(False, "", f"{nom} manquant — pip install -r requirements.txt")

    # Structure du projet
    print("\n[ Structure du projet ]")
    dossiers = ["agents", "api", "app", "data", "docs", "models", "scripts", "tests", "ui"]
    for d in dossiers:
        verifier((RACINE / d).exists(), f"Dossier {d}/", f"Dossier {d}/ manquant")

    fichiers_cles = [
        "agents/base.py", "agents/production/agent.py", "agents/maintenance/agent.py",
        "agents/quality/agent.py", "agents/inventory/agent.py",
        "agents/energy/agent.py", "agents/supervisor/agent.py",
        "api/main.py", "api/schemas.py",
        "app/orchestrator.py", "app/cli.py",
        "ui/app.py", "ui/client.py",
        "requirements.txt", "pyproject.toml", "pytest.ini",
    ]
    print("\n[ Fichiers clés ]")
    for f in fichiers_cles:
        verifier((RACINE / f).exists(), f"{f}", f"{f} manquant")

    # Données et modèles
    print("\n[ Données de simulation ]")
    csvs = ["machines.csv", "production.csv", "quality.csv", "inventory.csv", "energy.csv"]
    for csv in csvs:
        existe = (RACINE / "data" / csv).exists()
        verifier(existe, f"data/{csv}", f"data/{csv} absent — lancez : python scripts/generate_data.py",
                 avert=True)

    print("\n[ Modèles ML ]")
    modeles = ["anomaly_detector.joblib", "failure_predictor.joblib",
               "quality_classifier.joblib", "energy_forecaster.joblib", "metrics.json"]
    for m in modeles:
        existe = (RACINE / "models" / m).exists()
        verifier(existe, f"models/{m}", f"models/{m} absent — lancez : python scripts/train_models.py",
                 avert=True)

    # Résumé
    print(f"\n{'='*60}")
    print(f"  {len(ERREURS)} erreur(s),  {len(AVERTISSEMENTS)} avertissement(s)")
    print(f"{'='*60}\n")

    if ERREURS:
        print("Erreurs bloquantes :")
        for e in ERREURS:
            print(f"  ✗ {e}")
        return 1

    if AVERTISSEMENTS:
        print("Avertissements (non bloquants) :")
        for a in AVERTISSEMENTS:
            print(f"  ⚠ {a}")
        print()

    if not ERREURS:
        print("Système prêt. Lancez :")
        print("  python scripts/generate_data.py")
        print("  python scripts/train_models.py")
        print("  uvicorn api.main:app --reload")
        print("  streamlit run ui/app.py")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

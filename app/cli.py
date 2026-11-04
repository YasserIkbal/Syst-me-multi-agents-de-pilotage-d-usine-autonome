"""Commande CLI « usine » — point d'entrée du système multi-agents.

Usage :
    usine --version
    usine generer-donnees [--jours 30]
    usine entrainer
    usine api [--host 127.0.0.1] [--port 8000]
    usine dashboard
    usine analyser
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from app import __version__

RACINE = Path(__file__).resolve().parents[1]


def _generer(args: argparse.Namespace) -> int:
    jours = getattr(args, "jours", 30)
    return subprocess.call([sys.executable,
                            str(RACINE / "scripts" / "generate_data.py"),
                            "--jours", str(jours)])


def _entrainer(args: argparse.Namespace) -> int:
    return subprocess.call([sys.executable,
                            str(RACINE / "scripts" / "train_models.py")])


def _api(args: argparse.Namespace) -> int:
    import uvicorn
    uvicorn.run("api.main:app", host=args.host, port=args.port, reload=True)
    return 0


def _dashboard(args: argparse.Namespace) -> int:
    page = RACINE / "ui" / "app.py"
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(page)])


def _analyser(args: argparse.Namespace) -> int:
    """Analyse synchrone et affiche les résultats dans le terminal."""
    import json
    from app.orchestrator import Orchestrateur
    orch = Orchestrateur()
    print("Analyse en cours...")
    resultats = orch.analyser_tous()
    for agent, resultat in resultats.items():
        statut = resultat.get("statut", "?")
        print(f"  [{statut:12s}] {agent}")
    print("\nDécision superviseur :")
    sup = resultats.get("SupervisorAgent", {})
    print(f"  {sup.get('decision', 'N/A')} — {sup.get('message_decision', '')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="usine",
        description="Système Multi-Agents de Pilotage d'Usine Autonome"
    )
    parser.add_argument("--version", action="version", version=f"usine-autonome {__version__}")
    cmds = parser.add_subparsers(dest="commande", required=True)

    # generer-donnees
    gen = cmds.add_parser("generer-donnees", help="Génère les données de simulation")
    gen.add_argument("--jours", type=int, default=30)
    gen.set_defaults(fonction=_generer)

    # entrainer
    entr = cmds.add_parser("entrainer", help="Entraîne les modèles ML")
    entr.set_defaults(fonction=_entrainer)

    # api
    api_cmd = cmds.add_parser("api", help="Lance l'API FastAPI")
    api_cmd.add_argument("--host", default="127.0.0.1")
    api_cmd.add_argument("--port", type=int, default=8000)
    api_cmd.set_defaults(fonction=_api)

    # dashboard
    dash = cmds.add_parser("dashboard", help="Lance le dashboard Streamlit")
    dash.set_defaults(fonction=_dashboard)

    # analyser
    ana = cmds.add_parser("analyser", help="Analyse immédiate de tous les agents")
    ana.set_defaults(fonction=_analyser)

    args = parser.parse_args(argv)
    return int(args.fonction(args))


if __name__ == "__main__":
    raise SystemExit(main())

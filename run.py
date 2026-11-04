#!/usr/bin/env python
"""Script de lancement — démarre l'API et le dashboard depuis n'importe où.

Usage :
    python run.py            → démarre l'API + affiche les instructions
    python run.py --api      → lance uniquement l'API (port 8000)
    python run.py --ui       → lance uniquement le dashboard Streamlit (port 8501)
    python run.py --check    → diagnostic d'installation
"""
import argparse
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent


def lancer_api() -> subprocess.Popen:
    print("🚀 Démarrage de l'API sur http://127.0.0.1:8000 ...")
    print("   Documentation : http://127.0.0.1:8000/docs")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--reload",
         "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(RACINE)
    )


def lancer_ui() -> subprocess.Popen:
    print("🖥️  Démarrage du dashboard sur http://localhost:8501 ...")
    ui_path = RACINE / "ui" / "app.py"
    return subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(ui_path),
         "--server.port", "8501"],
        cwd=str(RACINE)
    )


def check() -> None:
    subprocess.call([sys.executable, str(RACINE / "scripts" / "check_setup.py")],
                    cwd=str(RACINE))


def main() -> None:
    parser = argparse.ArgumentParser(description="Lancement du système Usine Autonome")
    parser.add_argument("--api",   action="store_true", help="Lance uniquement l'API")
    parser.add_argument("--ui",    action="store_true", help="Lance uniquement le dashboard")
    parser.add_argument("--check", action="store_true", help="Diagnostic d'installation")
    args = parser.parse_args()

    if args.check:
        check()
        return

    if args.api:
        p = lancer_api()
        try:
            p.wait()
        except KeyboardInterrupt:
            p.terminate()
        return

    if args.ui:
        p = lancer_ui()
        try:
            p.wait()
        except KeyboardInterrupt:
            p.terminate()
        return

    # Par défaut : afficher les instructions claires
    print()
    print("=" * 60)
    print("  🏭  USINE AUTONOME — Système Multi-Agents")
    print("=" * 60)
    print()
    print("Ouvrez DEUX terminaux dans ce dossier :")
    print(f"  {RACINE}")
    print()
    print("─" * 60)
    print("  TERMINAL 1 — API FastAPI :")
    print("    python run.py --api")
    print("    → http://127.0.0.1:8000/docs")
    print()
    print("  TERMINAL 2 — Dashboard Streamlit :")
    print("    python run.py --ui")
    print("    → http://localhost:8501")
    print("─" * 60)
    print()
    print("  Ou manuellement :")
    print("    uvicorn api.main:app --reload")
    print("    streamlit run ui/app.py")
    print()
    print("  Diagnostic :")
    print("    python run.py --check")
    print("=" * 60)


if __name__ == "__main__":
    main()

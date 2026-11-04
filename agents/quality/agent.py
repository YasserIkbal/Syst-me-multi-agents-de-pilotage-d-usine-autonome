"""Agent de Contrôle Qualité — détecte les défauts, analyse les taux de non-conformité.

Responsabilités :
- Contrôler la qualité des lots produits
- Détecter les défauts et non-conformités
- Analyser les tendances de qualité par machine
- Proposer des actions correctives
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from agents.base import BaseAgent, MessageBus

RACINE = Path(__file__).resolve().parents[2]
DATA = RACINE / "data"
MODELS = RACINE / "models"

SEUIL_CONFORMITE_MIN = 0.95     # en dessous → alerte
SEUIL_CONFORMITE_CRITIQUE = 0.85  # en dessous → critique


class QualityAgent(BaseAgent):
    """Agent spécialisé dans le contrôle qualité des productions."""

    def __init__(self, bus: MessageBus) -> None:
        super().__init__("QualityAgent", bus)
        self._modele = self._charger_modele()

    def _charger_modele(self):
        chemin = MODELS / "quality_classifier.joblib"
        if chemin.exists():
            return joblib.load(chemin)
        return None

    def _lire_qualite_recente(self) -> list[dict]:
        fichier = DATA / "quality.csv"
        if not fichier.exists():
            return []
        seuil = (datetime.now() - timedelta(days=7)).date()
        lignes = []
        with open(fichier, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    if datetime.strptime(row["date"], "%Y-%m-%d").date() >= seuil:
                        lignes.append(row)
                except (ValueError, KeyError):
                    continue
        return lignes

    def _analyser_par_machine(self, donnees: list[dict]) -> dict[str, dict]:
        """Calcule les indicateurs qualité par machine."""
        par_machine: dict[str, dict] = {}
        for d in donnees:
            m = d.get("machine_id", "INCONNU")
            if m not in par_machine:
                par_machine[m] = {"taux": [], "defauts": 0, "lots": 0, "types_defauts": {}}
            try:
                par_machine[m]["taux"].append(float(d["taux_conformite"]))
                par_machine[m]["defauts"] += int(d["defauts"])
                par_machine[m]["lots"] += 1
                td = d.get("type_defaut", "Aucun")
                if td and td != "Aucun":
                    par_machine[m]["types_defauts"][td] = par_machine[m]["types_defauts"].get(td, 0) + 1
            except (ValueError, KeyError):
                continue

        # Calculer les moyennes
        for m, stats in par_machine.items():
            taux = stats["taux"]
            stats["taux_moyen"] = round(sum(taux) / len(taux), 3) if taux else 0
            stats["taux_min"] = round(min(taux), 3) if taux else 0
            del stats["taux"]

        return par_machine

    def _classifier_lot_ml(self, lot_taille: int, conformes: int,
                            defauts: int, taux: float) -> str:
        """Utilise le modèle ML pour classifier l'état d'un lot."""
        if not self._modele:
            return "INCONNU"
        try:
            X = np.array([[lot_taille, conformes, defauts, taux]])
            pred = self._modele.predict(X)[0]
            return ["OK", "ALERTE", "CRITIQUE"][int(pred)]
        except Exception:
            return "INCONNU"

    def analyser(self) -> dict[str, Any]:
        donnees = self._lire_qualite_recente()
        if not donnees:
            return {"statut": "DONNEES_MANQUANTES", "message": "Aucune donnée qualité"}

        par_machine = self._analyser_par_machine(donnees)

        # Indicateurs globaux
        tous_taux = [v["taux_moyen"] for v in par_machine.values() if v["taux_moyen"] > 0]
        taux_global = round(sum(tous_taux) / len(tous_taux), 3) if tous_taux else 0
        total_defauts = sum(v["defauts"] for v in par_machine.values())

        # Machines hors conformité
        machines_alertes = {m: v for m, v in par_machine.items()
                            if v["taux_moyen"] < SEUIL_CONFORMITE_MIN}
        machines_critiques = {m: v for m, v in par_machine.items()
                               if v["taux_moyen"] < SEUIL_CONFORMITE_CRITIQUE}

        # Actions correctives
        actions = []
        for machine, stats in machines_critiques.items():
            actions.append({
                "machine": machine,
                "taux_conformite": stats["taux_moyen"],
                "defauts_principaux": stats["types_defauts"],
                "action": "ARRET_INSPECTION",
                "urgence": "IMMEDIATE"
            })
        for machine, stats in machines_alertes.items():
            if machine not in machines_critiques:
                actions.append({
                    "machine": machine,
                    "taux_conformite": stats["taux_moyen"],
                    "action": "REGLAGE_PARAMETRES",
                    "urgence": "PLANIFIEE"
                })

        # Classification ML du dernier lot
        prediction_dernier_lot = None
        if donnees:
            dernier = donnees[-1]
            try:
                prediction_dernier_lot = self._classifier_lot_ml(
                    int(dernier["lot_taille"]), int(dernier["conformes"]),
                    int(dernier["defauts"]), float(dernier["taux_conformite"])
                )
            except (ValueError, KeyError):
                pass

        resultat = {
            "statut": "CRITIQUE" if machines_critiques else ("ALERTE" if machines_alertes else "OK"),
            "taux_conformite_global": taux_global,
            "total_defauts": total_defauts,
            "qualite_par_machine": par_machine,
            "machines_alertes": list(machines_alertes.keys()),
            "machines_critiques": list(machines_critiques.keys()),
            "actions_correctives": actions,
            "prediction_dernier_lot": prediction_dernier_lot,
            "nb_lots_analyses": len(donnees),
            "horodatage": datetime.now().isoformat()
        }

        if machines_critiques:
            self.publier_alerte(
                f"Qualité critique sur {list(machines_critiques.keys())} — taux < {SEUIL_CONFORMITE_CRITIQUE:.0%}",
                {"machines": list(machines_critiques.keys()), "actions": actions},
                critique=True
            )
        elif machines_alertes:
            self.publier_alerte(
                f"Qualité dégradée sur {list(machines_alertes.keys())}",
                {"machines": list(machines_alertes.keys()), "taux_global": taux_global}
            )

        self.publier("RAPPORT", resultat, destinataire="SupervisorAgent")
        return resultat

    def rapport(self) -> dict[str, Any]:
        base = super().rapport()
        base["taux_conformite"] = self._derniere_analyse.get("taux_conformite_global", 0)
        base["actions_correctives"] = self._derniere_analyse.get("actions_correctives", [])
        return base

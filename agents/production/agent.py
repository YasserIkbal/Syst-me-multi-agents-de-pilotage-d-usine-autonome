"""Agent de Production — surveille les objectifs, détecte les retards, optimise les OF.

Responsabilités :
- Suivre les quantités produites vs objectifs
- Détecter les retards de production
- Optimiser les ordres de fabrication
- Alerter le superviseur en cas de dérive critique
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from agents.base import BaseAgent, MessageBus

RACINE = Path(__file__).resolve().parents[2]
DATA = RACINE / "data"
MODELS = RACINE / "models"


class ProductionAgent(BaseAgent):
    """Agent spécialisé dans le pilotage de la production."""

    def __init__(self, bus: MessageBus) -> None:
        super().__init__("ProductionAgent", bus)
        self._modele = self._charger_modele()

    def _charger_modele(self):
        """Charge le modèle de prédiction d'état de production."""
        chemin = MODELS / "failure_predictor.joblib"
        if chemin.exists():
            return joblib.load(chemin)
        return None

    def _lire_production_recente(self) -> list[dict]:
        """Lit les données de production des 7 derniers jours."""
        fichier = DATA / "production.csv"
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
        return lignes[-50:] if len(lignes) > 50 else lignes

    def analyser(self) -> dict[str, Any]:
        """Analyse l'état de la production et publie les alertes nécessaires."""
        donnees = self._lire_production_recente()
        if not donnees:
            return {"statut": "DONNEES_MANQUANTES", "message": "Aucune donnée de production"}

        # Calcul des indicateurs clés
        total = len(donnees)
        en_retard = sum(1 for d in donnees if d.get("statut") in ("RETARD", "CRITIQUE"))
        critiques = sum(1 for d in donnees if d.get("statut") == "CRITIQUE")
        taux_retard = round(en_retard / total, 3) if total > 0 else 0

        # Taux de réalisation moyen
        taux_realisations = []
        for d in donnees:
            try:
                taux_realisations.append(float(d["taux_realisation"]))
            except (ValueError, KeyError):
                continue
        taux_moyen = round(sum(taux_realisations) / len(taux_realisations), 3) if taux_realisations else 0

        # Machines les plus problématiques
        retards_par_machine: dict[str, int] = {}
        for d in donnees:
            if d.get("statut") in ("RETARD", "CRITIQUE"):
                m = d.get("machine_id", "INCONNU")
                retards_par_machine[m] = retards_par_machine.get(m, 0) + 1
        machine_critique = max(retards_par_machine, key=retards_par_machine.get) if retards_par_machine else None

        # Prédiction ML si modèle disponible
        prediction_ml = None
        if self._modele and donnees:
            dernier = donnees[-1]
            try:
                X = np.array([[float(dernier["objectif"]), float(dernier["produit_reel"]),
                                float(dernier["taux_realisation"]), float(dernier["retard"])]])
                pred = self._modele.predict(X)[0]
                prediction_ml = ["OK", "RETARD", "CRITIQUE"][int(pred)]
            except Exception:
                prediction_ml = None

        # Décision et alertes
        resultat = {
            "statut": "CRITIQUE" if critiques > 3 else ("ALERTE" if taux_retard > 0.3 else "OK"),
            "total_ordres": total,
            "en_retard": en_retard,
            "critiques": critiques,
            "taux_retard": taux_retard,
            "taux_realisation_moyen": taux_moyen,
            "machine_la_plus_problematique": machine_critique,
            "retards_par_machine": retards_par_machine,
            "prediction_ml": prediction_ml,
            "horodatage": datetime.now().isoformat()
        }

        # Publication des alertes
        if critiques > 3:
            self.publier_alerte(
                f"Production critique : {critiques} ordres en état CRITIQUE",
                {"machine": machine_critique, "taux_retard": taux_retard},
                critique=True
            )
        elif taux_retard > 0.3:
            self.publier_alerte(
                f"Retards de production : {en_retard}/{total} ordres en retard",
                {"taux_retard": taux_retard, "machine": machine_critique}
            )

        # Rapport périodique au superviseur
        self.publier("RAPPORT", resultat, destinataire="SupervisorAgent")
        return resultat

    def optimiser_ordres(self) -> list[dict]:
        """Propose une optimisation des ordres de fabrication."""
        donnees = self._lire_production_recente()
        recommandations = []
        for d in donnees[-10:]:
            if d.get("statut") == "CRITIQUE":
                recommandations.append({
                    "machine": d["machine_id"],
                    "action": "REDUIRE_CHARGE",
                    "raison": f"Taux réalisation {d['taux_realisation']}",
                    "priorite": "HAUTE"
                })
        return recommandations

    def rapport(self) -> dict[str, Any]:
        base = super().rapport()
        base["indicateurs"] = self._derniere_analyse
        base["recommandations"] = self.optimiser_ordres()
        return base

"""Agent de Maintenance — surveille les machines, anticipe les pannes.

Responsabilités :
- Analyser les données des capteurs (température, vibration, pression)
- Détecter les comportements anormaux via IsolationForest
- Anticiper les risques de panne (score de risque)
- Proposer des interventions préventives
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

# Seuils d'alerte pour chaque capteur
SEUILS = {
    "temperature": {"avertissement": 85.0, "critique": 92.0},
    "vibration": {"avertissement": 3.0, "critique": 4.0},
    "pression": {"avertissement": 7.0, "critique": 8.0},
}


class MaintenanceAgent(BaseAgent):
    """Agent spécialisé dans la maintenance préventive des machines."""

    def __init__(self, bus: MessageBus) -> None:
        super().__init__("MaintenanceAgent", bus)
        self._modele = self._charger_modele()
        self._historique_scores: dict[str, list[float]] = {}

    def _charger_modele(self):
        chemin = MODELS / "anomaly_detector.joblib"
        if chemin.exists():
            return joblib.load(chemin)
        return None

    def _lire_capteurs_recents(self) -> list[dict]:
        """Lit les données capteurs des dernières 24h."""
        fichier = DATA / "machines.csv"
        if not fichier.exists():
            return []
        seuil = datetime.now() - timedelta(hours=24)
        lignes = []
        with open(fichier, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ts = datetime.fromisoformat(row["timestamp"])
                    if ts >= seuil:
                        lignes.append(row)
                except (ValueError, KeyError):
                    continue
        return lignes[-200:] if len(lignes) > 200 else lignes

    def _calculer_score_risque(self, machine_id: str, donnees: list[dict]) -> float:
        """Calcule un score de risque de panne pour une machine (0.0 à 1.0)."""
        donnees_machine = [d for d in donnees if d.get("machine_id") == machine_id]
        if not donnees_machine:
            return 0.0

        scores = []
        for d in donnees_machine[-20:]:  # 20 dernières mesures
            try:
                temp = float(d["temperature"])
                vib = float(d["vibration"])
                pression = float(d["pression"])
            except (ValueError, KeyError):
                continue

            # Score normalisé par seuil critique
            s_temp = min(1.0, max(0.0, (temp - 70) / (SEUILS["temperature"]["critique"] - 70)))
            s_vib = min(1.0, max(0.0, (vib - 2.0) / (SEUILS["vibration"]["critique"] - 2.0)))
            s_pres = min(1.0, max(0.0, (pression - 5.0) / (SEUILS["pression"]["critique"] - 5.0)))
            scores.append((s_temp + s_vib + s_pres) / 3)

        return round(sum(scores) / len(scores), 3) if scores else 0.0

    def _detecter_anomalies_ml(self, donnees: list[dict]) -> dict[str, bool]:
        """Utilise IsolationForest pour détecter les anomalies par machine."""
        if not self._modele or not donnees:
            return {}

        resultats: dict[str, bool] = {}
        machines = set(d.get("machine_id", "") for d in donnees)

        for machine in machines:
            donnees_m = [d for d in donnees if d.get("machine_id") == machine]
            if len(donnees_m) < 5:
                continue
            try:
                X = np.array([[float(d["temperature"]), float(d["vibration"]),
                                float(d["pression"]), float(d["rpm"])]
                               for d in donnees_m[-20:]])
                preds = self._modele.predict(X)
                # -1 = anomalie dans IsolationForest
                resultats[machine] = bool(np.any(preds == -1))
            except Exception:
                resultats[machine] = False

        return resultats

    def analyser(self) -> dict[str, Any]:
        """Analyse l'état de toutes les machines et publie les alertes."""
        donnees = self._lire_capteurs_recents()
        if not donnees:
            return {"statut": "DONNEES_MANQUANTES", "message": "Aucune donnée capteur"}

        machines = ["M001", "M002", "M003", "M004", "M005"]
        scores_risque = {m: self._calculer_score_risque(m, donnees) for m in machines}
        anomalies_ml = self._detecter_anomalies_ml(donnees)

        # Machines en alerte par seuil
        alertes_seuil: dict[str, list[str]] = {}
        for d in donnees[-50:]:
            machine = d.get("machine_id", "INCONNU")
            try:
                temp = float(d["temperature"])
                vib = float(d["vibration"])
                pression = float(d["pression"])
                problemes = []
                if temp > SEUILS["temperature"]["critique"]:
                    problemes.append(f"TEMP_CRITIQUE:{temp:.1f}°C")
                elif temp > SEUILS["temperature"]["avertissement"]:
                    problemes.append(f"TEMP_HAUTE:{temp:.1f}°C")
                if vib > SEUILS["vibration"]["critique"]:
                    problemes.append(f"VIB_CRITIQUE:{vib:.3f}")
                if pression > SEUILS["pression"]["critique"]:
                    problemes.append(f"PRESSION_CRITIQUE:{pression:.2f}")
                if problemes:
                    alertes_seuil[machine] = problemes
            except (ValueError, KeyError):
                continue

        # Machine la plus à risque
        machine_critique = max(scores_risque, key=scores_risque.get) if scores_risque else None
        score_max = scores_risque.get(machine_critique, 0) if machine_critique else 0

        # Interventions recommandées
        interventions = []
        for machine, score in scores_risque.items():
            if score > 0.7:
                interventions.append({
                    "machine": machine,
                    "urgence": "IMMEDIATE",
                    "score_risque": score,
                    "type": "MAINTENANCE_PREVENTIVE"
                })
            elif score > 0.4 or anomalies_ml.get(machine, False):
                interventions.append({
                    "machine": machine,
                    "urgence": "PLANIFIEE",
                    "score_risque": score,
                    "type": "INSPECTION"
                })

        resultat = {
            "statut": "CRITIQUE" if score_max > 0.7 else ("ALERTE" if score_max > 0.4 else "OK"),
            "scores_risque": scores_risque,
            "anomalies_ml": anomalies_ml,
            "alertes_seuil": alertes_seuil,
            "machine_plus_risquee": machine_critique,
            "score_risque_max": score_max,
            "interventions_recommandees": interventions,
            "nb_machines_surveillees": len(machines),
            "nb_alertes": len(alertes_seuil),
            "horodatage": datetime.now().isoformat()
        }

        # Publications
        if score_max > 0.7:
            self.publier_alerte(
                f"Machine {machine_critique} : risque de panne élevé (score={score_max:.2f})",
                {"machine": machine_critique, "score": score_max, "interventions": interventions},
                critique=True
            )
        elif alertes_seuil:
            machines_alerte = list(alertes_seuil.keys())
            self.publier_alerte(
                f"Anomalies capteurs sur {len(machines_alerte)} machine(s)",
                {"machines": machines_alerte, "details": alertes_seuil}
            )

        self.publier("RAPPORT", resultat, destinataire="SupervisorAgent")
        return resultat

    def rapport(self) -> dict[str, Any]:
        base = super().rapport()
        base["etat_machines"] = self._derniere_analyse.get("scores_risque", {})
        base["interventions"] = self._derniere_analyse.get("interventions_recommandees", [])
        return base

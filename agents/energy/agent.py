"""Agent Énergie — surveille la consommation, détecte les anomalies, optimise.

Responsabilités :
- Surveiller la consommation énergétique par machine
- Identifier les consommations anormales
- Calculer les coûts et tendances
- Proposer des optimisations énergétiques
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

SEUIL_CONSO_NORMALE = 20.0   # kWh — au-dessus : anomalie
SEUIL_CONSO_CRITIQUE = 28.0  # kWh — au-dessus : critique
TARIF_KWH = 0.12             # €/kWh


class EnergyAgent(BaseAgent):
    """Agent spécialisé dans la gestion de l'énergie."""

    def __init__(self, bus: MessageBus) -> None:
        super().__init__("EnergyAgent", bus)
        self._modele = self._charger_modele()

    def _charger_modele(self):
        chemin = MODELS / "energy_forecaster.joblib"
        if chemin.exists():
            return joblib.load(chemin)
        return None

    def _lire_energie_recente(self) -> list[dict]:
        """Lit les données énergétiques des dernières 24h."""
        fichier = DATA / "energy.csv"
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

    def _analyser_par_machine(self, donnees: list[dict]) -> dict[str, dict]:
        """Calcule les indicateurs énergétiques par machine."""
        par_machine: dict[str, dict] = {}
        for d in donnees:
            m = d.get("machine_id", "INCONNU")
            if m not in par_machine:
                par_machine[m] = {"consos": [], "couts": [], "anomalies": 0}
            try:
                conso = float(d["conso_kwh"])
                cout = float(d["cout_eur"])
                anomalie = int(d.get("anomalie_conso", 0))
                par_machine[m]["consos"].append(conso)
                par_machine[m]["couts"].append(cout)
                par_machine[m]["anomalies"] += anomalie
            except (ValueError, KeyError):
                continue

        # Résumé par machine
        resume: dict[str, dict] = {}
        for m, stats in par_machine.items():
            consos = stats["consos"]
            couts = stats["couts"]
            if consos:
                resume[m] = {
                    "conso_moyenne_kwh": round(sum(consos) / len(consos), 2),
                    "conso_max_kwh": round(max(consos), 2),
                    "conso_totale_kwh": round(sum(consos), 2),
                    "cout_total_eur": round(sum(couts), 2),
                    "nb_anomalies": stats["anomalies"],
                    "taux_anomalie": round(stats["anomalies"] / len(consos), 3)
                }
        return resume

    def _prevoir_consommation(self, machine_id: str, heure: int) -> float | None:
        """Prédit la consommation pour une machine à une heure donnée."""
        if not self._modele:
            return None
        machine_map = {"M001": 0, "M002": 1, "M003": 2, "M004": 3, "M005": 4}
        mid = machine_map.get(machine_id, 0)
        try:
            X = np.array([[heure, datetime.now().weekday(), mid, 60.0]])
            return round(float(self._modele.predict(X)[0]), 2)
        except Exception:
            return None

    def _calculer_optimisations(self, par_machine: dict) -> list[dict]:
        """Identifie les optimisations possibles."""
        optimisations = []
        for machine, stats in par_machine.items():
            if stats["conso_moyenne_kwh"] > SEUIL_CONSO_CRITIQUE:
                optimisations.append({
                    "machine": machine,
                    "type": "REDUCTION_CHARGE",
                    "conso_actuelle": stats["conso_moyenne_kwh"],
                    "economie_potentielle_eur_jour": round(
                        (stats["conso_moyenne_kwh"] - SEUIL_CONSO_NORMALE) * 96 * TARIF_KWH, 2
                    ),
                    "urgence": "IMMEDIATE"
                })
            elif stats["nb_anomalies"] > 5:
                optimisations.append({
                    "machine": machine,
                    "type": "INSPECTION_ELECTRIQUE",
                    "nb_anomalies": stats["nb_anomalies"],
                    "urgence": "PLANIFIEE"
                })
        return optimisations

    def analyser(self) -> dict[str, Any]:
        donnees = self._lire_energie_recente()
        if not donnees:
            return {"statut": "DONNEES_MANQUANTES", "message": "Aucune donnée énergétique"}

        par_machine = self._analyser_par_machine(donnees)

        # Indicateurs globaux
        conso_totale = sum(v["conso_totale_kwh"] for v in par_machine.values())
        cout_total = sum(v["cout_total_eur"] for v in par_machine.values())
        nb_anomalies_total = sum(v["nb_anomalies"] for v in par_machine.values())

        # Machines anormales
        machines_anomalie = {m: v for m, v in par_machine.items()
                             if v["conso_moyenne_kwh"] > SEUIL_CONSO_NORMALE}
        machines_critiques = {m: v for m, v in par_machine.items()
                              if v["conso_moyenne_kwh"] > SEUIL_CONSO_CRITIQUE}

        optimisations = self._calculer_optimisations(par_machine)

        # Prévisions pour la prochaine heure
        heure_suivante = (datetime.now().hour + 1) % 24
        previsions = {m: self._prevoir_consommation(m, heure_suivante)
                      for m in ["M001", "M002", "M003", "M004", "M005"]}

        resultat = {
            "statut": "CRITIQUE" if machines_critiques else ("ALERTE" if machines_anomalie else "OK"),
            "conso_totale_kwh_24h": round(conso_totale, 2),
            "cout_total_eur_24h": round(cout_total, 2),
            "nb_anomalies_24h": nb_anomalies_total,
            "consommation_par_machine": par_machine,
            "machines_anomalie": list(machines_anomalie.keys()),
            "machines_critiques": list(machines_critiques.keys()),
            "optimisations": optimisations,
            "previsions_prochaine_heure": previsions,
            "horodatage": datetime.now().isoformat()
        }

        if machines_critiques:
            self.publier_alerte(
                f"Surconsommation critique sur {list(machines_critiques.keys())}",
                {"machines": list(machines_critiques.keys()), "optimisations": optimisations},
                critique=True
            )
        elif machines_anomalie:
            self.publier_alerte(
                f"Consommation anormale sur {list(machines_anomalie.keys())}",
                {"machines": list(machines_anomalie.keys()), "economie_possible": optimisations}
            )

        self.publier("RAPPORT", resultat, destinataire="SupervisorAgent")
        return resultat

    def rapport(self) -> dict[str, Any]:
        base = super().rapport()
        base["conso_24h_kwh"] = self._derniere_analyse.get("conso_totale_kwh_24h", 0)
        base["cout_24h_eur"] = self._derniere_analyse.get("cout_total_eur_24h", 0)
        base["optimisations"] = self._derniere_analyse.get("optimisations", [])
        return base

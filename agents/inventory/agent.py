"""Agent Inventaire — surveille les stocks, détecte les ruptures, calcule les besoins.

Responsabilités :
- Surveiller les niveaux de stock des matières premières
- Détecter les risques de rupture de stock
- Calculer les besoins en approvisionnement
- Coordonner les besoins avec l'agent de production
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from agents.base import BaseAgent, MessageBus

RACINE = Path(__file__).resolve().parents[2]
DATA = RACINE / "data"

STOCK_MIN_JOURS = 7    # alerte si moins de 7 jours de stock
STOCK_CRITIQUE_JOURS = 3  # critique si moins de 3 jours


class InventoryAgent(BaseAgent):
    """Agent spécialisé dans la gestion des stocks."""

    def __init__(self, bus: MessageBus) -> None:
        super().__init__("InventoryAgent", bus)
        self._commandes_en_cours: dict[str, dict] = {}

    def _lire_stocks_actuels(self) -> list[dict]:
        """Lit les données de stock les plus récentes."""
        fichier = DATA / "inventory.csv"
        if not fichier.exists():
            return []
        # Prendre les données des 3 derniers jours
        seuil = (datetime.now() - timedelta(days=3)).date()
        lignes = []
        with open(fichier, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    if datetime.strptime(row["date"], "%Y-%m-%d").date() >= seuil:
                        lignes.append(row)
                except (ValueError, KeyError):
                    continue
        # Garder la dernière mesure par matière
        derniers: dict[str, dict] = {}
        for row in lignes:
            derniers[row.get("matiere", "")] = row
        return list(derniers.values())

    def _lire_historique_consommation(self, matiere: str, jours: int = 14) -> float:
        """Calcule la consommation moyenne journalière d'une matière."""
        fichier = DATA / "inventory.csv"
        if not fichier.exists():
            return 50.0  # valeur par défaut
        seuil = (datetime.now() - timedelta(days=jours)).date()
        consos = []
        with open(fichier, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    if (row.get("matiere") == matiere and
                            datetime.strptime(row["date"], "%Y-%m-%d").date() >= seuil):
                        consos.append(float(row["consommation_jour"]))
                except (ValueError, KeyError):
                    continue
        return round(sum(consos) / len(consos), 1) if consos else 50.0

    def _calculer_commande(self, matiere: str, stock: float, conso_jour: float) -> dict:
        """Calcule la quantité à commander pour remettre le stock à niveau."""
        jours_cibles = 30  # viser 30 jours de stock
        stock_cible = conso_jour * jours_cibles
        quantite = max(0, stock_cible - stock)
        return {
            "matiere": matiere,
            "stock_actuel": stock,
            "consommation_jour": conso_jour,
            "jours_restants": round(stock / conso_jour, 1) if conso_jour > 0 else 99,
            "quantite_a_commander": round(quantite, 0),
            "stock_cible": round(stock_cible, 0),
            "urgence": "IMMEDIATE" if stock / conso_jour < STOCK_CRITIQUE_JOURS else (
                "PLANIFIEE" if stock / conso_jour < STOCK_MIN_JOURS else "NON_URGENTE"
            )
        }

    def analyser(self) -> dict[str, Any]:
        stocks = self._lire_stocks_actuels()
        if not stocks:
            return {"statut": "DONNEES_MANQUANTES", "message": "Aucune donnée de stock"}

        commandes_urgentes = []
        commandes_planifiees = []
        ruptures = []
        detail_stocks: dict[str, dict] = {}

        for stock in stocks:
            matiere = stock.get("matiere", "INCONNU")
            try:
                stock_actuel = float(stock["stock_actuel"])
                conso = float(stock.get("consommation_jour", 50))
                jours_restants = float(stock.get("jours_restants", 99))
                statut = stock.get("statut", "OK")
            except (ValueError, KeyError):
                continue

            commande = self._calculer_commande(matiere, stock_actuel, conso)
            detail_stocks[matiere] = {
                "stock_actuel": stock_actuel,
                "jours_restants": jours_restants,
                "consommation_jour": conso,
                "statut": statut,
                "commande_suggeree": commande["quantite_a_commander"]
            }

            if statut == "RUPTURE" or jours_restants <= 0:
                ruptures.append(matiere)
                commandes_urgentes.append(commande)
            elif jours_restants < STOCK_CRITIQUE_JOURS:
                commandes_urgentes.append(commande)
            elif jours_restants < STOCK_MIN_JOURS:
                commandes_planifiees.append(commande)

        # Statut global
        if ruptures or commandes_urgentes:
            statut_global = "CRITIQUE"
        elif commandes_planifiees:
            statut_global = "ALERTE"
        else:
            statut_global = "OK"

        # Valeur totale du stock (estimation)
        prix_unitaire = {"Acier": 2.5, "Aluminium": 4.0, "Plastique": 1.8,
                         "Caoutchouc": 3.2, "Cuivre": 8.5}
        valeur_stock = sum(
            detail_stocks.get(m, {}).get("stock_actuel", 0) * prix_unitaire.get(m, 2.0)
            for m in detail_stocks
        )

        resultat = {
            "statut": statut_global,
            "stocks": detail_stocks,
            "ruptures": ruptures,
            "commandes_urgentes": commandes_urgentes,
            "commandes_planifiees": commandes_planifiees,
            "valeur_totale_stock_eur": round(valeur_stock, 2),
            "nb_matieres_surveillees": len(detail_stocks),
            "horodatage": datetime.now().isoformat()
        }

        # Alertes
        if ruptures:
            self.publier_alerte(
                f"RUPTURE DE STOCK : {ruptures}",
                {"ruptures": ruptures, "commandes_urgentes": commandes_urgentes},
                critique=True
            )
            # Informer aussi l'agent de production
            self.publier("ALERTE", {
                "type": "RUPTURE_STOCK",
                "matieres": ruptures,
                "impact": "ARRET_PRODUCTION_POSSIBLE"
            }, destinataire="ProductionAgent", priorite=2)
        elif commandes_urgentes:
            self.publier_alerte(
                f"Stock bas pour {len(commandes_urgentes)} matière(s)",
                {"commandes": commandes_urgentes}
            )

        self.publier("RAPPORT", resultat, destinataire="SupervisorAgent")
        return resultat

    def rapport(self) -> dict[str, Any]:
        base = super().rapport()
        base["stocks"] = self._derniere_analyse.get("stocks", {})
        base["commandes_urgentes"] = self._derniere_analyse.get("commandes_urgentes", [])
        return base

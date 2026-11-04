# Données de simulation — Usine Autonome

Ce dossier contient les données de simulation pour l'usine autonome.

## Fichiers générés par `scripts/generate_data.py`

| Fichier | Description |
|---------|-------------|
| `machines.csv` | Historique des capteurs (température, vibration, pression) |
| `production.csv` | Ordres de fabrication et quantités produites |
| `quality.csv` | Contrôles qualité et taux de conformité |
| `inventory.csv` | Niveaux de stock des matières premières |
| `energy.csv` | Consommation énergétique par machine |
| `events.csv` | Journal des événements de l'usine |

## Générer les données

```powershell
python scripts/generate_data.py
```

# Architecture — Système Multi-Agents Usine Autonome

## Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────┐
│                    Interface Streamlit                        │
│                    ui/app.py  (port 8501)                     │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP (httpx)
┌──────────────────────▼───────────────────────────────────────┐
│                     API FastAPI                               │
│                  api/main.py  (port 8000)                     │
│  /health  /usine/etat  /agents  /messages  /commandes        │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│                   Orchestrateur                               │
│              app/orchestrator.py                              │
│   Démarre / arrête les 6 agents · Expose leur état           │
└──────────────┬───────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────────┐
│                      Bus de Messages                                  │
│                   agents/base.py — MessageBus                        │
│   Thread-safe · Files par agent · Historique 500 messages           │
│                                                                      │
│  ┌──────────┐ ┌───────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐   │
│  │Production│ │Maintenance│ │Qualité  │ │Inventaire│ │Énergie │   │
│  │  Agent   │ │  Agent    │ │ Agent   │ │  Agent   │ │ Agent  │   │
│  └────┬─────┘ └─────┬─────┘ └────┬────┘ └─────┬────┘ └───┬────┘   │
│       └─────────────┴────────────┴─────────────┴──────────┘        │
│                              │ RAPPORT / ALERTE                      │
│                   ┌──────────▼──────────┐                           │
│                   │   SupervisorAgent   │                           │
│                   │  Coordonne · Décide │                           │
│                   └─────────────────────┘                           │
└──────────────────────────────────────────────────────────────────────┘
               │
┌──────────────▼────────────────────┐
│         Modèles ML (models/)       │
│  anomaly_detector.joblib           │  ← IsolationForest (Maintenance)
│  failure_predictor.joblib          │  ← RandomForest (Production)
│  quality_classifier.joblib         │  ← GradientBoosting (Qualité)
│  energy_forecaster.joblib          │  ← LinearRegression (Énergie)
└───────────────────────────────────┘
               │
┌──────────────▼────────────────────┐
│       Données de Simulation (data/)│
│  machines.csv   · production.csv   │
│  quality.csv    · inventory.csv    │
│  energy.csv     · events.csv       │
└───────────────────────────────────┘
```

## Agents et responsabilités

| Agent | Modèle ML | Données | Seuil d'alerte |
|-------|-----------|---------|----------------|
| ProductionAgent | RandomForest | production.csv | taux réalisation < 95% |
| MaintenanceAgent | IsolationForest | machines.csv | score risque > 0.4 |
| QualityAgent | GradientBoosting | quality.csv | conformité < 95% |
| InventoryAgent | Règles métier | inventory.csv | jours stock < 7 |
| EnergyAgent | LinearRegression | energy.csv | conso > 20 kWh |
| SupervisorAgent | Agrégation | tous les rapports | ≥ 2 agents CRITIQUE |

## Communication inter-agents

Chaque agent spécialisé publie deux types de messages vers le bus :

1. **RAPPORT** → SupervisorAgent : état complet toutes les N secondes
2. **ALERTE** → SupervisorAgent + TOUS : en cas d'anomalie détectée

Le SupervisorAgent collecte tous les rapports, détecte les conflits, et publie
une **DÉCISION** globale (FONCTIONNEMENT_NORMAL → ARRET_D_URGENCE).

## Flux de décision

```
Capteurs/CSV
    │
    ▼
Agent spécialisé
    │  analyser()
    ▼
Modèle ML + Règles métier
    │
    ▼
Résultat { statut, indicateurs, recommandations }
    │
    ├─► RAPPORT → SupervisorAgent
    └─► ALERTE  → SupervisorAgent + TOUS (si anomalie)
                        │
                        ▼
              SupervisorAgent.analyser()
                        │
              _detecter_conflits()
              _prioriser_actions()
              _calculer_sante_usine()
                        │
                        ▼
              DÉCISION GLOBALE
              → API → Dashboard
```

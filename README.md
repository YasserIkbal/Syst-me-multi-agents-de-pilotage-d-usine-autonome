# 🏭 Système Multi-Agents de Pilotage d'une Usine Autonome

Système intelligent de pilotage d'usine basé sur **6 agents IA spécialisés** qui communiquent
et collaborent en temps réel pour surveiller, analyser et prendre des décisions autonomes.

## Architecture rapide

```
Streamlit Dashboard (8501) ──► FastAPI (8000) ──► Orchestrateur
                                                        │
                              ┌─────────────────────────┤
                              │      Bus de Messages     │
                    ┌─────────┴──────────────────────────┴─────────┐
                    │                                               │
              [Production]  [Maintenance]  [Qualité]  [Inventaire]  [Énergie]
                    └──────────────────────┬────────────────────────┘
                                           │  RAPPORTS + ALERTES
                                    [Superviseur]
                                    Coordonne · Décide
```

## Agents IA

| Agent | Rôle | Modèle ML |
|-------|------|-----------|
| 🏗️ ProductionAgent | Objectifs, retards, ordres de fabrication | RandomForest |
| 🔧 MaintenanceAgent | Capteurs, anomalies, risques de panne | IsolationForest |
| ✅ QualityAgent | Conformité des lots, défauts, actions correctives | GradientBoosting |
| 📦 InventoryAgent | Stocks, ruptures, calcul des commandes | Règles métier |
| ⚡ EnergyAgent | Consommation, anomalies, optimisations | LinearRegression |
| 🧠 SupervisorAgent | Coordination, conflits, décision globale | Agrégation |

## Prérequis

- Python **3.11** ou 3.12
- Windows / Linux / macOS

## Installation

```powershell
# 1. Aller dans le dossier du projet
cd usine-autonome

# 2. Créer et activer l'environnement virtuel
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # Linux / macOS

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Vérifier l'installation
python scripts/check_setup.py
```

## Démarrage rapide (3 étapes)

### Étape 1 — Générer les données de simulation

```powershell
python scripts/generate_data.py --jours 30
```

Produit dans `data/` : machines.csv, production.csv, quality.csv, inventory.csv, energy.csv, events.csv

### Étape 2 — Entraîner les modèles ML

```powershell
python scripts/train_models.py
```

Produit dans `models/` : anomaly_detector.joblib, failure_predictor.joblib,
quality_classifier.joblib, energy_forecaster.joblib, metrics.json

### Étape 3 — Lancer le système (2 terminaux)

**Terminal 1 — API :**
```powershell
uvicorn api.main:app --reload
```

**Terminal 2 — Dashboard :**
```powershell
streamlit run ui/app.py
```

Ouvrez **http://localhost:8501** dans votre navigateur.

## Commande CLI

Après `pip install -e .` :

```powershell
usine --version
usine generer-donnees --jours 30
usine entrainer
usine api
usine dashboard
usine analyser          # analyse synchrone en terminal
```

## Lancer les tests

```powershell
# Tests complets
python -m pytest -q

# Avec couverture
python -m pytest --cov=agents --cov=api --cov=app --cov-report=term-missing

# Un groupe de tests
python -m pytest tests/test_agents_base.py -v
python -m pytest tests/test_agents_specialises.py -v
python -m pytest tests/test_api.py -v
```

## API — Documentation interactive

Une fois l'API lancée, ouvrez :
- **http://localhost:8000/docs** — Swagger UI
- **http://localhost:8000/redoc** — ReDoc

### Exemples d'appels

```powershell
# Santé de l'API
python -c "import httpx; print(httpx.get('http://localhost:8000/health').json())"

# État de l'usine
python -c "import httpx; print(httpx.get('http://localhost:8000/usine/etat').json())"

# Commande manuelle sur une machine
python -c "
import httpx, json
r = httpx.post('http://localhost:8000/machines/commande', json={
    'machine_id': 'M003',
    'action': 'MAINTENANCE',
    'raison': 'Maintenance preventive planifiee'
})
print(json.dumps(r.json(), indent=2, ensure_ascii=False))
"
```

## Structure du projet

```
usine-autonome/
├── agents/                    ← Les 6 agents IA
│   ├── base.py                ← BaseAgent + MessageBus
│   ├── production/agent.py    ← Agent Production (RandomForest)
│   ├── maintenance/agent.py   ← Agent Maintenance (IsolationForest)
│   ├── quality/agent.py       ← Agent Qualité (GradientBoosting)
│   ├── inventory/agent.py     ← Agent Inventaire (règles métier)
│   ├── energy/agent.py        ← Agent Énergie (LinearRegression)
│   └── supervisor/agent.py    ← Agent Superviseur (coordinateur)
│
├── api/                       ← API FastAPI
│   ├── main.py                ← Endpoints REST
│   └── schemas.py             ← Contrats Pydantic
│
├── app/                       ← Logique applicative
│   ├── __init__.py            ← Version 1.0.0
│   ├── orchestrator.py        ← Singleton — démarre les agents
│   └── cli.py                 ← Commande `usine`
│
├── ui/                        ← Interface Streamlit
│   ├── app.py                 ← Dashboard 6 pages
│   └── client.py              ← Client HTTP vers l'API
│
├── scripts/                   ← Scripts utilitaires
│   ├── generate_data.py       ← Génère les données CSV
│   ├── train_models.py        ← Entraîne les 4 modèles ML
│   └── check_setup.py         ← Diagnostic d'installation
│
├── tests/                     ← Tests (pytest)
│   ├── test_agents_base.py    ← Bus + BaseAgent (12 tests)
│   ├── test_agents_specialises.py ← 6 agents (24 tests)
│   ├── test_api.py            ← API FastAPI (16 tests)
│   ├── test_orchestrateur.py  ← Orchestrateur (6 tests)
│   └── test_scripts.py        ← Scripts utilitaires (4 tests)
│
├── data/                      ← Données de simulation (générées)
├── models/                    ← Modèles ML (entraînés)
├── docs/                      ← Documentation
│   ├── architecture.md        ← Schéma d'architecture
│   └── journal.md             ← Journal de bord
│
├── .github/workflows/ci.yml   ← CI GitHub Actions
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── pytest.ini
```

## Fonctionnement des agents

### Communication

```
ProductionAgent ──RAPPORT──► SupervisorAgent
MaintenanceAgent ──ALERTE──► SupervisorAgent + TOUS
QualityAgent ─────RAPPORT──► SupervisorAgent
InventoryAgent ───ALERTE───► SupervisorAgent + ProductionAgent
EnergyAgent ──────RAPPORT──► SupervisorAgent
SupervisorAgent ──DÉCISION─► API → Dashboard
```

### Décisions du Superviseur

| Situation | Décision |
|-----------|---------|
| Tous les agents OK | FONCTIONNEMENT_NORMAL |
| 1 agent en ALERTE | ACTION_PLANIFIEE |
| 2+ agents en ALERTE | SURVEILLANCE_RENFORCEE |
| 1 agent CRITIQUE | INTERVENTION_IMMEDIATE |
| 2+ agents CRITIQUES | ARRET_D_URGENCE |

## Variables d'environnement

Aucune variable obligatoire. Le système fonctionne out-of-the-box avec les données générées.

| Variable | Description | Défaut |
|----------|-------------|--------|
| `USINE_API_URL` | URL de l'API (pour l'interface) | `http://127.0.0.1:8000` |

## Dépannage

| Problème | Cause | Solution |
|---------|-------|---------|
| `Modèles ML absents` | Pas encore entraînés | `python scripts/train_models.py` |
| `Aucune donnée` | CSV non générés | `python scripts/generate_data.py` |
| `API injoignable` | Serveur non démarré | `uvicorn api.main:app --reload` |
| `ModuleNotFoundError` | Dépendance manquante | `pip install -r requirements.txt` |
| `Python 3.10 détecté` | Version insuffisante | Installer Python 3.11 |

## Licence

Projet pédagogique — Système Multi-Agents de Pilotage d'Usine Autonome.

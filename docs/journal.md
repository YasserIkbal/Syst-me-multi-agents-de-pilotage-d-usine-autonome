# Journal de Bord — Système Multi-Agents Usine Autonome

**Module** : Développement et déploiement de systèmes intelligents
**Projet** : Pilotage d'une Usine Autonome par Agents IA

---

## Étape 1 : Cadrage et Architecture

### Décisions d'architecture

- Bus de messages thread-safe pour la communication inter-agents
- 6 agents spécialisés + 1 superviseur coordinateur
- API FastAPI comme couche de service
- Interface Streamlit pour la visualisation
- Données de simulation pour fonctionner sans infrastructure physique

### Technologies retenues

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| API | FastAPI | Async, validation Pydantic, docs auto |
| ML Anomalies | IsolationForest | Non supervisé, pas besoin de labels |
| ML Production | RandomForest | Robuste aux outliers |
| ML Qualité | GradientBoosting | Précis sur données déséquilibrées |
| ML Énergie | LinearRegression | Consommation ~ linéaire |
| Interface | Streamlit | Rapide à développer, adapté à la data |
| Communication | Bus interne | Pas de dépendance externe (Redis, RabbitMQ) |

---

## Étape 2 : Implémentation des Agents

### Schéma de communication

Chaque agent hérite de `BaseAgent` et implémente `analyser()`.
Le bus de messages (`MessageBus`) est thread-safe et conserve 500 messages.

### Patterns utilisés
- **Singleton** : Orchestrateur partagé entre l'API et l'interface
- **Observer** : Les agents publient, le superviseur écoute
- **Strategy** : Chaque agent a sa propre logique d'analyse

---

## Étape 3 : Modèles ML

### Modèles entraînés

| Modèle | Algorithme | Métrique | Valeur |
|--------|-----------|---------|--------|
| Détection anomalies | IsolationForest | Rappel | À mesurer |
| Prédiction pannes | RandomForest | F1 macro | À mesurer |
| Contrôle qualité | GradientBoosting | F1 macro | À mesurer |
| Prévision énergie | LinearRegression | MAE (kWh) | À mesurer |

*Complétez après `python scripts/train_models.py`*

---

## Étape 4 : API FastAPI

### Endpoints implémentés

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /health | Santé de l'API |
| GET | /usine/etat | État temps réel |
| GET | /usine/analyser | Analyse immédiate |
| GET | /agents | Liste des agents |
| GET | /agents/{nom} | Rapport d'un agent |
| GET | /agents/{nom}/analyser | Analyse d'un agent |
| GET | /messages | Historique messages |
| GET | /alertes | Historique alertes |
| GET | /decisions | Historique décisions |
| POST | /machines/commande | Commande manuelle |

---

## Étape 5 : Interface Streamlit

### Pages du dashboard

1. **Dashboard Général** : KPIs, statuts agents, alertes récentes
2. **Agents IA** : Rapport détaillé par agent, analyse à la demande
3. **Alertes & Décisions** : Historique complet
4. **Messages Inter-Agents** : Traçabilité du bus
5. **Commandes Manuelles** : Contrôle direct des machines
6. **Analyse Approfondie** : Graphiques Plotly sur données historiques

---

## Difficultés rencontrées

| Composant | Problème | Solution |
|-----------|---------|---------|
| | | |

---

## Métriques finales

*À compléter après les tests*

- Tests passés : ? / ?
- Couverture de code : ?%
- Agents opérationnels : 6/6
- Temps de réponse API /health : < ?ms

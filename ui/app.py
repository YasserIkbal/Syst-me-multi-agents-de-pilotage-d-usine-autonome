"""Dashboard Streamlit — Système Multi-Agents Usine Autonome.

Lancement :
    streamlit run ui/app.py
    (l'API doit tourner : uvicorn api.main:app --reload)
"""
from __future__ import annotations

import time
from datetime import datetime

import streamlit as st

# ── Configuration de la page ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Usine Autonome — Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Import client API ─────────────────────────────────────────────────────────
# Assurer que la racine du projet est dans sys.path (fonctionne quelle que soit
# la façon dont streamlit est lancé : depuis la racine ou depuis ui/)
import sys
from pathlib import Path as _Path
_RACINE = _Path(__file__).resolve().parent.parent
if str(_RACINE) not in sys.path:
    sys.path.insert(0, str(_RACINE))

try:
    import ui.client as client  # type: ignore
    try:
        h = client.health()
        API_DISPONIBLE = True
        API_MESSAGE = f"✅ API prête — {h.get('systeme', '')} v{h.get('version', '')}"
        AGENTS_ACTIFS = h.get("agents_actifs", 0)
    except Exception:
        API_DISPONIBLE = False
        API_MESSAGE = "❌ API injoignable — lancez : uvicorn api.main:app --reload"
        AGENTS_ACTIFS = 0
except ImportError as _e:
    API_DISPONIBLE = False
    API_MESSAGE = f"❌ Module client introuvable ({_e})"
    AGENTS_ACTIFS = 0

# ── CSS personnalisé ──────────────────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
    border-radius: 12px;
    padding: 16px 20px;
    color: white;
    margin: 4px 0;
}
.status-ok     { background-color: #1a7a3c; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
.status-alerte { background-color: #d4821a; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
.status-crit   { background-color: #b02020; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
.status-attente{ background-color: #555; color: white; padding: 4px 12px; border-radius: 20px; }
.agent-card    { border-left: 4px solid #2d6a9f; padding: 8px 12px; margin: 6px 0; background: #0e1117; border-radius: 4px; }
.alerte-card   { border-left: 4px solid #e03030; padding: 6px 10px; margin: 4px 0; background: #1a0a0a; border-radius: 4px; font-size: 0.85em; }
.decision-card { border-left: 4px solid #28a745; padding: 8px 12px; margin: 6px 0; background: #0a1a0a; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def badge_statut(statut: str) -> str:
    css = {"OK": "status-ok", "ALERTE": "status-alerte",
           "CRITIQUE": "status-crit"}.get(statut, "status-attente")
    return f'<span class="{css}">{statut}</span>'


def couleur_statut(statut: str) -> str:
    return {"OK": "🟢", "ALERTE": "🟡", "CRITIQUE": "🔴",
            "EN_ATTENTE": "⚪", "DONNEES_MANQUANTES": "⚫"}.get(statut, "⚪")


def score_couleur(score: float) -> str:
    if score >= 80:
        return "🟢"
    if score >= 50:
        return "🟡"
    return "🔴"


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/factory.png", width=80)
    st.title("🏭 Usine Autonome")
    st.caption("Système Multi-Agents de Pilotage")
    st.divider()

    st.markdown(API_MESSAGE)
    if AGENTS_ACTIFS:
        st.metric("Agents actifs", AGENTS_ACTIFS)
    st.divider()

    page = st.radio("Navigation", [
        "📊 Dashboard Général",
        "🤖 Agents IA",
        "🔔 Alertes & Décisions",
        "💬 Messages Inter-Agents",
        "🔧 Commandes Manuelles",
        "📈 Analyse Approfondie",
        "🔬 Prédiction Interactive",
    ])

    st.divider()
    auto_refresh = st.toggle("⟳ Actualisation auto (10s)", value=False)
    if st.button("🔄 Actualiser maintenant"):
        st.rerun()


# ── Gestion du rechargement automatique ───────────────────────────────────────
if auto_refresh:
    time.sleep(10)
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE : Dashboard Général
# ═══════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard Général":
    st.title("📊 Dashboard Général — Usine Autonome")
    st.caption(f"Dernière mise à jour : {datetime.now().strftime('%H:%M:%S')}")

    if not API_DISPONIBLE:
        st.error("⚠️ API non disponible. Lancez `uvicorn api.main:app --reload` dans un terminal.")
        st.code("uvicorn api.main:app --reload", language="bash")
        st.stop()

    try:
        etat = client.etat_usine()
    except Exception as e:
        st.error(f"Impossible de récupérer l'état de l'usine : {e}")
        st.stop()

    sante = etat.get("sante_usine", {})
    score = sante.get("score_global", 0)
    niveau = sante.get("niveau", "INCONNU")
    decision = etat.get("decision_courante", "EN_ATTENTE")
    message = etat.get("message_decision", "")
    statuts = etat.get("statuts", {})

    # ── Ligne KPI principale ──────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        emoji = score_couleur(score)
        st.metric(f"{emoji} Santé Usine", f"{score:.0f} / 100", delta=niveau)
    with col2:
        nb_ok = sum(1 for s in statuts.values() if s == "OK")
        st.metric("🟢 Agents OK", nb_ok, delta=f"/{len(statuts)} total")
    with col3:
        nb_alerte = sum(1 for s in statuts.values() if s == "ALERTE")
        nb_crit = sum(1 for s in statuts.values() if s == "CRITIQUE")
        st.metric("⚠️ Alertes / Critiques", f"{nb_alerte} / {nb_crit}")
    with col4:
        alertes = etat.get("alertes_recentes", [])
        st.metric("🔔 Alertes récentes", len(alertes))

    st.divider()

    # ── Décision superviseur ──────────────────────────────────────────────────
    dec_color = {"FONCTIONNEMENT_NORMAL": "success", "ACTION_PLANIFIEE": "info",
                 "SURVEILLANCE_RENFORCEE": "warning", "INTERVENTION_IMMEDIATE": "warning",
                 "ARRET_D_URGENCE": "error"}.get(decision, "info")

    getattr(st, dec_color)(f"**🧠 Décision Superviseur :** {decision} — {message}")

    st.divider()

    # ── Statut des 6 agents ───────────────────────────────────────────────────
    st.subheader("🤖 État des Agents")
    noms_affichage = {
        "ProductionAgent":  ("🏗️", "Production"),
        "MaintenanceAgent": ("🔧", "Maintenance"),
        "QualityAgent":     ("✅", "Qualité"),
        "InventoryAgent":   ("📦", "Inventaire"),
        "EnergyAgent":      ("⚡", "Énergie"),
        "SupervisorAgent":  ("🧠", "Superviseur"),
    }
    cols = st.columns(3)
    for i, (nom, statut) in enumerate(statuts.items()):
        icone, label = noms_affichage.get(nom, ("🤖", nom))
        with cols[i % 3]:
            emoji = couleur_statut(statut)
            st.markdown(f"""
            <div class="agent-card">
                <b>{icone} {label}</b><br>
                {emoji} <code>{statut}</code>
            </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Indicateurs spécifiques ───────────────────────────────────────────────
    st.subheader("📈 Indicateurs Temps Réel")
    try:
        analyse = client.analyser_usine()
        resultats = analyse.get("resultats", {})

        col_prod, col_maint, col_qual = st.columns(3)

        with col_prod:
            st.markdown("**🏗️ Production**")
            prod = resultats.get("ProductionAgent", {})
            taux = prod.get("taux_realisation_moyen", 0)
            retards = prod.get("en_retard", 0)
            total = prod.get("total_ordres", 1)
            st.progress(taux if taux <= 1 else 1.0, text=f"Réalisation : {taux:.1%}")
            st.caption(f"Retards : {retards}/{total} ordres")

        with col_maint:
            st.markdown("**🔧 Maintenance**")
            maint = resultats.get("MaintenanceAgent", {})
            score_max = maint.get("score_risque_max", 0)
            machine_risque = maint.get("machine_plus_risquee", "N/A")
            st.progress(score_max, text=f"Risque max : {score_max:.0%}")
            st.caption(f"Machine à risque : {machine_risque}")

        with col_qual:
            st.markdown("**✅ Qualité**")
            qual = resultats.get("QualityAgent", {})
            taux_conf = qual.get("taux_conformite_global", 0)
            defauts = qual.get("total_defauts", 0)
            st.progress(taux_conf if taux_conf <= 1 else 1.0, text=f"Conformité : {taux_conf:.1%}")
            st.caption(f"Défauts détectés : {defauts}")

        col_inv, col_ener, col_sup = st.columns(3)

        with col_inv:
            st.markdown("**📦 Stocks**")
            inv = resultats.get("InventoryAgent", {})
            ruptures = inv.get("ruptures", [])
            valeur = inv.get("valeur_totale_stock_eur", 0)
            nb_mat = inv.get("nb_matieres_surveillees", 0)
            if ruptures:
                st.error(f"Ruptures : {', '.join(ruptures)}")
            else:
                st.success(f"{nb_mat} matières — Aucune rupture")
            st.caption(f"Valeur stock : {valeur:,.0f} €")

        with col_ener:
            st.markdown("**⚡ Énergie**")
            ener = resultats.get("EnergyAgent", {})
            conso = ener.get("conso_totale_kwh_24h", 0)
            cout = ener.get("cout_total_eur_24h", 0)
            anomalies = ener.get("nb_anomalies_24h", 0)
            st.metric("Conso 24h", f"{conso:,.0f} kWh", delta=f"{cout:.2f} €")
            st.caption(f"Anomalies : {anomalies}")

        with col_sup:
            st.markdown("**🧠 Superviseur**")
            sup = resultats.get("SupervisorAgent", {})
            nb_alertes = sup.get("nb_alertes_actives", 0)
            conflits = sup.get("conflits_detectes", [])
            st.metric("Alertes actives", nb_alertes)
            st.caption(f"Conflits détectés : {len(conflits)}")

    except Exception as e:
        st.warning(f"Impossible de récupérer l'analyse en temps réel : {e}")

    # ── Alertes récentes ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("🔔 Dernières Alertes")
    if alertes:
        for alerte in reversed(alertes[-8:]):
            agent = alerte.get("agent", "?")
            ts = alerte.get("horodatage", "")[:19].replace("T", " ")
            contenu = alerte.get("contenu", {})
            desc = contenu.get("description", str(contenu)[:100])
            prio = alerte.get("priorite", 0)
            icone = "🔴" if prio >= 2 else "🟡"
            st.markdown(f"""<div class="alerte-card">
                {icone} <b>{ts}</b> — <code>{agent}</code> : {desc}
            </div>""", unsafe_allow_html=True)
    else:
        st.success("✅ Aucune alerte active")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE : Agents IA
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 Agents IA":
    st.title("🤖 Agents IA — Détails et Analyses")

    if not API_DISPONIBLE:
        st.error("API non disponible.")
        st.stop()

    AGENTS = {
        "ProductionAgent":  "🏗️ Production",
        "MaintenanceAgent": "🔧 Maintenance",
        "QualityAgent":     "✅ Qualité",
        "InventoryAgent":   "📦 Inventaire",
        "EnergyAgent":      "⚡ Énergie",
        "SupervisorAgent":  "🧠 Superviseur",
    }

    agent_choisi = st.selectbox("Sélectionner un agent", list(AGENTS.keys()),
                                 format_func=lambda x: AGENTS[x])

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("🔄 Analyser maintenant"):
            st.rerun()

    try:
        rapport = client.rapport_agent(agent_choisi)
        analyse = client.analyser_agent(agent_choisi)

        st.divider()

        # Infos générales
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Statut", rapport.get("derniere_analyse", {}).get("statut", "EN_ATTENTE"))
        with col2:
            st.metric("Cycles effectués", rapport.get("cycles", 0))
        with col3:
            actif = rapport.get("actif", False)
            st.metric("État", "🟢 Actif" if actif else "🔴 Arrêté")

        st.divider()

        # Résultat de l'analyse
        st.subheader(f"📊 Analyse — {AGENTS[agent_choisi]}")
        res = analyse.get("resultat", {})

        if agent_choisi == "MaintenanceAgent":
            st.markdown("**Scores de risque par machine :**")
            scores = res.get("scores_risque", {})
            if scores:
                import pandas as pd
                df_scores = pd.DataFrame(
                    [{"Machine": k, "Score Risque": v, "Niveau": "🔴 CRITIQUE" if v > 0.7 else ("🟡 ALERTE" if v > 0.4 else "🟢 OK")}
                     for k, v in sorted(scores.items())]
                )
                st.dataframe(df_scores, use_container_width=True, hide_index=True)

            interventions = res.get("interventions_recommandees", [])
            if interventions:
                st.markdown("**Interventions recommandées :**")
                for iv in interventions:
                    urgence = iv.get("urgence", "")
                    machine = iv.get("machine", "")
                    type_iv = iv.get("type", "")
                    icone = "🔴" if urgence == "IMMEDIATE" else "🟡"
                    st.markdown(f"- {icone} **{machine}** — {type_iv} ({urgence})")

        elif agent_choisi == "ProductionAgent":
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Taux réalisation moyen",
                          f"{res.get('taux_realisation_moyen', 0):.1%}")
                st.metric("Ordres en retard",
                          f"{res.get('en_retard', 0)} / {res.get('total_ordres', 0)}")
            with col_b:
                st.metric("Ordres critiques", res.get("critiques", 0))
                m = res.get("machine_la_plus_problematique", "N/A")
                st.metric("Machine problématique", m or "Aucune")

        elif agent_choisi == "QualityAgent":
            st.metric("Taux conformité global",
                      f"{res.get('taux_conformite_global', 0):.1%}")
            actions = res.get("actions_correctives", [])
            if actions:
                st.markdown("**Actions correctives :**")
                import pandas as pd
                df_ac = pd.DataFrame(actions)
                st.dataframe(df_ac, use_container_width=True, hide_index=True)

        elif agent_choisi == "InventoryAgent":
            stocks = res.get("stocks", {})
            if stocks:
                import pandas as pd
                rows = []
                for mat, info in stocks.items():
                    rows.append({
                        "Matière": mat,
                        "Stock (unités)": info.get("stock_actuel", 0),
                        "Jours restants": info.get("jours_restants", 0),
                        "Conso/jour": info.get("consommation_jour", 0),
                        "Statut": info.get("statut", "?")
                    })
                df_inv = pd.DataFrame(rows)
                st.dataframe(df_inv, use_container_width=True, hide_index=True)

        elif agent_choisi == "EnergyAgent":
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                st.metric("Conso totale 24h",
                          f"{res.get('conso_totale_kwh_24h', 0):,.1f} kWh")
            with col_e2:
                st.metric("Coût total 24h",
                          f"{res.get('cout_total_eur_24h', 0):,.2f} €")
            par_machine = res.get("consommation_par_machine", {})
            if par_machine:
                import pandas as pd
                rows = []
                for m, info in par_machine.items():
                    rows.append({
                        "Machine": m,
                        "Conso moy. (kWh)": info.get("conso_moyenne_kwh", 0),
                        "Conso max (kWh)": info.get("conso_max_kwh", 0),
                        "Coût total (€)": info.get("cout_total_eur", 0),
                        "Anomalies": info.get("nb_anomalies", 0)
                    })
                df_ener = pd.DataFrame(rows)
                st.dataframe(df_ener, use_container_width=True, hide_index=True)

        elif agent_choisi == "SupervisorAgent":
            st.markdown(f"**Décision :** `{res.get('decision', 'N/A')}`")
            st.info(res.get("message_decision", ""))
            conflits = res.get("conflits_detectes", [])
            if conflits:
                st.warning(f"**{len(conflits)} conflit(s) détecté(s) :**")
                for c in conflits:
                    st.markdown(f"- ⚡ **{c.get('type')}** — {c.get('description')}")
                    st.caption(f"  Résolution : {c.get('resolution')}")

        # Données brutes (expandable)
        with st.expander("🔍 Données brutes (JSON)"):
            st.json(res)

    except Exception as e:
        st.error(f"Erreur lors de la récupération du rapport : {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE : Alertes & Décisions
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔔 Alertes & Décisions":
    st.title("🔔 Alertes & Décisions du Superviseur")

    if not API_DISPONIBLE:
        st.error("API non disponible.")
        st.stop()

    tab_alertes, tab_decisions = st.tabs(["🔔 Alertes", "🧠 Décisions"])

    with tab_alertes:
        try:
            data = client.historique_alertes(100)
            alertes = data.get("alertes", [])
            st.metric("Total alertes", data.get("total", 0))
            if alertes:
                for al in reversed(alertes):
                    prio = al.get("priorite", 0)
                    agent = al.get("agent", "?")
                    ts = al.get("horodatage", "")[:19].replace("T", " ")
                    contenu = al.get("contenu", {})
                    desc = contenu.get("description", str(contenu)[:150])
                    icone = "🔴" if prio >= 2 else "🟡"
                    with st.container():
                        st.markdown(f"""<div class="alerte-card">
                            {icone} <b>{ts}</b> | <code>{agent}</code><br>{desc}
                        </div>""", unsafe_allow_html=True)
            else:
                st.success("✅ Aucune alerte dans l'historique")
        except Exception as e:
            st.error(f"Erreur : {e}")

    with tab_decisions:
        try:
            data = client.historique_decisions(50)
            decisions = data.get("decisions", [])
            st.metric("Total décisions", data.get("total", 0))
            if decisions:
                for dec in reversed(decisions):
                    ts = dec.get("horodatage", "")[:19].replace("T", " ")
                    decision = dec.get("decision", "?")
                    msg = dec.get("message", "")
                    sante = dec.get("sante_usine", {})
                    score = sante.get("score_global", 0)
                    icone = {"FONCTIONNEMENT_NORMAL": "🟢", "ACTION_PLANIFIEE": "🔵",
                             "SURVEILLANCE_RENFORCEE": "🟡", "INTERVENTION_IMMEDIATE": "🟠",
                             "ARRET_D_URGENCE": "🔴"}.get(decision, "⚪")
                    st.markdown(f"""<div class="decision-card">
                        {icone} <b>{ts}</b> — <code>{decision}</code><br>
                        {msg} <i>(santé : {score:.0f}/100)</i>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("Aucune décision enregistrée")
        except Exception as e:
            st.error(f"Erreur : {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE : Messages Inter-Agents
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "💬 Messages Inter-Agents":
    st.title("💬 Messages Inter-Agents — Traçabilité")

    if not API_DISPONIBLE:
        st.error("API non disponible.")
        st.stop()

    n_msgs = st.slider("Nombre de messages à afficher", 10, 200, 50)
    filtre_type = st.selectbox("Filtrer par type", ["TOUS", "ALERTE", "RAPPORT", "COMMANDE", "ERREUR"])

    try:
        data = client.historique_messages(n_msgs)
        messages = data.get("messages", [])

        if filtre_type != "TOUS":
            messages = [m for m in messages if m.get("type") == filtre_type]

        st.metric("Messages affichés", len(messages))
        st.divider()

        import pandas as pd
        if messages:
            rows = []
            for m in reversed(messages):
                rows.append({
                    "Horodatage": m.get("horodatage", "")[:19].replace("T", " "),
                    "Expéditeur": m.get("expediteur", ""),
                    "Destinataire": m.get("destinataire", ""),
                    "Type": m.get("type", ""),
                    "Priorité": m.get("priorite", 0),
                    "Résumé": str(m.get("contenu", {}))[:80] + "..."
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun message dans l'historique")
    except Exception as e:
        st.error(f"Erreur : {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE : Commandes Manuelles
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔧 Commandes Manuelles":
    st.title("🔧 Commandes Manuelles — Contrôle des Machines")
    st.warning("⚠️ Les commandes envoyées ici sont transmises à tous les agents via le bus de messages.")

    if not API_DISPONIBLE:
        st.error("API non disponible.")
        st.stop()

    with st.form("commande_form"):
        col1, col2 = st.columns(2)
        with col1:
            machine = st.selectbox("Machine", ["M001", "M002", "M003", "M004", "M005"])
            action = st.selectbox("Action", ["DEMARRER", "ARRETER", "MAINTENANCE", "REINITIALISER"])
        with col2:
            raison = st.text_area("Raison / Commentaire",
                                   placeholder="Ex: Maintenance préventive planifiée - remplacement filtre")
        submitted = st.form_submit_button("📤 Envoyer la commande", type="primary")

    if submitted:
        if not raison or len(raison) < 5:
            st.error("La raison doit contenir au moins 5 caractères.")
        else:
            try:
                result = client.commande_machine(machine, action, raison)
                if result.get("succes"):
                    st.success(f"✅ {result.get('message')} à {result.get('horodatage', '')[:19]}")
                else:
                    st.error("La commande a échoué")
            except Exception as e:
                st.error(f"Erreur : {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE : Analyse Approfondie
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Analyse Approfondie":
    st.title("📈 Analyse Approfondie — Graphiques & Tendances")

    if not API_DISPONIBLE:
        st.error("API non disponible.")
        st.stop()

    try:
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go
        from pathlib import Path

        DATA = Path(__file__).resolve().parents[1] / "data"

        tab1, tab2, tab3, tab4 = st.tabs(["🏗️ Production", "🔧 Machines", "⚡ Énergie", "📦 Stocks"])

        with tab1:
            st.subheader("Historique de Production")
            fichier = DATA / "production.csv"
            if fichier.exists():
                df_prod = pd.read_csv(fichier)
                df_prod["date"] = pd.to_datetime(df_prod["date"])
                df_prod = df_prod.tail(90)

                fig_prod = px.line(df_prod, x="date", y="taux_realisation",
                                   color="machine_id",
                                   title="Taux de réalisation par machine",
                                   labels={"taux_realisation": "Taux", "date": "Date"})
                fig_prod.add_hline(y=0.95, line_dash="dash", line_color="orange",
                                   annotation_text="Seuil 95%")
                st.plotly_chart(fig_prod, use_container_width=True)

                # Répartition des statuts
                statuts_count = df_prod["statut"].value_counts().reset_index()
                statuts_count.columns = ["Statut", "Nombre"]
                fig_statuts = px.pie(statuts_count, values="Nombre", names="Statut",
                                     title="Répartition des statuts de production",
                                     color_discrete_map={"OK": "#28a745", "RETARD": "#ffc107", "CRITIQUE": "#dc3545"})
                st.plotly_chart(fig_statuts, use_container_width=True)
            else:
                st.info("Données de production non disponibles. Lancez `python scripts/generate_data.py`")

        with tab2:
            st.subheader("Données Capteurs Machines")
            fichier_m = DATA / "machines.csv"
            if fichier_m.exists():
                df_mach = pd.read_csv(fichier_m)
                df_mach["timestamp"] = pd.to_datetime(df_mach["timestamp"])
                df_mach = df_mach.tail(500)

                machine_sel = st.selectbox("Machine", ["M001", "M002", "M003", "M004", "M005"], key="mach_sel")
                df_sel = df_mach[df_mach["machine_id"] == machine_sel]

                fig_temp = go.Figure()
                fig_temp.add_trace(go.Scatter(x=df_sel["timestamp"], y=df_sel["temperature"],
                                              name="Température (°C)", line=dict(color="#e74c3c")))
                fig_temp.add_hline(y=85, line_dash="dash", line_color="orange", annotation_text="Seuil avertissement")
                fig_temp.add_hline(y=92, line_dash="dash", line_color="red", annotation_text="Seuil critique")
                fig_temp.update_layout(title=f"Température — {machine_sel}", xaxis_title="Temps", yaxis_title="°C")
                st.plotly_chart(fig_temp, use_container_width=True)

                col_v, col_p = st.columns(2)
                with col_v:
                    fig_vib = px.line(df_sel, x="timestamp", y="vibration",
                                      title=f"Vibration — {machine_sel}", color_discrete_sequence=["#3498db"])
                    st.plotly_chart(fig_vib, use_container_width=True)
                with col_p:
                    fig_pre = px.line(df_sel, x="timestamp", y="pression",
                                      title=f"Pression — {machine_sel}", color_discrete_sequence=["#2ecc71"])
                    st.plotly_chart(fig_pre, use_container_width=True)
            else:
                st.info("Données machines non disponibles.")

        with tab3:
            st.subheader("Consommation Énergétique")
            fichier_e = DATA / "energy.csv"
            if fichier_e.exists():
                df_ener = pd.read_csv(fichier_e)
                df_ener["timestamp"] = pd.to_datetime(df_ener["timestamp"])
                df_ener = df_ener.tail(500)

                fig_ener = px.line(df_ener, x="timestamp", y="conso_kwh",
                                   color="machine_id",
                                   title="Consommation énergétique par machine (kWh)")
                fig_ener.add_hline(y=20, line_dash="dash", line_color="orange",
                                   annotation_text="Seuil normal")
                fig_ener.add_hline(y=28, line_dash="dash", line_color="red",
                                   annotation_text="Seuil critique")
                st.plotly_chart(fig_ener, use_container_width=True)

                # Coût total par machine
                cout_par_machine = df_ener.groupby("machine_id")["cout_eur"].sum().reset_index()
                cout_par_machine.columns = ["Machine", "Coût total (€)"]
                fig_cout = px.bar(cout_par_machine, x="Machine", y="Coût total (€)",
                                  title="Coût énergétique total par machine",
                                  color="Coût total (€)", color_continuous_scale="Reds")
                st.plotly_chart(fig_cout, use_container_width=True)
            else:
                st.info("Données énergétiques non disponibles.")

        with tab4:
            st.subheader("Évolution des Stocks")
            fichier_inv = DATA / "inventory.csv"
            if fichier_inv.exists():
                df_inv = pd.read_csv(fichier_inv)
                df_inv["date"] = pd.to_datetime(df_inv["date"])

                fig_inv = px.line(df_inv, x="date", y="stock_actuel",
                                  color="matiere",
                                  title="Évolution du stock par matière première")
                fig_inv.add_hline(y=200, line_dash="dash", line_color="red",
                                  annotation_text="Stock minimum")
                st.plotly_chart(fig_inv, use_container_width=True)

                # Jours restants actuels
                derniers_stocks = df_inv.groupby("matiere").last().reset_index()
                fig_jours = px.bar(derniers_stocks, x="matiere", y="jours_restants",
                                   title="Jours de stock restants par matière",
                                   color="jours_restants",
                                   color_continuous_scale="RdYlGn")
                fig_jours.add_hline(y=7, line_dash="dash", annotation_text="Seuil alerte (7j)")
                st.plotly_chart(fig_jours, use_container_width=True)
            else:
                st.info("Données de stock non disponibles.")

    except ImportError:
        st.error("Plotly requis pour les graphiques. Installez avec : pip install plotly")
    except Exception as e:
        st.error(f"Erreur lors du chargement des graphiques : {e}")




# ═══════════════════════════════════════════════════════════════════════════════
# PAGE : Prédiction Interactive — équivalent du predict de sentiment-app
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔬 Prédiction Interactive":
    st.title("🔬 Prédiction Interactive — Testez les Modèles ML")
    st.markdown(
        "Comme dans sentiment-app où tu tapais un texte et le modèle répondait POSITIF/NÉGATIF, "
        "ici tu entres des valeurs et le modèle te répond **OK / ALERTE / CRITIQUE**."
    )

    from pathlib import Path as _P2
    import sys as _sys2
    _R2 = _P2(__file__).resolve().parents[1]
    if str(_R2) not in _sys2.path:
        _sys2.path.insert(0, str(_R2))

    MODELS_DIR = _R2 / "models"
    if not (MODELS_DIR / "metrics.json").exists():
        st.error("Modèles ML non entraînés. Lancez : `python scripts/train_models.py`")
        st.stop()

    import json as _json2
    metrics = _json2.loads((MODELS_DIR / "metrics.json").read_text(encoding="utf-8"))

    # ── session_state — valeurs par défaut des sliders ────────────────────────
    _sd = {
        "m_temp": 75.0, "m_vib": 2.5, "m_pres": 6.0, "m_rpm": 1500,
        "p_obj": 100,   "p_reel": 95,
        "q_lot": 100,   "q_def": 2,
        "e_heure": 10,  "e_puiss": 60.0,
    }
    for _k, _v in _sd.items():
        if _k not in st.session_state:
            st.session_state[_k] = _v

    st.divider()
    tab_maint, tab_prod, tab_qual, tab_ener = st.tabs([
        "🔧 Anomalie Machine",
        "🏗️ État Production",
        "✅ Qualité Lot",
        "⚡ Consommation Énergie",
    ])

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Anomalie Machine (IsolationForest)
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_maint:
        st.subheader("🔧 Détection d'Anomalie — IsolationForest")
        m_info = metrics.get("anomaly_detector", {})
        st.info(f"Modèle : **{m_info.get('modele','?')}** · "
                f"Rappel anomalies : **{m_info.get('rappel_anomalies', 0):.0%}**")

        # ── Boutons exemples — modifient session_state ────────────────────────
        st.markdown("**Charger un exemple :**")
        c1, c2, c3 = st.columns(3)
        if c1.button("✅ Machine normale",   use_container_width=True, key="ex_m1"):
            st.session_state["m_temp"] = 75.0
            st.session_state["m_vib"]  = 2.5
            st.session_state["m_pres"] = 6.0
            st.session_state["m_rpm"]  = 1500
            st.rerun()
        if c2.button("⚠️ Surchauffe légère", use_container_width=True, key="ex_m2"):
            st.session_state["m_temp"] = 88.0
            st.session_state["m_vib"]  = 3.2
            st.session_state["m_pres"] = 7.2
            st.session_state["m_rpm"]  = 1450
            st.rerun()
        if c3.button("🔴 Panne imminente",   use_container_width=True, key="ex_m3"):
            st.session_state["m_temp"] = 98.0
            st.session_state["m_vib"]  = 4.8
            st.session_state["m_pres"] = 8.5
            st.session_state["m_rpm"]  = 1350
            st.rerun()

        # ── Sliders liés à session_state ─────────────────────────────────────
        st.markdown("**Ou ajustez vous-même :**")
        col1, col2 = st.columns(2)
        with col1:
            temp     = st.slider("🌡️ Température (°C)", 40.0, 130.0,
                                  value=float(st.session_state["m_temp"]),
                                  step=0.5, key="m_temp")
            vibration = st.slider("📳 Vibration",       0.5,  6.0,
                                   value=float(st.session_state["m_vib"]),
                                   step=0.1, key="m_vib")
        with col2:
            pression = st.slider("💨 Pression (bar)",   3.0,  10.0,
                                  value=float(st.session_state["m_pres"]),
                                  step=0.1, key="m_pres")
            rpm      = st.slider("⚙️ RPM",              800,  2200,
                                  value=int(st.session_state["m_rpm"]),
                                  step=10,  key="m_rpm")

        # ── Bouton prédiction ─────────────────────────────────────────────────
        if st.button("🔍 Analyser cette machine", type="primary", key="btn_maint"):
            try:
                import joblib, numpy as np
                modele = joblib.load(MODELS_DIR / "anomaly_detector.joblib")
                X = np.array([[temp, vibration, pression, rpm]])
                pred  = modele.predict(X)[0]
                score = modele.decision_function(X)[0]
                st.divider()
                if pred == -1:
                    st.error("## 🔴 ANOMALIE DÉTECTÉE")
                    st.metric("Score d'anomalie", f"{score:.4f}", delta="anormal (négatif)")
                    problemes = []
                    if temp > 92:       problemes.append(f"Température critique : {temp}°C > 92°C")
                    elif temp > 85:     problemes.append(f"Température élevée : {temp}°C > 85°C")
                    if vibration > 4.0: problemes.append(f"Vibration critique : {vibration} > 4.0")
                    elif vibration > 3.0: problemes.append(f"Vibration élevée : {vibration} > 3.0")
                    if pression > 8.0:  problemes.append(f"Pression critique : {pression} bar > 8.0")
                    elif pression > 7.0: problemes.append(f"Pression élevée : {pression} bar > 7.0")
                    if problemes:
                        st.warning("**Seuils dépassés :**\n" + "\n".join(f"- {p}" for p in problemes))
                    st.error("**Action :** Arrêt machine · Inspection immédiate")
                else:
                    st.success("## 🟢 FONCTIONNEMENT NORMAL")
                    st.metric("Score d'anomalie", f"{score:.4f}", delta="normal (positif)")
                    st.success("**Tous les capteurs sont dans les plages normales.**")
            except Exception as e:
                st.error(f"Erreur : {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2 — État Production (RandomForest)
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_prod:
        st.subheader("🏗️ Prédiction État Production — RandomForest")
        p_info = metrics.get("failure_predictor", {})
        st.info(f"Modèle : **{p_info.get('modele','?')}** · "
                f"F1 macro : **{p_info.get('f1_macro',0):.1%}**")

        st.markdown("**Charger un exemple :**")
        c1, c2, c3 = st.columns(3)
        if c1.button("✅ Production OK",     use_container_width=True, key="ex_p1"):
            st.session_state["p_obj"]  = 100
            st.session_state["p_reel"] = 98
            st.rerun()
        if c2.button("⚠️ Retard modéré",    use_container_width=True, key="ex_p2"):
            st.session_state["p_obj"]  = 100
            st.session_state["p_reel"] = 83
            st.rerun()
        if c3.button("🔴 Retard critique",   use_container_width=True, key="ex_p3"):
            st.session_state["p_obj"]  = 100
            st.session_state["p_reel"] = 50
            st.rerun()

        st.markdown("**Ou entrez vos valeurs :**")
        col1, col2 = st.columns(2)
        with col1:
            objectif     = st.number_input("🎯 Objectif (unités)",          50, 300,
                                            value=int(st.session_state["p_obj"]))
            produit_reel = st.number_input("📦 Quantité produite (unités)",  0, 300,
                                            value=int(st.session_state["p_reel"]))
            # Synchroniser session_state avec les valeurs saisies
            st.session_state["p_obj"]  = objectif
            st.session_state["p_reel"] = produit_reel
        with col2:
            taux_calcule   = produit_reel / objectif if objectif > 0 else 0
            retard_calcule = max(0, objectif - produit_reel)
            st.metric("Taux de réalisation", f"{taux_calcule:.1%}")
            st.metric("Retard (unités)",     retard_calcule)

        if st.button("🔍 Prédire l'état de production", type="primary", key="btn_prod"):
            try:
                import joblib, numpy as np
                modele = joblib.load(MODELS_DIR / "failure_predictor.joblib")
                X = np.array([[objectif, produit_reel, taux_calcule, retard_calcule]])
                pred  = modele.predict(X)[0]
                proba = modele.predict_proba(X)[0]
                labels = ["OK", "RETARD", "CRITIQUE"]
                label  = labels[int(pred)]
                conf   = float(proba[int(pred)])
                st.divider()
                if label == "OK":
                    st.success(f"## ✅ PRODUCTION {label}")
                elif label == "RETARD":
                    st.warning(f"## ⚠️ PRODUCTION EN {label}")
                else:
                    st.error(f"## 🔴 PRODUCTION {label}")
                st.metric("Confiance du modèle", f"{conf:.1%}")
                st.markdown("**Probabilités par classe :**")
                for i, lbl in enumerate(labels):
                    st.progress(float(proba[i]), text=f"{lbl} : {float(proba[i]):.1%}")
            except Exception as e:
                st.error(f"Erreur : {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Qualité Lot (GradientBoosting)
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_qual:
        st.subheader("✅ Classification Qualité Lot — GradientBoosting")
        q_info = metrics.get("quality_classifier", {})
        st.info(f"Modèle : **{q_info.get('modele','?')}** · "
                f"F1 macro : **{q_info.get('f1_macro',0):.1%}**")

        st.markdown("**Charger un exemple :**")
        c1, c2, c3 = st.columns(3)
        if c1.button("✅ Lot conforme",      use_container_width=True, key="ex_q1"):
            st.session_state["q_lot"] = 100
            st.session_state["q_def"] = 1
            st.rerun()
        if c2.button("⚠️ Qualité dégradée", use_container_width=True, key="ex_q2"):
            st.session_state["q_lot"] = 100
            st.session_state["q_def"] = 8
            st.rerun()
        if c3.button("🔴 Lot à rebuter",    use_container_width=True, key="ex_q3"):
            st.session_state["q_lot"] = 100
            st.session_state["q_def"] = 22
            st.rerun()

        st.markdown("**Ou entrez vos valeurs :**")
        col1, col2 = st.columns(2)
        with col1:
            lot_taille = st.number_input("📦 Taille du lot",      20, 500,
                                          value=int(st.session_state["q_lot"]))
            defauts    = st.number_input("❌ Nombre de défauts",   0, 200,
                                          value=int(st.session_state["q_def"]))
            # Synchroniser session_state avec les valeurs saisies
            st.session_state["q_lot"] = lot_taille
            st.session_state["q_def"] = defauts
        with col2:
            conformes  = max(0, lot_taille - defauts)
            taux_conf  = conformes / lot_taille if lot_taille > 0 else 0
            st.metric("Pièces conformes",    conformes)
            st.metric("Taux de conformité",  f"{taux_conf:.1%}")

        if st.button("🔍 Classifier ce lot", type="primary", key="btn_qual"):
            try:
                import joblib, numpy as np
                modele = joblib.load(MODELS_DIR / "quality_classifier.joblib")
                X = np.array([[lot_taille, conformes, defauts, taux_conf]])
                pred  = modele.predict(X)[0]
                proba = modele.predict_proba(X)[0]
                labels = ["OK", "ALERTE", "CRITIQUE"]
                label  = labels[int(pred)]
                conf   = float(proba[int(pred)])
                st.divider()
                if label == "OK":
                    st.success(f"## ✅ LOT {label} — Confiance {conf:.1%}")
                    st.success("**Action :** Lot accepté · Poursuite normale")
                elif label == "ALERTE":
                    st.warning(f"## ⚠️ LOT EN {label} — Confiance {conf:.1%}")
                    st.warning("**Action :** Réglage des paramètres · Surveillance renforcée")
                else:
                    st.error(f"## 🔴 LOT {label} — Confiance {conf:.1%}")
                    st.error("**Action :** Arrêt machine · Inspection · Rebut du lot")
                st.markdown("**Probabilités :**")
                for i, lbl in enumerate(labels):
                    st.progress(float(proba[i]), text=f"{lbl} : {float(proba[i]):.1%}")
            except Exception as e:
                st.error(f"Erreur : {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 4 — Énergie (LinearRegression)
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_ener:
        st.subheader("⚡ Prévision Consommation — LinearRegression")
        e_info = metrics.get("energy_forecaster", {})
        st.info(f"Modèle : **{e_info.get('modele','?')}** · "
                f"MAE : **{e_info.get('mae_kwh',0):.3f} kWh**")

        st.markdown("**Charger un exemple :**")
        c1, c2, c3 = st.columns(3)
        if c1.button("✅ Conso normale",       use_container_width=True, key="ex_e1"):
            st.session_state["e_heure"] = 10
            st.session_state["e_puiss"] = 55.0
            st.rerun()
        if c2.button("⚠️ Conso élevée",        use_container_width=True, key="ex_e2"):
            st.session_state["e_heure"] = 14
            st.session_state["e_puiss"] = 95.0
            st.rerun()
        if c3.button("🔴 Surconsommation",     use_container_width=True, key="ex_e3"):
            st.session_state["e_heure"] = 14
            st.session_state["e_puiss"] = 130.0
            st.rerun()

        st.markdown("**Ou entrez vos valeurs :**")
        col1, col2 = st.columns(2)
        with col1:
            heure        = st.slider("🕐 Heure (0-23)",      0,    23,
                                      value=int(st.session_state["e_heure"]),
                                      key="e_heure")
            jour_noms    = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
            jour_sel     = st.selectbox("📅 Jour de la semaine", jour_noms, key="e_jour")
            jour_idx     = jour_noms.index(jour_sel)
        with col2:
            machine_e    = st.selectbox("🏭 Machine", ["M001","M002","M003","M004","M005"], key="e_mach")
            machine_map  = {"M001":0,"M002":1,"M003":2,"M004":3,"M005":4}
            puissance    = st.slider("⚡ Puissance (kW)",   20.0, 150.0,
                                      value=float(st.session_state["e_puiss"]),
                                      step=1.0, key="e_puiss")

        if st.button("🔍 Prévoir la consommation", type="primary", key="btn_ener"):
            try:
                import joblib, numpy as np
                import plotly.graph_objects as go
                modele = joblib.load(MODELS_DIR / "energy_forecaster.joblib")
                X = np.array([[heure, jour_idx, machine_map[machine_e], puissance]])
                pred_kwh = float(modele.predict(X)[0])
                SEUIL_N = 20.0
                SEUIL_C = 28.0
                st.divider()
                col_r1, col_r2, col_r3 = st.columns(3)
                col_r1.metric("⚡ Consommation prévue", f"{pred_kwh:.2f} kWh")
                col_r2.metric("💶 Coût estimé",         f"{pred_kwh * 0.12:.3f} €")
                col_r3.metric("🏭 Machine",             machine_e)
                if pred_kwh > SEUIL_C:
                    st.error(f"## 🔴 SURCONSOMMATION CRITIQUE — {pred_kwh:.1f} kWh")
                    st.error("**Action :** Réduire la charge · Inspection électrique")
                elif pred_kwh > SEUIL_N:
                    st.warning(f"## ⚠️ CONSOMMATION ÉLEVÉE — {pred_kwh:.1f} kWh")
                    st.warning("**Action :** Surveiller · Planifier inspection")
                else:
                    st.success(f"## 🟢 CONSOMMATION NORMALE — {pred_kwh:.1f} kWh")
                # Jauge
                fig_g = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=pred_kwh,
                    title={"text": f"Consommation prévue — {machine_e}"},
                    gauge={
                        "axis": {"range": [0, 40]},
                        "bar":  {"color": "#2c3e50"},
                        "steps": [
                            {"range": [0, SEUIL_N],    "color": "#2ecc71"},
                            {"range": [SEUIL_N, SEUIL_C], "color": "#f39c12"},
                            {"range": [SEUIL_C, 40],   "color": "#e74c3c"},
                        ],
                        "threshold": {"line": {"color":"red","width":4},
                                      "thickness":0.75,"value":SEUIL_C}
                    }
                ))
                st.plotly_chart(fig_g, use_container_width=True)
            except Exception as e:
                st.error(f"Erreur : {e}")

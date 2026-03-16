import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────────
# COLONNES EXACTES DU CSV
# ─────────────────────────────────────────────
COL_NUM       = "Numéro"
COL_DT        = "Date et Heure"
COL_PRESSION  = "Pression Relative (hPa)"
COL_TEMP_IN   = "Température intérieure (°C)"
COL_HUM_IN    = "Humidité intérieure (%)"
COL_TEMP_OUT  = "Température extérieure (°C)"
COL_HUM_OUT   = "Humidité extérieure (%)"
COL_ROSEE     = "Point de Rosée (°C)"
COL_RESSENTI  = "Température ressentie (°C)"
COL_VENT_SPD  = "Vitesse du vent (km/h)"
COL_VENT_DIR  = "Direction du vent"
COL_RAFALE    = "Rafale (km/h)"
COL_PLUIE_M   = "Pluviométrie sur le dernier mois (mm)"
COL_PLUIE_TOT = "Pluviométrie totale (mm)"

# ─────────────────────────────────────────────
# CONFIG PAGE
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Station Météo",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# STYLE
# ─────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
    .stApp { background: #0d1117; color: #e6edf3; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    [data-testid="stSidebar"] { background: #161b22; border-right: 1px solid #30363d; }
    [data-testid="stMetric"] {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 12px; padding: 1rem 1.25rem;
    }
    [data-testid="stMetric"] label {
        color: #8b949e !important; font-family: 'DM Mono', monospace !important;
        font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.08em;
    }
    [data-testid="stMetricValue"] {
        color: #e6edf3 !important; font-family: 'Syne', sans-serif !important;
        font-weight: 700 !important; font-size: 1.6rem !important;
    }
    .section-title {
        font-family: 'Syne', sans-serif; font-weight: 800; font-size: 1.05rem;
        color: #58a6ff; text-transform: uppercase; letter-spacing: 0.1em;
        margin: 1rem 0 0.4rem 0; padding-bottom: 0.4rem; border-bottom: 1px solid #21262d;
    }
    .stTabs [data-baseweb="tab"] { font-family: 'DM Mono', monospace; font-size: 0.85rem; color: #8b949e; }
    .stTabs [aria-selected="true"] { color: #58a6ff !important; border-bottom-color: #58a6ff !important; }
    h1 { font-family: 'Syne', sans-serif !important; font-weight: 800 !important; color: #e6edf3 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
C = {
    "blue":   "#58a6ff",
    "orange": "#f0883e",
    "green":  "#3fb950",
    "red":    "#f85149",
    "purple": "#bc8cff",
    "cyan":   "#39d353",
    "yellow": "#d29922",
    "gray":   "#8b949e",
}

BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(22,27,34,0.6)",
    font=dict(family="DM Mono, monospace", color="#8b949e", size=11),
    yaxis=dict(gridcolor="#21262d", linecolor="#30363d", zeroline=False),
    legend=dict(bgcolor="rgba(22,27,34,0.8)", bordercolor="#30363d", borderwidth=1),
    margin=dict(l=10, r=10, t=40, b=10),
    hovermode="x unified",
)

# Axe X adaptatif selon la durée de la période affichée
def xaxis_time(dff) -> dict:
    n_days = max((dff[COL_DT].max() - dff[COL_DT].min()).days, 1)
    if n_days <= 3:
        return dict(gridcolor="#21262d", linecolor="#30363d", zeroline=False,
                    dtick=2 * 3600 * 1000, tickformat="%d/%m\n%H:%M", tickangle=0)
    elif n_days <= 14:
        return dict(gridcolor="#21262d", linecolor="#30363d", zeroline=False,
                    dtick="D1", tickformat="%d/%m", tickangle=-45)
    elif n_days <= 60:
        return dict(gridcolor="#21262d", linecolor="#30363d", zeroline=False,
                    dtick=3 * 24 * 3600 * 1000, tickformat="%d/%m", tickangle=-45)
    elif n_days <= 365:
        return dict(gridcolor="#21262d", linecolor="#30363d", zeroline=False,
                    dtick=7 * 24 * 3600 * 1000, tickformat="%d/%m/%y", tickangle=-45)
    else:
        return dict(gridcolor="#21262d", linecolor="#30363d", zeroline=False,
                    dtick="M1", tickformat="%b %Y", tickangle=-45)

# Marqueurs pour les séries temporelles (points seuls)
def dot(color: str, size: int = 5) -> dict:
    return dict(mode="markers", marker=dict(color=color, size=size, opacity=0.85, line=dict(width=0)))

WIND_DIRS = {
    "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5,
    "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
    "S": 180, "SSO": 202.5, "SO": 225, "OSO": 247.5,
    "O": 270, "ONO": 292.5, "NO": 315, "NNO": 337.5,
}

# ─────────────────────────────────────────────
# CHARGEMENT
# ─────────────────────────────────────────────
def _normalize(s: str) -> str:
    """Normalise une chaîne : minuscules, sans accents, sans espaces superflus."""
    import unicodedata
    s = s.strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s

# Table de correspondance : clé normalisée → nom de constante attendu
_CANONICAL = {
    _normalize(COL_NUM):       COL_NUM,
    _normalize(COL_DT):        COL_DT,
    _normalize(COL_PRESSION):  COL_PRESSION,
    _normalize(COL_TEMP_IN):   COL_TEMP_IN,
    _normalize(COL_HUM_IN):    COL_HUM_IN,
    _normalize(COL_TEMP_OUT):  COL_TEMP_OUT,
    _normalize(COL_HUM_OUT):   COL_HUM_OUT,
    _normalize(COL_ROSEE):     COL_ROSEE,
    _normalize(COL_RESSENTI):  COL_RESSENTI,
    _normalize(COL_VENT_SPD):  COL_VENT_SPD,
    _normalize(COL_VENT_DIR):  COL_VENT_DIR,
    _normalize(COL_RAFALE):    COL_RAFALE,
    _normalize(COL_PLUIE_M):   COL_PLUIE_M,
    _normalize(COL_PLUIE_TOT): COL_PLUIE_TOT,
}

@st.cache_data
def load_data(file) -> pd.DataFrame:
    # Essai UTF-8, fallback Latin-1
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(file, sep=";", quotechar='"', encoding=enc, decimal=".")
            break
        except UnicodeDecodeError:
            file.seek(0)
            continue

    # Renommage robuste : compare les noms normalisés
    rename_map = {}
    for col in df.columns:
        key = _normalize(col)
        if key in _CANONICAL:
            rename_map[col] = _CANONICAL[key]
    df = df.rename(columns=rename_map)
    df.columns = df.columns.str.strip()

    # Parse date au format dd.mm.yyyy HH:MM
    if COL_DT in df.columns:
        df[COL_DT] = pd.to_datetime(df[COL_DT], format="%d.%m.%Y %H:%M", errors="coerce")
        df = df.sort_values(COL_DT).reset_index(drop=True)

    # Force numériques
    for col in [COL_PRESSION, COL_TEMP_IN, COL_HUM_IN, COL_TEMP_OUT, COL_HUM_OUT,
                COL_ROSEE, COL_RESSENTI, COL_VENT_SPD, COL_RAFALE, COL_PLUIE_M, COL_PLUIE_TOT]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌤️ Station Météo")
    st.markdown("---")
    uploaded = st.file_uploader("Charger le fichier CSV", type=["csv", "txt"])
    st.markdown("---")
    st.markdown("**Filtres temporels**")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
st.title("Dashboard Météo")

if uploaded is None:
    st.info("👈 Chargez votre fichier CSV depuis la barre latérale pour commencer.")
    st.markdown("""
    **Format attendu (séparateur `;`, guillemets `"`) :**
    ```
    "Numéro";"Date et Heure";"Pression Relative (hPa)";"Température intérieure (°C)";...
    "0";"10.07.2020 20:00";"1013.4";"31.3";...
    ```
    """)
    st.stop()

df = load_data(uploaded)

missing = [c for c in [COL_DT, COL_TEMP_OUT, COL_TEMP_IN, COL_PRESSION] if c not in df.columns]
if missing:
    st.error(f"Colonnes introuvables après normalisation : `{missing}`")
    st.markdown("**Colonnes lues dans le fichier (repr exact) :**")
    for i, col in enumerate(df.columns):
        st.code(f"{i:2d}  {repr(col)}")
    st.stop()

# ── Filtre de dates ──────────────────────────
date_min = df[COL_DT].min().date()
date_max = df[COL_DT].max().date()

with st.sidebar:
    date_range = st.date_input("Période", value=(date_min, date_max),
                                min_value=date_min, max_value=date_max)

if len(date_range) == 2:
    mask = (df[COL_DT].dt.date >= date_range[0]) & (df[COL_DT].dt.date <= date_range[1])
    dff = df[mask].copy()
else:
    dff = df.copy()

if dff.empty:
    st.warning("Aucune donnée sur la période sélectionnée.")
    st.stop()

# ── KPIs ─────────────────────────────────────
st.markdown('<div class="section-title">Résumé de la période</div>', unsafe_allow_html=True)
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.metric("🌡 Temp. ext.", f"{dff[COL_TEMP_OUT].iloc[-1]:.1f} °C")
with k2:
    st.metric("📊 Pression", f"{dff[COL_PRESSION].iloc[-1]:.1f} hPa")
with k3:
    st.metric("💧 Humidité ext.", f"{dff[COL_HUM_OUT].iloc[-1]:.0f} %")
with k4:
    st.metric("💨 Vent moyen", f"{dff[COL_VENT_SPD].mean():.1f} km/h")
with k5:
    st.metric("🌧 Pluie (mois)", f"{dff[COL_PLUIE_M].iloc[-1]:.1f} mm")

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ONGLETS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Courbes temporelles",
    "🌡 Intérieur / Extérieur",
    "🌹 Rose des vents",
    "🌧 Pluviométrie",
])

# ══════════════════════════════════════════════
# TAB 1 — Courbes temporelles
# ══════════════════════════════════════════════
with tab1:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="section-title">Températures & Pression</div>', unsafe_allow_html=True)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(
            x=dff[COL_DT], y=dff[COL_TEMP_OUT],
            name="Temp. extérieure", **dot(C["orange"], 5),
        ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=dff[COL_DT], y=dff[COL_TEMP_IN],
            name="Temp. intérieure", **dot(C["red"], 4),
        ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=dff[COL_DT], y=dff[COL_PRESSION],
            name="Pression", **dot(C["blue"], 4),
        ), secondary_y=True)
        fig.update_layout(**BASE_LAYOUT, title="Températures & Pression atmosphérique")
        fig.update_xaxes(**xaxis_time(dff))
        fig.update_yaxes(title_text="°C",  secondary_y=False, gridcolor="#21262d")
        fig.update_yaxes(title_text="hPa", secondary_y=True,  gridcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown('<div class="section-title">Humidité & Point de rosée</div>', unsafe_allow_html=True)
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(go.Scatter(
            x=dff[COL_DT], y=dff[COL_HUM_OUT],
            name="Humidité ext.", **dot(C["cyan"], 5),
        ), secondary_y=False)
        fig2.add_trace(go.Scatter(
            x=dff[COL_DT], y=dff[COL_HUM_IN],
            name="Humidité int.", **dot(C["purple"], 4),
        ), secondary_y=False)
        fig2.add_trace(go.Scatter(
            x=dff[COL_DT], y=dff[COL_ROSEE],
            name="Point de rosée", **dot(C["yellow"], 4),
        ), secondary_y=True)
        fig2.update_layout(**BASE_LAYOUT, title="Humidité & Point de rosée")
        fig2.update_xaxes(**xaxis_time(dff))
        fig2.update_yaxes(title_text="%",  secondary_y=False, gridcolor="#21262d")
        fig2.update_yaxes(title_text="°C", secondary_y=True,  gridcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Vent & Rafales</div>', unsafe_allow_html=True)
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=dff[COL_DT], y=dff[COL_VENT_SPD],
        name="Vitesse", **dot(C["blue"], 5),
    ))
    fig3.add_trace(go.Scatter(
        x=dff[COL_DT], y=dff[COL_RAFALE],
        name="Rafales", **dot(C["red"], 4),
    ))
    fig3.update_layout(**BASE_LAYOUT, title="Vitesse du vent & Rafales (km/h)")
    fig3.update_xaxes(**xaxis_time(dff))
    st.plotly_chart(fig3, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 2 — Intérieur / Extérieur
# ══════════════════════════════════════════════
with tab2:
    col_c, col_d = st.columns([3, 2])

    with col_c:
        st.markdown('<div class="section-title">Températures comparées</div>', unsafe_allow_html=True)
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(
            x=dff[COL_DT], y=dff[COL_TEMP_IN],
            name="Intérieure", **dot(C["orange"], 5),
        ))
        fig4.add_trace(go.Scatter(
            x=dff[COL_DT], y=dff[COL_TEMP_OUT],
            name="Extérieure", **dot(C["blue"], 5),
        ))
        fig4.add_trace(go.Scatter(
            x=dff[COL_DT], y=dff[COL_RESSENTI],
            name="Ressentie", **dot(C["purple"], 4),
        ))
        fig4.update_layout(**BASE_LAYOUT, title="Température intérieure vs extérieure (°C)")
        fig4.update_xaxes(**xaxis_time(dff))
        st.plotly_chart(fig4, use_container_width=True)

    with col_d:
        st.markdown('<div class="section-title">Statistiques</div>', unsafe_allow_html=True)
        diff = dff[COL_TEMP_IN] - dff[COL_TEMP_OUT]
        stats = pd.DataFrame({
            "Métrique": ["Temp. int. moy.", "Temp. ext. moy.", "Temp. ressentie moy.",
                         "Écart moyen", "Écart max", "Écart min"],
            "Valeur": [
                f"{dff[COL_TEMP_IN].mean():.1f} °C",
                f"{dff[COL_TEMP_OUT].mean():.1f} °C",
                f"{dff[COL_RESSENTI].mean():.1f} °C",
                f"{diff.mean():.1f} °C",
                f"{diff.max():.1f} °C",
                f"{diff.min():.1f} °C",
            ],
        })
        st.dataframe(stats, hide_index=True, use_container_width=True)

        st.markdown('<div class="section-title">Distribution de l\'écart int./ext.</div>', unsafe_allow_html=True)
        fig5 = go.Figure(go.Histogram(
            x=diff, nbinsx=30,
            marker_color=C["blue"], marker_line_color="#21262d",
            marker_line_width=1, opacity=0.85,
        ))
        fig5.update_layout(**BASE_LAYOUT, title="Écart int. - ext. (°C)")
        fig5.update_xaxes(gridcolor="#21262d", linecolor="#30363d", title_text="Écart (°C)")
        fig5.update_yaxes(title_text="Fréquence")
        st.plotly_chart(fig5, use_container_width=True)

    st.markdown('<div class="section-title">Humidité intérieure vs extérieure</div>', unsafe_allow_html=True)
    fig6 = go.Figure()
    fig6.add_trace(go.Scatter(
        x=dff[COL_DT], y=dff[COL_HUM_IN],
        name="Humidité int.", **dot(C["orange"], 5),
    ))
    fig6.add_trace(go.Scatter(
        x=dff[COL_DT], y=dff[COL_HUM_OUT],
        name="Humidité ext.", **dot(C["cyan"], 5),
    ))
    fig6.update_layout(**BASE_LAYOUT, title="Humidité relative comparée (%)")
    fig6.update_xaxes(**xaxis_time(dff))
    st.plotly_chart(fig6, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 3 — Rose des vents
# ══════════════════════════════════════════════
with tab3:
    col_e, col_f = st.columns([2, 1])

    with col_e:
        st.markdown('<div class="section-title">Rose des vents</div>', unsafe_allow_html=True)
        df_wind = dff[[COL_VENT_DIR, COL_VENT_SPD]].dropna().copy()

        bins   = [0, 5, 15, 30, 50, 9999]
        labels = ["0–5 km/h", "5–15 km/h", "15–30 km/h", "30–50 km/h", ">50 km/h"]
        colors_wind = [C["blue"], C["cyan"], C["green"], C["yellow"], C["red"]]
        df_wind["speed_bin"] = pd.cut(df_wind[COL_VENT_SPD], bins=bins, labels=labels)

        dirs_present = df_wind[COL_VENT_DIR].unique().tolist()
        total = len(df_wind) if len(df_wind) > 0 else 1

        fig_rose = go.Figure()
        for label, color in zip(labels, colors_wind):
            sub = df_wind[df_wind["speed_bin"] == label]
            counts = sub[COL_VENT_DIR].value_counts()
            r_vals, theta_vals = [], []
            for d in sorted(WIND_DIRS.keys(), key=lambda x: WIND_DIRS[x]):
                if d in dirs_present:
                    r_vals.append(counts.get(d, 0) / total * 100)
                    theta_vals.append(d)
            if r_vals:
                fig_rose.add_trace(go.Barpolar(
                    r=r_vals, theta=theta_vals, name=label,
                    marker_color=color, marker_line_color="#161b22",
                    marker_line_width=1, opacity=0.88,
                ))

        fig_rose.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            polar=dict(
                bgcolor="rgba(22,27,34,0.6)",
                radialaxis=dict(visible=True, gridcolor="#21262d",
                                tickfont=dict(color="#8b949e", size=9), ticksuffix="%"),
                angularaxis=dict(gridcolor="#21262d", direction="clockwise",
                                 tickfont=dict(color="#e6edf3", size=11, family="DM Mono")),
            ),
            font=dict(family="DM Mono, monospace", color="#8b949e"),
            legend=dict(bgcolor="rgba(22,27,34,0.8)", bordercolor="#30363d", borderwidth=1),
            margin=dict(l=40, r=40, t=40, b=40),
            title="Distribution direction & vitesse (%)",
        )
        st.plotly_chart(fig_rose, use_container_width=True)

    with col_f:
        st.markdown('<div class="section-title">Statistiques vent</div>', unsafe_allow_html=True)
        dir_dom = dff[COL_VENT_DIR].mode().iloc[0] if not dff[COL_VENT_DIR].dropna().empty else "—"
        wind_stats = pd.DataFrame({
            "Métrique": ["Vitesse moyenne", "Vitesse max", "Rafale max", "Direction dominante"],
            "Valeur": [
                f"{dff[COL_VENT_SPD].mean():.1f} km/h",
                f"{dff[COL_VENT_SPD].max():.1f} km/h",
                f"{dff[COL_RAFALE].max():.1f} km/h",
                dir_dom,
            ],
        })
        st.dataframe(wind_stats, hide_index=True, use_container_width=True)

        st.markdown('<div class="section-title">Rafales max / jour</div>', unsafe_allow_html=True)
        dff["_date"] = dff[COL_DT].dt.date
        gust_daily = dff.groupby("_date")[COL_RAFALE].max().reset_index()
        fig_gust = go.Figure(go.Bar(
            x=gust_daily["_date"], y=gust_daily[COL_RAFALE],
            marker_color=C["orange"], marker_line_color="#21262d", marker_line_width=1,
        ))
        fig_gust.update_layout(**BASE_LAYOUT, title="Rafale max journalière (km/h)")
        fig_gust.update_xaxes(**xaxis_time(dff))
        fig_gust.update_yaxes(title_text="km/h")
        st.plotly_chart(fig_gust, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 4 — Pluviométrie
# ══════════════════════════════════════════════
with tab4:
    dff["_date"] = dff[COL_DT].dt.date
    # Pluie journalière = delta positif du cumul total
    dff["_rain_delta"] = dff[COL_PLUIE_TOT].diff().clip(lower=0)

    col_g, col_h = st.columns(2)

    with col_g:
        st.markdown('<div class="section-title">Pluie journalière estimée</div>', unsafe_allow_html=True)
        daily_rain = dff.groupby("_date")["_rain_delta"].sum().reset_index()
        fig_daily = go.Figure(go.Bar(
            x=daily_rain["_date"], y=daily_rain["_rain_delta"],
            marker_color=C["blue"], marker_line_color="#21262d", marker_line_width=1,
        ))
        fig_daily.update_layout(**BASE_LAYOUT, title="Précipitations journalières (mm)")
        fig_daily.update_xaxes(**xaxis_time(dff))
        fig_daily.update_yaxes(title_text="mm")
        st.plotly_chart(fig_daily, use_container_width=True)

    with col_h:
        st.markdown('<div class="section-title">Cumul total des précipitations</div>', unsafe_allow_html=True)
        fig_cum = go.Figure(go.Scatter(
            x=dff[COL_DT], y=dff[COL_PLUIE_TOT],
            name="Cumul total", **dot(C["cyan"], 5),
        ))
        fig_cum.update_layout(**BASE_LAYOUT, title="Pluviométrie totale cumulée (mm)")
        fig_cum.update_xaxes(**xaxis_time(dff))
        fig_cum.update_yaxes(title_text="mm")
        st.plotly_chart(fig_cum, use_container_width=True)

    st.markdown('<div class="section-title">Pluie sur le dernier mois (glissant)</div>', unsafe_allow_html=True)
    fig_month = go.Figure(go.Scatter(
        x=dff[COL_DT], y=dff[COL_PLUIE_M],
        name="Pluie / mois", **dot(C["purple"], 5),
    ))
    fig_month.update_layout(**BASE_LAYOUT, title="Pluviométrie sur le dernier mois glissant (mm)")
    fig_month.update_xaxes(**xaxis_time(dff))
    fig_month.update_yaxes(title_text="mm")
    st.plotly_chart(fig_month, use_container_width=True)

    st.markdown('<div class="section-title">Corrélation pluie & humidité extérieure</div>', unsafe_allow_html=True)
    fig_corr = go.Figure(go.Scatter(
        x=dff[COL_HUM_OUT], y=dff["_rain_delta"],
        mode="markers",
        marker=dict(color=C["blue"], size=4, opacity=0.5, line=dict(width=0)),
    ))
    fig_corr.update_layout(**BASE_LAYOUT, title="Humidité ext. (%) vs Précipitations (mm)")
    fig_corr.update_layout(hovermode="closest")
    fig_corr.update_xaxes(gridcolor="#21262d", linecolor="#30363d", title_text="Humidité ext. (%)")
    fig_corr.update_yaxes(title_text="Pluie (mm)")
    st.plotly_chart(fig_corr, use_container_width=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f'<p style="color:#8b949e; font-family: DM Mono, monospace; font-size:0.75rem;">'
    f'📡 {len(dff):,} mesures · '
    f'{dff[COL_DT].min().strftime("%d/%m/%Y")} → {dff[COL_DT].max().strftime("%d/%m/%Y")}'
    f'</p>',
    unsafe_allow_html=True,
)

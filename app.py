"""
PSC Box Girder — Top Flange Transverse Design  (v5 Professional Engineering UI)
AASHTO LRFD Bridge Design Specifications  |  1.0 m transverse strip
"""

import math, datetime
from io import BytesIO

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ─────────────────────────────────────────────────────────────────────────────
# 1.  CONFIG & SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="PSC Box Girder Design | AASHTO LRFD",
    page_icon="🏗️",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════
#  CUSTOM CSS — Industrial Engineering Precision Theme
# ═══════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

:root {
    --bg-primary:    #0b0f1a;
    --bg-card:       #111827;
    --bg-card-alt:   #1a2235;
    --border:        #1e293b;
    --accent-blue:   #3b82f6;
    --accent-cyan:   #06b6d4;
    --accent-amber:  #f59e0b;
    --accent-green:  #10b981;
    --accent-red:    #ef4444;
    --text-primary:  #f1f5f9;
    --text-muted:    #64748b;
    --text-dim:      #94a3b8;
    --mono:          'JetBrains Mono', monospace;
    --sans:          'Inter', sans-serif;
    --display:       'Syne', sans-serif;
}

/* === Global === */
html, body, [class*="css"] { font-family: var(--sans); }
.block-container { padding: 1.5rem 2rem 3rem 2rem !important; max-width: 1600px !important; }
section[data-testid="stSidebar"] { background: #080d16 !important; border-right: 1px solid var(--border); }

/* === App Header === */
.eng-header {
    background: linear-gradient(135deg, #080d16 0%, #0f172a 50%, #0d1f3c 100%);
    border: 1px solid #1e3a5f;
    border-left: 4px solid var(--accent-blue);
    border-radius: 8px;
    padding: 1.6rem 2rem 1.4rem 2rem;
    margin-bottom: 1rem;
    position: relative;
    overflow: hidden;
}
.eng-header::before {
    content: '';
    position: absolute; top: 0; right: 0;
    width: 300px; height: 100%;
    background: radial-gradient(ellipse at top right, rgba(59,130,246,0.08) 0%, transparent 70%);
}
.eng-header-title {
    font-family: var(--display);
    font-size: 1.85rem; font-weight: 800;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    margin: 0 0 0.3rem 0;
}
.eng-header-sub {
    font-family: var(--mono);
    font-size: 0.78rem; color: var(--accent-cyan);
    letter-spacing: 0.08em;
    margin: 0;
}
.eng-badge {
    display: inline-block;
    background: rgba(59,130,246,0.15);
    border: 1px solid rgba(59,130,246,0.3);
    color: #93c5fd;
    font-family: var(--mono); font-size: 0.72rem;
    padding: 3px 10px; border-radius: 4px;
    margin-right: 6px; margin-top: 6px;
    letter-spacing: 0.05em;
}

/* === Project Metadata Bar === */
.meta-bar {
    background: #0f172a;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.65rem 1.2rem;
    margin-bottom: 1.2rem;
    display: flex; gap: 2rem; flex-wrap: wrap;
    font-family: var(--mono); font-size: 0.75rem;
}
.meta-item { color: var(--text-muted); }
.meta-item span { color: var(--text-dim); font-weight: 600; }

/* === Section Label === */
.section-label {
    font-family: var(--mono);
    font-size: 0.68rem; font-weight: 600;
    color: var(--accent-cyan);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    border-left: 3px solid var(--accent-cyan);
    padding-left: 0.6rem;
    margin: 1.2rem 0 0.7rem 0;
}

/* === Info Cards === */
.info-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1.2rem; }
.info-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-top: 3px solid;
    border-radius: 6px;
    padding: 0.9rem 1rem;
}
.info-card.blue  { border-top-color: var(--accent-blue); }
.info-card.cyan  { border-top-color: var(--accent-cyan); }
.info-card.amber { border-top-color: var(--accent-amber); }
.info-card.green { border-top-color: var(--accent-green); }
.info-card-label { font-family: var(--mono); font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.4rem; }
.info-card-val   { font-family: var(--mono); font-size: 1.35rem; font-weight: 700; color: var(--text-primary); }
.info-card-unit  { font-size: 0.75rem; color: var(--text-muted); margin-left: 3px; }
.info-card-ref   { font-family: var(--mono); font-size: 0.65rem; color: var(--text-muted); margin-top: 0.25rem; }

/* === Metric Cards === */
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.7rem; margin-bottom: 1.2rem; }
.kpi-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.85rem 1rem;
    position: relative;
}
.kpi-label { font-family: var(--mono); font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em; }
.kpi-value { font-family: var(--mono); font-size: 1.25rem; font-weight: 700; color: var(--accent-cyan); margin: 0.2rem 0; }
.kpi-sub   { font-family: var(--mono); font-size: 0.65rem; color: var(--text-muted); }
.kpi-ref   { position: absolute; top: 8px; right: 10px; font-family: var(--mono); font-size: 0.6rem; color: #334155; }

/* === Loss Breakdown Panel === */
.loss-row { display: grid; grid-template-columns: repeat(6, 1fr); gap: 0.6rem; margin-bottom: 1rem; }
.loss-card {
    background: #0f172a;
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 0.7rem 0.8rem;
    text-align: center;
}
.loss-label { font-family: var(--mono); font-size: 0.62rem; color: var(--text-muted); text-transform: uppercase; }
.loss-value { font-family: var(--mono); font-size: 1.1rem; font-weight: 700; color: var(--accent-amber); }
.loss-unit  { font-family: var(--mono); font-size: 0.65rem; color: var(--text-muted); }
.loss-pct   { font-family: var(--mono); font-size: 0.7rem; color: #94a3b8; }

/* === Status Chips === */
.chip-pass { background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.35); color: #6ee7b7; font-family: var(--mono); font-size: 0.72rem; padding: 3px 10px; border-radius: 20px; font-weight: 600; }
.chip-warn { background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.35); color: #fcd34d; font-family: var(--mono); font-size: 0.72rem; padding: 3px 10px; border-radius: 20px; font-weight: 600; }
.chip-fail { background: rgba(239,68,68,0.15);  border: 1px solid rgba(239,68,68,0.35);  color: #fca5a5; font-family: var(--mono); font-size: 0.72rem; padding: 3px 10px; border-radius: 20px; font-weight: 600; }

/* === Code Reference Box === */
.code-ref {
    background: #0a0f1e;
    border: 1px solid #1e3a5f;
    border-left: 3px solid var(--accent-blue);
    border-radius: 4px;
    padding: 0.6rem 1rem;
    margin: 0.6rem 0;
    font-family: var(--mono);
    font-size: 0.72rem;
    color: #93c5fd;
}
.code-ref strong { color: var(--accent-cyan); }

/* === Summary Table === */
.summary-hdr {
    background: #0f172a;
    border-bottom: 1px solid var(--border);
    padding: 0.5rem 1rem;
    font-family: var(--mono); font-size: 0.72rem; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.1em;
    border-radius: 6px 6px 0 0;
}

/* === Tabs === */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    background: #080d16;
    padding: 4px;
    border-radius: 8px;
    border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px;
    padding: 8px 20px;
    background: transparent;
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    background: var(--bg-card-alt) !important;
    color: var(--accent-cyan) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 1.2rem;
}

/* === Sidebar === */
section[data-testid="stSidebar"] .stExpander {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 6px;
}
section[data-testid="stSidebar"] label {
    color: #94a3b8 !important;
    font-family: var(--mono) !important;
    font-size: 0.75rem !important;
}
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #e2e8f0;
    font-family: var(--display);
    font-size: 1rem;
    font-weight: 700;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 0.5rem;
    margin-bottom: 0.8rem;
}

/* === DataFrames === */
div[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 8px;
    overflow: hidden;
}

/* === Metric override === */
div[data-testid="stMetricValue"] {
    font-family: var(--mono) !important;
    color: var(--accent-cyan) !important;
    font-weight: 700 !important;
}
div[data-testid="stMetricLabel"] {
    font-family: var(--mono) !important;
    font-size: 0.72rem !important;
    color: var(--text-muted) !important;
}

/* === Alert === */
.stAlert { border-radius: 6px; font-family: var(--sans); }

/* === Plotly Chart container === */
.js-plotly-plot { border-radius: 6px; }

/* === Divider === */
hr { border-color: var(--border); margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  PLOTLY DARK THEME (applied to all charts)
# ─────────────────────────────────────────────────────────────────────────────
ENG_TEMPLATE = dict(
    layout=go.Layout(
        paper_bgcolor="#0b0f1a",
        plot_bgcolor="#0f172a",
        font=dict(family="JetBrains Mono, monospace", color="#94a3b8", size=11),
        xaxis=dict(gridcolor="#1e293b", linecolor="#334155", zeroline=False, tickfont=dict(size=10)),
        yaxis=dict(gridcolor="#1e293b", linecolor="#334155", zeroline=False, tickfont=dict(size=10)),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1e293b", borderwidth=1, font=dict(size=10)),
        margin=dict(l=55, r=20, t=40, b=45),
        hoverlabel=dict(bgcolor="#1e293b", bordercolor="#334155", font=dict(family="JetBrains Mono", size=11)),
    )
)

# ─────────────────────────────────────────────────────────────────────────────
# 2.  DEFAULTS & SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_SCALARS = dict(
    width=12.0, cl_lweb=2.0, cl_rweb=10.0,
    fc=45.0, fci=36.0, fpu=1860.0, fpy_ratio=0.90,
    aps_strand=140.0, duct_dia_mm=70.0,
    num_tendon=1, n_strands=5,
    fpi_ratio=0.75,
    t0=3, RH=75, anch_slip_mm=6.0,
    phi_flex=1.00, phi_shear=0.90,
    proj_name="Expressway Overpass — Segment 4A", doc_no="CALC-STR-001",
    eng_name="Engineer Name", chk_name="Checker Name",
)

if "thk_src" not in st.session_state:
    st.session_state["thk_src"] = pd.DataFrame({"x (m)": [0.0, 6.0, 12.0], "t (m)": [0.25, 0.25, 0.25]})
if "tdn_src" not in st.session_state:
    st.session_state["tdn_src"] = pd.DataFrame({"x (m)": [0.0, 6.0, 12.0], "z_top (m)": [0.10, 0.10, 0.10]})
if "ld_src" not in st.session_state:
    st.session_state["ld_src"] = pd.DataFrame({
        "x (m)": [0.0, 6.0, 12.0],
        "M_DL (kNm/m)":  [0.0, 0.0, 0.0], "V_DL (kN/m)":  [0.0, 0.0, 0.0],
        "M_SDL (kNm/m)": [0.0, 0.0, 0.0], "V_SDL (kN/m)": [0.0, 0.0, 0.0],
        "M_LL (kNm/m)":  [0.0, 0.0, 0.0], "V_LL (kN/m)":  [0.0, 0.0, 0.0],
    })

for k, v in DEFAULT_SCALARS.items():
    if k not in st.session_state:
        st.session_state[k] = v

if "_tbl_ver" not in st.session_state:
    st.session_state["_tbl_ver"] = 0

# Shorthand aliases from session state
fc           = st.session_state["fc"]
fci          = st.session_state["fci"]
fpu          = st.session_state["fpu"]
fpi_ratio    = st.session_state["fpi_ratio"]
fpy_ratio    = st.session_state["fpy_ratio"]
aps_strand   = st.session_state["aps_strand"]
duct_dia_mm  = st.session_state["duct_dia_mm"]
num_tendon   = st.session_state["num_tendon"]
n_strands    = st.session_state["n_strands"]
width        = st.session_state["width"]
t0           = st.session_state["t0"]
RH           = st.session_state["RH"]
anch_slip_mm = st.session_state["anch_slip_mm"]

# ─────────────────────────────────────────────────────────────────────────────
# 3.  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏗️ PARAMETER INPUTS")

    with st.expander("📐 Materials & Geometry", expanded=True):
        st.caption("**Concrete**")
        fc   = st.number_input("f'c  — Service Strength (MPa)", key="fc",   min_value=20.0, step=1.0)
        fci  = st.number_input("f'ci — Transfer Strength (MPa)", key="fci", min_value=15.0, step=1.0)
        st.caption("**Prestressing Steel**")
        fpu  = st.number_input("fpu — UTS (MPa)",  key="fpu",  min_value=1000.0, step=10.0)
        fpy_ratio = st.selectbox("fpy / fpu", [0.90, 0.85], key="fpy_ratio")
        aps_strand = st.number_input("Aps per strand (mm²)", key="aps_strand", min_value=50.0, step=10.0)
        st.caption("**Section**")
        width      = st.number_input("Total Flange Width (m)", key="width",    min_value=1.0, step=0.5)
        duct_dia_mm = st.number_input("Duct Diameter (mm)",  key="duct_dia_mm", min_value=30.0, step=5.0)

    with st.expander("🌐 Web Geometry", expanded=False):
        st.caption("Transverse CL position from left edge")
        cl_lweb = st.number_input("Left Web CL (m)",  key="cl_lweb", min_value=0.0, step=0.1)
        cl_rweb = st.number_input("Right Web CL (m)", key="cl_rweb", min_value=0.0, step=0.1)

    with st.expander("🔩 Prestressing Layout", expanded=False):
        num_tendon = st.number_input("Tendons per 1m strip",  key="num_tendon",  min_value=1, step=1)
        n_strands  = st.number_input("Strands per tendon",    key="n_strands",   min_value=1, step=1)
        fpi_ratio  = st.slider("Jacking ratio  fpi / fpu",    0.70, 0.80, key="fpi_ratio", step=0.005)
        st.markdown(f"""<div class="code-ref">
        <strong>AASHTO 5.9.3:</strong> fpi ≤ 0.80·fpu (Low-Relax)<br>
        Current fpi = {fpi_ratio*fpu:.0f} MPa ({fpi_ratio*100:.1f}% of fpu)
        </div>""", unsafe_allow_html=True)

    with st.expander("📉 Losses & Resistance Factors", expanded=False):
        t0 = st.number_input("Age at Transfer (days)", key="t0",          min_value=1, step=1)
        RH = st.number_input("Relative Humidity (%)",  key="RH",          min_value=40, max_value=100)
        anch_slip_mm = st.number_input("Anchorage Slip (mm)", key="anch_slip_mm", min_value=0.0, step=1.0)
        st.divider()
        st.caption("**AASHTO 5.5.4.2 Resistance Factors**")
        phi_flex  = st.number_input("φ — Flexure  (bonded PT)",  key="phi_flex",  min_value=0.5, max_value=1.0, step=0.01)
        phi_shear = st.number_input("φ — Shear",                 key="phi_shear", min_value=0.5, max_value=1.0, step=0.01)

    with st.expander("📄 Document Control", expanded=False):
        proj_name = st.text_input("Project Name", key="proj_name")
        doc_no    = st.text_input("Document No.", key="doc_no")
        eng_name  = st.text_input("Designed by",  key="eng_name")
        chk_name  = st.text_input("Checked by",   key="chk_name")

    st.divider()
    st.markdown(f"""<div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:#334155;line-height:1.8;">
    AASHTO LRFD 9th Edition<br>
    Strip Method: 1.0 m transverse<br>
    Generated: {datetime.date.today().strftime('%d %b %Y')}
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 4.  LOGIC ENGINES  ← UNCHANGED FROM v4
# ─────────────────────────────────────────────────────────────────────────────
def calc_losses(dft, dfp, fc, fci, fpu, fpi_ratio, aps_strand, num_tendon,
                n_strands, duct_dia_mm, t0, RH, anch_slip_mm, width):
    Ep, mu, Kw, KL = 197000.0, 0.20, 0.0066, 45.0
    b, wc = 1.0, 2400.0
    x_mid = width / 2.0
    t_m = float(np.interp(x_mid, dft["x (m)"], dft["t (m)"]))
    z_m = float(np.interp(x_mid, dfp["x (m)"], dfp["z_top (m)"]))
    yc_m = t_m / 2.0
    e_m  = yc_m - z_m
    An   = b * t_m - int(num_tendon) * (math.pi / 4 * (duct_dia_mm / 1000) ** 2)
    In   = (b * t_m ** 3 / 12)
    Aps  = int(num_tendon * n_strands) * (aps_strand * 1e-6)
    Ec   = 0.043 * (wc ** 1.5) * math.sqrt(fc)
    Eci  = 0.043 * (wc ** 1.5) * math.sqrt(fci)
    fpj  = fpu * fpi_ratio
    dfF  = fpj * 0.02
    dfA  = 30.0
    dfES = 40.0
    dfSH = 35.0
    dfCR = 60.0
    dfR  = 20.0
    fpe  = fpj - (dfF + dfA + dfES + dfSH + dfCR + dfR)
    return {
        "Aps": Aps,
        "Pi":  Aps * (fpj - dfF - dfA - dfES) * 1e3,
        "Pe":  Aps * fpe * 1e3,
        "fpe": fpe,
        "fpj": fpj,
        "imm_loss_pct": (dfF + dfA + dfES) / fpj * 100,
        "lt_loss_pct":  (dfSH + dfCR + dfR)  / fpj * 100,
        "total_loss_pct": (fpj - fpe) / fpj * 100,
        "delta_imm": (dfF + dfA + dfES),
        "delta_lt":  (dfSH + dfCR + dfR),
        "dfF": dfF, "dfA": dfA, "dfES": dfES,
        "dfSH": dfSH, "dfCR": dfCR, "dfR": dfR,
        "Ec": Ec, "Eci": Eci, "Ep": Ep,
        "t_m": t_m, "z_m": z_m,
    }


def run_calc(dft, dfp, dfl, L):
    N = 200
    x = np.linspace(0, st.session_state.width, N)
    t  = np.interp(x, dft["x (m)"], dft["t (m)"])
    z  = np.interp(x, dfp["x (m)"], dfp["z_top (m)"])
    yc = t / 2.0
    e  = yc - z
    Ag = 1.0 * t
    Ig = 1.0 * t ** 3 / 12
    m_dl  = np.interp(x, dfl["x (m)"], dfl["M_DL (kNm/m)"])
    m_sdl = np.interp(x, dfl["x (m)"], dfl["M_SDL (kNm/m)"])
    m_ll  = np.interp(x, dfl["x (m)"], dfl["M_LL (kNm/m)"])
    ms1   = m_dl + m_sdl + m_ll
    mu    = 1.25 * m_dl + 1.5 * m_sdl + 1.75 * m_ll
    v_dl  = np.interp(x, dfl["x (m)"], dfl["V_DL (kN/m)"])
    vu    = 1.25 * np.abs(v_dl) + 1.75 * 10.0
    tr_top = (-L["Pi"] / Ag / 1000 + L["Pi"] * e * (t / 2) / Ig / 1000 - m_dl * (t / 2) / Ig / 1000)
    sv1_top = (-L["Pe"] / Ag / 1000 + L["Pe"] * e * (t / 2) / Ig / 1000 - ms1 * (t / 2) / Ig / 1000)
    phi_Mn = st.session_state.phi_flex  * L["Aps"] * 1800 * (z - 0.05) * 1000
    phi_Vn = st.session_state.phi_shear * 0.083 * 2 * math.sqrt(fc) * 1000 * 0.9 * z
    return {
        "x": x, "t": t, "z": z, "yc": yc, "e": e,
        "tr_top": tr_top, "sv1_top": sv1_top,
        "tr_bot": tr_top, "sv1_bot": sv1_top,
        "mu": mu, "phi_Mn_pos": phi_Mn, "phi_Mn_neg": -phi_Mn,
        "vu": vu, "phi_Vn": phi_Vn,
        "Pe": L["Pe"], "Pi": L["Pi"], "L": L, "Aps": L["Aps"],
        "lim_tr_c": -0.6 * fci, "lim_tr_t": 0.25 * math.sqrt(fci),
        "lim_sv_ct": -0.6 * fc, "lim_sv_t": 0.5 * math.sqrt(fc),
    }


def dcr_style(obj, col):
    def _s(val):
        try: v = float(val)
        except: return ""
        if v <= 0.80: return "background-color:#052e16;color:#6ee7b7;font-weight:bold;"
        if v <= 1.00: return "background-color:#431407;color:#fcd34d;font-weight:bold;"
        return "background-color:#450a0a;color:#fca5a5;font-weight:bold;"
    if isinstance(obj, pd.DataFrame):
        return obj.style.map(_s, subset=[col])
    return obj.map(_s, subset=[col])


# ─────────────────────────────────────────────────────────────────────────────
# 5.  HEADER & PROJECT INFO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="eng-header">
    <div class="eng-header-title">🏗️ PSC Box Girder — Top Flange Transverse Design</div>
    <div class="eng-header-sub">AASHTO LRFD BRIDGE DESIGN SPECIFICATIONS · 1.0 M TRANSVERSE STRIP METHOD · STRENGTH + SERVICE CHECKS</div>
    <div style="margin-top:0.7rem;">
        <span class="eng-badge">AASHTO LRFD 9th Ed.</span>
        <span class="eng-badge">Art. 5.9 Prestress</span>
        <span class="eng-badge">Art. 5.7 Flexure</span>
        <span class="eng-badge">Art. 5.8 Shear</span>
        <span class="eng-badge">Art. 3.6 Live Load</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="meta-bar">
    <div class="meta-item">PROJECT <span>{st.session_state.proj_name}</span></div>
    <div class="meta-item">DOC NO. <span>{st.session_state.doc_no}</span></div>
    <div class="meta-item">DESIGNED <span>{st.session_state.eng_name}</span></div>
    <div class="meta-item">CHECKED <span>{st.session_state.chk_name}</span></div>
    <div class="meta-item">DATE <span>{datetime.date.today().strftime('%d %b %Y')}</span></div>
    <div class="meta-item">REV <span>A</span></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 6.  MATERIAL PROPERTY CARDS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">MATERIAL PROPERTIES</div>', unsafe_allow_html=True)

fpy    = fpy_ratio * fpu
Ec_val = 0.043 * (2400 ** 1.5) * math.sqrt(fc) / 1000
Es_val = 197.0

col_m = st.columns(8)
mats = [
    ("f'c Service",   fc,    "MPa",  "AASHTO 5.4.2.1"),
    ("f'ci Transfer", fci,   "MPa",  "AASHTO 5.9.4.1"),
    ("fpu",           fpu,   "MPa",  "ASTM A416"),
    ("fpy",           fpy,   "MPa",  f"{fpy_ratio:.0%}·fpu"),
    ("fpi (jack)",    fpi_ratio*fpu, "MPa", f"{fpi_ratio:.1%}·fpu"),
    ("Ec",            Ec_val,"GPa",  "AASHTO 5.4.2.4"),
    ("Ep",            Es_val,"GPa",  "AASHTO 5.4.4.2"),
    ("φ flex / shear",f"{st.session_state.phi_flex:.2f}/{st.session_state.phi_shear:.2f}", "", "AASHTO 5.5.4.2"),
]
colors = ["blue","blue","cyan","cyan","amber","green","green","amber"]
for i, (lbl, val, unit, ref) in enumerate(mats):
    with col_m[i]:
        st.markdown(f"""<div class="info-card {colors[i]}">
            <div class="info-card-label">{lbl}</div>
            <div class="info-card-val">{val if isinstance(val, str) else f"{val:.1f}"}<span class="info-card-unit">{unit}</span></div>
            <div class="info-card-ref">{ref}</div>
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 7.  DATA INPUT EDITORS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">STATION DATA INPUTS</div>', unsafe_allow_html=True)

_v = st.session_state["_tbl_ver"]
with st.container(border=True):
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.markdown("**📏 Slab Thickness Profile `t(x)`**")
        st.caption("Varies along transverse width (m)")
        df_thk = st.data_editor(
            st.session_state["thk_src"], num_rows="dynamic",
            key=f"ed_thk_{_v}", use_container_width=True,
            column_config={
                "x (m)": st.column_config.NumberColumn("x (m)", format="%.3f"),
                "t (m)": st.column_config.NumberColumn("t (m)", format="%.3f"),
            }
        )
    with c2:
        st.markdown("**🔩 Tendon CG Profile `z(x)`**")
        st.caption("Depth from top fiber to tendon CG (m)")
        df_tdn = st.data_editor(
            st.session_state["tdn_src"], num_rows="dynamic",
            key=f"ed_tdn_{_v}", use_container_width=True,
            column_config={
                "x (m)":      st.column_config.NumberColumn("x (m)",      format="%.3f"),
                "z_top (m)":  st.column_config.NumberColumn("z_top (m)",  format="%.3f"),
            }
        )
    with c3:
        st.markdown("**📦 Applied Loads per Unit Width**")
        st.caption("Unfactored moments (kNm/m) and shears (kN/m)")
        df_ld = st.data_editor(
            st.session_state["ld_src"], num_rows="dynamic",
            key=f"ed_ld_{_v}", use_container_width=True,
            column_config={
                "x (m)":         st.column_config.NumberColumn("x (m)",   format="%.2f"),
                "M_DL (kNm/m)":  st.column_config.NumberColumn("M_DL",    format="%.1f"),
                "V_DL (kN/m)":   st.column_config.NumberColumn("V_DL",    format="%.1f"),
                "M_SDL (kNm/m)": st.column_config.NumberColumn("M_SDL",   format="%.1f"),
                "V_SDL (kN/m)":  st.column_config.NumberColumn("V_SDL",   format="%.1f"),
                "M_LL (kNm/m)":  st.column_config.NumberColumn("M_LL",    format="%.1f"),
                "V_LL (kN/m)":   st.column_config.NumberColumn("V_LL",    format="%.1f"),
            }
        )

# ─────────────────────────────────────────────────────────────────────────────
# 8.  RUN CALCULATIONS
# ─────────────────────────────────────────────────────────────────────────────
try:
    L = calc_losses(df_thk, df_tdn, fc, fci, fpu, fpi_ratio, aps_strand,
                    num_tendon, n_strands, duct_dia_mm, t0, RH, anch_slip_mm, width)
    R = run_calc(df_thk, df_tdn, df_ld, L)

    # ─────────────────────────────────────────────────────────────────────
    # 9.  KPI DASHBOARD
    # ─────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">PRESTRESS ANALYSIS — KEY RESULTS</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi-card">
            <div class="kpi-ref">Art. 5.9.3</div>
            <div class="kpi-label">Aps  (1m strip)</div>
            <div class="kpi-value">{R['Aps']*1e6:.0f} <span style="font-size:0.75rem;color:#64748b;">mm²/m</span></div>
            <div class="kpi-sub">{int(num_tendon)} tendon × {int(n_strands)} strands × {aps_strand:.0f} mm²</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-ref">Art. 5.9.5.2</div>
            <div class="kpi-label">Pi  — Initial Force</div>
            <div class="kpi-value">{R['Pi']:.1f} <span style="font-size:0.75rem;color:#64748b;">kN/m</span></div>
            <div class="kpi-sub">After Friction, Slip, ES</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-ref">Art. 5.9.5.4</div>
            <div class="kpi-label">Pe  — Effective Force</div>
            <div class="kpi-value">{R['Pe']:.1f} <span style="font-size:0.75rem;color:#64748b;">kN/m</span></div>
            <div class="kpi-sub">After all long-term losses</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-ref">AASHTO Table</div>
            <div class="kpi-label">fpe  — Eff. Stress</div>
            <div class="kpi-value">{R['L']['fpe']:.0f} <span style="font-size:0.75rem;color:#64748b;">MPa</span></div>
            <div class="kpi-sub">≤ 0.80·fpy = {0.80*fpy:.0f} MPa</div>
        </div>
        <div class="kpi-card" style="border-top-color: {'#ef4444' if R['L']['total_loss_pct']>20 else '#10b981'};">
            <div class="kpi-ref">Art. 5.9.5</div>
            <div class="kpi-label">Total Prestress Loss</div>
            <div class="kpi-value" style="color:{'#fca5a5' if R['L']['total_loss_pct']>20 else '#6ee7b7'}">
                {R['L']['total_loss_pct']:.1f} <span style="font-size:0.75rem;">%</span>
            </div>
            <div class="kpi-sub">Imm:{R['L']['imm_loss_pct']:.1f}%  LT:{R['L']['lt_loss_pct']:.1f}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Loss Breakdown
    st.markdown(f"""
    <div class="loss-row">
        <div class="loss-card">
            <div class="loss-label">Friction ΔfpF</div>
            <div class="loss-value">{R['L']['dfF']:.1f}</div>
            <div class="loss-unit">MPa</div>
            <div class="loss-pct">{R['L']['dfF']/R['L']['fpj']*100:.1f}% fpj</div>
        </div>
        <div class="loss-card">
            <div class="loss-label">Anch. Slip ΔfpA</div>
            <div class="loss-value">{R['L']['dfA']:.1f}</div>
            <div class="loss-unit">MPa</div>
            <div class="loss-pct">{R['L']['dfA']/R['L']['fpj']*100:.1f}% fpj</div>
        </div>
        <div class="loss-card">
            <div class="loss-label">Elast. Short. ΔfpES</div>
            <div class="loss-value">{R['L']['dfES']:.1f}</div>
            <div class="loss-unit">MPa</div>
            <div class="loss-pct">{R['L']['dfES']/R['L']['fpj']*100:.1f}% fpj</div>
        </div>
        <div class="loss-card">
            <div class="loss-label">Shrinkage ΔfpSH</div>
            <div class="loss-value">{R['L']['dfSH']:.1f}</div>
            <div class="loss-unit">MPa</div>
            <div class="loss-pct">{R['L']['dfSH']/R['L']['fpj']*100:.1f}% fpj</div>
        </div>
        <div class="loss-card">
            <div class="loss-label">Creep ΔfpCR</div>
            <div class="loss-value">{R['L']['dfCR']:.1f}</div>
            <div class="loss-unit">MPa</div>
            <div class="loss-pct">{R['L']['dfCR']/R['L']['fpj']*100:.1f}% fpj</div>
        </div>
        <div class="loss-card">
            <div class="loss-label">Relaxation ΔfpR</div>
            <div class="loss-value">{R['L']['dfR']:.1f}</div>
            <div class="loss-unit">MPa</div>
            <div class="loss-pct">{R['L']['dfR']/R['L']['fpj']*100:.1f}% fpj</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────
    # 10.  TABBED ANALYSIS PANELS
    # ─────────────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "📐 Section Geometry",
        "📉 Prestress Losses",
        "🔬 Stress Verification",
        "💪 Strength Check",
        "📊 DCR Summary",
        "📋 Design Report",
    ])

    # ═══════════ TAB 1 — SECTION GEOMETRY ═══════════
    with tabs[0]:
        st.markdown("""<div class="code-ref"><strong>AASHTO Art. 5.7.1.1</strong> — Strip Method for Slab Analysis.
        Transverse 1.0 m strip treated as a continuous beam between webs.</div>""", unsafe_allow_html=True)

        col_g1, col_g2 = st.columns([3, 2])

        with col_g1:
            fig_geo = make_subplots(rows=2, cols=1, row_heights=[0.5, 0.5],
                                     subplot_titles=("Slab Thickness Profile t(x)", "Tendon CG Profile z_top(x)"),
                                     vertical_spacing=0.18)
            # Thickness fill
            fig_geo.add_trace(go.Scatter(
                x=np.concatenate([R["x"], R["x"][::-1]]),
                y=np.concatenate([np.zeros(len(R["x"])), -R["t"][::-1] * 1000]),
                fill="toself", fillcolor="rgba(59,130,246,0.12)",
                line=dict(color="#3b82f6", width=1.5), name="Slab Section",
            ), row=1, col=1)
            fig_geo.add_trace(go.Scatter(
                x=R["x"], y=-R["t"] * 1000,
                line=dict(color="#3b82f6", width=2), name="Bottom fiber", showlegend=False,
            ), row=1, col=1)
            # Web lines
            for xw, lbl in [(st.session_state.cl_lweb, "L.Web"), (st.session_state.cl_rweb, "R.Web")]:
                fig_geo.add_vline(x=xw, line=dict(color="#f59e0b", width=1.5, dash="dash"),
                                   annotation_text=lbl, annotation_font_color="#f59e0b",
                                   annotation_font_size=10, row=1, col=1)
            # Tendon profile
            fig_geo.add_trace(go.Scatter(
                x=R["x"], y=-R["z"] * 1000,
                line=dict(color="#ef4444", width=2.5), name="Tendon CG",
            ), row=2, col=1)
            fig_geo.add_trace(go.Scatter(
                x=R["x"], y=-R["e"] * 1000,
                line=dict(color="#a855f7", width=1.5, dash="dot"), name="Eccentricity e",
            ), row=2, col=1)
            fig_geo.update_yaxes(title_text="Depth (mm)", row=1, col=1)
            fig_geo.update_yaxes(title_text="Depth (mm)", row=2, col=1)
            fig_geo.update_xaxes(title_text="Transverse Position x (m)", row=2, col=1)
            fig_geo.update_layout(template=ENG_TEMPLATE["layout"], height=480,
                                   legend=dict(x=0.01, y=0.48))
            for ann in fig_geo.layout.annotations:
                ann.font = dict(color="#94a3b8", size=11, family="JetBrains Mono")
            st.plotly_chart(fig_geo, use_container_width=True)

        with col_g2:
            st.markdown("**Section Properties — Midspan**")
            t_mid = float(np.interp(width/2, R["x"], R["t"]))
            z_mid = float(np.interp(width/2, R["x"], R["z"]))
            e_mid = t_mid/2 - z_mid
            Ag_m  = 1.0 * t_mid
            Ig_m  = 1.0 * t_mid**3 / 12
            St_m  = Ig_m / (t_mid/2)
            Sb_m  = St_m
            props = [
                ("h = t",       f"{t_mid*1000:.1f} mm",   "Slab thickness"),
                ("Ag",          f"{Ag_m*1e6:.0f} mm²/m",  "Gross area"),
                ("Ig",          f"{Ig_m*1e9:.3e} mm⁴/m",  "2nd moment of area"),
                ("St = Sb",     f"{St_m*1e6:.0f} mm³/m",  "Section modulus"),
                ("z_top",       f"{z_mid*1000:.1f} mm",   "Tendon depth"),
                ("e",           f"{e_mid*1000:.1f} mm",   "Eccentricity"),
                ("duct dia",    f"{duct_dia_mm:.0f} mm",   "PT duct"),
                ("n·Aps/Ag",    f"{L['Aps']*1e6/(Ag_m*1e6)*100:.2f}%", "PT ratio"),
            ]
            data_df = pd.DataFrame(props, columns=["Parameter", "Value", "Description"])
            st.dataframe(data_df, use_container_width=True, hide_index=True, height=310)

            st.markdown("""<div class="code-ref">
            <strong>AASHTO 5.9.1.5:</strong> Minimum avg. prestress after losses ≥ 1.0 MPa (for PT slabs)
            </div>""", unsafe_allow_html=True)
            avg_stress = L["Pe"] / (Ag_m * 1000)
            color = "#6ee7b7" if avg_stress >= 1.0 else "#fca5a5"
            st.markdown(f"""<div class="code-ref" style="border-left-color:{color};">
            <strong>Avg. Precompression</strong>  Pe/Ag = {avg_stress:.2f} MPa
            {'✅ ≥ 1.0 MPa — OK' if avg_stress >= 1.0 else '❌ < 1.0 MPa — CHECK'}
            </div>""", unsafe_allow_html=True)

    # ═══════════ TAB 2 — LOSSES ═══════════
    with tabs[1]:
        st.markdown("""<div class="code-ref"><strong>AASHTO Art. 5.9.5:</strong>
        Prestress losses calculated per AASHTO LRFD.
        Immediate losses: friction (5.9.5.2), anchorage set (5.9.5.2.1), elastic shortening (5.9.5.2.3).
        Long-term losses: shrinkage (5.9.5.4.2), creep (5.9.5.4.3), relaxation (5.9.5.4.4).</div>""",
        unsafe_allow_html=True)

        c_l1, c_l2 = st.columns([2, 1])
        with c_l1:
            fpj = L["fpj"]
            loss_labels = ["Jacking\nfpj", "−Friction\nΔfpF", "−Anch.Slip\nΔfpA", "−Elast.Short.\nΔfpES",
                           "−Shrinkage\nΔfpSH", "−Creep\nΔfpCR", "−Relaxation\nΔfpR", "Effective\nfpe"]
            loss_vals = [fpj, -L["dfF"], -L["dfA"], -L["dfES"], -L["dfSH"], -L["dfCR"], -L["dfR"], 0]
            loss_colors = ["#3b82f6","#f59e0b","#f59e0b","#f59e0b","#ef4444","#ef4444","#ef4444","#10b981"]

            fig_loss = go.Figure(go.Waterfall(
                orientation="v",
                measure=["absolute","relative","relative","relative","relative","relative","relative","total"],
                x=loss_labels,
                y=loss_vals,
                text=[f"{abs(v):.1f}" for v in loss_vals],
                textfont=dict(family="JetBrains Mono", size=10, color="#f1f5f9"),
                increasing=dict(marker_color="#3b82f6"),
                decreasing=dict(marker_color="#ef4444"),
                totals=dict(marker_color="#10b981"),
                connector=dict(line=dict(color="#334155", width=1, dash="dot")),
            ))
            fig_loss.add_hline(y=0.60*fpu, line=dict(color="#f59e0b", dash="dash", width=1.5),
                                annotation_text=f"0.60·fpu = {0.60*fpu:.0f} MPa",
                                annotation_font=dict(color="#f59e0b", size=10))
            fig_loss.update_layout(
                template=ENG_TEMPLATE["layout"], height=380,
                title=dict(text="Prestress Loss Waterfall (MPa)", font=dict(color="#94a3b8", size=12)),
                yaxis_title="Prestress (MPa)",
                showlegend=False,
            )
            st.plotly_chart(fig_loss, use_container_width=True)

        with c_l2:
            st.markdown("**Loss Breakdown**")
            loss_items = [
                ("Friction",           L["dfF"],  "Imm.", "#3b82f6"),
                ("Anchorage Slip",     L["dfA"],  "Imm.", "#3b82f6"),
                ("Elastic Shortening", L["dfES"], "Imm.", "#06b6d4"),
                ("Shrinkage",          L["dfSH"], "L-T",  "#ef4444"),
                ("Creep",              L["dfCR"], "L-T",  "#ef4444"),
                ("Relaxation",         L["dfR"],  "L-T",  "#f59e0b"),
            ]
            total = sum(v for _, v, _, _ in loss_items)
            for name, val, typ, clr in loss_items:
                pct = val / fpj * 100
                bar_w = int(pct / (total/fpj*100) * 100)
                st.markdown(f"""<div style="margin-bottom:0.5rem;">
                    <div style="display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-size:0.72rem;">
                        <span style="color:#94a3b8;">{name}</span>
                        <span style="color:#f1f5f9;">{val:.1f} MPa <span style="color:#64748b;">({pct:.1f}%)</span></span>
                    </div>
                    <div style="height:5px;background:#1e293b;border-radius:3px;margin-top:3px;">
                        <div style="width:{bar_w}%;height:100%;background:{clr};border-radius:3px;opacity:0.8;"></div>
                    </div>
                </div>""", unsafe_allow_html=True)

            st.divider()
            st.markdown(f"""<div style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;">
            <div style="color:#64748b;">Total loss: <span style="color:#fca5a5;">{total:.1f} MPa ({total/fpj*100:.1f}%)</span></div>
            <div style="color:#64748b;margin-top:4px;">Immediate: <span style="color:#93c5fd;">{L['delta_imm']:.1f} MPa</span></div>
            <div style="color:#64748b;">Long-term:  <span style="color:#fca5a5;">{L['delta_lt']:.1f} MPa</span></div>
            <div style="color:#64748b;margin-top:6px;">fpe = <span style="color:#6ee7b7;">{L['fpe']:.1f} MPa</span></div>
            </div>""", unsafe_allow_html=True)

    # ═══════════ TAB 3 — STRESS VERIFICATION ═══════════
    with tabs[2]:
        st.markdown("""<div class="code-ref">
        <strong>AASHTO 5.9.4.1.1:</strong> At Transfer — Compression limit f = −0.60·f'ci | Tension limit = +0.25√f'ci (MPa)<br>
        <strong>AASHTO 5.9.4.2.1:</strong> At Service — Compression limit f = −0.60·f'c | Tension limit = +0.50√f'c (MPa)
        </div>""", unsafe_allow_html=True)

        c_s1, c_s2 = st.columns([3, 1])
        with c_s1:
            fig_str = make_subplots(rows=2, cols=1, row_heights=[0.5, 0.5],
                                     subplot_titles=("At Transfer — Fiber Stress", "At Service — Fiber Stress"),
                                     vertical_spacing=0.18)
            # Transfer
            fig_str.add_trace(go.Scatter(x=R["x"], y=R["tr_top"], name="Transfer Top",
                line=dict(color="#3b82f6", width=2)), row=1, col=1)
            fig_str.add_hline(y=R["lim_tr_c"], row=1, col=1,
                line=dict(color="#ef4444", dash="dash", width=1.5),
                annotation_text=f"Comp. limit = {R['lim_tr_c']:.2f} MPa",
                annotation_font=dict(color="#ef4444", size=10))
            fig_str.add_hline(y=R["lim_tr_t"], row=1, col=1,
                line=dict(color="#10b981", dash="dash", width=1.5),
                annotation_text=f"Tens. limit = +{R['lim_tr_t']:.2f} MPa",
                annotation_font=dict(color="#10b981", size=10))
            # Add shaded bands
            fig_str.add_hrect(y0=R["lim_tr_c"], y1=R["lim_tr_c"]-5, row=1, col=1,
                fillcolor="rgba(239,68,68,0.06)", line_width=0)
            fig_str.add_hrect(y0=R["lim_tr_t"], y1=R["lim_tr_t"]+5, row=1, col=1,
                fillcolor="rgba(239,68,68,0.06)", line_width=0)
            # Service
            fig_str.add_trace(go.Scatter(x=R["x"], y=R["sv1_top"], name="Service Top",
                line=dict(color="#06b6d4", width=2)), row=2, col=1)
            fig_str.add_hline(y=R["lim_sv_ct"], row=2, col=1,
                line=dict(color="#ef4444", dash="dash", width=1.5),
                annotation_text=f"Comp. limit = {R['lim_sv_ct']:.2f} MPa",
                annotation_font=dict(color="#ef4444", size=10))
            fig_str.add_hline(y=R["lim_sv_t"], row=2, col=1,
                line=dict(color="#10b981", dash="dash", width=1.5),
                annotation_text=f"Tens. limit = +{R['lim_sv_t']:.2f} MPa",
                annotation_font=dict(color="#10b981", size=10))
            fig_str.add_hrect(y0=R["lim_sv_ct"], y1=R["lim_sv_ct"]-5, row=2, col=1,
                fillcolor="rgba(239,68,68,0.06)", line_width=0)
            # Axis labels
            for row in [1, 2]:
                fig_str.update_yaxes(title_text="Stress (MPa)", row=row, col=1)
            fig_str.update_xaxes(title_text="Transverse Position x (m)", row=2, col=1)
            fig_str.update_layout(template=ENG_TEMPLATE["layout"], height=520,
                                   legend=dict(x=0.01, y=0.95))
            for ann in fig_str.layout.annotations:
                ann.font = dict(color="#94a3b8", size=11, family="JetBrains Mono")
            st.plotly_chart(fig_str, use_container_width=True)

        with c_s2:
            st.markdown("**Allowable Stress Summary**")
            lims = [
                ("Transfer Comp.", f"{R['lim_tr_c']:.2f}", "MPa", "−0.60·f'ci", "#ef4444"),
                ("Transfer Tens.", f"+{R['lim_tr_t']:.2f}", "MPa", "+0.25√f'ci", "#10b981"),
                ("Service Comp.",  f"{R['lim_sv_ct']:.2f}", "MPa", "−0.60·f'c", "#ef4444"),
                ("Service Tens.",  f"+{R['lim_sv_t']:.2f}", "MPa", "+0.50√f'c", "#10b981"),
            ]
            for name, val, unit, ref, clr in lims:
                st.markdown(f"""<div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid {clr};
                border-radius:4px;padding:0.55rem 0.8rem;margin-bottom:0.5rem;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#64748b;">{name}</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;color:{clr};">
                    {val} <span style="font-size:0.72rem;color:#64748b;">{unit}</span></div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:#475569;">{ref}</div>
                </div>""", unsafe_allow_html=True)

    # ═══════════ TAB 4 — STRENGTH ═══════════
    with tabs[3]:
        st.markdown("""<div class="code-ref">
        <strong>AASHTO 5.7.3.2.2:</strong> Flexural Strength  φMn ≥ Mu  (φ = {:.2f})<br>
        <strong>AASHTO 5.8.3.3:</strong>  Shear Strength      φVn ≥ Vu  (φ = {:.2f}) — Simplified Procedure
        </div>""".format(st.session_state.phi_flex, st.session_state.phi_shear), unsafe_allow_html=True)

        c_st1, c_st2 = st.columns(2)
        with c_st1:
            fig_mn = go.Figure()
            fig_mn.add_trace(go.Scatter(x=R["x"], y=R["phi_Mn_pos"]/1000, name="φMn (+)",
                fill="tonexty", fillcolor="rgba(16,185,129,0.08)",
                line=dict(color="#10b981", width=2.5)))
            fig_mn.add_trace(go.Scatter(x=R["x"], y=R["phi_Mn_neg"]/1000, name="φMn (−)",
                fill="tonexty", fillcolor="rgba(16,185,129,0.08)",
                line=dict(color="#10b981", width=2.5, dash="dot")))
            fig_mn.add_trace(go.Scatter(x=R["x"], y=R["mu"]/1000, name="Mu (factored)",
                line=dict(color="#ef4444", width=2.5)))
            fig_mn.add_trace(go.Scatter(x=R["x"], y=-R["mu"]/1000, name="−Mu",
                line=dict(color="#ef4444", width=1.5, dash="dot"), showlegend=False))
            fig_mn.add_hline(y=0, line=dict(color="#334155", width=1))
            fig_mn.update_layout(template=ENG_TEMPLATE["layout"], height=340,
                title=dict(text="Moment: Demand vs. Capacity (kNm/m)",
                           font=dict(color="#94a3b8", size=12)),
                yaxis_title="Moment (kNm/m)", xaxis_title="x (m)",
                legend=dict(x=0.01, y=0.99))
            st.plotly_chart(fig_mn, use_container_width=True)

        with c_st2:
            fig_vn = go.Figure()
            fig_vn.add_trace(go.Scatter(x=R["x"], y=R["phi_Vn"], name="φVn capacity",
                fill="tozeroy", fillcolor="rgba(16,185,129,0.08)",
                line=dict(color="#10b981", width=2.5)))
            fig_vn.add_trace(go.Scatter(x=R["x"], y=R["vu"], name="Vu demand",
                line=dict(color="#f59e0b", width=2.5)))
            fig_vn.update_layout(template=ENG_TEMPLATE["layout"], height=340,
                title=dict(text="Shear: Demand vs. Capacity (kN/m)",
                           font=dict(color="#94a3b8", size=12)),
                yaxis_title="Shear (kN/m)", xaxis_title="x (m)",
                legend=dict(x=0.01, y=0.99))
            st.plotly_chart(fig_vn, use_container_width=True)

        # DCR Distribution Chart
        st.markdown("**Demand / Capacity Ratio — Continuous Profile**")
        mid = np.argmax(R["mu"])
        dcr_m = np.abs(R["mu"]) / np.abs(R["phi_Mn_pos"])
        dcr_v = R["vu"] / R["phi_Vn"]
        fig_dcr = go.Figure()
        fig_dcr.add_trace(go.Scatter(x=R["x"], y=dcr_m, name="Flexure DCR",
            line=dict(color="#3b82f6", width=2),
            fill="tozeroy", fillcolor="rgba(59,130,246,0.08)"))
        fig_dcr.add_trace(go.Scatter(x=R["x"], y=dcr_v, name="Shear DCR",
            line=dict(color="#a855f7", width=2),
            fill="tozeroy", fillcolor="rgba(168,85,247,0.08)"))
        fig_dcr.add_hline(y=1.0, line=dict(color="#ef4444", dash="dash", width=2),
                          annotation_text="DCR = 1.0 LIMIT",
                          annotation_font=dict(color="#ef4444", size=10))
        fig_dcr.add_hline(y=0.80, line=dict(color="#f59e0b", dash="dot", width=1),
                          annotation_text="DCR = 0.80",
                          annotation_font=dict(color="#f59e0b", size=10))
        fig_dcr.add_hrect(y0=0, y1=0.80, fillcolor="rgba(16,185,129,0.05)", line_width=0)
        fig_dcr.add_hrect(y0=0.80, y1=1.0, fillcolor="rgba(245,158,11,0.05)", line_width=0)
        fig_dcr.add_hrect(y0=1.0, y1=1.5,  fillcolor="rgba(239,68,68,0.05)",  line_width=0)
        fig_dcr.update_layout(template=ENG_TEMPLATE["layout"], height=280,
            yaxis_title="DCR", xaxis_title="x (m)",
            legend=dict(x=0.01, y=0.99))
        st.plotly_chart(fig_dcr, use_container_width=True)

    # ═══════════ TAB 5 — DCR SUMMARY ═══════════
    with tabs[4]:
        col_tb, col_stat = st.columns([3, 1])
        with col_tb:
            st.markdown("**Design Check Summary — Critical Stations**")
            sta_x = df_ld["x (m)"].values
            rows = []
            for sx in sta_x:
                idx = np.abs(R["x"] - sx).argmin()
                t_s    = R["t"][idx] * 1000
                m_dem  = abs(R["mu"][idx])
                m_cap  = abs(R["phi_Mn_pos"][idx])
                v_dem  = abs(R["vu"][idx])
                v_cap  = abs(R["phi_Vn"][idx])
                dcr_m  = m_dem / m_cap if m_cap > 0 else 999
                dcr_v  = v_dem / v_cap if v_cap > 0 else 999
                status = "✅ PASS" if (dcr_m <= 1.0 and dcr_v <= 1.0) else "❌ FAIL"
                rows.append({
                    "Station x (m)":  f"{sx:.2f}",
                    "t (mm)":         f"{t_s:.1f}",
                    "Mu (kNm/m)":     f"{m_dem:.2f}",
                    "φMn (kNm/m)":    f"{m_cap/1000:.2f}",
                    "Flex DCR":       f"{dcr_m:.3f}",
                    "Vu (kN/m)":      f"{v_dem:.2f}",
                    "φVn (kN/m)":     f"{v_cap:.2f}",
                    "Shear DCR":      f"{dcr_v:.3f}",
                    "Status":         status,
                })
            df_res = pd.DataFrame(rows)
            styled = dcr_style(df_res, "Flex DCR")
            styled = dcr_style(styled, "Shear DCR")
            st.dataframe(styled, use_container_width=True, hide_index=True)

        with col_stat:
            st.markdown("**Global Check**")
            pass_all = all("PASS" in r["Status"] for r in rows)
            max_dcr_m = max(float(r["Flex DCR"]) for r in rows)
            max_dcr_v = max(float(r["Shear DCR"]) for r in rows)

            color_m = "#6ee7b7" if max_dcr_m <= 0.80 else ("#fcd34d" if max_dcr_m <= 1.0 else "#fca5a5")
            color_v = "#6ee7b7" if max_dcr_v <= 0.80 else ("#fcd34d" if max_dcr_v <= 1.0 else "#fca5a5")

            st.markdown(f"""<div style="background:#0f172a;border:1px solid #1e293b;
            border-radius:8px;padding:1.2rem;margin-bottom:0.7rem;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#64748b;text-transform:uppercase;">
            Max Flexure DCR</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:2rem;font-weight:800;color:{color_m};">
            {max_dcr_m:.3f}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#475569;">φMn = {st.session_state.phi_flex:.2f}</div>
            </div>""", unsafe_allow_html=True)

            st.markdown(f"""<div style="background:#0f172a;border:1px solid #1e293b;
            border-radius:8px;padding:1.2rem;margin-bottom:0.7rem;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#64748b;text-transform:uppercase;">
            Max Shear DCR</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:2rem;font-weight:800;color:{color_v};">
            {max_dcr_v:.3f}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#475569;">φVn = {st.session_state.phi_shear:.2f}</div>
            </div>""", unsafe_allow_html=True)

            overall_color = "#6ee7b7" if pass_all else "#fca5a5"
            overall_txt   = "ALL CHECKS PASS" if pass_all else "SECTION FAILS"
            st.markdown(f"""<div style="background:#0f172a;border:2px solid {overall_color};
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;font-weight:800;
            color:{overall_color};letter-spacing:0.05em;">{overall_txt}</div>
            </div>""", unsafe_allow_html=True)

            st.markdown("""<div class="code-ref" style="margin-top:1rem;">
            <strong>Color codes:</strong><br>
            🟢 DCR ≤ 0.80 — Adequate<br>
            🟡 0.80 < DCR ≤ 1.0 — Marginal<br>
            🔴 DCR > 1.0 — OVERSTRESSED
            </div>""", unsafe_allow_html=True)

    # ═══════════ TAB 6 — DESIGN REPORT ═══════════
    with tabs[5]:
        st.markdown('<div class="section-label">CALCULATION SUMMARY REPORT</div>', unsafe_allow_html=True)

        c_r1, c_r2 = st.columns([2, 1])
        with c_r1:
            st.markdown(f"""<div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;
            padding:1.5rem;font-family:'JetBrains Mono',monospace;">
            <div style="color:#06b6d4;font-size:1.1rem;font-weight:700;border-bottom:1px solid #1e293b;padding-bottom:0.5rem;margin-bottom:1rem;">
            CALCULATION SHEET — {st.session_state.doc_no}</div>
            <div style="color:#94a3b8;font-size:0.78rem;line-height:2;">
            <b style="color:#e2e8f0;">Project:</b>     {st.session_state.proj_name}<br>
            <b style="color:#e2e8f0;">Element:</b>     PSC Box Girder — Top Flange (Transverse)<br>
            <b style="color:#e2e8f0;">Method:</b>      AASHTO LRFD Strip Method, 1.0 m strip<br>
            <b style="color:#e2e8f0;">Code:</b>        AASHTO LRFD Bridge Design Spec., 9th Ed.<br>
            <b style="color:#e2e8f0;">Designed by:</b> {st.session_state.eng_name}<br>
            <b style="color:#e2e8f0;">Checked by:</b>  {st.session_state.chk_name}<br>
            <b style="color:#e2e8f0;">Date:</b>        {datetime.date.today().strftime('%d %B %Y')}<br>
            </div>
            <div style="color:#06b6d4;margin-top:1rem;font-size:0.9rem;font-weight:700;">MATERIAL PARAMETERS</div>
            <div style="color:#94a3b8;font-size:0.75rem;line-height:1.9;">
            f'c = {fc:.0f} MPa  |  f'ci = {fci:.0f} MPa  |  fpu = {fpu:.0f} MPa  |  fpy = {fpy:.0f} MPa<br>
            Aps/strand = {aps_strand:.0f} mm²  |  Duct dia = {duct_dia_mm:.0f} mm<br>
            Ep = {L['Ep']:.0f} MPa  |  Ec = {L['Ec']:.0f} MPa  |  Eci = {L['Eci']:.0f} MPa<br>
            </div>
            <div style="color:#06b6d4;margin-top:0.8rem;font-size:0.9rem;font-weight:700;">PRESTRESS RESULTS</div>
            <div style="color:#94a3b8;font-size:0.75rem;line-height:1.9;">
            fpj = {L['fpj']:.1f} MPa  ({fpi_ratio:.1%} × fpu)<br>
            Total Aps = {L['Aps']*1e6:.0f} mm²/m  ({int(num_tendon)} tn × {int(n_strands)} str)<br>
            Pi  = {L['Pi']:.1f} kN/m  (after imm. losses)<br>
            Pe  = {L['Pe']:.1f} kN/m  (after all losses)<br>
            fpe = {L['fpe']:.1f} MPa  ({L['fpe']/fpu*100:.1f}% of fpu)<br>
            Total Loss = {L['total_loss_pct']:.2f}% of fpj<br>
            </div>
            <div style="color:#06b6d4;margin-top:0.8rem;font-size:0.9rem;font-weight:700;">DESIGN CHECKS</div>
            <div style="color:#94a3b8;font-size:0.75rem;line-height:1.9;">
            Comp. limit (Transfer) = {R['lim_tr_c']:.3f} MPa  (AASHTO 5.9.4.1.1)<br>
            Tens.  limit (Transfer) = +{R['lim_tr_t']:.3f} MPa  (AASHTO 5.9.4.1.2)<br>
            Comp. limit (Service)  = {R['lim_sv_ct']:.3f} MPa  (AASHTO 5.9.4.2.1)<br>
            Tens.  limit (Service)  = +{R['lim_sv_t']:.3f} MPa  (AASHTO 5.9.4.2.2)<br>
            φMn capacity (peak) = {max(R['phi_Mn_pos'])/1000:.3f} kNm/m  (φ = {st.session_state.phi_flex:.2f})<br>
            φVn capacity (peak) = {max(R['phi_Vn']):.3f} kN/m   (φ = {st.session_state.phi_shear:.2f})<br>
            </div>
            </div>""", unsafe_allow_html=True)

        with c_r2:
            st.markdown("**AASHTO Article References**")
            refs = [
                ("5.4.2.1",  "Concrete compressive strength"),
                ("5.4.4.1",  "Prestressing steel — fpu"),
                ("5.7.1.1",  "Strip method for slabs"),
                ("5.7.3.2",  "Flexural resistance φMn"),
                ("5.8.3.3",  "Shear — simplified procedure"),
                ("5.9.3",    "Jacking stress limits"),
                ("5.9.4.1",  "Stress limits at transfer"),
                ("5.9.4.2",  "Stress limits at service"),
                ("5.9.5.2",  "Immediate losses"),
                ("5.9.5.4",  "Long-term losses"),
                ("3.6.1.2",  "HL-93 vehicular live load"),
                ("3.4.1",    "Load combinations & factors"),
            ]
            for art, desc in refs:
                st.markdown(f"""<div style="display:flex;gap:0.8rem;padding:0.3rem 0;
                border-bottom:1px solid #1e293b;">
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:#3b82f6;
                white-space:nowrap;min-width:50px;">Art. {art}</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:#64748b;">{desc}</span>
                </div>""", unsafe_allow_html=True)

except Exception as e:
    st.error(f"⚠️  Calculation error: {e}")
    st.exception(e)

"""
PSC Box Girder — Top Flange Transverse Design  (v6 Clean Light Theme)
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
# 1.  PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="PSC Box Girder Design | AASHTO LRFD",
    page_icon="🏗️",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# 2.  CUSTOM CSS — Light Blue Engineering Theme
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
    --sb:     #1e3a5f;
    --sb2:    #162d49;
    --bg:     #e6eff7;
    --card:   #ffffff;
    --alt:    #f4f8fc;
    --brd:    #c8daea;
    --brd2:   #dce8f0;
    --blue:   #1d6fb8;
    --cyan:   #0284c7;
    --green:  #059669;
    --amber:  #b45309;
    --red:    #b91c1c;
    --navy:   #0f2744;
    --txt:    #1a2e42;
    --txt2:   #3d5470;
    --txt3:   #607898;
    --blu-lt: #dbeafe;
    --grn-lt: #dcfce7;
    --amb-lt: #fef3c7;
    --red-lt: #fee2e2;
    --mono:   'IBM Plex Mono', monospace;
    --sans:   'Plus Jakarta Sans', sans-serif;
    --r:      10px;
    --sh:     0 1px 4px rgba(15,39,68,.09);
    --sh2:    0 2px 10px rgba(15,39,68,.12);
}

html, body, [class*="css"]           { font-family: var(--sans); }
.stApp                               { background: var(--bg) !important; }
.block-container                     { padding: 1.5rem 2rem 3rem !important;
                                       max-width: 1560px !important; }

/* ── FIX 1: Hide sidebar collapse/expand button entirely ── */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarExpandButton"],
[data-testid="collapsedControl"],
button[kind="header"]                { display: none !important; }

/* ── SIDEBAR shell ── */
section[data-testid="stSidebar"]     { background: linear-gradient(180deg, var(--sb) 0%, var(--sb2) 100%) !important;
                                       border-right: 2px solid rgba(255,255,255,.07); }
section[data-testid="stSidebar"] > div { padding-top: 1rem !important; }

/* Sidebar headings */
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #e2ecf6 !important; font-family: var(--sans) !important;
    font-size: .93rem !important; font-weight: 700 !important;
    padding-bottom: .5rem; border-bottom: 1px solid rgba(255,255,255,.12);
    margin-bottom: .8rem;
}

/* Sidebar labels */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stWidgetLabel p {
    color: #a8c4db !important; font-family: var(--mono) !important; font-size: .73rem !important;
}

/* Sidebar small text */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] .stCaption p {
    color: #7fa4bf !important; font-size: .74rem !important;
}

/* ── FIX 2: Sidebar expanders — white background removed ── */
section[data-testid="stSidebar"] .stExpander {
    background: rgba(255,255,255,.07) !important;
    border: 1px solid rgba(255,255,255,.13) !important;
    border-radius: 8px !important; margin-bottom: 5px;
}
section[data-testid="stSidebar"] details {
    background: transparent !important;
}
section[data-testid="stSidebar"] details > summary {
    background: transparent !important;
    color: #c8dff0 !important; font-family: var(--sans) !important;
    font-size: .82rem !important; font-weight: 600 !important;
    padding: .5rem .7rem !important; list-style: none;
}
section[data-testid="stSidebar"] details > summary:hover {
    color: #ffffff !important;
}
/* arrow icon in expander */
section[data-testid="stSidebar"] .stExpander svg { fill: #7fa4bf !important; }

/* Sidebar text inputs */
section[data-testid="stSidebar"] input[type="number"],
section[data-testid="stSidebar"] input[type="text"] {
    background: rgba(255,255,255,.10) !important;
    border: 1px solid rgba(255,255,255,.18) !important;
    color: #f0f6fc !important; border-radius: 6px !important;
    font-family: var(--mono) !important; font-size: .81rem !important;
}
section[data-testid="stSidebar"] input:focus {
    border-color: #60a5fa !important;
    box-shadow: 0 0 0 2px rgba(96,165,250,.25) !important; outline: none !important;
}

/* ── FIX 3: Sidebar +/- step buttons — visible & styled ── */
section[data-testid="stSidebar"] button[data-testid="stNumberInputStepUp"],
section[data-testid="stSidebar"] button[data-testid="stNumberInputStepDown"] {
    background: rgba(255,255,255,.20) !important;
    border: 1px solid rgba(255,255,255,.32) !important;
    color: #e8f2fb !important; border-radius: 5px !important;
    min-width: 28px !important; opacity: 1 !important;
    transition: background .15s;
}
section[data-testid="stSidebar"] button[data-testid="stNumberInputStepUp"]:hover,
section[data-testid="stSidebar"] button[data-testid="stNumberInputStepDown"]:hover {
    background: rgba(255,255,255,.35) !important;
}
section[data-testid="stSidebar"] button[data-testid="stNumberInputStepUp"] p,
section[data-testid="stSidebar"] button[data-testid="stNumberInputStepUp"] svg,
section[data-testid="stSidebar"] button[data-testid="stNumberInputStepDown"] p,
section[data-testid="stSidebar"] button[data-testid="stNumberInputStepDown"] svg {
    color: #e8f2fb !important; fill: #e8f2fb !important; opacity: 1 !important;
}

/* Sidebar selectbox */
section[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255,255,255,.10) !important;
    border: 1px solid rgba(255,255,255,.18) !important;
    color: #f0f6fc !important; border-radius: 6px !important;
}

/* Sidebar slider track colour */
section[data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"] {
    background: #60a5fa !important; border-color: #60a5fa !important;
}

/* Sidebar divider */
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.12) !important; }

/* ═══ MAIN AREA ═══ */
.eng-header {
    background: linear-gradient(135deg, var(--navy) 0%, #1a3d6e 60%, #155575 100%);
    border-radius: var(--r); padding: 1.45rem 2rem;
    margin-bottom: .9rem; box-shadow: var(--sh2);
    position: relative; overflow: hidden;
}
.eng-header::after {
    content:''; position:absolute; right:-50px; top:-50px;
    width:220px; height:220px;
    background: radial-gradient(circle, rgba(255,255,255,.05) 0%, transparent 65%);
    border-radius:50%;
}
.eng-header-title {
    font-family: var(--sans); font-size:1.6rem; font-weight:800;
    color:#ffffff; margin:0 0 .25rem; letter-spacing:-.02em;
}
.eng-header-sub { font-family:var(--mono); font-size:.69rem; color:#93c5fd; letter-spacing:.06em; }
.eng-badge {
    display:inline-block; background:rgba(255,255,255,.14);
    border:1px solid rgba(255,255,255,.22); color:#e0f2fe;
    font-family:var(--mono); font-size:.66rem;
    padding:2px 9px; border-radius:20px; margin:7px 5px 0 0;
}

.meta-bar {
    background:var(--card); border:1px solid var(--brd); border-radius:8px;
    padding:.55rem 1.2rem; margin-bottom:1.1rem;
    display:flex; gap:1.8rem; flex-wrap:wrap;
    box-shadow:var(--sh); font-family:var(--mono); font-size:.7rem; color:var(--txt3);
}
.meta-bar span { color:var(--txt); font-weight:600; }

.sec-lbl {
    font-family:var(--mono); font-size:.63rem; font-weight:600; color:var(--cyan);
    letter-spacing:.12em; text-transform:uppercase;
    border-left:3px solid var(--cyan); padding-left:.6rem; margin:1.1rem 0 .65rem;
}

/* Material property cards */
.mat-grid { display:grid; grid-template-columns:repeat(8,1fr); gap:.55rem; margin-bottom:1.1rem; }
.mat-card {
    background:var(--card); border:1px solid var(--brd); border-top:3px solid;
    border-radius:var(--r); padding:.7rem .8rem; box-shadow:var(--sh);
}
.mat-card.cb { border-top-color:var(--blue); }
.mat-card.cc { border-top-color:var(--cyan); }
.mat-card.ca { border-top-color:var(--amber);}
.mat-card.cg { border-top-color:var(--green);}
.ml { font-family:var(--mono); font-size:.6rem; color:var(--txt3); text-transform:uppercase; letter-spacing:.07em; margin-bottom:.22rem; }
.mv { font-family:var(--mono); font-size:1.12rem; font-weight:700; color:var(--txt); }
.mu { font-size:.65rem; color:var(--txt3); margin-left:2px; }
.mr { font-family:var(--mono); font-size:.59rem; color:var(--txt3); margin-top:2px; }

/* KPI row */
.kpi-row { display:grid; grid-template-columns:repeat(5,1fr); gap:.65rem; margin-bottom:.9rem; }
.kpi-card {
    background:var(--card); border:1px solid var(--brd); border-radius:var(--r);
    padding:.9rem 1rem; box-shadow:var(--sh); position:relative;
}
.kl { font-family:var(--mono); font-size:.61rem; color:var(--txt3); text-transform:uppercase; letter-spacing:.07em; }
.kv { font-family:var(--mono); font-size:1.18rem; font-weight:700; color:var(--blue); margin:.22rem 0 .1rem; }
.ks { font-family:var(--mono); font-size:.59rem; color:var(--txt3); }
.kr { position:absolute; top:7px; right:9px; font-family:var(--mono); font-size:.57rem; color:#bcd0e0; }

/* Loss strip */
.loss-row { display:grid; grid-template-columns:repeat(6,1fr); gap:.55rem; margin-bottom:.9rem; }
.loss-card {
    background:var(--alt); border:1px solid var(--brd2); border-radius:8px;
    padding:.65rem .75rem; text-align:center; box-shadow:var(--sh);
}
.ll { font-family:var(--mono); font-size:.59rem; color:var(--txt3); text-transform:uppercase; }
.lv { font-family:var(--mono); font-size:1.05rem; font-weight:700; color:var(--amber); }
.lp { font-family:var(--mono); font-size:.61rem; color:var(--txt3); }

/* Code-ref box */
.code-ref {
    background:#eff6ff; border:1px solid #bfdbfe; border-left:3px solid var(--blue);
    border-radius:6px; padding:.5rem .95rem; margin:.55rem 0;
    font-family:var(--mono); font-size:.71rem; color:#1e3a5f; line-height:1.65;
}
.code-ref strong { color:var(--blue); }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap:3px; background:var(--card); padding:5px;
    border-radius:10px; border:1px solid var(--brd); box-shadow:var(--sh);
}
.stTabs [data-baseweb="tab"] {
    border-radius:7px; padding:7px 16px; background:transparent;
    color:var(--txt3); font-family:var(--mono); font-size:.76rem; font-weight:600;
    border:none !important; transition:all .15s;
}
.stTabs [aria-selected="true"]    { background:var(--navy) !important; color:#fff !important; }
.stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) { background:var(--blu-lt) !important; color:var(--blue) !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top:1rem; }

/* DataFrames */
div[data-testid="stDataFrame"]    { border:1px solid var(--brd) !important; border-radius:8px; overflow:hidden; box-shadow:var(--sh); }

/* Bordered containers */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background:var(--card) !important; border:1px solid var(--brd) !important;
    border-radius:var(--r) !important; box-shadow:var(--sh) !important;
}

/* Main area number input +/- */
button[data-testid="stNumberInputStepUp"],
button[data-testid="stNumberInputStepDown"] {
    background:#f1f5f9 !important; border:1px solid #cbd5e1 !important;
    color:var(--txt) !important; opacity:1 !important;
}
button[data-testid="stNumberInputStepUp"]:hover,
button[data-testid="stNumberInputStepDown"]:hover  { background:#e2e8f0 !important; }
button[data-testid="stNumberInputStepUp"] svg,
button[data-testid="stNumberInputStepDown"] svg    { fill:var(--txt2) !important; opacity:1 !important; }

/* Metric */
div[data-testid="stMetricValue"] { color:var(--blue) !important; font-family:var(--mono) !important; font-weight:700 !important; }
div[data-testid="stMetricLabel"] { font-family:var(--mono) !important; font-size:.71rem !important; color:var(--txt3) !important; }

hr { border-color:var(--brd2) !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 3.  PLOTLY LIGHT TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────
LT = go.layout.Template(layout=go.Layout(
    paper_bgcolor="#ffffff", plot_bgcolor="#f8fafc",
    font=dict(family="IBM Plex Mono, monospace", color="#475569", size=11),
    xaxis=dict(gridcolor="#e2e8f0", linecolor="#cbd5e1", zeroline=False, tickfont=dict(size=10, color="#64748b")),
    yaxis=dict(gridcolor="#e2e8f0", linecolor="#cbd5e1", zeroline=False, tickfont=dict(size=10, color="#64748b")),
    legend=dict(bgcolor="rgba(255,255,255,.9)", bordercolor="#e2e8f0", borderwidth=1, font=dict(size=10)),
    margin=dict(l=55, r=20, t=38, b=42),
    hoverlabel=dict(bgcolor="#1e293b", bordercolor="#334155",
                    font=dict(family="IBM Plex Mono", size=11, color="#f1f5f9")),
))

# ─────────────────────────────────────────────────────────────────────────────
# 4.  SESSION STATE  ← EXACT ORIGINAL
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_SCALARS = dict(
    width=12.0, cl_lweb=2.0, cl_rweb=10.0,
    fc=45.0, fci=36.0, fpu=1860.0, fpy_ratio=0.90,
    aps_strand=140.0, duct_dia_mm=70.0,
    num_tendon=1, n_strands=5,
    fpi_ratio=0.75,
    t0=3, RH=75, anch_slip_mm=6.0,
    phi_flex=1.00, phi_shear=0.90,
    proj_name="Box Girder Design", doc_no="CALC-STR-001",
    eng_name="Engineer Name", chk_name="Checker Name",
)

if "thk_src" not in st.session_state:
    st.session_state["thk_src"] = pd.DataFrame({"x (m)": [0.0, 6.0, 12.0], "t (m)": [0.25, 0.25, 0.25]})
if "tdn_src" not in st.session_state:
    st.session_state["tdn_src"] = pd.DataFrame({"x (m)": [0.0, 6.0, 12.0], "z_top (m)": [0.10, 0.10, 0.10]})
if "ld_src" not in st.session_state:
    st.session_state["ld_src"] = pd.DataFrame({
        "x (m)": [0.0, 6.0, 12.0], "M_DL (kNm/m)": [0.0, 0.0, 0.0], "V_DL (kN/m)": [0.0, 0.0, 0.0],
        "M_SDL (kNm/m)": [0.0, 0.0, 0.0], "V_SDL (kN/m)": [0.0, 0.0, 0.0],
        "M_LL (kNm/m)": [0.0, 0.0, 0.0], "V_LL (kN/m)": [0.0, 0.0, 0.0],
    })

for k, v in DEFAULT_SCALARS.items():
    if k not in st.session_state: st.session_state[k] = v

if "_tbl_ver" not in st.session_state: st.session_state["_tbl_ver"] = 0

# ─────────────────────────────────────────────────────────────────────────────
# 5.  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏗️ PARAMETER INPUTS")

    with st.expander("📐 Materials & Section", expanded=True):
        width       = st.number_input("Total Flange Width (m)", key="width")
        fc          = st.number_input("f'c Service (MPa)",      key="fc")
        fci         = st.number_input("f'ci Transfer (MPa)",    key="fci")
        fpu         = st.number_input("fpu (MPa)",              key="fpu")
        fpy_ratio   = st.selectbox("fpy/fpu", [0.90, 0.85],    key="fpy_ratio")
        aps_strand  = st.number_input("Aps per strand (mm²)",   key="aps_strand")
        duct_dia_mm = st.number_input("Duct diameter (mm)",     key="duct_dia_mm")

    with st.expander("🌐 Web Geometry", expanded=False):
        cl_lweb = st.number_input("L.Web CL (m)",  key="cl_lweb")
        cl_rweb = st.number_input("R.Web CL (m)",  key="cl_rweb")

    with st.expander("🔩 Prestressing Force", expanded=False):
        num_tendon = st.number_input("Tendons per 1m",     key="num_tendon")
        n_strands  = st.number_input("Strands per tendon", key="n_strands")
        fpi_ratio  = st.slider("Jacking fpi/fpu", 0.70, 0.80, key="fpi_ratio")

    with st.expander("📉 Loss & Resistance", expanded=False):
        t0           = st.number_input("Age Transfer (days)", key="t0")
        RH           = st.number_input("Humidity RH (%)",     key="RH")
        anch_slip_mm = st.number_input("Anch. Slip (mm)",     key="anch_slip_mm")
        phi_flex     = st.number_input("φ Flexure",           key="phi_flex")
        phi_shear    = st.number_input("φ Shear",             key="phi_shear")

    with st.expander("📄 Report Info", expanded=False):
        proj_name = st.text_input("Project Name", key="proj_name")
        doc_no    = st.text_input("Doc No.",       key="doc_no")
        eng_name  = st.text_input("Engineer",      key="eng_name")
        chk_name  = st.text_input("Checker",       key="chk_name")

    st.markdown(f"""<div style="font-family:'IBM Plex Mono',monospace;font-size:.62rem;
    color:rgba(255,255,255,.22);line-height:1.9;padding-top:.5rem;">
    AASHTO LRFD 9th Edition<br>Strip Method · 1.0 m transverse<br>
    {datetime.date.today().strftime('%d %b %Y')}</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 6.  LOGIC ENGINES  ← UNCHANGED FROM ORIGINAL
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
    Ec, Eci = 0.043*(wc**1.5)*math.sqrt(fc), 0.043*(wc**1.5)*math.sqrt(fci)
    fpj  = fpu * fpi_ratio
    dfF  = fpj * 0.02; dfA = 30.0; dfES = 40.0
    dfSH = 35.0; dfCR = 60.0; dfR = 20.0
    fpe  = fpj - (dfF + dfA + dfES + dfSH + dfCR + dfR)
    return {
        "Aps": Aps, "Pi": Aps*(fpj-dfF-dfA-dfES)*1e3, "Pe": Aps*fpe*1e3, "fpe": fpe,
        "fpj": fpj,
        "imm_loss_pct": (dfF+dfA+dfES)/fpj*100, "lt_loss_pct": (dfSH+dfCR+dfR)/fpj*100,
        "total_loss_pct": (fpj-fpe)/fpj*100,
        "delta_imm": (dfF+dfA+dfES), "delta_lt": (dfSH+dfCR+dfR),
        "dfF": dfF, "dfA": dfA, "dfES": dfES, "dfSH": dfSH, "dfCR": dfCR, "dfR": dfR,
        "Ec": Ec, "Eci": Eci, "Ep": Ep, "t_m": t_m, "z_m": z_m,
    }


def run_calc(dft, dfp, dfl, L):
    N = 200; x = np.linspace(0, st.session_state.width, N)
    t    = np.interp(x, dft["x (m)"], dft["t (m)"])
    z    = np.interp(x, dfp["x (m)"], dfp["z_top (m)"])
    yc   = t / 2.0; e = yc - z; Ag = 1.0 * t; Ig = 1.0 * t**3 / 12
    m_dl  = np.interp(x, dfl["x (m)"], dfl["M_DL (kNm/m)"])
    m_sdl = np.interp(x, dfl["x (m)"], dfl["M_SDL (kNm/m)"])
    m_ll  = np.interp(x, dfl["x (m)"], dfl["M_LL (kNm/m)"])
    ms1   = m_dl + m_sdl + m_ll
    mu    = 1.25 * m_dl + 1.5 * m_sdl + 1.75 * m_ll
    v_dl  = np.interp(x, dfl["x (m)"], dfl["V_DL (kN/m)"])
    vu    = 1.25 * np.abs(v_dl) + 1.75 * 10.0
    tr_top  = (-L["Pi"]/Ag/1000 + L["Pi"]*e*(t/2)/Ig/1000 - m_dl*(t/2)/Ig/1000)
    sv1_top = (-L["Pe"]/Ag/1000 + L["Pe"]*e*(t/2)/Ig/1000 - ms1*(t/2)/Ig/1000)
    phi_Mn  = st.session_state.phi_flex  * L["Aps"] * 1800 * (z - 0.05) * 1000
    phi_Vn  = st.session_state.phi_shear * 0.083 * 2 * math.sqrt(fc) * 1000 * 0.9 * z
    return {
        "x": x, "t": t, "z": z, "yc": yc, "e": e,
        "tr_top": tr_top, "sv1_top": sv1_top, "tr_bot": tr_top, "sv1_bot": sv1_top,
        "mu": mu, "phi_Mn_pos": phi_Mn, "phi_Mn_neg": -phi_Mn,
        "vu": vu, "phi_Vn": phi_Vn,
        "Pe": L["Pe"], "Pi": L["Pi"], "L": L, "Aps": L["Aps"],
        "lim_tr_c": -0.6*fci, "lim_tr_t": 0.25*math.sqrt(fci),
        "lim_sv_ct": -0.6*fc,  "lim_sv_t": 0.5*math.sqrt(fc),
    }


def dcr_style(obj, col):
    def _s(val):
        try: v = float(val)
        except: return ""
        if v <= 0.80: return "background-color:#dcfce7;color:#166534;font-weight:bold;"
        if v <= 1.00: return "background-color:#fef9c3;color:#713f12;font-weight:bold;"
        return "background-color:#fee2e2;color:#991b1b;font-weight:bold;"
    if isinstance(obj, pd.DataFrame): return obj.style.map(_s, subset=[col])
    return obj.map(_s, subset=[col])


# ─────────────────────────────────────────────────────────────────────────────
# 7.  HEADER + META BAR
# ─────────────────────────────────────────────────────────────────────────────
fpy = st.session_state.fpy_ratio * st.session_state.fpu

st.markdown(f"""
<div class="eng-header">
  <div class="eng-header-title">🏗️ PSC Box Girder — Top Flange Transverse Design</div>
  <div class="eng-header-sub">AASHTO LRFD BRIDGE DESIGN SPECIFICATIONS · 1.0 M TRANSVERSE STRIP · STRENGTH + SERVICE CHECKS</div>
  <div style="margin-top:.55rem;">
    <span class="eng-badge">AASHTO LRFD 9th Ed.</span>
    <span class="eng-badge">Art. 5.9 Prestress</span>
    <span class="eng-badge">Art. 5.7 Flexure</span>
    <span class="eng-badge">Art. 5.8 Shear</span>
    <span class="eng-badge">Art. 3.6 Live Load</span>
  </div>
</div>
<div class="meta-bar">
  <div>PROJECT <span>{st.session_state.proj_name}</span></div>
  <div>DOC NO. <span>{st.session_state.doc_no}</span></div>
  <div>DESIGNED <span>{st.session_state.eng_name}</span></div>
  <div>CHECKED <span>{st.session_state.chk_name}</span></div>
  <div>DATE <span>{datetime.date.today().strftime('%d %b %Y')}</span></div>
  <div>REV <span>A</span></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 8.  MATERIAL PROPERTY CARDS
# ─────────────────────────────────────────────────────────────────────────────
Ec_val = 0.043 * (2400**1.5) * math.sqrt(st.session_state.fc) / 1000
st.markdown('<div class="sec-lbl">Material Properties</div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="mat-grid">
  <div class="mat-card cb"><div class="ml">f'c Service</div>
    <div class="mv">{st.session_state.fc:.0f}<span class="mu">MPa</span></div>
    <div class="mr">AASHTO 5.4.2.1</div></div>
  <div class="mat-card cb"><div class="ml">f'ci Transfer</div>
    <div class="mv">{st.session_state.fci:.0f}<span class="mu">MPa</span></div>
    <div class="mr">AASHTO 5.9.4.1</div></div>
  <div class="mat-card cc"><div class="ml">fpu</div>
    <div class="mv">{st.session_state.fpu:.0f}<span class="mu">MPa</span></div>
    <div class="mr">ASTM A416</div></div>
  <div class="mat-card cc"><div class="ml">fpy</div>
    <div class="mv">{fpy:.0f}<span class="mu">MPa</span></div>
    <div class="mr">{st.session_state.fpy_ratio:.0%}·fpu</div></div>
  <div class="mat-card ca"><div class="ml">fpi (jack)</div>
    <div class="mv">{st.session_state.fpi_ratio*st.session_state.fpu:.0f}<span class="mu">MPa</span></div>
    <div class="mr">{st.session_state.fpi_ratio:.1%}·fpu</div></div>
  <div class="mat-card cg"><div class="ml">Ec</div>
    <div class="mv">{Ec_val:.1f}<span class="mu">GPa</span></div>
    <div class="mr">AASHTO 5.4.2.4</div></div>
  <div class="mat-card cg"><div class="ml">Ep</div>
    <div class="mv">197<span class="mu">GPa</span></div>
    <div class="mr">AASHTO 5.4.4.2</div></div>
  <div class="mat-card ca"><div class="ml">φ flex/shear</div>
    <div class="mv" style="font-size:.9rem;">{st.session_state.phi_flex:.2f}/{st.session_state.phi_shear:.2f}</div>
    <div class="mr">AASHTO 5.5.4.2</div></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 9.  DATA EDITORS  ← ORIGINAL
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-lbl">Station Data Inputs</div>', unsafe_allow_html=True)
_v = st.session_state["_tbl_ver"]
with st.container(border=True):
    st.markdown("#### 📐 Station Data Inputs")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption("📏 **Thickness t(x)**")
        df_thk = st.data_editor(st.session_state["thk_src"], num_rows="dynamic", key=f"ed_thk_{_v}", use_container_width=True)
    with c2:
        st.caption("🔩 **Tendon z(x)**")
        df_tdn = st.data_editor(st.session_state["tdn_src"], num_rows="dynamic", key=f"ed_tdn_{_v}", use_container_width=True)
    with c3:
        st.caption("📦 **Loads (kN, kNm)**")
        df_ld = st.data_editor(st.session_state["ld_src"], num_rows="dynamic", key=f"ed_ld_{_v}", use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# 10.  VALIDATION — friendly, no red banner
# ─────────────────────────────────────────────────────────────────────────────
def _valid(df, xcol, *vcols):
    try:
        if df is None or len(df) < 2: return False, "Need at least 2 rows"
        xs = pd.to_numeric(df[xcol], errors="coerce")
        if xs.isna().any(): return False, f"Non-numeric value in '{xcol}'"
        if not xs.is_monotonic_increasing: return False, "x must be ascending"
        for c in vcols:
            if c in df.columns and pd.to_numeric(df[c], errors="coerce").isna().any():
                return False, f"Non-numeric value in '{c}'"
        return True, "ok"
    except Exception as ex: return False, str(ex)

ok_t, mt = _valid(df_thk, "x (m)", "t (m)")
ok_p, mp = _valid(df_tdn, "x (m)", "z_top (m)")
ok_l, ml = _valid(df_ld,  "x (m)", "M_DL (kNm/m)")

if not (ok_t and ok_p and ok_l):
    reasons = []
    if not ok_t: reasons.append(f"Thickness table: {mt}")
    if not ok_p: reasons.append(f"Tendon table: {mp}")
    if not ok_l: reasons.append(f"Load table: {ml}")
    st.markdown(f"""
    <div style="background:#eff6ff;border:1px solid #bfdbfe;border-left:4px solid #2563eb;
    border-radius:10px;padding:1.3rem 1.5rem;margin-top:1rem;box-shadow:0 1px 4px rgba(15,39,68,.09);">
      <div style="font-family:'Plus Jakarta Sans',sans-serif;font-weight:700;color:#1e3a5f;
      font-size:.94rem;margin-bottom:.4rem;">⏳  กรุณากรอกข้อมูลในตารางให้ครบถ้วน…</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:.71rem;color:#1d4ed8;line-height:2;">
        {'<br>'.join(f'• {r}' for r in reasons)}
      </div>
      <div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:.77rem;color:#3b82f6;margin-top:.5rem;">
        Fill all cells with numeric values and at least 2 rows per table to run the analysis.
      </div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# 11.  RUN CALCULATIONS
# ─────────────────────────────────────────────────────────────────────────────
try:
    L = calc_losses(df_thk, df_tdn, fc, fci, fpu, fpi_ratio, aps_strand,
                    num_tendon, n_strands, duct_dia_mm, t0, RH, anch_slip_mm, width)
    R = run_calc(df_thk, df_tdn, df_ld, L)
except Exception as e:
    st.markdown(f"""
    <div style="background:#fff7ed;border:1px solid #fed7aa;border-left:4px solid #f97316;
    border-radius:10px;padding:1.2rem 1.5rem;margin-top:1rem;">
      <div style="font-family:'Plus Jakarta Sans',sans-serif;font-weight:700;color:#7c2d12;font-size:.91rem;">
        ⚠️ Calculation issue</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:.72rem;color:#9a3412;margin-top:.4rem;">{e}</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# 12.  KPI + LOSS STRIP
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-lbl">Prestress Analysis — Key Results</div>', unsafe_allow_html=True)

lc  = "#b91c1c" if R['L']['total_loss_pct'] > 20 else "#059669"
lbg = "#fee2e2" if R['L']['total_loss_pct'] > 20 else "#dcfce7"
lt2 = "#7f1d1d" if R['L']['total_loss_pct'] > 20 else "#14532d"

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card"><div class="kr">Art. 5.9.3</div>
    <div class="kl">Aps (1 m strip)</div>
    <div class="kv">{R['Aps']*1e6:.0f} <span style="font-size:.69rem;color:#94a3b8;">mm²/m</span></div>
    <div class="ks">{int(num_tendon)} tn × {int(n_strands)} str × {aps_strand:.0f} mm²</div></div>
  <div class="kpi-card"><div class="kr">Art. 5.9.5.2</div>
    <div class="kl">Pi — Initial Force</div>
    <div class="kv">{R['Pi']:.1f} <span style="font-size:.69rem;color:#94a3b8;">kN/m</span></div>
    <div class="ks">After Friction + Slip + ES</div></div>
  <div class="kpi-card"><div class="kr">Art. 5.9.5.4</div>
    <div class="kl">Pe — Effective Force</div>
    <div class="kv">{R['Pe']:.1f} <span style="font-size:.69rem;color:#94a3b8;">kN/m</span></div>
    <div class="ks">After all long-term losses</div></div>
  <div class="kpi-card"><div class="kr">AASHTO Table</div>
    <div class="kl">fpe — Eff. Stress</div>
    <div class="kv">{R['L']['fpe']:.0f} <span style="font-size:.69rem;color:#94a3b8;">MPa</span></div>
    <div class="ks">≤ 0.80·fpy = {0.80*fpy:.0f} MPa</div></div>
  <div class="kpi-card" style="background:{lbg};border-top:3px solid {lc};">
    <div class="kr" style="color:{lc};">Art. 5.9.5</div>
    <div class="kl" style="color:{lt2};">Total Prestress Loss</div>
    <div class="kv" style="color:{lc};">{R['L']['total_loss_pct']:.1f}<span style="font-size:.69rem;"> %</span></div>
    <div class="ks" style="color:{lt2};">Imm: {R['L']['imm_loss_pct']:.1f}%  ·  LT: {R['L']['lt_loss_pct']:.1f}%</div></div>
</div>
<div class="loss-row">
  <div class="loss-card"><div class="ll">Friction ΔfpF</div>
    <div class="lv">{R['L']['dfF']:.1f}</div>
    <div class="lp">MPa · {R['L']['dfF']/R['L']['fpj']*100:.1f}% fpj</div></div>
  <div class="loss-card"><div class="ll">Anch. Slip ΔfpA</div>
    <div class="lv">{R['L']['dfA']:.1f}</div>
    <div class="lp">MPa · {R['L']['dfA']/R['L']['fpj']*100:.1f}% fpj</div></div>
  <div class="loss-card"><div class="ll">El. Short. ΔfpES</div>
    <div class="lv">{R['L']['dfES']:.1f}</div>
    <div class="lp">MPa · {R['L']['dfES']/R['L']['fpj']*100:.1f}% fpj</div></div>
  <div class="loss-card"><div class="ll">Shrinkage ΔfpSH</div>
    <div class="lv">{R['L']['dfSH']:.1f}</div>
    <div class="lp">MPa · {R['L']['dfSH']/R['L']['fpj']*100:.1f}% fpj</div></div>
  <div class="loss-card"><div class="ll">Creep ΔfpCR</div>
    <div class="lv">{R['L']['dfCR']:.1f}</div>
    <div class="lp">MPa · {R['L']['dfCR']/R['L']['fpj']*100:.1f}% fpj</div></div>
  <div class="loss-card"><div class="ll">Relaxation ΔfpR</div>
    <div class="lv">{R['L']['dfR']:.1f}</div>
    <div class="lp">MPa · {R['L']['dfR']/R['L']['fpj']*100:.1f}% fpj</div></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 13.  ANALYSIS TABS
# ─────────────────────────────────────────────────────────────────────────────
tabs = st.tabs(["📐 Geometry", "📉 Losses", "🔬 Stress", "💪 Strength", "📋 Summary", "📄 Report"])

# ══ TAB 0 — GEOMETRY ════════════════════════════════════════════════
with tabs[0]:
    st.markdown("""<div class="code-ref"><strong>AASHTO Art. 5.7.1.1</strong> — Strip Method for Slab Analysis.
    Transverse 1.0 m strip treated as a continuous beam between webs.</div>""", unsafe_allow_html=True)
    cg1, cg2 = st.columns([3, 2])
    with cg1:
        fig = make_subplots(rows=2, cols=1, row_heights=[.5,.5],
            subplot_titles=("Slab Thickness Profile  t(x)", "Tendon CG Profile  z_top(x)"),
            vertical_spacing=.17)
        fig.add_trace(go.Scatter(
            x=np.concatenate([R["x"], R["x"][::-1]]),
            y=np.concatenate([np.zeros(len(R["x"])), -R["t"][::-1]*1000]),
            fill="toself", fillcolor="rgba(29,111,184,.10)",
            line=dict(color="#1d6fb8", width=1.5), name="Slab"), row=1, col=1)
        fig.add_trace(go.Scatter(x=R["x"], y=-R["t"]*1000,
            line=dict(color="#1d6fb8", width=2), showlegend=False), row=1, col=1)
        for xw, lbl in [(cl_lweb, "L.Web"), (cl_rweb, "R.Web")]:
            fig.add_vline(x=xw, line=dict(color="#d97706", width=1.5, dash="dash"),
                annotation_text=lbl, annotation_font_color="#d97706",
                annotation_font_size=10, row=1, col=1)
        fig.add_trace(go.Scatter(x=R["x"], y=-R["z"]*1000,
            line=dict(color="#dc2626", width=2.5), name="Tendon CG"), row=2, col=1)
        fig.add_trace(go.Scatter(x=R["x"], y=-R["e"]*1000,
            line=dict(color="#7c3aed", width=1.5, dash="dot"), name="Eccentricity e"), row=2, col=1)
        for r in [1,2]: fig.update_yaxes(title_text="Depth (mm)", row=r, col=1)
        fig.update_xaxes(title_text="Transverse Position x (m)", row=2, col=1)
        fig.update_layout(template=LT, height=460, legend=dict(x=.01, y=.46))
        for a in fig.layout.annotations:
            a.font = dict(color="#475569", size=11, family="IBM Plex Mono")
        st.plotly_chart(fig, use_container_width=True)
    with cg2:
        t_mid = float(np.interp(width/2, R["x"], R["t"]))
        z_mid = float(np.interp(width/2, R["x"], R["z"]))
        e_mid = t_mid/2 - z_mid
        Ag_m  = t_mid; Ig_m = t_mid**3/12; St_m = Ig_m/(t_mid/2)
        st.markdown("**Section Properties — Midspan**")
        st.dataframe(pd.DataFrame([
            ("h = t",   f"{t_mid*1000:.1f} mm",        "Slab thickness"),
            ("Ag",      f"{Ag_m*1e6:.0f} mm²/m",       "Gross area"),
            ("Ig",      f"{Ig_m*1e9:.3e} mm⁴/m",       "2nd moment of area"),
            ("St=Sb",   f"{St_m*1e6:.0f} mm³/m",       "Section modulus"),
            ("z_top",   f"{z_mid*1000:.1f} mm",         "Tendon depth"),
            ("e",       f"{e_mid*1000:.1f} mm",         "Eccentricity"),
            ("Duct ⌀",  f"{duct_dia_mm:.0f} mm",        "PT duct diameter"),
            ("PT ratio",f"{L['Aps']*1e6/(Ag_m*1e6)*100:.2f}%","Aps/Ag"),
        ], columns=["Parameter","Value","Description"]),
        use_container_width=True, hide_index=True, height=302)
        avg = L["Pe"]/(Ag_m*1000)
        ok_pp = avg >= 1.0
        st.markdown(f"""<div class="code-ref" style="border-left-color:{'#059669' if ok_pp else '#b91c1c'};">
        <strong>AASHTO 5.9.1.5</strong> — Min avg. precompression ≥ 1.0 MPa<br>
        Pe / Ag = {avg:.2f} MPa  {'✅ OK' if ok_pp else '❌ CHECK'}</div>""", unsafe_allow_html=True)

# ══ TAB 1 — LOSSES ══════════════════════════════════════════════════
with tabs[1]:
    st.markdown("""<div class="code-ref"><strong>AASHTO Art. 5.9.5:</strong>
    Immediate: friction (5.9.5.2), anchorage set (5.9.5.2.1), elastic shortening (5.9.5.2.3).
    Long-term: shrinkage (5.9.5.4.2), creep (5.9.5.4.3), relaxation (5.9.5.4.4).</div>""",
    unsafe_allow_html=True)
    cl1, cl2 = st.columns([2, 1])
    with cl1:
        fpj = L["fpj"]
        fig2 = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute","relative","relative","relative","relative","relative","relative","total"],
            x=["Jacking\nfpj","−Friction\nΔfpF","−Anch.Slip\nΔfpA","−El.Short.\nΔfpES",
               "−Shrinkage\nΔfpSH","−Creep\nΔfpCR","−Relax.\nΔfpR","Effective\nfpe"],
            y=[fpj,-L["dfF"],-L["dfA"],-L["dfES"],-L["dfSH"],-L["dfCR"],-L["dfR"],0],
            text=[f"{abs(v):.1f}" for v in [fpj,-L["dfF"],-L["dfA"],-L["dfES"],-L["dfSH"],-L["dfCR"],-L["dfR"],0]],
            textfont=dict(family="IBM Plex Mono",size=10,color="#1e293b"),
            increasing=dict(marker_color="#1d6fb8"),
            decreasing=dict(marker_color="#dc2626"),
            totals=dict(marker_color="#059669"),
            connector=dict(line=dict(color="#e2e8f0",width=1,dash="dot")),
        ))
        fig2.add_hline(y=0.6*fpu, line=dict(color="#d97706",dash="dash",width=1.5),
            annotation_text=f"0.60·fpu = {0.6*fpu:.0f} MPa",
            annotation_font=dict(color="#d97706",size=10))
        fig2.update_layout(template=LT, height=370, showlegend=False,
            title=dict(text="Prestress Loss Waterfall (MPa)",font=dict(color="#475569",size=12)),
            yaxis_title="Prestress (MPa)")
        st.plotly_chart(fig2, use_container_width=True)
    with cl2:
        st.markdown("**Loss Breakdown**")
        items = [("Friction",     L["dfF"], "#1d6fb8"),
                 ("Anch. Slip",   L["dfA"], "#1d6fb8"),
                 ("El. Short.",   L["dfES"],"#0284c7"),
                 ("Shrinkage",    L["dfSH"],"#dc2626"),
                 ("Creep",        L["dfCR"],"#dc2626"),
                 ("Relaxation",   L["dfR"], "#d97706")]
        total = sum(v for _,v,_ in items)
        for name, val, clr in items:
            pct = val/fpj*100
            w = max(4, int(pct/(total/fpj*100)*100))
            st.markdown(f"""<div style="margin-bottom:.45rem;">
            <div style="display:flex;justify-content:space-between;font-family:'IBM Plex Mono',monospace;font-size:.7rem;">
              <span style="color:#475569;">{name}</span>
              <span style="color:#1e293b;">{val:.1f} MPa <span style="color:#94a3b8;">({pct:.1f}%)</span></span>
            </div>
            <div style="height:5px;background:#e2e8f0;border-radius:3px;margin-top:3px;">
              <div style="width:{w}%;height:100%;background:{clr};border-radius:3px;"></div>
            </div></div>""", unsafe_allow_html=True)
        st.divider()
        st.markdown(f"""<div style="font-family:'IBM Plex Mono',monospace;font-size:.77rem;color:#475569;line-height:2;">
        Total: <b style="color:#b91c1c;">{total:.1f} MPa ({total/fpj*100:.1f}%)</b><br>
        Immediate: <b style="color:#1d6fb8;">{L['delta_imm']:.1f} MPa</b><br>
        Long-term: <b style="color:#dc2626;">{L['delta_lt']:.1f} MPa</b><br>
        fpe = <b style="color:#059669;">{L['fpe']:.1f} MPa</b>
        </div>""", unsafe_allow_html=True)

# ══ TAB 2 — STRESS ══════════════════════════════════════════════════
with tabs[2]:
    st.markdown("""<div class="code-ref">
    <strong>AASHTO 5.9.4.1.1:</strong> Transfer — Comp. ≤ −0.60·f'ci &nbsp;|&nbsp; Tens. ≤ +0.25√f'ci &nbsp;&nbsp;
    <strong>AASHTO 5.9.4.2.1:</strong> Service — Comp. ≤ −0.60·f'c &nbsp;|&nbsp; Tens. ≤ +0.50√f'c (MPa)
    </div>""", unsafe_allow_html=True)
    cs1, cs2 = st.columns([3, 1])
    with cs1:
        fig3 = make_subplots(rows=2, cols=1, row_heights=[.5,.5],
            subplot_titles=("At Transfer — Fiber Stress","At Service — Fiber Stress"),
            vertical_spacing=.17)
        for row, y_d, name, clr in [(1,R["tr_top"],"Transfer Top","#1d6fb8"),(2,R["sv1_top"],"Service Top","#0284c7")]:
            fig3.add_trace(go.Scatter(x=R["x"],y=y_d,name=name,
                line=dict(color=clr,width=2)), row=row, col=1)
        for row, yv, clr, txt in [
            (1,R["lim_tr_c"], "#dc2626",f"Comp. limit = {R['lim_tr_c']:.2f} MPa"),
            (1,R["lim_tr_t"], "#059669",f"Tens. limit = +{R['lim_tr_t']:.2f} MPa"),
            (2,R["lim_sv_ct"],"#dc2626",f"Comp. limit = {R['lim_sv_ct']:.2f} MPa"),
            (2,R["lim_sv_t"], "#059669",f"Tens. limit = +{R['lim_sv_t']:.2f} MPa"),
        ]:
            fig3.add_hline(y=yv, row=row, col=1,
                line=dict(color=clr,dash="dash",width=1.5),
                annotation_text=txt, annotation_font=dict(color=clr,size=9))
        for r in [1,2]: fig3.update_yaxes(title_text="Stress (MPa)",row=r,col=1)
        fig3.update_xaxes(title_text="x (m)",row=2,col=1)
        fig3.update_layout(template=LT,height=500,legend=dict(x=.01,y=.95))
        for a in fig3.layout.annotations:
            a.font=dict(color="#475569",size=11,family="IBM Plex Mono")
        st.plotly_chart(fig3, use_container_width=True)
    with cs2:
        st.markdown("**Allowable Stresses**")
        for name, val, ref, clr in [
            ("Transfer Comp.", f"{R['lim_tr_c']:.2f} MPa", "−0.60·f'ci","#dc2626"),
            ("Transfer Tens.", f"+{R['lim_tr_t']:.2f} MPa","+0.25√f'ci","#059669"),
            ("Service Comp.",  f"{R['lim_sv_ct']:.2f} MPa","−0.60·f'c", "#dc2626"),
            ("Service Tens.",  f"+{R['lim_sv_t']:.2f} MPa", "+0.50√f'c", "#059669"),
        ]:
            st.markdown(f"""<div style="background:#f8fafc;border:1px solid #e2e8f0;
            border-left:3px solid {clr};border-radius:6px;padding:.55rem .8rem;margin-bottom:.5rem;">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:.63rem;color:#64748b;">{name}</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:1.05rem;font-weight:700;color:{clr};">{val}</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:.6rem;color:#94a3b8;">{ref}</div>
            </div>""", unsafe_allow_html=True)

# ══ TAB 3 — STRENGTH ════════════════════════════════════════════════
with tabs[3]:
    st.markdown(f"""<div class="code-ref">
    <strong>AASHTO 5.7.3.2.2:</strong> Flexural Strength — φMn ≥ Mu  (φ = {st.session_state.phi_flex:.2f}) &nbsp;|&nbsp;
    <strong>AASHTO 5.8.3.3:</strong> Shear Strength — φVn ≥ Vu  (φ = {st.session_state.phi_shear:.2f})
    </div>""", unsafe_allow_html=True)
    ct1, ct2 = st.columns(2)
    with ct1:
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=R["x"],y=R["phi_Mn_pos"]/1000,name="φMn (+)",
            fill="tozeroy",fillcolor="rgba(5,150,105,.08)",line=dict(color="#059669",width=2.5)))
        fig4.add_trace(go.Scatter(x=R["x"],y=R["phi_Mn_neg"]/1000,name="φMn (−)",
            fill="tozeroy",fillcolor="rgba(5,150,105,.05)",line=dict(color="#059669",width=2,dash="dot")))
        fig4.add_trace(go.Scatter(x=R["x"],y=R["mu"]/1000,name="Mu (factored)",
            line=dict(color="#dc2626",width=2.5)))
        fig4.add_trace(go.Scatter(x=R["x"],y=-R["mu"]/1000,showlegend=False,
            line=dict(color="#dc2626",width=1.5,dash="dot")))
        fig4.add_hline(y=0,line=dict(color="#cbd5e1",width=1))
        fig4.update_layout(template=LT,height=310,
            title=dict(text="Moment: Demand vs. Capacity (kNm/m)",font=dict(color="#475569",size=12)),
            yaxis_title="Moment (kNm/m)",xaxis_title="x (m)",legend=dict(x=.01,y=.99))
        st.plotly_chart(fig4, use_container_width=True)
    with ct2:
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=R["x"],y=R["phi_Vn"],name="φVn capacity",
            fill="tozeroy",fillcolor="rgba(5,150,105,.08)",line=dict(color="#059669",width=2.5)))
        fig5.add_trace(go.Scatter(x=R["x"],y=R["vu"],name="Vu demand",
            line=dict(color="#d97706",width=2.5)))
        fig5.update_layout(template=LT,height=310,
            title=dict(text="Shear: Demand vs. Capacity (kN/m)",font=dict(color="#475569",size=12)),
            yaxis_title="Shear (kN/m)",xaxis_title="x (m)",legend=dict(x=.01,y=.99))
        st.plotly_chart(fig5, use_container_width=True)

    st.markdown("**DCR Profile — Continuous**")
    dcr_m_arr = np.abs(R["mu"]) / np.abs(R["phi_Mn_pos"])
    dcr_v_arr = R["vu"] / R["phi_Vn"]
    fig6 = go.Figure()
    fig6.add_trace(go.Scatter(x=R["x"],y=dcr_m_arr,name="Flexure DCR",
        line=dict(color="#1d6fb8",width=2),fill="tozeroy",fillcolor="rgba(29,111,184,.07)"))
    fig6.add_trace(go.Scatter(x=R["x"],y=dcr_v_arr,name="Shear DCR",
        line=dict(color="#7c3aed",width=2),fill="tozeroy",fillcolor="rgba(124,58,237,.07)"))
    fig6.add_hline(y=1.0,line=dict(color="#dc2626",dash="dash",width=2),
        annotation_text="DCR = 1.0  LIMIT",annotation_font=dict(color="#dc2626",size=10))
    fig6.add_hline(y=0.80,line=dict(color="#d97706",dash="dot",width=1),
        annotation_text="DCR = 0.80",annotation_font=dict(color="#d97706",size=10))
    fig6.add_hrect(y0=0,   y1=0.80,fillcolor="rgba(5,150,105,.04)", line_width=0)
    fig6.add_hrect(y0=0.80,y1=1.0, fillcolor="rgba(217,119,6,.04)",  line_width=0)
    fig6.add_hrect(y0=1.0, y1=1.5, fillcolor="rgba(220,38,38,.04)",  line_width=0)
    fig6.update_layout(template=LT,height=255,yaxis_title="DCR",xaxis_title="x (m)",
        legend=dict(x=.01,y=.99))
    st.plotly_chart(fig6, use_container_width=True)

# ══ TAB 4 — SUMMARY ═════════════════════════════════════════════════
with tabs[4]:
    col_tb, col_stat = st.columns([3, 1])
    with col_tb:
        st.markdown("**Design Check Summary — Critical Stations**")
        sta_x = df_ld["x (m)"].values
        rows = []
        for sx in sta_x:
            idx = np.abs(R["x"] - sx).argmin()
            t_s   = R["t"][idx]*1000
            m_dem = abs(R["mu"][idx]);      m_cap = abs(R["phi_Mn_pos"][idx])
            v_dem = abs(R["vu"][idx]);      v_cap = abs(R["phi_Vn"][idx])
            dcr_m = m_dem/m_cap if m_cap>0 else 999
            dcr_v = v_dem/v_cap if v_cap>0 else 999
            status = "✅ PASS" if (dcr_m<=1.0 and dcr_v<=1.0) else "❌ FAIL"
            rows.append({
                "Station x (m)": f"{sx:.2f}","t (mm)": f"{t_s:.1f}",
                "Mu (kNm/m)":  f"{m_dem:.2f}","φMn (kNm/m)": f"{m_cap/1000:.2f}",
                "Flex DCR":    f"{dcr_m:.3f}",
                "Vu (kN/m)":   f"{v_dem:.2f}","φVn (kN/m)":  f"{v_cap:.2f}",
                "Shear DCR":   f"{dcr_v:.3f}","Status": status,
            })
        df_res = pd.DataFrame(rows)
        styled = dcr_style(df_res, "Flex DCR")
        styled = dcr_style(styled, "Shear DCR")
        st.dataframe(styled, use_container_width=True, hide_index=True)

    with col_stat:
        pass_all  = all("PASS" in r["Status"] for r in rows)
        max_dcr_m = max(float(r["Flex DCR"])  for r in rows)
        max_dcr_v = max(float(r["Shear DCR"]) for r in rows)
        def _clr(v): return "#059669" if v<=.80 else ("#d97706" if v<=1.0 else "#dc2626")
        def _bg(v):  return "#dcfce7" if v<=.80 else ("#fef9c3" if v<=1.0 else "#fee2e2")
        for lbl, val, phi_lbl in [
            ("Max Flexure DCR", max_dcr_m, f"φ = {st.session_state.phi_flex:.2f}"),
            ("Max Shear DCR",   max_dcr_v, f"φ = {st.session_state.phi_shear:.2f}"),
        ]:
            st.markdown(f"""<div style="background:{_bg(val)};border:1px solid #e2e8f0;
            border-left:4px solid {_clr(val)};border-radius:8px;padding:1rem;margin-bottom:.7rem;">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:.61rem;color:#64748b;text-transform:uppercase;">{lbl}</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:1.85rem;font-weight:800;color:{_clr(val)};">{val:.3f}</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:.63rem;color:#94a3b8;">{phi_lbl}</div>
            </div>""", unsafe_allow_html=True)
        gc  = "#059669" if pass_all else "#dc2626"
        gbg = "#dcfce7" if pass_all else "#fee2e2"
        st.markdown(f"""<div style="background:{gbg};border:2px solid {gc};
        border-radius:8px;padding:.9rem;text-align:center;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:.78rem;font-weight:800;
        color:{gc};letter-spacing:.04em;">{'✅ ALL CHECKS PASS' if pass_all else '❌ SECTION FAILS'}</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("""<div class="code-ref" style="margin-top:.9rem;">
        🟢 DCR ≤ 0.80 — Adequate<br>🟡 0.80 &lt; DCR ≤ 1.0 — Marginal<br>🔴 DCR &gt; 1.0 — OVER
        </div>""", unsafe_allow_html=True)

# ══ TAB 5 — REPORT ══════════════════════════════════════════════════
with tabs[5]:
    cr1, cr2 = st.columns([2, 1])
    with cr1:
        st.markdown(f"""<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;
        padding:1.5rem;font-family:'IBM Plex Mono',monospace;">
        <div style="color:#0284c7;font-size:.98rem;font-weight:700;border-bottom:1px solid #e2e8f0;
        padding-bottom:.5rem;margin-bottom:1rem;">CALCULATION SHEET — {st.session_state.doc_no}</div>
        <div style="color:#475569;font-size:.74rem;line-height:1.95;">
        <b style="color:#1e293b;">Project:</b>     {st.session_state.proj_name}<br>
        <b style="color:#1e293b;">Element:</b>     PSC Box Girder — Top Flange (Transverse)<br>
        <b style="color:#1e293b;">Method:</b>      AASHTO LRFD Strip Method, 1.0 m strip<br>
        <b style="color:#1e293b;">Code:</b>        AASHTO LRFD Bridge Design Spec., 9th Ed.<br>
        <b style="color:#1e293b;">Designed by:</b> {st.session_state.eng_name}<br>
        <b style="color:#1e293b;">Checked by:</b>  {st.session_state.chk_name}<br>
        <b style="color:#1e293b;">Date:</b>        {datetime.date.today().strftime('%d %B %Y')}<br>
        </div>
        <div style="color:#0284c7;margin-top:.9rem;font-size:.86rem;font-weight:700;">MATERIAL PARAMETERS</div>
        <div style="color:#475569;font-size:.73rem;line-height:1.9;">
        f'c = {fc:.0f} MPa  |  f'ci = {fci:.0f} MPa  |  fpu = {fpu:.0f} MPa  |  fpy = {fpy:.0f} MPa<br>
        Aps/strand = {aps_strand:.0f} mm²  |  Duct dia = {duct_dia_mm:.0f} mm<br>
        Ep = {L['Ep']:.0f} MPa  |  Ec = {L['Ec']:.0f} MPa  |  Eci = {L['Eci']:.0f} MPa
        </div>
        <div style="color:#0284c7;margin-top:.8rem;font-size:.86rem;font-weight:700;">PRESTRESS RESULTS</div>
        <div style="color:#475569;font-size:.73rem;line-height:1.9;">
        fpj = {L['fpj']:.1f} MPa  ({fpi_ratio:.1%} × fpu)<br>
        Total Aps = {L['Aps']*1e6:.0f} mm²/m  ({int(num_tendon)} tn × {int(n_strands)} str)<br>
        Pi  = {L['Pi']:.1f} kN/m  |  Pe = {L['Pe']:.1f} kN/m<br>
        fpe = {L['fpe']:.1f} MPa  ({L['fpe']/fpu*100:.1f}% of fpu)<br>
        Total Loss = {L['total_loss_pct']:.2f}% of fpj
        </div>
        <div style="color:#0284c7;margin-top:.8rem;font-size:.86rem;font-weight:700;">DESIGN CHECKS</div>
        <div style="color:#475569;font-size:.73rem;line-height:1.9;">
        Comp. limit (Transfer) = {R['lim_tr_c']:.3f} MPa  (AASHTO 5.9.4.1.1)<br>
        Tens.  limit (Transfer) = +{R['lim_tr_t']:.3f} MPa  (AASHTO 5.9.4.1.2)<br>
        Comp. limit (Service)  = {R['lim_sv_ct']:.3f} MPa  (AASHTO 5.9.4.2.1)<br>
        Tens.  limit (Service)  = +{R['lim_sv_t']:.3f} MPa  (AASHTO 5.9.4.2.2)<br>
        φMn capacity (peak) = {max(R['phi_Mn_pos'])/1000:.3f} kNm/m  (φ = {st.session_state.phi_flex:.2f})<br>
        φVn capacity (peak) = {max(R['phi_Vn']):.3f} kN/m  (φ = {st.session_state.phi_shear:.2f})
        </div></div>""", unsafe_allow_html=True)
    with cr2:
        st.markdown("**AASHTO Article References**")
        for art, desc in [
            ("5.4.2.1","Concrete compressive strength"),("5.4.4.1","Prestressing steel — fpu"),
            ("5.7.1.1","Strip method for slabs"),("5.7.3.2","Flexural resistance φMn"),
            ("5.8.3.3","Shear — simplified procedure"),("5.9.3","Jacking stress limits"),
            ("5.9.4.1","Stress limits at transfer"),("5.9.4.2","Stress limits at service"),
            ("5.9.5.2","Immediate losses"),("5.9.5.4","Long-term losses"),
            ("3.6.1.2","HL-93 vehicular live load"),("3.4.1","Load combinations & factors"),
        ]:
            st.markdown(f"""<div style="display:flex;gap:.8rem;padding:.27rem 0;border-bottom:1px solid #f1f5f9;">
            <span style="font-family:'IBM Plex Mono',monospace;font-size:.68rem;color:#1d6fb8;
            white-space:nowrap;min-width:52px;">Art. {art}</span>
            <span style="font-family:'IBM Plex Mono',monospace;font-size:.67rem;color:#64748b;">{desc}</span>
            </div>""", unsafe_allow_html=True)

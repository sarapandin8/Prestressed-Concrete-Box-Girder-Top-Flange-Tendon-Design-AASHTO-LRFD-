"""
PSC Box Girder — Top Flange Transverse Design  (v3)
AASHTO LRFD Bridge Design Specifications
Analysis per 1.0 m transverse strip

Bug Fixes vs v2:
  [1] dp_pos = z (sagging, compression face=TOP)
      dp_neg = t-z (hogging, compression face=BOTTOM)
  [2] Vu uses FACTORED shear (1.25VDL + 1.50VSDL + 1.75VLL)
  [3] Report uses actual computed c, fps, a (not hardcoded)

New Features:
  [4] Net section properties (duct area & I deduction at Transfer)
  [5] c/dp ductility check <= 0.42  (AASHTO 5.7.3.3.1)
  [6] Min reinforcement: phi*Mn >= 1.2*Mcr  (AASHTO 5.6.3.3)
  [7] DCR colour-coding  green<=0.80 / yellow 0.80-1.00 / red>1.00
  [8] Full step-by-step professional Word report

Sign convention: compression (-), tension (+)
Positive moment = sagging (compression at TOP)
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
from docx.enum.table import WD_ALIGN_VERTICAL

# ─────────────────────────────────────────────────────────────────────────────
# 1.  CONFIG & SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="PSC Box Girder — Top Flange Design")

def init_df(key, data):
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(data)

init_df("df_thickness", {
    "x (m)": [0.0, 3.0, 6.0],
    "t (m)":  [0.30, 0.25, 0.30],
})
init_df("df_tendon", {
    "x (m)":          [0.0,  3.0,  6.0],
    "z_top (m)":      [0.08, 0.18, 0.08],   # z = tendon CG from TOP face
})
init_df("df_load", {
    "x (m)":         [ 0.0,    3.0,    6.0],
    "M_DL (kNm/m)":  [-120.0,  80.0, -120.0],
    "V_DL (kN/m)":   [  60.0,   0.0,   60.0],
    "M_SDL (kNm/m)": [ -40.0,  25.0,  -40.0],
    "V_SDL (kN/m)":  [  20.0,   0.0,   20.0],
    "M_LL (kNm/m)":  [-180.0, 120.0, -180.0],
    "V_LL (kN/m)":   [  80.0,   0.0,   80.0],
})

# ─────────────────────────────────────────────────────────────────────────────
# 2.  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Design Parameters")

    with st.expander("📐 Materials & Section", expanded=True):
        width        = st.number_input("Total Flange Width (m)", value=6.0, min_value=1.0)
        fc           = st.number_input("f'c  Service (MPa)",     value=40.0, min_value=20.0)
        fci          = st.number_input("f'ci Transfer (MPa)",    value=30.0, min_value=15.0)
        fpu          = st.number_input("fpu (MPa)",              value=1860.0)
        fpy_ratio    = st.selectbox("fpy/fpu",  [0.90, 0.85], index=0,
                                    help="Low-relaxation=0.90  |  Stress-relieved=0.85")
        aps_strand   = st.number_input("Aps per strand (mm²)",   value=140.0)
        duct_dia_mm  = st.number_input("Duct diameter (mm)",     value=70.0, min_value=20.0)

    with st.expander("🔩 Prestressing Force", expanded=True):
        num_tendon    = st.number_input("Tendons per 1 m strip", value=2, min_value=1)
        n_strands     = st.number_input("Strands per tendon",    value=12, min_value=1)
        fpi_ratio     = st.slider("fpi / fpu  (at jacking)",     0.70, 0.80, 0.75)
        init_loss_pct = st.slider("Immediate loss at Transfer (%)", 0, 15, 5)
        eff_ratio     = st.slider("Pe / Pi  (long-term ratio)",  0.50, 0.95, 0.80)

    with st.expander("⚖️ Resistance Factors φ"):
        phi_flex  = st.number_input("φ  Flexure", value=1.00, min_value=0.75, max_value=1.00)
        phi_shear = st.number_input("φ  Shear",   value=0.90, min_value=0.70, max_value=1.00)

    st.markdown("---")
    st.subheader("📄 Report Information")
    proj_name = st.text_input("Project Name",   "Bridge Lane Expansion")
    doc_no    = st.text_input("Document No.",   "CALC-STR-001")
    eng_name  = st.text_input("Prepared by",    "Engineer Name")
    chk_name  = st.text_input("Checked by",     "Checker Name")

# ─────────────────────────────────────────────────────────────────────────────
# 3.  DATA EDITORS
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏗️  PSC Box Girder — Top Flange Transverse Design")
st.caption("AASHTO LRFD  |  1.0 m transverse strip  |  "
           "Compression (−)  Tension (+)  |  +M = sagging")

c1, c2 = st.columns(2)
with c1:
    st.subheader("📏 Flange Thickness t(x)")
    df_thk = st.data_editor(st.session_state.df_thickness, num_rows="dynamic", key="ed_thk")
    st.subheader("🔩 Tendon Profile z(x)  [from top face]")
    df_tdn = st.data_editor(st.session_state.df_tendon,    num_rows="dynamic", key="ed_tdn")
with c2:
    st.subheader("📦 Loads per 1 m strip")
    df_ld  = st.data_editor(st.session_state.df_load,      num_rows="dynamic", key="ed_ld")

# ─────────────────────────────────────────────────────────────────────────────
# 4.  CALCULATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def prep(df):
    return df.dropna().sort_values("x (m)").reset_index(drop=True)

try:
    dft = prep(df_thk);  dfp = prep(df_tdn);  dfl = prep(df_ld)
    if any(len(d) < 2 for d in [dft, dfp, dfl]):
        st.warning("⚠️ Enter at least 2 rows in each table.");  st.stop()

    N     = 500
    b     = 1.0
    x_arr = np.linspace(0, width, N)

    # ── Geometry
    t   = np.interp(x_arr, dft["x (m)"], dft["t (m)"])
    z   = np.interp(x_arr, dfp["x (m)"], dfp["z_top (m)"])
    yc  = t / 2.0

    # ── Loads
    def ip(col): return np.interp(x_arr, dfl["x (m)"], dfl[col])
    m_dl=ip("M_DL (kNm/m)"); v_dl=ip("V_DL (kN/m)")
    m_sdl=ip("M_SDL (kNm/m)"); v_sdl=ip("V_SDL (kN/m)")
    m_ll=ip("M_LL (kNm/m)");  v_ll=ip("V_LL (kN/m)")

    ms1 = m_dl + m_sdl + m_ll
    ms3 = m_dl + m_sdl + 0.8*m_ll
    mu  = 1.25*m_dl + 1.50*m_sdl + 1.75*m_ll
    # [FIX 2] Factored shear using absolute values per component
    vu  = 1.25*np.abs(v_dl) + 1.50*np.abs(v_sdl) + 1.75*np.abs(v_ll)

    # ── Gross section
    Ag = b * t
    Ig = b * t**3 / 12.0

    # ── [FIX 4] Net section (duct deduction — used only at Transfer)
    A_duct  = math.pi / 4.0 * (duct_dia_mm / 1000.0)**2   # m² per duct
    n_ducts = int(num_tendon)
    y_duct  = z - yc                                        # signed dist duct→CG
    An = Ag - n_ducts * A_duct
    In = Ig - n_ducts * A_duct * y_duct**2

    # ── Eccentricity  (e > 0 → tendon above CG → sagging prestress)
    e = yc - z

    # ── Prestress
    aps_m2  = aps_strand * 1e-6
    n_total = int(num_tendon * n_strands)
    Aps     = n_total * aps_m2
    fpi_val = fpu * fpi_ratio * (1.0 - init_loss_pct / 100.0)
    Pi      = Aps * fpi_val * 1e3     # kN/m
    Pe      = Pi * eff_ratio           # kN/m

    # ── Stress calculator
    # σ_top = (−P/A + P·e·ht/I − M·ht/I) / 1000   [MPa]
    # σ_bot = (−P/A − P·e·ht/I + M·ht/I) / 1000
    def stress(P, M, ev, tv, Av, Iv):
        ht = tv / 2.0
        top = (-P/Av + P*ev*ht/Iv - M*ht/Iv) / 1000.0
        bot = (-P/Av - P*ev*ht/Iv + M*ht/Iv) / 1000.0
        return top, bot

    tr_top,  tr_bot  = stress(Pi, m_dl, e, t, An, In)      # Transfer (net section)
    sv1_top, sv1_bot = stress(Pe, ms1,  e, t, Ag, Ig)      # Service I
    sv3_top, sv3_bot = stress(Pe, ms3,  e, t, Ag, Ig)      # Service III

    # ── [FIX 1] Flexure — correct dp for each sign of moment
    beta1 = float(np.clip(0.85 - 0.05*(fc-28.0)/7.0, 0.65, 0.85))
    k_fac = 2.0 * (1.04 - fpy_ratio)

    def flexure(dp_arr):
        dp_s = np.maximum(dp_arr, 1e-4)
        c_   = Aps*fpu / (0.85*fc*beta1*b*1000.0 + k_fac*Aps*fpu/dp_s)
        fps_ = np.clip(fpu*(1.0 - k_fac*c_/dp_s), 0.0, fpu)
        a_   = beta1 * c_
        Mn_  = Aps * fps_ * (dp_s - a_/2.0) * 1000.0   # kNm/m
        return c_, a_, fps_, Mn_

    dp_pos = z        # sagging : compression face = TOP
    dp_neg = t - z    # hogging : compression face = BOTTOM

    c_pos, a_pos, fps_pos, Mn_pos = flexure(dp_pos)
    c_neg, a_neg, fps_neg, Mn_neg = flexure(dp_neg)

    phi_Mn_pos =  phi_flex * Mn_pos
    phi_Mn_neg = -phi_flex * Mn_neg   # capacity expressed as negative number

    # [FIX 5] c/dp ductility
    cdp_pos = np.where(dp_pos>0, c_pos/dp_pos, np.inf)
    cdp_neg = np.where(dp_neg>0, c_neg/dp_neg, np.inf)

    # [FIX 6] Minimum reinforcement
    fr   = 0.63 * math.sqrt(fc)
    fpe  = Pe / Ag / 1000.0            # axial prestress (MPa)
    Sb   = Ig / yc
    Mcr  = (fr + fpe) * Sb / 1000.0   # kNm/m

    # ── Shear
    dp_use = np.maximum(dp_pos, dp_neg)
    dv     = np.maximum(0.9*dp_use, 0.72*t)
    Vc     = 0.083*2.0*1.0*math.sqrt(fc)*b*dv*1000.0
    Vn_lim = 0.25*fc*b*dv*1000.0
    phi_Vn = phi_shear * np.minimum(Vc, Vn_lim)

    # ── Allowable limits
    lim_tr_c  = -0.60*fci;  lim_tr_t  =  0.25*math.sqrt(fci)
    lim_sv_cp = -0.45*fc;   lim_sv_ct = -0.60*fc
    lim_sv_t  =  0.50*math.sqrt(fc)

    # Stations
    sta_x   = dfl["x (m)"].values
    sta_idx = [int(np.abs(x_arr-v).argmin()) for v in sta_x]

    # ─────────────────────────────────────────────────────────────────────
    # 5.  REPORT GENERATOR
    # ─────────────────────────────────────────────────────────────────────
    def make_report():
        doc = Document()
        # Page margins
        for sec in doc.sections:
            sec.top_margin    = Cm(2.0)
            sec.bottom_margin = Cm(2.0)
            sec.left_margin   = Cm(2.5)
            sec.right_margin  = Cm(2.0)

        normal = doc.styles["Normal"]
        normal.font.name = "Calibri"
        normal.font.size = Pt(10)

        # colours
        C_BLUE  = RGBColor(0x00, 0x44, 0x88)
        C_GREEN = RGBColor(0x00, 0x70, 0x00)
        C_RED   = RGBColor(0xC0, 0x00, 0x00)
        C_GRAY  = RGBColor(0x60, 0x60, 0x60)

        # ── helpers ────────────────────────────────────────────────────
        def h1(s): doc.add_heading(s, level=1)
        def h2(s): doc.add_heading(s, level=2)
        def h3(s): doc.add_heading(s, level=3)

        def para(s, bold=False, italic=False, color=None, indent=0.0, align=None):
            p = doc.add_paragraph()
            r = p.add_run(s)
            r.bold = bold; r.italic = italic
            if color: r.font.color.rgb = color
            p.paragraph_format.left_indent = Inches(indent)
            if align: p.alignment = align
            return p

        def formula(s):  return para(s, italic=True,  indent=0.5, color=C_GRAY)
        def subst(s):    return para(s, italic=True,  indent=0.7, color=C_GRAY)
        def result(s):   return para(s, bold=True,    indent=0.7, color=C_BLUE)
        def blank():     return doc.add_paragraph()
        def hrule():     return para("─"*80, color=C_GRAY)

        def pf(cond, ok, fail):
            if cond: para(f"  ✔  {ok}   ▶  PASS", bold=True, color=C_GREEN, indent=0.5)
            else:    para(f"  ✘  {fail}  ▶  FAIL", bold=True, color=C_RED,   indent=0.5)

        def table(headers, rows, col_widths_cm=None):
            t_ = doc.add_table(rows=1, cols=len(headers))
            t_.style = "Table Grid"
            hdr = t_.rows[0].cells
            for j,h in enumerate(headers):
                hdr[j].text = h
                hdr[j].paragraphs[0].runs[0].bold = True
                hdr[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            for row in rows:
                rc = t_.add_row().cells
                for j,v in enumerate(row):
                    rc[j].text = str(v)
            if col_widths_cm:
                for row in t_.rows:
                    for j,cell in enumerate(row.cells):
                        cell.width = Cm(col_widths_cm[j])
            return t_

        # ══════════════════════════════════════════════════════════════
        # COVER PAGE
        # ══════════════════════════════════════════════════════════════
        blank(); blank()
        doc.add_heading("STRUCTURAL CALCULATION REPORT", 0)
        blank()
        table(
            ["Item", "Description"],
            [
                ["Project",      proj_name],
                ["Document No.", doc_no],
                ["Subject",
                 "Transverse Tendon Design — PSC Box Girder Top Flange (1.0 m Strip)"],
                ["Code",         "AASHTO LRFD Bridge Design Specifications"],
                ["Prepared by",  eng_name],
                ["Checked by",   chk_name],
                ["Date",         datetime.datetime.now().strftime("%d %B %Y")],
            ],
            col_widths_cm=[4.5, 13.0]
        )
        doc.add_page_break()

        # ══════════════════════════════════════════════════════════════
        # SEC 1 — DESIGN BASIS
        # ══════════════════════════════════════════════════════════════
        h1("1.  Design Basis")
        items = [
            "Code of Practice: AASHTO LRFD Bridge Design Specifications",
            "Analysis basis: 1.0 m transverse strip across top flange width",
            "Load Combinations per AASHTO Table 3.4.1-1 :",
            "   •  Strength I  :  1.25·DC + 1.50·DW + 1.75·LL",
            "   •  Service  I  :  1.00·DC + 1.00·DW + 1.00·LL  (compression check)",
            "   •  Service III :  1.00·DC + 1.00·DW + 0.80·LL  (tension check)",
            "Transfer        :  Pi (after immediate losses) + M_DC  (Self-weight only)",
            "Strand type     :  Post-tensioned, bonded (fully grouted), low-relaxation",
            "Sign convention :  Compression (−)  |  Tension (+)",
            "                   Positive moment = sagging (compression at TOP fibre)",
        ]
        for it in items:
            doc.add_paragraph(it, style="List Bullet" if it.startswith("•") else "Normal")
        blank()

        # ══════════════════════════════════════════════════════════════
        # SEC 2 — DESIGN INPUT SUMMARY
        # ══════════════════════════════════════════════════════════════
        h1("2.  Design Input Summary")

        h2("2.1  Material Properties")
        table(
            ["Parameter", "Symbol", "Value", "Unit", "Reference"],
            [
                ["Concrete — service",       "f'c",    f"{fc:.1f}",         "MPa", "AASHTO 5.4.2"],
                ["Concrete — transfer",      "f'ci",   f"{fci:.1f}",        "MPa", "AASHTO 5.9.2"],
                ["Strand — tensile strength","fpu",    f"{fpu:.0f}",        "MPa", "AASHTO 5.4.4"],
                ["Strand — fpy / fpu",       "ξ",      f"{fpy_ratio:.2f}",  "—",   "Low-relax"],
                ["Area per strand",          "asp",    f"{aps_strand:.1f}", "mm²", "Product data"],
                ["PT duct outer diameter",   "d_duct", f"{duct_dia_mm:.0f}","mm",  "Supplier"],
            ],
            col_widths_cm=[4.5, 2.0, 2.0, 1.5, 4.5]
        )
        blank()

        h2("2.2  Prestressing Configuration")
        table(
            ["Parameter", "Symbol", "Value", "Unit"],
            [
                ["Tendons per 1 m strip",      "n_t",    f"{int(num_tendon)}",  "—"],
                ["Strands per tendon",          "n_s",    f"{int(n_strands)}",   "—"],
                ["Total strands (1 m strip)",   "n",      f"{n_total}",          "—"],
                ["Total Aps (1 m strip)",        "Aps",    f"{Aps*1e6:.2f}",     "mm²/m"],
                ["Jacking stress ratio",        "fpi/fpu",f"{fpi_ratio:.4f}",    "—"],
                ["Immediate loss at transfer",  "Δi",     f"{init_loss_pct:.1f}","%"],
                ["Long-term effective ratio",   "Pe/Pi",  f"{eff_ratio:.4f}",    "—"],
            ],
            col_widths_cm=[5.5, 2.5, 2.5, 2.0]
        )
        blank()

        h2("2.3  Resistance Factors (AASHTO Table 5.5.4.2.1-1)")
        table(
            ["Limit State", "Symbol", "Value"],
            [
                ["Flexure — tension-controlled", "φ_f", f"{phi_flex:.2f}"],
                ["Shear",                        "φ_v", f"{phi_shear:.2f}"],
            ],
            col_widths_cm=[6.0, 2.5, 2.5]
        )
        blank()

        h2("2.4  Allowable Stress Limits")
        table(
            ["Condition", "Limit Expression", "Computed (MPa)", "Article"],
            [
                ["Transfer — Compression",
                 "fa,comp = −0.60·f'ci",
                 f"{lim_tr_c:.3f}", "5.9.2.3.1a"],
                ["Transfer — Tension (bonded)",
                 "fa,tens = +0.25·√f'ci",
                 f"+{lim_tr_t:.4f}", "5.9.2.3.1b"],
                ["Service I — Comp. (permanent loads)",
                 "fa = −0.45·f'c",
                 f"{lim_sv_cp:.3f}", "5.9.2.3.2a"],
                ["Service I — Comp. (total loads)",
                 "fa = −0.60·f'c",
                 f"{lim_sv_ct:.3f}", "5.9.2.3.2a"],
                ["Service III — Tension (bonded)",
                 "fa,tens = +0.50·√f'c",
                 f"+{lim_sv_t:.4f}", "5.9.2.3.2b"],
            ],
            col_widths_cm=[5.5, 4.0, 2.5, 2.5]
        )
        blank()

        h2("2.5  Input Geometry & Load Stations")
        grws = []
        for i in sta_idx:
            grws.append([
                f"{x_arr[i]:.2f}",
                f"{t[i]*1000:.2f}", f"{z[i]*1000:.2f}", f"{yc[i]*1000:.2f}",
                f"{e[i]*1000:.2f}",
                f"{m_dl[i]:.2f}", f"{m_sdl[i]:.2f}", f"{m_ll[i]:.2f}",
                f"{v_dl[i]:.2f}", f"{v_sdl[i]:.2f}", f"{v_ll[i]:.2f}",
            ])
        table(
            ["x (m)","t (mm)","z (mm)","yc (mm)","e (mm)",
             "M_DL","M_SDL","M_LL","V_DL","V_SDL","V_LL"],
            grws,
            col_widths_cm=[1.4,1.4,1.4,1.4,1.4,1.6,1.6,1.6,1.6,1.6,1.6]
        )
        para("Units: M in kNm/m  |  V in kN/m", italic=True, color=C_GRAY)
        doc.add_page_break()

        # ══════════════════════════════════════════════════════════════
        # SEC 3 — GLOBAL PRESTRESS
        # ══════════════════════════════════════════════════════════════
        h1("3.  Global Prestress Force Calculation")

        h2("3.1  Total Prestress Steel Area  Aps")
        formula("Aps  =  n_total × asp")
        subst( f"     =  {n_total} strands  ×  {aps_strand:.1f} mm²/strand")
        result(f"     =  {Aps*1e6:.2f} mm²/m  =  {Aps:.6f} m²/m")
        blank()

        h2("3.2  Effective Prestress  fpi  (after immediate losses at Transfer)")
        formula("fpi  =  fpu × (fpi/fpu) × (1 − Δi/100)")
        subst( f"     =  {fpu:.0f} × {fpi_ratio:.4f} × (1 − {init_loss_pct:.1f}/100)")
        result(f"     =  {fpi_val:.4f} MPa")
        blank()

        h2("3.3  Initial Prestress Force  Pi  (at Transfer)")
        formula("Pi   =  Aps × fpi")
        subst( f"     =  {Aps*1e6:.2f} mm²/m  ×  {fpi_val:.4f} MPa  ×  10⁻³  (kN unit)")
        result(f"     =  {Pi:.4f} kN/m")
        blank()

        h2("3.4  Effective Prestress Force  Pe  (after all long-term losses)")
        formula("Pe   =  Pi × (Pe/Pi)")
        subst( f"     =  {Pi:.4f}  ×  {eff_ratio:.4f}")
        result(f"     =  {Pe:.4f} kN/m")
        blank()

        h2("3.5  Section Factors (Gross)")
        formula("β₁  =  0.85 − 0.05 × (f'c − 28.0) / 7.0   [0.65 ≤ β₁ ≤ 0.85]")
        subst( f"    =  0.85 − 0.05 × ({fc:.1f} − 28.0) / 7.0")
        result(f"    =  {beta1:.4f}")
        blank()
        formula("k   =  2.0 × (1.04 − fpy/fpu)   (AASHTO C5.6.3.1.1)")
        subst( f"    =  2.0 × (1.04 − {fpy_ratio:.2f})")
        result(f"    =  {k_fac:.4f}")
        doc.add_page_break()

        # ══════════════════════════════════════════════════════════════
        # SEC 4 — STATION BY STATION
        # ══════════════════════════════════════════════════════════════
        h1("4.  Detailed Station-by-Station Calculations")
        para("Each station is analysed for: (a) Transfer, (b) Service, "
             "(c) Flexural Strength, (d) Shear.", italic=True)
        blank()

        for ks, i in enumerate(sta_idx):
            xi   = float(x_arr[i])
            ti   = float(t[i]);    zi   = float(z[i]);  yci  = float(yc[i])
            Agi  = float(Ag[i]);   Igi  = float(Ig[i])
            Ani  = float(An[i]);   Ini  = float(In[i])
            ei   = float(e[i])
            ydi  = float(y_duct[i])
            mdi  = float(m_dl[i]); msdi = float(m_sdl[i]); mli  = float(m_ll[i])
            vdi  = float(v_dl[i]); vsdi = float(v_sdl[i]); vli  = float(v_ll[i])
            ms1i = float(ms1[i]);  ms3i = float(ms3[i])
            mui  = float(mu[i]);   vui  = float(vu[i])
            # Transfer
            trt  = float(tr_top[i]);  trb  = float(tr_bot[i])
            # Service
            s1t  = float(sv1_top[i]); s1b  = float(sv1_bot[i])
            s3t  = float(sv3_top[i]); s3b  = float(sv3_bot[i])
            # Flexure
            cpp  = float(c_pos[i]);   app  = float(a_pos[i]);   fpp  = float(fps_pos[i])
            cpn  = float(c_neg[i]);   apn  = float(a_neg[i]);   fpn  = float(fps_neg[i])
            dpp  = float(dp_pos[i]);  dpn  = float(dp_neg[i])
            pMp  = float(phi_Mn_pos[i]); pMn_ = float(phi_Mn_neg[i])
            Mcri = float(Mcr[i])
            cdpp = float(cdp_pos[i]); cdpn = float(cdp_neg[i])
            # Shear
            dvi  = float(dv[i]);  Vci  = float(Vc[i]);  pVi  = float(phi_Vn[i])
            Vnli = float(Vn_lim[i])

            doc.add_heading(f"4.{ks+1}   Station  x = {xi:.2f} m", level=2)
            hrule()

            # ── 4.x.1 Section Properties ────────────────────────────
            h3(f"4.{ks+1}.1   Net Section Properties  (used at Transfer)")
            table(
                ["Property","Formula","Substitution","Value","Unit"],
                [
                    ["Slab thickness","t","input",f"{ti*1000:.2f}","mm"],
                    ["Tendon CG from top","z","input",f"{zi*1000:.2f}","mm"],
                    ["Section centroid","yc = t/2",
                     f"{ti*1000:.2f}/2",f"{yci*1000:.2f}","mm"],
                    ["Eccentricity","e = yc − z",
                     f"{yci*1000:.2f} − {zi*1000:.2f}",f"{ei*1000:.2f}","mm"],
                    ["Gross area","Ag = b·t  (b=1m)",
                     f"1000×{ti*1000:.2f}",f"{Agi*1e6:.1f}","mm²/m"],
                    ["Gross inertia","Ig = b·t³/12",
                     f"1000×{ti*1000:.2f}³/12",f"{Igi*1e12:.4f}×10⁻³","mm⁴/m"],
                    ["Duct area (each)","Ad = π/4·d²",
                     f"π/4×{duct_dia_mm:.0f}²",f"{A_duct*1e6:.2f}","mm²"],
                    ["Duct CG from section CG","yd = z−yc",
                     f"{zi*1000:.2f}−{yci*1000:.2f}",f"{ydi*1000:.2f}","mm"],
                    ["Net area","An = Ag − n·Ad",
                     f"{Agi*1e6:.1f}−{n_ducts}×{A_duct*1e6:.2f}",
                     f"{Ani*1e6:.1f}","mm²/m"],
                    ["Net inertia","In = Ig − n·Ad·yd²",
                     f"{Igi*1e12:.4f}×10⁻³ − {n_ducts}×{A_duct*1e6:.2f}×{ydi*1000:.2f}²×10⁻⁶",
                     f"{Ini*1e12:.4f}×10⁻³","mm⁴/m"],
                ],
                col_widths_cm=[3.5,3.5,5.5,2.5,1.5]
            )
            blank()

            # ── 4.x.2 Load Combinations ─────────────────────────────
            h3(f"4.{ks+1}.2   Load Combinations at this Station")
            table(
                ["Combination","Expression","Substitution","Value","Unit"],
                [
                    ["Service I",
                     "Ms1 = M_DL + M_SDL + M_LL",
                     f"{mdi:.2f} + {msdi:.2f} + {mli:.2f}",
                     f"{ms1i:.4f}","kNm/m"],
                    ["Service III",
                     "Ms3 = M_DL + M_SDL + 0.8·M_LL",
                     f"{mdi:.2f} + {msdi:.2f} + 0.8×{mli:.2f}",
                     f"{ms3i:.4f}","kNm/m"],
                    ["Strength I — Moment",
                     "Mu = 1.25·M_DL + 1.50·M_SDL + 1.75·M_LL",
                     f"1.25×{mdi:.2f} + 1.50×{msdi:.2f} + 1.75×{mli:.2f}",
                     f"{mui:.4f}","kNm/m"],
                    ["Strength I — Shear",
                     "Vu = 1.25|V_DL| + 1.50|V_SDL| + 1.75|V_LL|",
                     f"1.25×|{vdi:.2f}| + 1.50×|{vsdi:.2f}| + 1.75×|{vli:.2f}|",
                     f"{vui:.4f}","kN/m"],
                ],
                col_widths_cm=[2.5,5.5,5.0,2.0,1.5]
            )
            blank()

            # ── 4.x.3 Transfer Stress ────────────────────────────────
            h3(f"4.{ks+1}.3   Stress Check — Transfer  (AASHTO Art. 5.9.2.3.1)")
            para("Loading : Pi + M_DL   |   Net section properties used  (duct deducted)",
                 italic=True, indent=0.3)
            blank()
            para("General stress formula at any fibre (y measured down from centroid):",
                 bold=True, indent=0.3)
            formula("σ(y)  =  [−Pi/An  +  Pi·e·y / In  −  M·y / In]  ×  10⁻³  MPa")
            formula("At TOP fibre  : y = −yc = −t/2")
            formula("At BOT fibre  : y = +yc = +t/2")
            blank()
            para("Values used:", bold=True, indent=0.3)
            table(
                ["Item","Symbol","Value","Unit"],
                [
                    ["Initial prestress force","Pi",   f"{Pi:.4f}","kN/m"],
                    ["Dead load moment at station","M_DL",f"{mdi:.4f}","kNm/m"],
                    ["Net area","An",f"{Ani*1e6:.2f}","mm²/m"],
                    ["Net inertia","In",f"{Ini*1e12:.6f}×10⁻³","mm⁴/m"],
                    ["Eccentricity","e",f"{ei*1000:.4f}","mm"],
                    ["Half thickness","yc",f"{yci*1000:.4f}","mm"],
                ],
                col_widths_cm=[4.5,2.5,4.0,2.5]
            )
            blank()

            para("─── Top Fibre  (y = −yc) ───", bold=True, indent=0.3)
            formula("σ_tr,top  =  [−Pi/An  +  Pi·e·(+yc)/In  −  M_DL·(−yc)/In]  ×  10⁻³")
            formula(f"          =  [−{Pi:.4f}/{Ani*1e6:.2f}  "
                    f"+  {Pi:.4f}×{ei*1000:.4f}×{yci*1000:.4f}/{Ini*1e12:.6f}×10⁻³  "
                    f"+  {mdi:.4f}×{yci*1000:.4f}/{Ini*1e12:.6f}×10⁻³]  ×  10⁻³")
            result(f"σ_tr,top  =  {trt:.6f} MPa")
            pf(lim_tr_c <= trt <= lim_tr_t,
               f"σ_tr,top = {trt:.4f} MPa   within [{lim_tr_c:.3f}, +{lim_tr_t:.4f}] MPa",
               f"σ_tr,top = {trt:.4f} MPa   outside [{lim_tr_c:.3f}, +{lim_tr_t:.4f}] MPa")
            blank()

            para("─── Bottom Fibre  (y = +yc) ───", bold=True, indent=0.3)
            formula("σ_tr,bot  =  [−Pi/An  −  Pi·e·yc/In  +  M_DL·yc/In]  ×  10⁻³")
            formula(f"          =  [−{Pi:.4f}/{Ani*1e6:.2f}  "
                    f"−  {Pi:.4f}×{ei*1000:.4f}×{yci*1000:.4f}/{Ini*1e12:.6f}×10⁻³  "
                    f"+  {mdi:.4f}×{yci*1000:.4f}/{Ini*1e12:.6f}×10⁻³]  ×  10⁻³")
            result(f"σ_tr,bot  =  {trb:.6f} MPa")
            pf(lim_tr_c <= trb <= lim_tr_t,
               f"σ_tr,bot = {trb:.4f} MPa   within [{lim_tr_c:.3f}, +{lim_tr_t:.4f}] MPa",
               f"σ_tr,bot = {trb:.4f} MPa   outside [{lim_tr_c:.3f}, +{lim_tr_t:.4f}] MPa")
            blank()

            # ── 4.x.4 Service Stress ────────────────────────────────
            h3(f"4.{ks+1}.4   Stress Check — Service  (AASHTO Art. 5.9.2.3.2)")
            para("Gross section properties used  (ducts fully grouted).  "
                 "Loading: Pe + load combination.", italic=True, indent=0.3)
            blank()
            para("Values used:", bold=True, indent=0.3)
            table(
                ["Item","Symbol","Value","Unit"],
                [
                    ["Effective prestress force","Pe",f"{Pe:.4f}","kN/m"],
                    ["Gross area","Ag",f"{Agi*1e6:.2f}","mm²/m"],
                    ["Gross inertia","Ig",f"{Igi*1e12:.6f}×10⁻³","mm⁴/m"],
                    ["Service I moment","Ms1",f"{ms1i:.4f}","kNm/m"],
                    ["Service III moment","Ms3",f"{ms3i:.4f}","kNm/m"],
                ],
                col_widths_cm=[4.5,2.5,4.0,2.5]
            )
            blank()

            for combo, M_combo, top_s, bot_s, lim_c, lim_t, note in [
                ("Service I  (compression check)",
                 ms1i, s1t, s1b, lim_sv_ct, lim_sv_t,
                 "−0.60·f'c  and  −0.45·f'c (permanent)"),
                ("Service III  (tension check)",
                 ms3i, s3t, s3b, lim_sv_ct, lim_sv_t,
                 "+0.50·√f'c"),
            ]:
                para(f"─── {combo}  (M = {M_combo:.4f} kNm/m) ───",
                     bold=True, indent=0.3)
                formula("σ_top  =  [−Pe/Ag  +  Pe·e·yc/Ig  −  M·yc/Ig]  ×  10⁻³")
                formula(f"       =  [−{Pe:.4f}/{Agi*1e6:.2f}  "
                        f"+  {Pe:.4f}×{ei*1000:.4f}×{yci*1000:.4f}/{Igi*1e12:.6f}×10⁻³  "
                        f"−  {M_combo:.4f}×{yci*1000:.4f}/{Igi*1e12:.6f}×10⁻³]  ×  10⁻³")
                result(f"σ_top  =  {top_s:.6f} MPa")
                pf(top_s >= lim_sv_ct,
                   f"σ_top = {top_s:.4f} ≥ {lim_sv_ct:.3f} MPa  (−0.60·f'c)",
                   f"σ_top = {top_s:.4f} < {lim_sv_ct:.3f} MPa  (−0.60·f'c)  EXCEEDS LIMIT")
                blank()
                formula("σ_bot  =  [−Pe/Ag  −  Pe·e·yc/Ig  +  M·yc/Ig]  ×  10⁻³")
                formula(f"       =  [−{Pe:.4f}/{Agi*1e6:.2f}  "
                        f"−  {Pe:.4f}×{ei*1000:.4f}×{yci*1000:.4f}/{Igi*1e12:.6f}×10⁻³  "
                        f"+  {M_combo:.4f}×{yci*1000:.4f}/{Igi*1e12:.6f}×10⁻³]  ×  10⁻³")
                result(f"σ_bot  =  {bot_s:.6f} MPa")
                pf(bot_s >= lim_sv_ct,
                   f"σ_bot = {bot_s:.4f} ≥ {lim_sv_ct:.3f} MPa  (−0.60·f'c)",
                   f"σ_bot = {bot_s:.4f} < {lim_sv_ct:.3f} MPa  EXCEEDS LIMIT")
                # Tension check (Service III)
                if "tension" in note:
                    pf(bot_s >= 0 or bot_s >= -lim_sv_t,
                       f"σ_bot = {bot_s:.4f} ≥ {-lim_sv_t:.4f} MPa  (tension limit)",
                       f"σ_bot = {bot_s:.4f} < {-lim_sv_t:.4f} MPa  TENSION EXCEEDS LIMIT")
                blank()

            # ── 4.x.5 Flexural Strength ─────────────────────────────
            h3(f"4.{ks+1}.5   Flexural Strength Check — Strength I  (AASHTO Art. 5.6.3)")
            para("Approach: Rectangular stress block.  No mild steel.  "
                 "Separate capacity for +Mu (sagging) and −Mu (hogging).",
                 italic=True, indent=0.3)
            blank()

            for sign, dp_v, c_v, a_v, fp_v, pMn_v, cdp_v, mux in [
                ("+Mu (sagging, comp. face = TOP)",  dpp, cpp, app, fpp, pMp,  cdpp, mui),
                ("−Mu (hogging, comp. face = BOT)",  dpn, cpn, apn, fpn, abs(pMn_), cdpn, mui),
            ]:
                para(f"─── {sign} ───", bold=True, indent=0.3)
                para(f"  Effective depth  dp = {dp_v*1000:.2f} mm", indent=0.4)
                blank()

                para("  Step 1 — Depth of neutral axis  c  (equilibrium Cc = Ts):",
                     bold=True, indent=0.3)
                formula("  c  =  Aps·fpu / [0.85·f'c·β₁·b·1000  +  k·Aps·fpu / dp]")
                subst( f"     =  {Aps*1e6:.2f}mm²·{fpu:.0f}MPa"
                       f" / [0.85×{fc:.1f}×{beta1:.4f}×1000mm  "
                       f"+  {k_fac:.4f}×{Aps*1e6:.2f}mm²×{fpu:.0f}MPa / {dp_v*1000:.2f}mm]")
                result(f"  c  =  {c_v*1000:.4f} mm")
                blank()

                para("  Step 2 — Depth of equivalent stress block  a:", bold=True, indent=0.3)
                formula("  a  =  β₁ × c")
                subst( f"     =  {beta1:.4f} × {c_v*1000:.4f} mm")
                result(f"  a  =  {a_v*1000:.4f} mm")
                pf(a_v <= dp_v,
                   f"a ({a_v*1000:.2f} mm) ≤ dp ({dp_v*1000:.2f} mm)  — rectangular block valid",
                   f"a ({a_v*1000:.2f} mm) > dp ({dp_v*1000:.2f} mm)  — T-section behaviour!")
                blank()

                para("  Step 3 — Average stress in prestress steel  fps:", bold=True, indent=0.3)
                formula("  fps  =  fpu × [1 − k·(c/dp)]")
                subst( f"      =  {fpu:.0f} × [1 − {k_fac:.4f} × ({c_v*1000:.4f}/{dp_v*1000:.2f})]")
                result(f"  fps  =  {fp_v:.4f} MPa")
                blank()

                para("  Step 4 — Nominal Flexural Resistance  Mn:", bold=True, indent=0.3)
                formula("  Mn   =  Aps·fps·(dp − a/2)")
                subst( f"      =  {Aps*1e6:.2f}mm²  ×  {fp_v:.4f}MPa  "
                       f"×  ({dp_v*1000:.2f} − {a_v*1000:.4f}/2) mm  ×  10⁻⁶")
                result(f"  Mn   =  {pMn_v/phi_flex:.4f} kNm/m")
                blank()

                para("  Step 5 — Factored Resistance  φMn:", bold=True, indent=0.3)
                formula(f"  φMn  =  φ × Mn  =  {phi_flex:.2f} × {pMn_v/phi_flex:.4f}")
                result(f"  φMn  =  {pMn_v:.4f} kNm/m")
                blank()

                para("  Step 6 — Demand / Capacity check  (DCR):", bold=True, indent=0.3)
                if abs(pMn_v) > 0:
                    dcr_v = abs(mux) / abs(pMn_v)
                    pf(abs(mux) <= abs(pMn_v),
                       f"|Mu| = {abs(mux):.4f} kNm/m  ≤  φMn = {abs(pMn_v):.4f} kNm/m  "
                       f"(DCR = {dcr_v:.4f})",
                       f"|Mu| = {abs(mux):.4f} kNm/m  >  φMn = {abs(pMn_v):.4f} kNm/m  "
                       f"(DCR = {dcr_v:.4f})  INSUFFICIENT CAPACITY")
                blank()

                # Ductility check
                para("  Step 7 — Ductility Check  c/dp  (AASHTO 5.7.3.3.1):",
                     bold=True, indent=0.3)
                formula("  c/dp  ≤  0.42")
                result(f"  c/dp  =  {c_v*1000:.4f} / {dp_v*1000:.2f}  =  {cdp_v:.4f}")
                pf(cdp_v <= 0.42,
                   f"c/dp = {cdp_v:.4f}  ≤  0.42  — tension-controlled section",
                   f"c/dp = {cdp_v:.4f}  >  0.42  — section NOT tension-controlled")
                blank()

            # Min reinforcement (AASHTO 5.6.3.3)
            para("─── Minimum Reinforcement  (AASHTO 5.6.3.3) ───", bold=True, indent=0.3)
            formula("Mcr  =  (fr + fpe) × Sb")
            formula(f"     =  ({fr:.4f} MPa  +  {fpe:.4f} MPa)  ×  {float(Sb[i]):.6f} m³")
            result(f"Mcr  =  {Mcri:.4f} kNm/m")
            blank()
            formula("Requirement:  φMn  ≥  min(1.2·Mcr,  1.33·Mu)")
            formula(f"  1.2·Mcr  =  {1.2*Mcri:.4f} kNm/m")
            formula(f"  1.33·Mu  =  {1.33*abs(mui):.4f} kNm/m")
            min_req = min(1.2*Mcri, 1.33*abs(mui))
            result(f"  Governing min requirement  =  {min_req:.4f} kNm/m")
            pf(pMp >= min_req or abs(pMn_) >= min_req,
               f"φMn = {max(pMp, abs(pMn_)):.4f} ≥ {min_req:.4f} kNm/m — min. reinf. satisfied",
               f"φMn = {max(pMp, abs(pMn_)):.4f} < {min_req:.4f} kNm/m — min. reinf. NOT satisfied")
            blank()

            # ── 4.x.6 Shear ─────────────────────────────────────────
            h3(f"4.{ks+1}.6   Shear Strength Check — Strength I  (AASHTO Art. 5.7.3)")
            para("Simplified method: β = 2.0 (minimum transverse reinforcement provided).  "
                 "Vp = 0 (horizontal tendons).  Vs = 0 (conservative for thin flange).",
                 italic=True, indent=0.3)
            blank()

            para("  Step 1 — Effective shear depth  dv  (AASHTO 5.7.2.8):",
                 bold=True, indent=0.3)
            formula("  dv  =  max(0.9·dp,  0.72·t)")
            dp_use_v = max(dpp, dpn)
            formula(f"      =  max(0.9×{dp_use_v*1000:.2f}mm,  0.72×{ti*1000:.2f}mm)")
            result(f"  dv  =  {dvi*1000:.4f} mm")
            blank()

            para("  Step 2 — Concrete shear resistance  Vc  (AASHTO 5.7.3.3-3):",
                 bold=True, indent=0.3)
            formula("  Vc  =  0.083·β·λ·√f'c·bv·dv")
            formula(f"      =  0.083 × 2.0 × 1.0 × √{fc:.1f} × 1000mm × {dvi*1000:.4f}mm  × 10⁻³")
            result(f"  Vc  =  {Vci:.4f} kN/m")
            blank()

            para("  Step 3 — Upper limit  Vn,max  (AASHTO 5.7.3.3-2):",
                 bold=True, indent=0.3)
            formula("  Vn,max  =  0.25·f'c·bv·dv")
            formula(f"         =  0.25 × {fc:.1f}MPa × 1000mm × {dvi*1000:.4f}mm  × 10⁻³")
            result(f"  Vn,max  =  {Vnli:.4f} kN/m")
            blank()

            para("  Step 4 — Nominal shear resistance:", bold=True, indent=0.3)
            formula("  Vn  =  min(Vc, Vn,max)  [Vs=0, Vp=0]")
            Vn_use = min(Vci, Vnli)
            result(f"  Vn  =  {Vn_use:.4f} kN/m")
            blank()

            para("  Step 5 — Factored resistance  φVn:", bold=True, indent=0.3)
            formula(f"  φVn  =  {phi_shear:.2f} × {Vn_use:.4f}")
            result(f"  φVn  =  {pVi:.4f} kN/m")
            blank()

            para("  Step 6 — Demand / Capacity check:", bold=True, indent=0.3)
            pf(vui <= pVi,
               f"Vu = {vui:.4f} kN/m  ≤  φVn = {pVi:.4f} kN/m  "
               f"(DCR = {vui/pVi:.4f})",
               f"Vu = {vui:.4f} kN/m  >  φVn = {pVi:.4f} kN/m  "
               f"(DCR = {vui/pVi:.4f})  INADEQUATE SHEAR CAPACITY")
            blank()

            doc.add_page_break()

        # ══════════════════════════════════════════════════════════════
        # SEC 5 — SUMMARY TABLE
        # ══════════════════════════════════════════════════════════════
        h1("5.  Summary of Results — All Stations")

        sum_rows = []
        for i in sta_idx:
            xi   = float(x_arr[i])
            mui_ = float(mu[i]);  vui_ = float(vu[i])
            s1t_ = float(sv1_top[i]); s1b_ = float(sv1_bot[i])
            pMp_ = float(phi_Mn_pos[i]); pMn__ = float(phi_Mn_neg[i])
            pVi_ = float(phi_Vn[i])
            dcr_m = abs(mui_)/max(pMp_, abs(pMn__))
            dcr_v = vui_/pVi_ if pVi_>0 else 999
            ok_m = "PASS" if abs(mui_) <= max(pMp_, abs(pMn__)) else "FAIL"
            ok_v = "PASS" if vui_ <= pVi_ else "FAIL"
            sum_rows.append([
                f"{xi:.2f}",
                f"{s1t_:.3f}", f"{s1b_:.3f}",
                f"{mui_:.2f}", f"{max(pMp_, abs(pMn__)):.2f}", f"{dcr_m:.3f}", ok_m,
                f"{vui_:.2f}", f"{pVi_:.2f}",                  f"{dcr_v:.3f}", ok_v,
            ])
        table(
            ["x (m)",
             "σ_top (MPa)","σ_bot (MPa)",
             "Mu (kNm/m)","φMn (kNm/m)","DCR_M","M-Status",
             "Vu (kN/m)","φVn (kN/m)","DCR_V","V-Status"],
            sum_rows,
            col_widths_cm=[1.4,1.8,1.8,1.8,1.8,1.4,1.6,1.8,1.8,1.4,1.6]
        )
        blank()

        # ── Conclusion
        h1("6.  Conclusions")
        all_pass_tr  = all(lim_tr_c  <= float(tr_top[i]) <= lim_tr_t  and
                           lim_tr_c  <= float(tr_bot[i]) <= lim_tr_t  for i in sta_idx)
        all_pass_sv  = all(float(sv1_top[i]) >= lim_sv_ct and
                           float(sv3_bot[i]) >= -lim_sv_t for i in sta_idx)
        all_pass_flx = all(abs(float(mu[i])) <= max(float(phi_Mn_pos[i]),
                            abs(float(phi_Mn_neg[i]))) for i in sta_idx)
        all_pass_shr = all(float(vu[i]) <= float(phi_Vn[i]) for i in sta_idx)

        checks = [
            ("Transfer Stress",   all_pass_tr),
            ("Service Stress",    all_pass_sv),
            ("Flexural Strength", all_pass_flx),
            ("Shear Strength",    all_pass_shr),
        ]
        for name, passed in checks:
            pf(passed,
               f"{name}: All stations PASS",
               f"{name}: One or more stations FAIL — revise design")

        blank()
        if all(p for _,p in checks):
            para("► OVERALL: The top flange tendon design is ADEQUATE for all "
                 "applicable AASHTO LRFD limit states.",
                 bold=True, color=C_GREEN)
        else:
            para("► OVERALL: The design does NOT satisfy all limit states. "
                 "Review and revise the tendon layout, spacing, or section geometry.",
                 bold=True, color=C_RED)

        blank()
        para("─── END OF CALCULATION ───", color=C_GRAY,
             align=WD_ALIGN_PARAGRAPH.CENTER)

        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

    # ── Download button in sidebar ───────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.download_button(
            label="📥 Download Calculation Report (.docx)",
            data=make_report(),
            file_name=f"CalcReport_{proj_name.replace(' ','_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    # ─────────────────────────────────────────────────────────────────────
    # 6.  TABS & VISUALISATION
    # ─────────────────────────────────────────────────────────────────────
    def dcr_color(dcr):
        if   dcr <= 0.80: return "background-color:#c6efce; color:#276221"
        elif dcr <= 1.00: return "background-color:#ffeb9c; color:#9c6500"
        else:             return "background-color:#ffc7ce; color:#9c0006"

    def styled_dcr(df_in, col):
        def _style(val):
            try: v = float(val)
            except: return ""
            return dcr_color(v)
        return df_in.style.applymap(_style, subset=[col])

    tabs = st.tabs([
        "📐 Geometry",
        "🚀 Transfer Stress",
        "⚖️ Service Stress",
        "💪 Flexure (Envelope)",
        "🔪 Shear",
        "📋 Summary",
    ])

    # ── Tab 0: Geometry
    with tabs[0]:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x_arr, y=np.zeros(N),  name="Top",    line_color="black"))
        fig.add_trace(go.Scatter(x=x_arr, y=-t, fill="tonexty", name="Section",
                                 fillcolor="rgba(180,210,255,0.3)", line_color="black"))
        fig.add_trace(go.Scatter(x=x_arr, y=-yc, name="CG",
                                 line=dict(color="gray", dash="dot")))
        fig.add_trace(go.Scatter(x=x_arr, y=-z,  name="Tendon",
                                 line=dict(color="red", width=3)))
        fig.update_layout(height=380, xaxis_title="x (m)", yaxis_title="Depth (m)")
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab 1: Transfer
    with tabs[1]:
        st.subheader("Transfer Stress  (Pi + M_DL)  — Net Section")
        fig2 = go.Figure([
            go.Scatter(x=x_arr, y=tr_top, name="Top",  line_color="red"),
            go.Scatter(x=x_arr, y=tr_bot, name="Bottom", line_color="blue"),
        ])
        fig2.add_hline(y=lim_tr_c, line_dash="dash", line_color="orange",
                       annotation_text=f"−0.60f'ci = {lim_tr_c:.2f} MPa")
        fig2.add_hline(y=lim_tr_t, line_dash="dash", line_color="green",
                       annotation_text=f"+0.25√f'ci = +{lim_tr_t:.3f} MPa")
        fig2.update_layout(height=380, xaxis_title="x (m)", yaxis_title="Stress (MPa)")
        st.plotly_chart(fig2, use_container_width=True)
        rows_tr = [{"x (m)": f"{x_arr[i]:.2f}",
                    "σ_top (MPa)": f"{tr_top[i]:.4f}",
                    "σ_bot (MPa)": f"{tr_bot[i]:.4f}",
                    "Status": "✅" if (lim_tr_c<=tr_top[i]<=lim_tr_t and
                                       lim_tr_c<=tr_bot[i]<=lim_tr_t) else "❌"}
                   for i in sta_idx]
        st.dataframe(pd.DataFrame(rows_tr), use_container_width=True)

    # ── Tab 2: Service
    with tabs[2]:
        st.subheader("Service I  &  Service III  — Gross Section")
        fig3 = make_subplots(1, 2, subplot_titles=("Service I", "Service III"))
        for col, tops, bots in [(1, sv1_top, sv1_bot), (2, sv3_top, sv3_bot)]:
            fig3.add_trace(go.Scatter(x=x_arr, y=tops, name="Top",  line_color="red"),   1, col)
            fig3.add_trace(go.Scatter(x=x_arr, y=bots, name="Bot",  line_color="blue"),  1, col)
            fig3.add_hline(y=lim_sv_ct, row=1, col=col,
                           line_dash="dash", line_color="orange")
            fig3.add_hline(y=lim_sv_t,  row=1, col=col,
                           line_dash="dash", line_color="green")
        fig3.update_layout(height=380)
        st.plotly_chart(fig3, use_container_width=True)
        rows_sv = [{"x (m)": f"{x_arr[i]:.2f}",
                    "σ_top SvcI": f"{sv1_top[i]:.4f}",
                    "σ_bot SvcI": f"{sv1_bot[i]:.4f}",
                    "σ_top SvcIII": f"{sv3_top[i]:.4f}",
                    "σ_bot SvcIII": f"{sv3_bot[i]:.4f}",
                    "Status": "✅" if (sv1_top[i]>=lim_sv_ct and sv1_bot[i]>=lim_sv_ct and
                                       sv3_bot[i]>=-lim_sv_t) else "❌"}
                   for i in sta_idx]
        st.dataframe(pd.DataFrame(rows_sv), use_container_width=True)

    # ── Tab 3: Flexure
    with tabs[3]:
        st.subheader("Flexural Strength Envelope")
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=x_arr, y=phi_Mn_pos, name="+φMn",
                                   line=dict(color="green", dash="dash")))
        fig4.add_trace(go.Scatter(x=x_arr, y=phi_Mn_neg, name="−φMn",
                                   line=dict(color="darkgreen", dash="dash")))
        fig4.add_trace(go.Scatter(x=x_arr, y=mu,  name="Mu",
                                   fill="tozeroy", line_color="rgba(220,50,50,0.8)"))
        fig4.update_layout(height=380, xaxis_title="x (m)", yaxis_title="Moment (kNm/m)")
        st.plotly_chart(fig4, use_container_width=True)

        rows_flx = []
        for i in sta_idx:
            mx   = float(mu[i])
            cap  = phi_Mn_pos[i] if mx >= 0 else abs(phi_Mn_neg[i])
            dcr  = abs(mx)/cap if cap>0 else 999
            cdp  = cdp_pos[i] if mx >= 0 else cdp_neg[i]
            ok_m = "✅" if abs(mx) <= cap else "❌"
            ok_d = "✅" if cdp <= 0.42    else "❌"
            rows_flx.append({
                "x (m)":      f"{x_arr[i]:.2f}",
                "Mu (kNm/m)": f"{mx:.4f}",
                "φMn (kNm/m)":f"{cap:.4f}",
                "DCR":        f"{dcr:.4f}",
                "c/dp":       f"{cdp:.4f}",
                "Str.":       ok_m,
                "Ductility":  ok_d,
            })
        df_flx = pd.DataFrame(rows_flx)
        st.dataframe(styled_dcr(df_flx, "DCR"), use_container_width=True)

    # ── Tab 4: Shear
    with tabs[4]:
        st.subheader("Shear Strength  (Simplified Method, β = 2.0)")
        fig5 = go.Figure([
            go.Scatter(x=x_arr, y=phi_Vn, name="φVn", line_color="green"),
            go.Scatter(x=x_arr, y=vu, name="Vu (factored)",
                       fill="tozeroy", line_color="rgba(0,100,220,0.8)"),
        ])
        fig5.update_layout(height=380, xaxis_title="x (m)", yaxis_title="Shear (kN/m)")
        st.plotly_chart(fig5, use_container_width=True)

        rows_shr = []
        for i in sta_idx:
            vui_ = float(vu[i]); pVi_ = float(phi_Vn[i])
            dcr  = vui_/pVi_ if pVi_>0 else 999
            rows_shr.append({
                "x (m)":       f"{x_arr[i]:.2f}",
                "dv (mm)":     f"{dv[i]*1000:.2f}",
                "Vc (kN/m)":   f"{Vc[i]:.4f}",
                "φVn (kN/m)":  f"{pVi_:.4f}",
                "Vu (kN/m)":   f"{vui_:.4f}",
                "DCR":         f"{dcr:.4f}",
                "Status":      "✅" if vui_ <= pVi_ else "❌",
            })
        df_shr = pd.DataFrame(rows_shr)
        st.dataframe(styled_dcr(df_shr, "DCR"), use_container_width=True)

    # ── Tab 5: Overall Summary
    with tabs[5]:
        st.subheader("📋 Overall Design Summary")
        rows_sum = []
        for i in sta_idx:
            mx    = float(mu[i]); vx = float(vu[i])
            cap_m = phi_Mn_pos[i] if mx>=0 else abs(phi_Mn_neg[i])
            dcr_m = abs(mx)/cap_m if cap_m>0 else 999
            dcr_v = vx/phi_Vn[i] if phi_Vn[i]>0 else 999
            ok_tr = (lim_tr_c<=tr_top[i]<=lim_tr_t and lim_tr_c<=tr_bot[i]<=lim_tr_t)
            ok_sv = (sv1_top[i]>=lim_sv_ct and sv3_bot[i]>=-lim_sv_t)
            rows_sum.append({
                "x (m)":     f"{x_arr[i]:.2f}",
                "Transfer":  "✅" if ok_tr else "❌",
                "Service":   "✅" if ok_sv else "❌",
                "DCR_M":     f"{dcr_m:.4f}",
                "Flexure":   "✅" if abs(mx)<=cap_m else "❌",
                "DCR_V":     f"{dcr_v:.4f}",
                "Shear":     "✅" if vx<=phi_Vn[i] else "❌",
            })
        df_sum = pd.DataFrame(rows_sum)
        st.dataframe(styled_dcr(df_sum, "DCR_M"), use_container_width=True)

        all_ok = all(
            r["Transfer"]=="✅" and r["Service"]=="✅" and
            r["Flexure"]=="✅" and r["Shear"]=="✅"
            for r in rows_sum
        )
        if all_ok:
            st.success("✅  DESIGN ADEQUATE — All checks pass at all stations.")
        else:
            st.error("❌  DESIGN INADEQUATE — One or more checks fail. Review design.")

        st.caption(
            "DCR colour: 🟢 ≤ 0.80  |  🟡 0.80–1.00  |  🔴 > 1.00  |  "
            "Sign: compression (−), tension (+)"
        )

except Exception as err:
    st.error(f"Calculation error: {err}")
    raise
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide", page_title="PSC Box Girder — Top Flange Design")

st.title("🏗️ Prestressed Concrete Box Girder — Top Flange Tendon Design")
st.caption("AASHTO LRFD Bridge Design Specifications | 1.0 m Transverse Strip")

# ══════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════
def init_df(key, data):
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(data)

init_df("df_thickness", {
    "Delete": [False, False, False],
    "x (m)": [0.0, 3.0, 6.0],
    "t (m)": [0.30, 0.25, 0.30]
})

init_df("df_tendon", {
    "Delete": [False, False, False],
    "x (m)": [0.0, 3.0, 6.0],
    "z from top (m)": [0.08, 0.20, 0.08]
})

init_df("df_load", {
    "Delete": [False, False, False],
    "x (m)": [0.0, 3.0, 6.0],
    "M_DL (kN·m/m)":  [120,  80, 120],
    "V_DL (kN/m)":    [ 60,  20,  60],
    "M_SDL (kN·m/m)": [ 40,  25,  40],
    "V_SDL (kN/m)":   [ 20,   8,  20],
    "M_LL (kN·m/m)":  [180, 120, 180],
    "V_LL (kN/m)":    [ 80,  30,  80],
})

# ══════════════════════════════════════════════
# SIDEBAR INPUT
# ══════════════════════════════════════════════
st.sidebar.header("⚙️ Input Panel")

# ---------- Section ----------
st.sidebar.subheader("📐 Section Geometry")
width        = st.sidebar.number_input("Total Width (m)", value=6.0, min_value=1.0)
web_thickness = st.sidebar.number_input("Web Thickness (m)", value=0.50, min_value=0.1)
cover        = st.sidebar.number_input("Clear Cover (m)", value=0.04, min_value=0.01)

st.sidebar.markdown("**Flange Thickness Profile**")
df_thickness = st.sidebar.data_editor(
    st.session_state.df_thickness,
    num_rows="dynamic",
    key="thickness_editor",
    use_container_width=True
)

# ---------- Tendon ----------
st.sidebar.subheader("🔩 Tendon Profile")
num_tendon        = st.sidebar.number_input("Number of Tendons (per 1m strip)", value=2, min_value=1)
strands_per_tendon = st.sidebar.number_input("Strands per Tendon", value=12, min_value=1)
duct_dia          = st.sidebar.number_input("Duct Diameter (m)", value=0.070, min_value=0.01)

st.sidebar.markdown("**Tendon CG from Top Profile**")
df_tendon = st.sidebar.data_editor(
    st.session_state.df_tendon,
    num_rows="dynamic",
    key="tendon_editor",
    use_container_width=True
)

# ---------- Material ----------
st.sidebar.subheader("🧱 Material & Prestress")
fc      = st.sidebar.number_input("f'c (MPa)", value=40.0, min_value=20.0)
fpu     = st.sidebar.number_input("fpu (MPa)", value=1860, min_value=1600)
fpy_ratio = st.sidebar.selectbox("fpy/fpu", [0.90, 0.85], index=0,
                                  help="Low-relaxation=0.90, Stress-relieved=0.85")
aps_strand = st.sidebar.number_input("Aps per strand (mm²)", value=140.0, min_value=50.0)
eff     = st.sidebar.slider("Effective Prestress Ratio (Pe/Pi)", 0.50, 0.95, 0.80,
                             help="Typical 0.75–0.85 after all losses")
phi_flex = st.sidebar.number_input("φ (Flexure)", value=1.00, min_value=0.75, max_value=1.0)
phi_shear = st.sidebar.number_input("φ (Shear)", value=0.90, min_value=0.70, max_value=1.0)

# ---------- Loads ----------
st.sidebar.subheader("📦 Service Loads (per 1m strip)")
df_load = st.sidebar.data_editor(
    st.session_state.df_load,
    num_rows="dynamic",
    key="load_editor",
    use_container_width=True
)

# ══════════════════════════════════════════════
# HELPER: CLEAN DATAFRAME
# ══════════════════════════════════════════════
def clean_df(df, xcol="x (m)"):
    df = df.copy()
    if "Delete" in df.columns:
        df["Delete"] = df["Delete"].fillna(False)
        df = df[df["Delete"] == False].drop(columns=["Delete"])
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna()
    df = df.drop_duplicates(subset=xcol)
    df = df.sort_values(xcol).reset_index(drop=True)
    return df

df_thk = clean_df(df_thickness)
df_tdn = clean_df(df_tendon)
df_ld  = clean_df(df_load)

# ══════════════════════════════════════════════
# CALCULATION GRID
# ══════════════════════════════════════════════
N = 400
x_plot = np.linspace(0, width, N)

# Geometry
t  = np.interp(x_plot, df_thk["x (m)"], df_thk["t (m)"])      # flange thickness (m)
z  = np.interp(x_plot, df_tdn["x (m)"], df_tdn["z from top (m)"]) # tendon depth from top (m)

# Section properties (1m strip, rectangular)
b  = 1.0          # strip width (m)
A  = b * t
yc = t / 2        # centroid from top
I  = b * t**3 / 12
St = I / yc       # section modulus top
Sb = I / yc       # symmetric → same

# Effective tendon area
aps_m2    = aps_strand * 1e-6        # m² per strand
total_str = int(num_tendon * strands_per_tendon)
Aps       = total_str * aps_m2        # total per 1m strip (m²)

# Effective prestress force (compression = negative by convention; use magnitude here)
fse   = fpu * eff                    # MPa
Pe    = Aps * fse * 1e3              # kN (positive magnitude)

# Eccentricity: positive if tendon below centroid (sagging), negative if above
e = yc - z   # m  (positive = tendon below CG → hogging relief at bottom)

# ══════════════════════════════════════════════
# LOADS
# ══════════════════════════════════════════════
if len(df_ld) >= 2:
    M_DL  = np.interp(x_plot, df_ld["x (m)"], df_ld["M_DL (kN·m/m)"])
    V_DL  = np.interp(x_plot, df_ld["x (m)"], df_ld["V_DL (kN/m)"])
    M_SDL = np.interp(x_plot, df_ld["x (m)"], df_ld["M_SDL (kN·m/m)"])
    V_SDL = np.interp(x_plot, df_ld["x (m)"], df_ld["V_SDL (kN/m)"])
    M_LL  = np.interp(x_plot, df_ld["x (m)"], df_ld["M_LL (kN·m/m)"])
    V_LL  = np.interp(x_plot, df_ld["x (m)"], df_ld["V_LL (kN/m)"])

    # AASHTO LRFD Strength I
    Mu = 1.25*M_DL + 1.50*M_SDL + 1.75*M_LL    # kN·m/m
    Vu = 1.25*V_DL + 1.50*V_SDL + 1.75*V_LL    # kN/m

    # Service I (compression check)
    Ms1 = M_DL + M_SDL + M_LL
    # Service III (tension check — for PSC)
    Ms3 = M_DL + M_SDL + 0.8*M_LL
else:
    st.error("Need at least 2 load points"); st.stop()

if len(df_thk) < 2 or len(df_tdn) < 2:
    st.error("Need at least 2 points for thickness / tendon profile"); st.stop()

# ══════════════════════════════════════════════
# TAB LAYOUT
# ══════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📐 Section View",
    "📊 Load Diagram",
    "✅ Stress Check (Service)",
    "💪 Flexural Strength (Strength I)",
    "🔪 Shear Check (Strength I)"
])

# ══════════════════════════════════════════════════════════════
# TAB 1 — SECTION VIEW
# ══════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Section Profile & Tendon Layout")

    col1, col2 = st.columns([3,1])

    with col1:
        fig = go.Figure()

        # Top surface
        fig.add_trace(go.Scatter(x=x_plot, y=np.zeros(N),
                                  fill=None, mode="lines",
                                  line=dict(color="black", width=2), name="Top Surface"))
        # Bottom surface
        fig.add_trace(go.Scatter(x=x_plot, y=-t,
                                  fill="tonexty", fillcolor="rgba(180,200,255,0.3)",
                                  mode="lines", line=dict(color="black", width=2),
                                  name="Bottom Surface"))
        # CG line
        fig.add_trace(go.Scatter(x=x_plot, y=-yc,
                                  mode="lines", line=dict(color="gray", dash="dot", width=1),
                                  name="Section CG"))
        # Tendon profile
        fig.add_trace(go.Scatter(x=x_plot, y=-z,
                                  mode="lines", line=dict(color="red", width=3),
                                  name="Tendon CG"))
        # Web lines
        fig.add_vline(x=web_thickness/2,       line_dash="dash", line_color="orange", annotation_text="Web")
        fig.add_vline(x=width-web_thickness/2, line_dash="dash", line_color="orange")

        fig.update_layout(
            height=400,
            xaxis_title="Transverse Position x (m)",
            yaxis_title="Depth (m)",
            legend=dict(orientation="h"),
            yaxis=dict(autorange=True)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Section Summary**")
        st.metric("Total Width", f"{width:.2f} m")
        st.metric("Min Thickness", f"{t.min():.3f} m")
        st.metric("Max Thickness", f"{t.max():.3f} m")
        st.metric("Total Strands (1m)", f"{total_str}")
        st.metric("Aps (1m strip)", f"{Aps*1e4:.2f} cm²")
        st.metric("Pe (effective)", f"{Pe:.1f} kN")

# ══════════════════════════════════════════════════════════════
# TAB 2 — LOAD DIAGRAM
# ══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Load Distribution — AASHTO LRFD")

    fig2 = make_subplots(rows=1, cols=2,
                          subplot_titles=("Factored Moment Mu (kN·m/m)",
                                          "Factored Shear Vu (kN/m)"))

    fig2.add_trace(go.Scatter(x=x_plot, y=Mu, name="Mu (Str-I)",
                               line=dict(color="crimson", width=2)), row=1, col=1)
    fig2.add_trace(go.Scatter(x=x_plot, y=M_DL,  name="M_DL",  line=dict(dash="dash")), row=1, col=1)
    fig2.add_trace(go.Scatter(x=x_plot, y=M_SDL, name="M_SDL", line=dict(dash="dot")),  row=1, col=1)
    fig2.add_trace(go.Scatter(x=x_plot, y=M_LL,  name="M_LL",  line=dict(dash="dashdot")), row=1, col=1)

    fig2.add_trace(go.Scatter(x=x_plot, y=Vu, name="Vu (Str-I)",
                               line=dict(color="navy", width=2)), row=1, col=2)
    fig2.add_trace(go.Scatter(x=x_plot, y=V_DL,  name="V_DL",  line=dict(dash="dash")), row=1, col=2)
    fig2.add_trace(go.Scatter(x=x_plot, y=V_SDL, name="V_SDL", line=dict(dash="dot")),  row=1, col=2)
    fig2.add_trace(go.Scatter(x=x_plot, y=V_LL,  name="V_LL",  line=dict(dash="dashdot")), row=1, col=2)

    fig2.update_layout(height=420, legend=dict(orientation="h"))
    st.plotly_chart(fig2, use_container_width=True)

    st.info(f"**Strength I:** 1.25·DC + 1.50·DW + 1.75·LL  |  "
            f"**Service I (compression):** 1.0·DC + 1.0·DW + 1.0·LL  |  "
            f"**Service III (tension):** 1.0·DC + 1.0·DW + 0.8·LL")

# ══════════════════════════════════════════════════════════════
# TAB 3 — STRESS CHECK (SERVICE)
# ══════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Stress Check — Service Limit State (AASHTO LRFD 5.9.2)")

    # -------- Allowable Stress (AASHTO LRFD Table 5.9.2.3.2a-1 / 5.9.2.3.1a-1) --------
    f_allow_comp_perm   =  0.45 * fc     # MPa  compression under permanent load
    f_allow_comp_total  =  0.60 * fc     # MPa  compression under total load
    f_allow_tens_bonded = -0.50 * np.sqrt(fc)  # MPa  tension (bonded tendons, Svc III)
    f_allow_tens_none   =  0.0            # MPa  no tension allowed (unbonded)

    # -------- Stress calculation --------
    # Prestress contribution (axial + bending from eccentricity)
    # Sign: compression = negative
    sig_P_top = -(Pe / A) + (Pe * e * yc / I)     # kN/m² → need /1000 for MPa? No: Pe in kN, A in m²
    sig_P_bot = -(Pe / A) - (Pe * e * yc / I)     # Pe·e·y/I in kN·m/m³ = kN/m² → /1000 = MPa

    # Convert to MPa (kN/m² = 0.001 MPa)
    sig_P_top_MPa = sig_P_top / 1000.0
    sig_P_bot_MPa = sig_P_bot / 1000.0

    # Service I — compression governs (total load)
    sig_M1_top = -Ms1 * yc / I / 1000.0   # negative = compression for sagging moment
    sig_M1_bot =  Ms1 * yc / I / 1000.0   # tension for sagging at bottom

    # Service III — tension check
    sig_M3_top = -Ms3 * yc / I / 1000.0
    sig_M3_bot =  Ms3 * yc / I / 1000.0

    sigma_svcI_top = sig_P_top_MPa + sig_M1_top
    sigma_svcI_bot = sig_P_bot_MPa + sig_M1_bot

    sigma_svcIII_top = sig_P_top_MPa + sig_M3_top
    sigma_svcIII_bot = sig_P_bot_MPa + sig_M3_bot

    # -------- Plot --------
    fig3 = make_subplots(rows=1, cols=2,
                          subplot_titles=("Service I — Compression Check",
                                          "Service III — Tension Check"))

    fig3.add_trace(go.Scatter(x=x_plot, y=sigma_svcI_top, name="Top Fiber",
                               line=dict(color="red", width=2)), row=1, col=1)
    fig3.add_trace(go.Scatter(x=x_plot, y=sigma_svcI_bot, name="Bottom Fiber",
                               line=dict(color="blue", width=2)), row=1, col=1)
    fig3.add_hline(y=-f_allow_comp_total,  row=1, col=1,
                   line_dash="dash", line_color="red",
                   annotation_text=f"−0.60f'c = {-f_allow_comp_total:.1f} MPa")
    fig3.add_hline(y=-f_allow_comp_perm,   row=1, col=1,
                   line_dash="dot",  line_color="orange",
                   annotation_text=f"−0.45f'c = {-f_allow_comp_perm:.1f} MPa")

    fig3.add_trace(go.Scatter(x=x_plot, y=sigma_svcIII_top, name="Top (SvcIII)",
                               line=dict(color="red",  dash="dot", width=2)), row=1, col=2)
    fig3.add_trace(go.Scatter(x=x_plot, y=sigma_svcIII_bot, name="Bottom (SvcIII)",
                               line=dict(color="blue", dash="dot", width=2)), row=1, col=2)
    fig3.add_hline(y=f_allow_tens_bonded, row=1, col=2,
                   line_dash="dash", line_color="green",
                   annotation_text=f"0.5√f'c = {f_allow_tens_bonded:.2f} MPa (tension limit)")
    fig3.add_hline(y=0, row=1, col=2, line_dash="dash", line_color="gray")

    fig3.update_layout(height=450, legend=dict(orientation="h"))
    for r, c in [(1,1),(1,2)]:
        fig3.update_yaxes(title_text="Stress (MPa)", row=r, col=c)
        fig3.update_xaxes(title_text="x (m)", row=r, col=c)
    st.plotly_chart(fig3, use_container_width=True)

    # -------- Pass/Fail Summary --------
    st.subheader("📋 Stress Check Summary")

    checks_stress = []
    locs = ["x=0", "x=L/2", "x=L"]
    idxs = [0, N//2, -1]

    for label, i in zip(locs, idxs):
        # Svc I compression
        top_I   = sigma_svcI_top[i]
        bot_I   = sigma_svcI_bot[i]
        top_III = sigma_svcIII_top[i]
        bot_III = sigma_svcIII_bot[i]

        c_top = "✅" if top_I >= -f_allow_comp_total else "❌"
        c_bot = "✅" if bot_I >= -f_allow_comp_total else "❌"
        t_top = "✅" if top_III >= f_allow_tens_bonded else "❌"
        t_bot = "✅" if bot_III >= f_allow_tens_bonded else "❌"

        checks_stress.append({
            "Location": label,
            "σ top SvcI (MPa)": f"{top_I:.2f}",
            "Limit": f"≥ {-f_allow_comp_total:.1f}",
            "Status C-Top": c_top,
            "σ bot SvcI (MPa)": f"{bot_I:.2f}",
            "Status C-Bot": c_bot,
            "σ top SvcIII (MPa)": f"{top_III:.2f}",
            "Status T-Top": t_top,
            "σ bot SvcIII (MPa)": f"{bot_III:.2f}",
            "Status T-Bot": t_bot,
        })

    st.dataframe(pd.DataFrame(checks_stress), use_container_width=True)
    st.caption("Compression = negative | −0.60f'c = total load | −0.45f'c = permanent load | Tension limit = 0.5√f'c (bonded)")

# ══════════════════════════════════════════════════════════════
# TAB 4 — FLEXURAL STRENGTH (STRENGTH I)
# ══════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Flexural Strength Check — Strength I (AASHTO LRFD 5.6.3)")

    # dp = effective depth from compression face to tendon CG
    # For top flange: compression face depends on sign of moment
    # Assume sagging moment (positive) → compression at top, tension at bottom
    dp = t - z   # depth from top to tendon (m)  [= distance to tendon from compression face]

    # β₁ (AASHTO LRFD 5.6.2.2)
    beta1 = np.clip(0.85 - 0.05*(fc - 28.0)/7.0, 0.65, 0.85)

    # k factor (AASHTO LRFD C5.6.3.1.1)
    k = 2.0 * (1.04 - fpy_ratio)    # Low-relax: k=0.28

    # Solve for c (neutral axis depth from compression face) — rectangular section, no mild steel
    # Aps·fps = 0.85·f'c·β₁·b·c  →  fps = fpu(1 - k·c/dp)
    # → c = Aps·fpu / (0.85·f'c·β₁·b + k·Aps·fpu/dp)
    c = (Aps * fpu) / (0.85 * fc * beta1 * b * 1000.0 + k * Aps * fpu / dp)  # m
    # (fc in MPa, fpu in MPa, Aps in m², b in m  → numerator kN, denominator kN/m → c in m)

    fps = fpu * (1.0 - k * c / dp)   # MPa

    # a = β₁·c
    a = beta1 * c    # m

    # Mn = Aps·fps·(dp − a/2)
    Mn = Aps * fps * (dp - a/2.0) * 1000.0    # kN·m/m  (Aps m², fps MPa=kN/m², dp m)

    phi_Mn = phi_flex * Mn     # kN·m/m

    # Minimum reinforcement (AASHTO LRFD 5.6.3.3)
    # Mcr = (fr + fpe)·Sb  — simplified check
    fr   = 0.63 * np.sqrt(fc)   # MPa  modulus of rupture
    fpe  = Pe / A / 1000.0      # MPa  axial prestress
    Mcr  = (fr + fpe) * Sb / 1000.0  # kN·m/m
    phi_Mn_min = 1.33 * Mu     # kN·m/m alternative

    # -------- Plot --------
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=x_plot, y=phi_Mn, name="φMn (capacity)",
                               line=dict(color="green", width=2.5)))
    fig4.add_trace(go.Scatter(x=x_plot, y=Mu, name="Mu (demand)",
                               line=dict(color="crimson", width=2.5)))
    fig4.add_trace(go.Scatter(x=x_plot, y=Mcr, name="Mcr (cracking)",
                               line=dict(color="orange", dash="dot", width=1.5)))

    fig4.update_layout(
        height=420,
        xaxis_title="x (m)",
        yaxis_title="Moment (kN·m/m)",
        legend=dict(orientation="h")
    )
    st.plotly_chart(fig4, use_container_width=True)

    # -------- Flexure Data Table --------
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("β₁", f"{beta1:.3f}")
        st.metric("k", f"{k:.3f}")

    with col2:
        c_mid = c[N//2]; fps_mid = fps[N//2]; a_mid = a[N//2]
        st.metric("c (midspan)", f"{c_mid*100:.1f} cm")
        st.metric("fps (midspan)", f"{fps_mid:.0f} MPa")

    with col3:
        st.metric("φMn (midspan)", f"{phi_Mn[N//2]:.1f} kN·m/m")
        st.metric("Mu (midspan)",  f"{Mu[N//2]:.1f} kN·m/m")

    # -------- Pass/Fail --------
    st.subheader("📋 Flexural Strength Check Summary")

    checks_flex = []
    for label, i in zip(locs, idxs):
        ratio = Mu[i] / phi_Mn[i] if phi_Mn[i] > 0 else 999
        status = "✅" if Mu[i] <= phi_Mn[i] else "❌"
        min_ok = "✅" if phi_Mn[i] >= min(1.2*Mcr[i], phi_Mn_min[i]) else "❌"
        checks_flex.append({
            "Location":        label,
            "dp (m)":          f"{(t-z)[i]:.3f}",
            "c (m)":           f"{c[i]:.4f}",
            "fps (MPa)":       f"{fps[i]:.1f}",
            "a (m)":           f"{a[i]:.4f}",
            "φMn (kN·m/m)":    f"{phi_Mn[i]:.2f}",
            "Mu (kN·m/m)":     f"{Mu[i]:.2f}",
            "DCR (Mu/φMn)":    f"{ratio:.3f}",
            "Str. Status":     status,
            "Min. Reinf.":     min_ok,
        })

    st.dataframe(pd.DataFrame(checks_flex), use_container_width=True)
    st.caption("DCR = Demand/Capacity Ratio — must be ≤ 1.00 | Min reinforcement: φMn ≥ 1.2·Mcr")

# ══════════════════════════════════════════════════════════════
# TAB 5 — SHEAR CHECK (STRENGTH I)
# ══════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Shear Check — Strength I (AASHTO LRFD 5.7.3 Simplified)")

    # Effective shear depth (AASHTO LRFD 5.7.2.8)
    dv = np.maximum(0.9 * dp, 0.72 * t)   # m

    # Net longitudinal tensile strain εs (simplified — ignore prestress effect → conservative)
    # Using simplified approach: θ = 45°, β from table or simplified β
    # Simplified procedure (AASHTO LRFD 5.7.3.4.3): β = 2.0 for sections with min Av
    beta_v = 2.0
    lambda_factor = 1.0  # normal weight concrete

    # Vc = 0.083·β·λ·√f'c·bv·dv  (MPa, m)
    bv = b    # 1.0 m strip
    Vc = 0.083 * beta_v * lambda_factor * np.sqrt(fc) * bv * dv * 1000.0  # kN/m

    # Assume minimum transverse reinforcement provided → Vs
    # Av_min = 0.083·√f'c·bv·s/fvy  — use Vs=0 for conservative (no stirrups typical in flange)
    Vs = np.zeros(N)   # kN/m (conservative — no stirrups in thin flange)

    # Vp = vertical component of prestress (assume 0 for horizontal tendons in top flange)
    Vp = np.zeros(N)

    Vn = Vc + Vs + Vp   # kN/m
    Vn_limit = 0.25 * fc * bv * dv * 1000.0  # kN/m  (upper limit)
    Vn_final = np.minimum(Vn, Vn_limit)

    phi_Vn = phi_shear * Vn_final   # kN/m

    # -------- Plot --------
    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(x=x_plot, y=phi_Vn, name="φVn (capacity)",
                               line=dict(color="green", width=2.5)))
    fig5.add_trace(go.Scatter(x=x_plot, y=Vu, name="Vu (demand)",
                               line=dict(color="crimson", width=2.5)))
    fig5.add_trace(go.Scatter(x=x_plot, y=Vc, name="Vc only",
                               line=dict(color="blue", dash="dot", width=1.5)))

    fig5.update_layout(
        height=420,
        xaxis_title="x (m)",
        yaxis_title="Shear (kN/m)",
        legend=dict(orientation="h")
    )
    st.plotly_chart(fig5, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("dv (midspan)", f"{dv[N//2]*100:.1f} cm")
        st.metric("Vc (midspan)", f"{Vc[N//2]:.1f} kN/m")
    with col2:
        st.metric("φVn (midspan)", f"{phi_Vn[N//2]:.1f} kN/m")
        st.metric("Vu (midspan)",  f"{Vu[N//2]:.1f} kN/m")

    # -------- Pass/Fail --------
    st.subheader("📋 Shear Check Summary")

    checks_shear = []
    for label, i in zip(locs, idxs):
        ratio  = Vu[i] / phi_Vn[i] if phi_Vn[i] > 0 else 999
        status = "✅" if Vu[i] <= phi_Vn[i] else "❌"
        checks_shear.append({
            "Location":        label,
            "dv (m)":          f"{dv[i]:.3f}",
            "Vc (kN/m)":       f"{Vc[i]:.2f}",
            "Vn_limit (kN/m)": f"{Vn_limit[i]:.2f}",
            "φVn (kN/m)":      f"{phi_Vn[i]:.2f}",
            "Vu (kN/m)":       f"{Vu[i]:.2f}",
            "DCR (Vu/φVn)":    f"{ratio:.3f}",
            "Status":          status,
        })

    st.dataframe(pd.DataFrame(checks_shear), use_container_width=True)
    st.caption("Simplified method: β=2.0 | Vs=0 (no stirrups assumed in top flange) | "
               "Vn ≤ 0.25f'c·bv·dv (AASHTO 5.7.3.3-2)")

    st.info("⚠️ If shear fails, consider adding transverse reinforcement or increasing flange thickness.")

# ══════════════════════════════════════════════════════════════
# OVERALL SUMMARY
# ══════════════════════════════════════════════════════════════
st.divider()
st.subheader("🏁 Overall Design Summary")

all_pass_stress_comp = all(sigma_svcI_top[i] >= -f_allow_comp_total and
                            sigma_svcI_bot[i] >= -f_allow_comp_total for _,i in zip(locs, idxs))
all_pass_stress_tens = all(sigma_svcIII_bot[i] >= f_allow_tens_bonded for _,i in zip(locs, idxs))
all_pass_flex        = all(Mu[i] <= phi_Mn[i] for _,i in zip(locs, idxs))
all_pass_shear       = all(Vu[i] <= phi_Vn[i] for _,i in zip(locs, idxs))

summary_data = {
    "Check": [
        "Service I — Compression (0.60f'c)",
        "Service III — Tension (0.5√f'c)",
        "Flexural Strength (Strength I)",
        "Shear Strength (Strength I)",
    ],
    "Criterion": [
        f"σ ≥ −{f_allow_comp_total:.1f} MPa",
        f"σ ≥ {f_allow_tens_bonded:.2f} MPa",
        "Mu ≤ φMn",
        "Vu ≤ φVn",
    ],
    "Result": [
        "✅ PASS" if all_pass_stress_comp else "❌ FAIL",
        "✅ PASS" if all_pass_stress_tens else "❌ FAIL",
        "✅ PASS" if all_pass_flex        else "❌ FAIL",
        "✅ PASS" if all_pass_shear       else "❌ FAIL",
    ]
}

df_summary = pd.DataFrame(summary_data)
st.dataframe(df_summary, use_container_width=True, hide_index=True)

overall = all([all_pass_stress_comp, all_pass_stress_tens, all_pass_flex, all_pass_shear])
if overall:
    st.success("✅ Design is ADEQUATE for all checks per AASHTO LRFD.")
else:
    st.error("❌ Design FAILS one or more checks. Review Input Panel and adjust tendon layout or section geometry.")

st.caption("Note: This tool performs preliminary design checks. Final design must be verified by a licensed engineer.")
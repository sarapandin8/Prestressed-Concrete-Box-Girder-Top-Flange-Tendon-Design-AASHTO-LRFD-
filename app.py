import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ══════════════════════════════════════════════
# 1. APP CONFIG & SESSION STATE
# ══════════════════════════════════════════════
st.set_page_config(layout="wide", page_title="PSC Box Girder — Top Flange Design")

def init_df(key, data):
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(data)

# Initial Data (ตัวอย่างตำแหน่ง Web ที่ 0.0 และ 6.0, กลางปีกที่ 3.0)
init_df("df_thickness", {"x (m)": [0.0, 3.0, 6.0], "t (m)": [0.30, 0.25, 0.30]})
init_df("df_tendon", {"x (m)": [0.0, 3.0, 6.0], "z from top (m)": [0.08, 0.18, 0.08]})
init_df("df_load", {
    "x (m)": [0.0, 3.0, 6.0],
    "M_DL (kN·m)":  [-120, 80, -120], # โมเมนต์ลบที่ Web, บวกที่กลางปีก
    "V_DL (kN)":    [60, 0, 60],
    "M_SDL (kN·m)": [-40, 25, -40],
    "V_SDL (kN)":   [20, 0, 20],
    "M_LL (kN·m)":  [-180, 120, -180],
    "V_LL (kN)":    [80, 0, 80],
})

# ══════════════════════════════════════════════
# 2. SIDEBAR INPUTS
# ══════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Design Parameters")
    
    with st.expander("📐 Section & Materials", expanded=True):
        width = st.number_input("Total Width (m)", value=6.0)
        fc = st.number_input("f'c (MPa) @ Service", value=40.0)
        fci = st.number_input("f'ci (MPa) @ Transfer", value=30.0)
        fpu = st.number_input("fpu (MPa)", value=1860.0)
        fpy_ratio = st.selectbox("fpy/fpu", [0.90, 0.85], index=0)
        aps_strand = st.number_input("Area per strand (mm²)", value=140.0)

    with st.expander("🔩 Prestressing Force", expanded=True):
        num_tendon = st.number_input("Tendons per 1m strip", value=2)
        strands_per_tendon = st.number_input("Strands per Tendon", value=12)
        fpi_ratio = st.slider("Initial Stress (fpi/fpu)", 0.70, 0.80, 0.75)
        init_loss = st.slider("Initial Loss @ Transfer (%)", 0, 15, 5)
        eff_ratio = st.slider("Total Effective Ratio (Pe/Pi)", 0.50, 0.95, 0.80)

    with st.expander("⚖️ Resistance Factors (φ)"):
        phi_flex = st.number_input("φ Flexure", value=1.0)
        phi_shear = st.number_input("φ Shear", value=0.9)

# ══════════════════════════════════════════════
# 3. DATA PROCESSING
# ══════════════════════════════════════════════
# Editor tables in main area
col_ed1, col_ed2 = st.columns(2)
with col_ed1:
    st.subheader("📏 Geometry & Tendon Profile")
    df_thk = st.data_editor(st.session_state.df_thickness, num_rows="dynamic", use_container_width=True)
    df_tdn = st.data_editor(st.session_state.df_tendon, num_rows="dynamic", use_container_width=True)
with col_ed2:
    st.subheader("📦 Load Stations")
    df_ld = st.data_editor(st.session_state.df_load, num_rows="dynamic", use_container_width=True)

# Interpolation
N = 400
x_plot = np.linspace(0, width, N)
t = np.interp(x_plot, df_thk["x (m)"], df_thk["t (m)"])
z = np.interp(x_plot, df_tdn["x (m)"], df_tdn["z from top (m)"])

M_DL = np.interp(x_plot, df_ld["x (m)"], df_ld["M_DL (kN·m)"])
M_SDL = np.interp(x_plot, df_ld["x (m)"], df_ld["M_SDL (kN·m)"])
M_LL = np.interp(x_plot, df_ld["x (m)"], df_ld["M_LL (kN·m)"])
V_DL = np.interp(x_plot, df_ld["x (m)"], df_ld["V_DL (kN)"])
V_SDL = np.interp(x_plot, df_ld["x (m)"], df_ld["V_SDL (kN)"])
V_LL = np.interp(x_plot, df_ld["x (m)"], df_ld["V_LL (kN)"])

# Load Combinations
Ms1 = M_DL + M_SDL + M_LL
Ms3 = M_DL + M_SDL + 0.8 * M_LL
Mu = 1.25 * M_DL + 1.50 * M_SDL + 1.75 * M_LL
Vu = 1.25 * V_DL + 1.50 * V_SDL + 1.75 * V_LL

# Section Properties (1m strip)
A = 1.0 * t
I = (1.0 * t**3) / 12
yc = t / 2
e = yc - z  # Positive = Tendon above CG (Hogging), Negative = Tendon below CG (Sagging)

# Forces
Aps = (num_tendon * strands_per_tendon) * (aps_strand * 1e-6) # m²
Pi = Aps * (fpu * fpi_ratio * (1 - init_loss/100)) * 1e3 # kN
Pe = Pi * eff_ratio # kN

# ══════════════════════════════════════════════
# 4. CALCULATIONS (Transfer, Service, Strength)
# ══════════════════════════════════════════════

# --- STRESS AT TRANSFER ---
sig_Pi_top = -(Pi/A)/1000 + (Pi*e*(t/2)/I)/1000
sig_Pi_bot = -(Pi/A)/1000 + (Pi*e*(-t/2)/I)/1000
sig_MDL_top = -(M_DL*(t/2)/I)/1000
sig_MDL_bot = -(M_DL*(-t/2)/I)/1000
sigma_trans_top = sig_Pi_top + sig_MDL_top
sigma_trans_bot = sig_Pi_bot + sig_MDL_bot

# --- STRESS AT SERVICE ---
sig_Pe_top = -(Pe/A)/1000 + (Pe*e*(t/2)/I)/1000
sig_Pe_bot = -(Pe/A)/1000 + (Pe*e*(-t/2)/I)/1000
sig_Ms1_top = -(Ms1*(t/2)/I)/1000
sig_Ms1_bot = -(Ms1*(-t/2)/I)/1000
sigma_svcI_top = sig_Pe_top + sig_Ms1_top
sigma_svcI_bot = sig_Pe_bot + sig_Ms1_bot

# --- FLEXURAL STRENGTH ---
dp = np.where(Mu < 0, z, t - z) # Adaptive dp
beta1 = np.clip(0.85 - 0.05*(fc - 28.0)/7.0, 0.65, 0.85)
k = 2.0 * (1.04 - fpy_ratio)
# Solve for c & fps
c = (Aps * fpu) / (0.85 * fc * beta1 * 1.0 * 1000 + k * Aps * fpu / dp)
fps = fpu * (1.0 - k * c / dp)
phi_Mn = phi_flex * (Aps * fps * (dp - (beta1 * c) / 2) * 1000)

# --- SHEAR STRENGTH ---
dv = np.maximum(0.9 * dp, 0.72 * t)
Vc = 0.083 * 2.0 * 1.0 * np.sqrt(fc) * 1.0 * dv * 1000 # kN
phi_Vn = phi_shear * Vc

# ══════════════════════════════════════════════
# 5. TABS & VISUALIZATION
# ══════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📐 Geometry", "🚀 Transfer Stress", "⚖️ Service Stress", "💪 Flexure", "🔪 Shear"
])

# Utility for Tables
input_stations = df_ld["x (m)"].values
idx_res = [np.abs(x_plot - val).argmin() for val in input_stations]

with tab1:
    fig_geo = go.Figure()
    fig_geo.add_trace(go.Scatter(x=x_plot, y=np.zeros(N), name="Top", line=dict(color='black')))
    fig_geo.add_trace(go.Scatter(x=x_plot, y=-t, fill='tonexty', name="Bottom", line=dict(color='black')))
    fig_geo.add_trace(go.Scatter(x=x_plot, y=-z, name="Tendon CG", line=dict(color='red', width=3)))
    fig_geo.update_layout(title="Transverse Section Profile", yaxis_title="Depth (m)", xaxis_title="x (m)")
    st.plotly_chart(fig_geo, use_container_width=True)

with tab2:
    st.subheader("Stress at Transfer (Stage: Pi + M_DL)")
    f_all_comp_tr = -0.60 * fci
    f_all_tens_tr = 0.25 * np.sqrt(fci)
    
    fig_tr = go.Figure()
    fig_tr.add_trace(go.Scatter(x=x_plot, y=sigma_trans_top, name="Top Fiber", line=dict(color='red')))
    fig_tr.add_trace(go.Scatter(x=x_plot, y=sigma_trans_bot, name="Bottom Fiber", line=dict(color='blue')))
    fig_tr.add_hline(y=f_all_comp_tr, line_dash="dash", line_color="orange", annotation_text="Comp Limit")
    fig_tr.add_hline(y=f_all_tens_tr, line_dash="dash", line_color="green", annotation_text="Tens Limit")
    st.plotly_chart(fig_tr, use_container_width=True)
    
    res_tr = [{"x": x_plot[i], "Top": f"{sigma_trans_top[i]:.2f}", "Bot": f"{sigma_trans_bot[i]:.2f}", "Status": "✅" if (f_all_comp_tr <= sigma_trans_top[i] <= f_all_tens_tr) else "❌"} for i in idx_res]
    st.table(pd.DataFrame(res_tr))

with tab3:
    st.subheader("Stress at Service (Stage: Pe + Ms1)")
    f_all_comp_svc = -0.60 * fc
    f_all_tens_svc = 0.50 * np.sqrt(fc)
    
    fig_svc = go.Figure()
    fig_svc.add_trace(go.Scatter(x=x_plot, y=sigma_svcI_top, name="Top Fiber", line=dict(color='red')))
    fig_svc.add_trace(go.Scatter(x=x_plot, y=sigma_svcI_bot, name="Bottom Fiber", line=dict(color='blue')))
    fig_svc.add_hline(y=f_all_comp_svc, line_dash="dash", line_color="orange")
    fig_svc.add_hline(y=f_all_tens_svc, line_dash="dash", line_color="green")
    st.plotly_chart(fig_svc, use_container_width=True)

with tab4:
    st.subheader("Flexural Strength Check (Strength I)")
    fig_mn = go.Figure()
    fig_mn.add_trace(go.Scatter(x=x_plot, y=phi_Mn, name="Capacity (phi*Mn)", line=dict(color='green', width=3)))
    fig_mn.add_trace(go.Scatter(x=x_plot, y=np.abs(Mu), name="Demand (|Mu|)", fill='tozeroy', line=dict(color='red')))
    st.plotly_chart(fig_mn, use_container_width=True)
    
    res_flex = [{"x (m)": x_plot[i], "Mu": f"{Mu[i]:.1f}", "phi*Mn": f"{phi_Mn[i]:.1f}", "dp (mm)": f"{dp[i]*1000:.0f}", "DCR": f"{np.abs(Mu[i])/phi_Mn[i]:.3f}"} for i in idx_res]
    st.dataframe(pd.DataFrame(res_flex), use_container_width=True)

with tab5:
    st.subheader("Shear Strength Check (Strength I)")
    fig_vn = go.Figure()
    fig_vn.add_trace(go.Scatter(x=x_plot, y=phi_Vn, name="Capacity (phi*Vn)", line=dict(color='green', width=3)))
    fig_vn.add_trace(go.Scatter(x=x_plot, y=np.abs(Vu), name="Demand (|Vu|)", fill='tozeroy', line=dict(color='blue')))
    st.plotly_chart(fig_vn, use_container_width=True)
    
    res_shear = [{"x (m)": x_plot[i], "Vu": f"{Vu[i]:.1f}", "phi*Vn": f"{phi_Vn[i]:.1f}", "dv (mm)": f"{dv[i]*1000:.0f}", "DCR": f"{np.abs(Vu[i])/phi_Vn[i]:.3f}"} for i in idx_res]
    st.dataframe(pd.DataFrame(res_shear), use_container_width=True)
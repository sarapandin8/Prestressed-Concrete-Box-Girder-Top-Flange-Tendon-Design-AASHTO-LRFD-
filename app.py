import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# 1. APP CONFIG
st.set_page_config(layout="wide", page_title="PSC Box Girder Design")

def init_df(key, data):
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(data)

# Initializing Data
init_df("df_thickness", {"x (m)": [0.0, 3.0, 6.0], "t (m)": [0.30, 0.25, 0.30]})
init_df("df_tendon", {"x (m)": [0.0, 3.0, 6.0], "z from top (m)": [0.08, 0.18, 0.08]})
init_df("df_load", {
    "x (m)": [0.0, 3.0, 6.0],
    "M_DL (kNm)": [-120.0, 80.0, -120.0],
    "V_DL (kN)": [60.0, 0.0, 60.0],
    "M_SDL (kNm)": [-40.0, 25.0, -40.0],
    "V_SDL (kN)": [20.0, 0.0, 20.0],
    "M_LL (kNm)": [-180.0, 120.0, -180.0],
    "V_LL (kN)": [80.0, 0.0, 80.0],
})

# 2. SIDEBAR
with st.sidebar:
    st.header("⚙️ Design Parameters")
    width = st.number_input("Total Width (m)", value=6.0)
    fc = st.number_input("f'c (MPa)", value=40.0)
    fci = st.number_input("f'ci (MPa)", value=30.0)
    fpu = st.number_input("fpu (MPa)", value=1860.0)
    fpy_ratio = st.selectbox("fpy/fpu", [0.90, 0.85], index=0)
    aps_strand = st.number_input("Area per strand (mm²)", value=140.0)
    
    st.subheader("Prestressing")
    num_tendon = st.number_input("Tendons/m", value=2)
    strands_per_tendon = st.number_input("Strands/Tendon", value=12)
    fpi_ratio = st.slider("fpi/fpu", 0.70, 0.80, 0.75)
    init_loss = st.slider("Initial Loss (%)", 0, 15, 5)
    eff_ratio = st.slider("Pe/Pi Ratio", 0.50, 0.95, 0.80)
    
    phi_flex = 1.0
    phi_shear = 0.9

# 3. MAIN UI
st.title("🏗️ PSC Box Girder — Top Flange Design")
col1, col2 = st.columns(2)
with col1:
    df_thk = st.data_editor(st.session_state.df_thickness, num_rows="dynamic", key="ed_thk")
    df_tdn = st.data_editor(st.session_state.df_tendon, num_rows="dynamic", key="ed_tdn")
with col2:
    df_ld = st.data_editor(st.session_state.df_load, num_rows="dynamic", key="ed_ld")

# 4. CALCULATION
def prepare_data(df):
    return df.dropna().sort_values("x (m)")

try:
    dft, dfp, dfl = prepare_data(df_thk), prepare_data(df_tdn), prepare_data(df_ld)
    N = 400
    x_plot = np.linspace(0, width, N)
    
    t = np.interp(x_plot, dft["x (m)"], dft["t (m)"])
    z = np.interp(x_plot, dfp["x (m)"], dfp["z from top (m)"])
    m_dl = np.interp(x_plot, dfl["x (m)"], dfl["M_DL (kNm)"])
    m_sdl = np.interp(x_plot, dfl["x (m)"], dfl["M_SDL (kNm)"])
    m_ll = np.interp(x_plot, dfl["x (m)"], dfl["M_LL (kNm)"])
    v_total = np.interp(x_plot, dfl["x (m)"], dfl["V_DL (kN)"]) + \
               np.interp(x_plot, dfl["x (m)"], dfl["V_SDL (kN)"]) + \
               np.interp(x_plot, dfl["x (m)"], dfl["V_LL (kN)"])

    ms1 = m_dl + m_sdl + m_ll
    mu = 1.25 * m_dl + 1.50 * m_sdl + 1.75 * m_ll
    
    area, inertia, yc = 1.0*t, (1.0*t**3)/12, t/2
    ecc = yc - z
    aps_total = (num_tendon * strands_per_tendon) * (aps_strand * 1e-6)
    pi_force = aps_total * (fpu * fpi_ratio * (1 - init_loss/100)) * 1e3
    pe_force = pi_force * eff_ratio

    # Stress Functions
    def get_stress(P, M, e_val, t_val, I_val, A_val):
        f_a = -(P/A_val)/1000
        s_p_t, s_p_b = f_a + (P*e_val*(t_val/2)/I_val)/1000, f_a + (P*e_val*(-t_val/2)/I_val)/1000
        s_m_t, s_m_b = -(M*(t_val/2)/I_val)/1000, -(M*(-t_val/2)/I_val)/1000
        return s_p_t + s_m_t, s_p_b + s_m_b

    tr_t, tr_b = get_stress(pi_force, m_dl, ecc, t, inertia, area)
    sv_t, sv_b = get_stress(pe_force, ms1, ecc, t, inertia, area)

    # Strength (Envelope)
    b1 = np.clip(0.85 - 0.05*(fc - 28.0)/7.0, 0.65, 0.85)
    k = 2.0 * (1.04 - fpy_ratio)
    
    def calc_mn(dp_val):
        c = (aps_total * fpu) / (0.85 * fc * b1 * 1000 + k * aps_total * fpu / dp_val)
        fps = fpu * (1.0 - k * c / dp_val)
        return phi_flex * (aps_total * fps * (dp_val - (b1 * c) / 2) * 1000)

    phi_mn_pos, phi_mn_neg = calc_mn(t-z), -calc_mn(z)

    # 5. TABS
    tabs = st.tabs(["📐 Geo", "🚀 Transfer", "⚖️ Service", "💪 Flexure", "🔪 Shear"])
    idx = [np.abs(x_plot - v).argmin() for v in dfl["x (m)"].values]

    with tabs[0]:
        fig = go.Figure([go.Scatter(x=x_plot, y=-t, fill='tozeroy', name="Section", line_color='black'),
                         go.Scatter(x=x_plot, y=-z, name="Tendon", line=dict(color='red', width=3))])
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        f_c_tr, f_t_tr = -0.6 * fci, 0.25 * np.sqrt(fci)
        fig2 = go.Figure([go.Scatter(x=x_plot, y=tr_t, name="Top"), go.Scatter(x=x_plot, y=tr_b, name="Bot")])
        fig2.add_hline(y=f_c_tr, line_dash="dash", line_color="orange")
        fig2.add_hline(y=f_t_tr, line_dash="dash", line_color="green")
        st.plotly_chart(fig2, use_container_width=True)

    with tabs[3]:
        st.subheader("Moment Envelope")
        fig4 = go.Figure([go.Scatter(x=x_plot, y=phi_mn_pos, name="+Mn Cap", line=dict(color='green', dash='dash')),
                          go.Scatter(x=x_plot, y=phi_mn_neg, name="-Mn Cap", line=dict(color='darkgreen', dash='dash')),
                          go.Scatter(x=x_plot, y=mu, name="Mu Demand", fill='tozeroy', line_color='red')])
        st.plotly_chart(fig4, use_container_width=True)
        
        res = [{"x": x_plot[i], "Mu": f"{mu[i]:.1f}", "DCR": f"{abs(mu[i])/(phi_mn_pos[i] if mu[i]>=0 else abs(phi_mn_neg[i])):.3f}"} for i in idx]
        st.table(pd.DataFrame(res))

except Exception as e:
    st.error(f"Error: {e}")
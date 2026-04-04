import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ══════════════════════════════════════════════
# 1. APP CONFIG & INITIALIZATION
# ══════════════════════════════════════════════
st.set_page_config(layout="wide", page_title="PSC Box Girder — Top Flange Design")

# ฟังก์ชันจัดการ Session State เพื่อให้ค่าไม่หายเมื่อกดปุ่มอื่น
def init_df(key, data):
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(data)

# กำหนดชื่อคอลัมน์ให้มาตรฐาน (Standard Column Names)
# ใช้ "M_DL (kNm)" แทน "M_DL (kN·m)" เพื่อลดปัญหา Encoding
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

# ══════════════════════════════════════════════
# 2. SIDEBAR INPUTS
# ══════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Design Parameters")
    
    with st.expander("📐 Materials", expanded=True):
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
# 3. MAIN INTERFACE - DATA EDITORS
# ══════════════════════════════════════════════
st.title("🏗️ PSC Box Girder — Top Flange Design")

col_ed1, col_ed2 = st.columns(2)
with col_ed1:
    st.subheader("📏 Geometry & Tendon")
    df_thk = st.data_editor(st.session_state.df_thickness, num_rows="dynamic", key="ed_thk")
    df_tdn = st.data_editor(st.session_state.df_tendon, num_rows="dynamic", key="ed_tdn")

with col_ed2:
    st.subheader("📦 Load Stations")
    df_ld = st.data_editor(st.session_state.df_load, num_rows="dynamic", key="ed_ld")

# ══════════════════════════════════════════════
# 4. CALCULATION ENGINE
# ══════════════════════════════════════════════

# Helper Function: ล้างข้อมูลและเรียงลำดับ x เพื่อป้องกัน Error ใน np.interp
def prepare_data(df):
    return df.dropna().sort_values("x (m)")

try:
    dft = prepare_data(df_thk)
    dfp = prepare_data(df_tdn)
    dfl = prepare_data(df_ld)

    # Interpolation Array (400 จุด เพื่อความละเอียดของกราฟ)
    N = 400
    x_plot = np.linspace(0, width, N)
    
    t = np.interp(x_plot, dft["x (m)"], dft["t (m)"])
    z = np.interp(x_plot, dfp["x (m)"], dfp["z from top (m)"])
    
    m_dl = np.interp(x_plot, dfl["x (m)"], dfl["M_DL (kNm)"])
    m_sdl = np.interp(x_plot, dfl["x (m)"], dfl["M_SDL (kNm)"])
    m_ll = np.interp(x_plot, dfl["x (m)"], dfl["M_LL (kNm)"])
    
    v_dl = np.interp(x_plot, dfl["x (m)"], dfl["V_DL (kN)"])
    v_sdl = np.interp(x_plot, dfl["x (m)"], dfl["V_SDL (kN)"])
   import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ══════════════════════════════════════════════
# 1. APP CONFIG & INITIALIZATION
# ══════════════════════════════════════════════
st.set_page_config(layout="wide", page_title="PSC Box Girder — Top Flange Design")

def init_df(key, data):
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(data)

# ใช้ชื่อคอลัมน์มาตรฐานเพื่อป้องกัน KeyError
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

# ══════════════════════════════════════════════
# 2. SIDEBAR INPUTS
# ══════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Design Parameters")
    
    with st.expander("📐 Materials", expanded=True):
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
# 3. MAIN INTERFACE - DATA EDITORS
# ══════════════════════════════════════════════
st.title("🏗️ PSC Box Girder — Top Flange Design")

col_ed1, col_ed2 = st.columns(2)
with col_ed1:
    st.subheader("📏 Geometry & Tendon")
    df_thk = st.data_editor(st.session_state.df_thickness, num_rows="dynamic", key="ed_thk")
    df_tdn = st.data_editor(st.session_state.df_tendon, num_rows="dynamic", key="ed_tdn")

with col_ed2:
    st.subheader("📦 Load Stations")
    df_ld = st.data_editor(st.session_state.df_load, num_rows="dynamic", key="ed_ld")

# ══════════════════════════════════════════════
# 4. CALCULATION ENGINE
# ══════════════════════════════════════════════

def prepare_data(df):
    return df.dropna().sort_values("x (m)")

try:
    dft = prepare_data(df_thk)
    dfp = prepare_data(df_tdn)
    dfl = prepare_data(df_ld)

    N = 400
    x_plot = np.linspace(0, width, N)
    
    t = np.interp(x_plot, dft["x (m)"], dft["t (m)"])
    z = np.interp(x_plot, dfp["x (m)"], dfp["z from top (m)"])
    
    m_dl = np.interp(x_plot, dfl["x (m)"], dfl["M_DL (kNm)"])
    m_sdl = np.interp(x_plot, dfl["x (m)"], dfl["M_SDL (kNm)"])
    m_ll = np.interp(x_plot, dfl["x (m)"], dfl["M_LL (kNm)"])
    v_dl = np.interp(x_plot, dfl["x (m)"], dfl["V_DL (kN)"])
    v_sdl = np.interp(x_plot, dfl["x (m)"], dfl["V_SDL (kN)"])
    v_ll = np.interp(x_plot, dfl["x (m)"], dfl["V_LL (kN)"])

    ms1 = m_dl + m_sdl + m_ll
    mu = 1.25 * m_dl + 1.50 * m_sdl + 1.75 * m_ll
    vu = 1.25 * v_dl + 1.50 * v_sdl + 1.75 * v_ll

    area = 1.0 * t
    inertia = (1.0 * t**3) / 12
    yc = t / 2
    ecc = yc - z  # (+) Tendon Above CG, (-) Tendon Below CG

    aps_total = (num_tendon * strands_per_tendon) * (aps_strand * 1e-6)
    pi_force = aps_total * (fpu * fpi_ratio * (1 - init_loss/100)) * 1e3
    pe_force = pi_force * eff_ratio

    # --- STRESS ANALYSIS (Consistent Sign) ---
    def calc_stresses(P, M, e_val, t_val, I_val, A_val):
        f_axial = -(P/A_val)/1000
        sig_P_top = f_axial + (P * e_val * (t_val/2) / I_val) / 1000
        sig_P_bot = f_axial + (P * e_val * (-t_val/2) / I_val) / 1000
        sig_M_top = -(M * (t_val/2) / I_val) / 1000
        sig_M_bot = -(M * (-t_val/2) / I_val) / 1000
        return sig_P_top + sig_M_top, sig_P_bot + sig_M_bot

    stress_trans_top, stress_trans_bot = calc_stresses(pi_force, m_dl, ecc, t, inertia, area)
    stress_svc_top, stress_svc_bot = calc_stresses(pe_force, ms1, ecc, t, inertia, area)

    # --- STRENGTH ANALYSIS (Envelope Logic) ---
    beta1 = np.clip(0.85 - 0.05*(fc - 28.0)/7.0, 0.65, 0.85)
    k_fact = 2.0 * (1.04 - fpy_ratio)

    def calc_phiMn(dp_val):
        # คำนวณหา Mn สำหรับค่า dp ที่กำหนด
        c_val = (aps_total * fpu) / (0.85 * fc * beta1 * 1.0 * 1000 + k_fact * aps_total * fpu / dp_val)
        fps_val = fpu * (1.0 - k_fact * c_val / dp_val)
        return phi_flex * (aps_total * fps_val * (dp_val - (beta1 * c_val) / 2) * 1000)

    # 1. Positive Capacity (Compression at Top, dp from top to tendon)
    phi_mn_pos = calc_phiMn(t - z)
    # 2. Negative Capacity (Compression at Bottom, dp from bottom to tendon)
    phi_mn_neg = -1.0 * calc_phiMn(z)

    # Shear
    dv_eff = np.maximum(0.9 * (t-z), 0.72 * t)
    phi_vn_cap = phi_shear * (0.083 * 2.0 * 1.0 * np.sqrt(fc) * 1.0 * dv_eff * 1000)

    # ══════════════════════════════════════════════
    # 5. TABS & VISUALIZATION
    # ══════════════════════════════════════════════
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📐 Geometry", "🚀 Transfer Stress", "⚖️ Service Stress", "💪 Flexure (Envelope)", "🔪 Shear"
    ])

    idx_res = [np.abs(x_plot - val).argmin() for val in dfl["x (m)"].values]

    with tab1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=x_plot, y=np.zeros(N), name="Top Surface", line=dict(color='black')))
        fig1.add_trace(go.Scatter(x=x_plot, y=-t, fill='tonexty', name="Bottom Surface", line=dict(color='black')))
        fig1.add_trace(go.Scatter(x=x_plot, y=-z, name="Tendon CG", line=dict(color='red', width=3)))
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader("Stress Check @ Transfer")
        f_comp_tr, f_tens_tr = -0.60 * fci, 0.25 * np.sqrt(fci)
        fig2 = go.Figure([
            go.Scatter(x=x_plot, y=stress_trans_top, name="Top", line=dict(color='red')),
            go.Scatter(x=x_plot, y=stress_trans_bot, name="Bottom", line=dict(color='blue'))
        ])
        fig2.add_hline(y=f_comp_tr, line_dash="dash", line_color="orange")
        fig2.add_hline(y=f_tens_tr, line_dash="dash", line_color="green")
        st.plotly_chart(fig2, use_container_width=True)
        
        tr_res = [{"x": x_plot[i], "Top": f"{stress_trans_top[i]:.2f}", "Bot": f"{stress_trans_bot[i]:.2f}", "Status": "✅" if (f_comp_tr <= stress_trans_top[i] <= f_tens_tr) and (f_comp_tr <= stress_trans_bot[i] <= f_tens_tr) else "❌"} for i in idx_res]
        st.table(pd.DataFrame(tr_res))

    with tab3:
        st.subheader("Stress Check @ Service")
        f_comp_svc, f_tens_svc = -0.60 * fc, 0.50 * np.sqrt(fc)
        fig3 = go.Figure([
            go.Scatter(x=x_plot, y=stress_svc_top, name="Top", line=dict(color='red')),
            go.Scatter(x=x_plot, y=stress_svc_bot, name="Bottom", line=dict(color='blue'))
        ])
        fig3.add_hline(y=f_comp_svc, line_dash="dash", line_color="orange")
        fig3.add_hline(y=f_tens_svc, line_dash="dash", line_color="green")
        st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        st.subheader("Flexural Capacity Envelope (Continuous)")
        fig4 = go.Figure()
        # พล็อต Capacity เป็นขอบเขต บน-ล่าง
        fig4.add_trace(go.Scatter(x=x_plot, y=phi_mn_pos, name="+phi*Mn (Sagging Cap)", line=dict(color='green', width=2, dash='dash')))
        fig4.add_trace(go.Scatter(x=x_plot, y=phi_mn_neg, name="-phi*Mn (Hogging Cap)", line=dict(color='darkgreen', width=2, dash='dash')))
        # พล็อต Demand (Mu จริง)
        fig4.add_trace(go.Scatter(x=x_plot, y=mu, name="Mu (Actual Demand)", fill='tozeroy', line=dict(color='rgba(255, 0, 0, 0.8)', width=3)))
        
        fig4.update_layout(yaxis_title="Moment (kNm)", title="Moment Demand vs Capacity Envelope")
        st.plotly_chart(fig4, use_container_width=True)
        
        # ตารางสรุป (เลือกว่าจุดนั้น Mu เป็นบวกหรือลบ เพื่อเช็ค DCR)
        flx_res = []
        for i in idx_res:
            cap = phi_mn_pos[i] if mu[i] >= 0 else np.abs(phi_mn_neg[i])
            dcr = np.abs(mu[i]) / cap
            flx_res.append({"x": x_plot[i], "Mu": f"{mu[i]:.1f}", "phi*Mn": f"{cap:.1f}", "DCR": f"{dcr:.3f}", "Status": "✅" if dcr <= 1.0 else "❌"})
        st.dataframe(pd.DataFrame(flx_res), use_container_width=True)

    with tab5:
        st.subheader("Shear Strength")
        fig5 = go.Figure([
            go.Scatter(x=x_plot, y=phi_vn_cap, name="phi*Vn", line=dict(color='green', width=3)),
            go.Scatter(x=x_plot, y=np.abs(vu), name="|Vu|", fill='tozeroy', line=dict(color='blue'))
        ])
        st.plotly_chart(fig5, use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Calculation Error: {e}")
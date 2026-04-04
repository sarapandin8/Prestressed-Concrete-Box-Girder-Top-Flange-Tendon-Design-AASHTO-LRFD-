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
    v_ll = np.interp(x_plot, dfl["x (m)"], dfl["V_LL (kN)"])

    # Combinations
    ms1 = m_dl + m_sdl + m_ll
    ms3 = m_dl + m_sdl + 0.8 * m_ll
    mu = 1.25 * m_dl + 1.50 * m_sdl + 1.75 * m_ll
    vu = 1.25 * v_dl + 1.50 * v_sdl + 1.75 * v_ll

    # Section Properties
    area = 1.0 * t
    inertia = (1.0 * t**3) / 12
    yc = t / 2
    ecc = yc - z  # Positive = Tendon above CG

    # Prestress Forces
    aps_total = (num_tendon * strands_per_tendon) * (aps_strand * 1e-6)
    pi_force = aps_total * (fpu * fpi_ratio * (1 - init_loss/100)) * 1e3 # kN
    pe_force = pi_force * eff_ratio # kN

    # --- STRESS ANALYSIS ---
    # Transfer Stage (Pi + M_DL)
    sig_pi_top = -(pi_force/area)/1000 + (pi_force*ecc*(-t/2)/inertia)/1000
    sig_pi_bot = -(pi_force/area)/1000 + (pi_force*ecc*(t/2)/inertia)/1000
    sig_mdl_top = -(m_dl*(t/2)/inertia)/1000
    sig_mdl_bot = -(m_dl*(-t/2)/inertia)/1000
    stress_trans_top = sig_pi_top + sig_mdl_top
    stress_trans_bot = sig_pi_bot + sig_mdl_bot

    # Service Stage (Pe + Ms1)
    sig_pe_top = -(pe_force/area)/1000 + (pe_force*ecc*(-t/2)/inertia)/1000
    sig_pe_bot = -(pe_force/area)/1000 + (pe_force*ecc*(t/2)/inertia)/1000
    sig_ms1_top = -(ms1*(t/2)/inertia)/1000
    sig_ms1_bot = -(ms1*(-t/2)/inertia)/1000
    stress_svc_top = sig_pe_top + sig_ms1_top
    stress_svc_bot = sig_pe_bot + sig_ms1_bot

    # --- STRENGTH ANALYSIS ---
    # Flexure
    dp_eff = np.where(mu < 0, z, t - z)
    beta1 = np.clip(0.85 - 0.05*(fc - 28.0)/7.0, 0.65, 0.85)
    k_fact = 2.0 * (1.04 - fpy_ratio)
    c_dist = (aps_total * fpu) / (0.85 * fc * beta1 * 1.0 * 1000 + k_fact * aps_total * fpu / dp_eff)
    fps_stress = fpu * (1.0 - k_fact * c_dist / dp_eff)
    phi_mn_cap = phi_flex * (aps_total * fps_stress * (dp_eff - (beta1 * c_dist) / 2) * 1000)

    # Shear (Simplified)
    dv_eff = np.maximum(0.9 * dp_eff, 0.72 * t)
    vc_cap = 0.083 * 2.0 * 1.0 * np.sqrt(fc) * 1.0 * dv_eff * 1000
    phi_vn_cap = phi_shear * vc_cap

    # ══════════════════════════════════════════════
    # 5. TABS & VISUALIZATION
    # ══════════════════════════════════════════════
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📐 Geometry", "🚀 Transfer Stress", "⚖️ Service Stress", "💪 Flexure", "🔪 Shear"
    ])

    # ค้นหา Index ของจุดที่ User กรอกไว้ใน Load Stations เพื่อทำตาราง
    idx_res = [np.abs(x_plot - val).argmin() for val in dfl["x (m)"].values]

    with tab1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=x_plot, y=np.zeros(N), name="Top Surface", line=dict(color='black')))
        fig1.add_trace(go.Scatter(x=x_plot, y=-t, fill='tonexty', name="Bottom Surface", line=dict(color='black')))
        fig1.add_trace(go.Scatter(x=x_plot, y=-z, name="Tendon CG", line=dict(color='red', width=3)))
        fig1.update_layout(title="Transverse Section & Tendon Profile", yaxis_title="Depth (m)", xaxis_title="x (m)")
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader("Stress Check @ Transfer (Pi + M_DL)")
        f_comp_tr = -0.60 * fci
        f_tens_tr = 0.25 * np.sqrt(fci)
        
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=x_plot, y=stress_trans_top, name="Top Stress", line=dict(color='red')))
        fig2.add_trace(go.Scatter(x=x_plot, y=stress_trans_bot, name="Bottom Stress", line=dict(color='blue')))
        fig2.add_hline(y=f_comp_tr, line_dash="dash", line_color="orange", annotation_text="Compression Limit")
        fig2.add_hline(y=f_tens_tr, line_dash="dash", line_color="green", annotation_text="Tension Limit")
        st.plotly_chart(fig2, use_container_width=True)
        
        # ตารางสรุปจุดที่ User กรอก
        tr_data = [{"Station x": x_plot[i], "Top (MPa)": f"{stress_trans_top[i]:.2f}", "Bot (MPa)": f"{stress_trans_bot[i]:.2f}", 
                    "Status": "✅" if (f_comp_tr <= stress_trans_top[i] <= f_tens_tr) and (f_comp_tr <= stress_trans_bot[i] <= f_tens_tr) else "❌"} for i in idx_res]
        st.dataframe(pd.DataFrame(tr_data), use_container_width=True)

    with tab3:
        st.subheader("Stress Check @ Service (Pe + Ms1)")
        f_comp_svc = -0.60 * fc
        f_tens_svc = 0.50 * np.sqrt(fc)
        
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=x_plot, y=stress_svc_top, name="Top Stress", line=dict(color='red')))
        fig3.add_trace(go.Scatter(x=x_plot, y=stress_svc_bot, name="Bottom Stress", line=dict(color='blue')))
        fig3.add_hline(y=f_comp_svc, line_dash="dash", line_color="orange")
        fig3.add_hline(y=f_tens_svc, line_dash="dash", line_color="green")
        st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        st.subheader("Flexural Strength (Strength I)")
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=x_plot, y=phi_mn_cap, name="phi*Mn (Capacity)", line=dict(color='green', width=3)))
        fig4.add_trace(go.Scatter(x=x_plot, y=np.abs(mu), name="|Mu| (Demand)", fill='tozeroy', line=dict(color='red')))
        st.plotly_chart(fig4, use_container_width=True)
        
        flx_data = [{"Station x": x_plot[i], "Mu (kNm)": f"{mu[i]:.1f}", "phi*Mn (kNm)": f"{phi_mn_cap[i]:.1f}", "DCR": f"{np.abs(mu[i])/phi_mn_cap[i]:.3f}",
                     "Status": "✅" if np.abs(mu[i]) <= phi_mn_cap[i] else "❌"} for i in idx_res]
        st.dataframe(pd.DataFrame(flx_data), use_container_width=True)

    with tab5:
        st.subheader("Shear Strength (Strength I)")
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=x_plot, y=phi_vn_cap, name="phi*Vn (Capacity)", line=dict(color='green', width=3)))
        fig5.add_trace(go.Scatter(x=x_plot, y=np.abs(vu), name="|Vu| (Demand)", fill='tozeroy', line=dict(color='blue')))
        st.plotly_chart(fig5, use_container_width=True)
        
        shr_data = [{"Station x": x_plot[i], "Vu (kN)": f"{vu[i]:.1f}", "phi*Vn (kN)": f"{phi_vn_cap[i]:.1f}", "DCR": f"{np.abs(vu[i])/phi_vn_cap[i]:.3f}",
                     "Status": "✅" if np.abs(vu[i]) <= phi_vn_cap[i] else "❌"} for i in idx_res]
        st.dataframe(pd.DataFrame(shr_data), use_container_width=True)

except Exception as e:
    st.error(f"⚠️ เกิดข้อผิดพลาดในการคำนวณ: {e}")
    st.info("ตรวจสอบว่าคุณกรอกข้อมูลในตารางครบถ้วนและไม่มีค่าที่ผิดปกติ")
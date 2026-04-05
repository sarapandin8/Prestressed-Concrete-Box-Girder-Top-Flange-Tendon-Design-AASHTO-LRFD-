import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from docx import Document
from docx.shared import Inches, Pt
from io import BytesIO
import datetime

# ══════════════════════════════════════════════
# 1. APP CONFIG & INITIALIZATION
# ══════════════════════════════════════════════
st.set_page_config(layout="wide", page_title="PSC Box Girder — Top Flange Design")

def init_df(key, data):
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(data)

# กำหนดค่าเริ่มต้นของข้อมูลในตาราง
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

    st.markdown("---")
    st.subheader("📄 Export Report")
    proj_name = st.text_input("Project Name", "Bridge Lane Expansion")
    eng_name = st.text_input("Engineer Name", "Your Name")

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
# 4. CALCULATION ENGINE (Original Logic)
# ══════════════════════════════════════════════
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

    area, inertia, yc = 1.0 * t, (1.0 * t**3) / 12, t / 2
    ecc = yc - z  # (+) Tendon Above CG, (-) Tendon Below CG

    aps_total = (num_tendon * strands_per_tendon) * (aps_strand * 1e-6)
    pi_force = aps_total * (fpu * fpi_ratio * (1 - init_loss/100)) * 1e3
    pe_force = pi_force * eff_ratio

    def get_stresses(P, M, e_val, t_val, I_val, A_val):
        f_axial = -(P/A_val)/1000
        sig_P_top = f_axial + (P * e_val * (-t_val/2) / I_val) / 1000
        sig_P_bot = f_axial + (P * e_val * (t_val/2) / I_val) / 1000
        sig_M_top = -(M * (t_val/2) / I_val) / 1000
        sig_M_bot = -(M * (-t_val/2) / I_val) / 1000
        return sig_P_top + sig_M_top, sig_P_bot + sig_M_bot

    tr_top, tr_bot = get_stresses(pi_force, m_dl, ecc, t, inertia, area)
    sv_top, sv_bot = get_stresses(pe_force, ms1, ecc, t, inertia, area)

    beta1 = np.clip(0.85 - 0.05*(fc - 28.0)/7.0, 0.65, 0.85)
    k_fact = 2.0 * (1.04 - fpy_ratio)

    def calc_phiMn(dp_val):
        c = (aps_total * fpu) / (0.85 * fc * beta1 * 1000 + k_fact * aps_total * fpu / dp_val)
        fps = fpu * (1.0 - k_fact * c / dp_val)
        return phi_flex * (aps_total * fps * (dp_val - (beta1 * c) / 2) * 1000)

    phi_mn_pos, phi_mn_neg = calc_phiMn(t - z), -calc_phiMn(z)

    # ══════════════════════════════════════════════
    # 🌟 NEW: WORD EXPORT LOGIC
    # ══════════════════════════════════════════════
    def generate_report():
        doc = Document()
        # Title
        title = doc.add_heading('Structural Calculation Report', 0)
        doc.add_paragraph(f"Project: {proj_name}")
        doc.add_paragraph(f"Engineer: {eng_name}")
        doc.add_paragraph(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # 1. Materials
        doc.add_heading('1. Material Properties & Standard Reference', level=1)
        doc.add_paragraph("Design Code: AASHTO LRFD Bridge Design Specifications", style='List Bullet')
        doc.add_paragraph(f"Concrete Strength: fc' = {fc} MPa, fci' = {fci} MPa", style='List Bullet')
        doc.add_paragraph(f"Prestressing Steel: fpu = {fpu} MPa (Low Relaxation Strands)", style='List Bullet')

        # 2. Stress Limits
        doc.add_heading('2. Allowable Stress Limits', level=1)
        doc.add_paragraph(f"Transfer Stage (AASHTO 5.9.2.3.1): Compression {0.6*fci:.2f} MPa, Tension {0.25*np.sqrt(fci):.2f} MPa")
        doc.add_paragraph(f"Service Stage (AASHTO 5.9.2.3.2): Compression {0.6*fc:.2f} MPa, Tension {0.50*np.sqrt(fc):.2f} MPa")

        # 3. Strength Table
        doc.add_heading('3. Strength and Stress Summary Table', level=1)
        table = doc.add_table(rows=1, cols=6)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        cols = ["X (m)", "Mu (kNm)", "phi*Mn", "DCR", "S-Top", "S-Bot"]
        for i, name in enumerate(cols): hdr_cells[i].text = name

        idx_report = [np.abs(x_plot - v).argmin() for v in dfl["x (m)"].values]
        for i in idx_report:
            row = table.add_row().cells
            cap = phi_mn_pos[i] if mu[i] >= 0 else abs(phi_mn_neg[i])
            row[0].text = f"{x_plot[i]:.2f}"
            row[1].text = f"{mu[i]:.1f}"
            row[2].text = f"{cap:.1f}"
            row[3].text = f"{abs(mu[i])/cap:.3f}"
            row[4].text = f"{sv_top[i]:.2f}"
            row[5].text = f"{sv_bot[i]:.2f}"

        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

    st.sidebar.download_button(
        label="📥 Download Word Report",
        data=generate_report(),
        file_name=f"Report_{proj_name}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    # ══════════════════════════════════════════════
    # 5. TABS & VISUALIZATION (Original Logic)
    # ══════════════════════════════════════════════
    tabs = st.tabs(["📐 Geometry", "🚀 Transfer Stress", "⚖️ Service Stress", "💪 Flexure (Envelope)", "🔪 Shear"])
    idx = [np.abs(x_plot - v).argmin() for v in dfl["x (m)"].values]

    with tabs[0]:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=x_plot, y=np.zeros(N), name="Top Surface", line_color='black'))
        fig1.add_trace(go.Scatter(x=x_plot, y=-t, fill='tonexty', name="Section", line_color='black'))
        fig1.add_trace(go.Scatter(x=x_plot, y=-z, name="Tendon", line=dict(color='red', width=3)))
        st.plotly_chart(fig1, use_container_width=True)

    with tabs[1]:
        st.subheader("Stress Check @ Transfer (Pi + M_DL)")
        f_c_tr, f_t_tr = -0.6 * fci, 0.25 * np.sqrt(fci)
        fig2 = go.Figure([
            go.Scatter(x=x_plot, y=tr_top, name="Top", line_color='red'),
            go.Scatter(x=x_plot, y=tr_bot, name="Bottom", line_color='blue')
        ])
        fig2.add_hline(y=f_c_tr, line_dash="dash", line_color="orange")
        fig2.add_hline(y=f_t_tr, line_dash="dash", line_color="green")
        st.plotly_chart(fig2, use_container_width=True)
        tr_df = [{"x": x_plot[i], "Top": f"{tr_top[i]:.2f}", "Bot": f"{tr_bot[i]:.2f}", "Status": "✅" if (f_c_tr <= tr_top[i] <= f_t_tr) and (f_c_tr <= tr_bot[i] <= f_t_tr) else "❌"} for i in idx]
        st.dataframe(pd.DataFrame(tr_df), use_container_width=True)

    with tabs[2]:
        st.subheader("Stress Check @ Service (Pe + Ms1)")
        f_c_sv, f_t_sv = -0.6 * fc, 0.50 * np.sqrt(fc)
        fig3 = go.Figure([
            go.Scatter(x=x_plot, y=sv_top, name="Top", line_color='red'),
            go.Scatter(x=x_plot, y=sv_bot, name="Bottom", line_color='blue')
        ])
        fig3.add_hline(y=f_c_sv, line_dash="dash", line_color="orange")
        fig3.add_hline(y=f_t_sv, line_dash="dash", line_color="green")
        st.plotly_chart(fig3, use_container_width=True)
        sv_df = [{"x": x_plot[i], "Top": f"{sv_top[i]:.2f}", "Bot": f"{sv_bot[i]:.2f}", "Status": "✅" if (f_c_sv <= sv_top[i] <= f_t_sv) and (f_c_sv <= sv_bot[i] <= f_t_sv) else "❌"} for i in idx]
        st.dataframe(pd.DataFrame(sv_df), use_container_width=True)

    with tabs[3]:
        st.subheader("Flexural Capacity Envelope")
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=x_plot, y=phi_mn_pos, name="+Mn Cap", line=dict(color='green', dash='dash')))
        fig4.add_trace(go.Scatter(x=x_plot, y=phi_mn_neg, name="-Mn Cap", line=dict(color='darkgreen', dash='dash')))
        fig4.add_trace(go.Scatter(x=x_plot, y=mu, name="Mu Demand", fill='tozeroy', line_color='rgba(255,0,0,0.5)'))
        st.plotly_chart(fig4, use_container_width=True)
        flx_res = []
        for i in idx:
            cap = phi_mn_pos[i] if mu[i] >= 0 else abs(phi_mn_neg[i])
            dcr = abs(mu[i]) / cap
            flx_res.append({"x": x_plot[i], "Mu": f"{mu[i]:.1f}", "phi*Mn": f"{cap:.1f}", "DCR": f"{dcr:.3f}", "Status": "✅" if dcr <= 1.0 else "❌"})
        st.dataframe(pd.DataFrame(flx_res), use_container_width=True)

    with tabs[4]:
        st.subheader("Shear Strength Check")
        dv_eff = np.maximum(0.9 * (t-z), 0.72 * t)
        phi_vn = 0.9 * (0.083 * 2.0 * 1.0 * np.sqrt(fc) * 1.0 * dv_eff * 1000)
        fig5 = go.Figure([
            go.Scatter(x=x_plot, y=phi_vn, name="phi*Vn", line_color='green'),
            go.Scatter(x=x_plot, y=np.abs(v_total), name="|Vu|", fill='tozeroy', line_color='blue')
        ])
        st.plotly_chart(fig5, use_container_width=True)
        shr_res = [{"x": x_plot[i], "Vu": f"{v_total[i]:.1f}", "phi*Vn": f"{phi_vn[i]:.1f}", "DCR": f"{abs(v_total[i])/phi_vn[i]:.3f}", "Status": "✅" if abs(v_total[i]) <= phi_vn[i] else "❌"} for i in idx]
        st.dataframe(pd.DataFrame(shr_res), use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
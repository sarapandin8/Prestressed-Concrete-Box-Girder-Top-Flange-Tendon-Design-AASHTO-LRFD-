"""PSC Box Girder — Top Flange Transverse Design  (v3 fixed + Table Sync)
AASHTO LRFD Bridge Design Specifications  |  1.0 m transverse strip
"""
import math, datetime, json
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
st.set_page_config(layout="wide", page_title="PSC Box Girder — Top Flange Design")

DEFAULT_SCALARS = dict(
    width=6.0, cl_lweb=1.50, cl_rweb=4.50,
    fc=40.0, fci=30.0, fpu=1860.0, fpy_ratio=0.90,
    aps_strand=140.0, duct_dia_mm=70.0,
    num_tendon=2, n_strands=12,
    fpi_ratio=0.75, init_loss_pct=5, eff_ratio=0.80,
    phi_flex=1.00, phi_shear=0.90,
    proj_name="Bridge Lane Expansion", doc_no="CALC-STR-001",
    eng_name="Engineer Name", chk_name="Checker Name",
)

DEFAULT_TABLES = dict(
    df_thickness={"x (m)": [0.0, 3.0, 6.0], "t (m)": [0.30, 0.25, 0.30]},
    df_tendon={"x (m)": [0.0, 3.0, 6.0], "z_top (m)": [0.08, 0.18, 0.08]},
    df_load={
        "x (m)":         [ 0.0,    3.0,    6.0],
        "M_DL (kNm/m)":  [-120.0,  80.0, -120.0],
        "V_DL (kN/m)":   [  60.0,   0.0,   60.0],
        "M_SDL (kNm/m)": [ -40.0,  25.0,  -40.0],
        "V_SDL (kN/m)":  [  20.0,   0.0,   20.0],
        "M_LL (kNm/m)":  [-180.0, 120.0, -180.0],
        "V_LL (kN/m)":   [  80.0,   0.0,   80.0],
    },
)

# ── ฟังก์ชัน Sync ข้อมูลตาราง (หัวใจสำคัญของการแก้ปัญหา) ──
def sync_table(src_key, editor_key):
    """ทำหน้าที่รวมการแก้ไขจาก data_editor (Deltas) เข้ากับ DataFrame หลักใน session_state"""
    if editor_key not in st.session_state:
        return
    
    edits = st.session_state[editor_key]
    df = st.session_state[src_key].copy()

    # 1. จัดการแถวที่ถูกแก้ไข (Edited)
    for row_idx, values in edits.get("edited_rows", {}).items():
        for col, val in values.items():
            df.at[df.index[int(row_idx)], col] = val

    # 2. จัดการแถวที่เพิ่มใหม่ (Added)
    added = edits.get("added_rows", [])
    if added:
        new_rows = pd.DataFrame(added)
        df = pd.concat([df, new_rows], ignore_index=True)

    # 3. จัดการแถวที่ถูกลบ (Deleted)
    deleted = edits.get("deleted_rows", [])
    if deleted:
        df = df.drop(df.index[deleted]).reset_index(drop=True)

    st.session_state[src_key] = df

# Init scalars
for k, v in DEFAULT_SCALARS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Init table sources
_TABLE_SRC = {"thk_src": "df_thickness", "tdn_src": "df_tendon", "ld_src": "df_load"}
for src_key, tbl_key in _TABLE_SRC.items():
    if src_key not in st.session_state:
        st.session_state[src_key] = pd.DataFrame(DEFAULT_TABLES[tbl_key])

if "_uploader_reset" not in st.session_state:
    st.session_state["_uploader_reset"] = 0

# ─────────────────────────────────────────────────────────────────────────────
# 2.  SIDEBAR (SAVE / OPEN)
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    with st.expander("💾  Save  /  📂  Open Project", expanded=True):
        
        def _tbl_save(src_key):
            """ดึงข้อมูลจาก source ตรงๆ เพราะ sync_table ทำงานให้ตลอดเวลาแล้ว"""
            df = st.session_state.get(src_key, pd.DataFrame())
            try:
                # ทำความสะอาดข้อมูลแปลงเป็นตัวเลขก่อน Save
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df.dropna(how="all")
                return df.to_dict(orient="list")
            except Exception:
                return {}

        _save_data = {
            "scalars": {k: st.session_state[k] for k in DEFAULT_SCALARS.keys()},
            "tables": {
                "df_thickness": _tbl_save("thk_src"),
                "df_tendon":    _tbl_save("tdn_src"),
                "df_load":      _tbl_save("ld_src"),
            },
        }
        
        _json_bytes = json.dumps(_save_data, indent=2, ensure_ascii=False).encode("utf-8")
        _fname = f"{st.session_state.proj_name.replace(' ','_')}_{st.session_state.doc_no}.json"
        
        st.download_button(
            label="💾  Save Project  (.json)",
            data=_json_bytes,
            file_name=_fname,
            mime="application/json",
            use_container_width=True,
        )

        st.markdown("---")
        
        _up_key = f"uploader_{st.session_state['_uploader_reset']}"
        uploaded_file = st.file_uploader("📂  Open Project  (.json)", type="json", key=_up_key)
                
        if uploaded_file is not None:
            try:
                loaded = json.loads(uploaded_file.read().decode("utf-8"))
                # Load Scalars พร้อมบังคับ Type ให้ตรงกับ Default
                for k, v in loaded.get("scalars", {}).items():
                    if k in DEFAULT_SCALARS:
                        st.session_state[k] = type(DEFAULT_SCALARS[k])(v)
                
                # Load Tables ลงใน src_key
                _load_map = {"df_thickness":"thk_src","df_tendon":"tdn_src","df_load":"ld_src"}
                loaded_tables = loaded.get("tables", {})
                for tbl_key, src_key in _load_map.items():
                    if tbl_key in loaded_tables and loaded_tables[tbl_key]:
                        st.session_state[src_key] = pd.DataFrame(loaded_tables[tbl_key])
                
                # ลบ editor state เพื่อให้ data_editor ดึงค่าจาก src_key ใหม่
                for ek in ["ed_thk", "ed_tdn", "ed_ld"]:
                    if ek in st.session_state: del st.session_state[ek]
                
                st.session_state["_uploader_reset"] += 1
                st.success("✅  Project loaded!")
                st.rerun()
            except Exception as e:
                st.error(f"❌  Load error: {e}")

    # Materials & Section
    with st.expander("📐 Materials & Section", expanded=True):
        st.number_input("Total Flange Width (m)", min_value=1.0, key="width")
        st.number_input("f'c  Service (MPa)", min_value=20.0, key="fc")
        st.number_input("f'ci Transfer (MPa)", min_value=15.0, key="fci")
        st.number_input("fpu (MPa)", key="fpu")
        st.selectbox("fpy/fpu", [0.90, 0.85], key="fpy_ratio")
        st.number_input("Aps per strand (mm²)", key="aps_strand")
        st.number_input("Duct diameter (mm)", min_value=20.0, key="duct_dia_mm")

    # Web Geometry
    with st.expander("🌐  Web Geometry", expanded=True):
        col_wl, col_wr = st.columns(2)
        col_wl.number_input("CL. L.Web (m)", min_value=0.0, step=0.05, key="cl_lweb")
        col_wr.number_input(" CL. R.Web (m)", min_value=0.0, step=0.05, key="cl_rweb")

    # Prestressing Force
    with st.expander("🔩 Prestressing Force", expanded=True):
        st.number_input("Tendons per 1 m strip", min_value=1, key="num_tendon")
        st.number_input("Strands per tendon", min_value=1, key="n_strands")
        st.slider("fpi / fpu  (at jacking)", 0.70, 0.80, key="fpi_ratio")
        st.slider("Immediate loss at Transfer (%)", 0, 15, key="init_loss_pct")
        st.slider("Pe / Pi  (long-term ratio)", 0.50, 0.95, key="eff_ratio")

    # Resistance Factors
    with st.expander("⚖️ Resistance Factors φ"):
        st.number_input("φ  Flexure", min_value=0.75, max_value=1.00, key="phi_flex")
        st.number_input("φ  Shear", min_value=0.70, max_value=1.00, key="phi_shear")

    st.markdown("---")
    st.subheader("📄 Report Information")
    st.text_input("Project Name", key="proj_name")
    st.text_input("Document No.", key="doc_no")
    st.text_input("Prepared by",  key="eng_name")
    st.text_input("Checked by",   key="chk_name")

# ─────────────────────────────────────────────────────────────────────────────
# 3.  DATA EDITORS (Main Area)
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏗️  PSC Box Girder — Top Flange Transverse Design")
st.caption("AASHTO LRFD  |  1.0 m strip  |  Compression (−) Tension (+)")

c1, c2 = st.columns(2)
with c1:
    st.subheader("📏 Flange Thickness t(x)")
    df_thk = st.data_editor(
        st.session_state["thk_src"], 
        num_rows="dynamic", 
        key="ed_thk",
        on_change=sync_table,
        args=("thk_src", "ed_thk")
    )
    st.subheader("🔩 Tendon Profile z(x)")
    df_tdn = st.data_editor(
        st.session_state["tdn_src"], 
        num_rows="dynamic", 
        key="ed_tdn",
        on_change=sync_table,
        args=("tdn_src", "ed_tdn")
    )
with c2:
    st.subheader("📦 Loads per 1 m strip")
    df_ld  = st.data_editor(
        st.session_state["ld_src"], 
        num_rows="dynamic", 
        key="ed_ld",
        on_change=sync_table,
        args=("ld_src", "ed_ld")
    )

# ─────────────────────────────────────────────────────────────────────────────
# 4.  CALCULATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def prep(df):
    df = df.copy()
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna()
    if df.empty: return df
    return df.sort_values("x (m)").drop_duplicates(subset="x (m)").reset_index(drop=True)

def run_calc(dft, dfp, dfl):
    """Run all calculations and return results dict."""
    N = 500; b = 1.0
    x = np.linspace(0, st.session_state.width, N)
    
    # ดึงค่าจาก session_state มาใช้ตรงๆ เพื่อความแม่นยำ
    fc = st.session_state.fc
    fci = st.session_state.fci
    fpu = st.session_state.fpu
    fpy_ratio = st.session_state.fpy_ratio
    aps_strand = st.session_state.aps_strand
    duct_dia_mm = st.session_state.duct_dia_mm
    num_tendon = st.session_state.num_tendon
    n_strands = st.session_state.n_strands
    fpi_ratio = st.session_state.fpi_ratio
    init_loss_pct = st.session_state.init_loss_pct
    eff_ratio = st.session_state.eff_ratio
    phi_flex = st.session_state.phi_flex
    phi_shear = st.session_state.phi_shear

    # Geometry
    t  = np.interp(x, dft["x (m)"], dft["t (m)"])
    z  = np.interp(x, dfp["x (m)"], dfp["z_top (m)"])
    yc = t / 2.0
    
    # Loads
    def ip(col): return np.interp(x, dfl["x (m)"], dfl[col])
    m_dl=ip("M_DL (kNm/m)"); v_dl=ip("V_DL (kN/m)")
    m_sdl=ip("M_SDL (kNm/m)"); v_sdl=ip("V_SDL (kN/m)")
    m_ll=ip("M_LL (kNm/m)");  v_ll=ip("V_LL (kN/m)")
    ms1 = m_dl + m_sdl + m_ll
    ms3 = m_dl + m_sdl + 0.8*m_ll
    mu  = 1.25*m_dl + 1.50*m_sdl + 1.75*m_ll
    vu  = 1.25*np.abs(v_dl) + 1.50*np.abs(v_sdl) + 1.75*np.abs(v_ll)

    # Gross section
    Ag = b * t
    Ig = b * t**3 / 12.0

    # Net section (duct deduction)
    A_duct = math.pi / 4.0 * (duct_dia_mm / 1000.0)**2
    n_ducts = int(num_tendon)
    y_duct  = z - yc
    An = Ag - n_ducts * A_duct
    In = Ig - n_ducts * A_duct * y_duct**2
    e = yc - z

    # Prestress
    aps_m2  = aps_strand * 1e-6
    n_total = int(num_tendon * n_strands)
    Aps     = n_total * aps_m2
    fpi_val = fpu * fpi_ratio * (1.0 - init_loss_pct / 100.0)
    Pi      = Aps * fpi_val * 1e3
    Pe      = Pi * eff_ratio

    # Stress function
    def stress(P, M, ev, tv, Av, Iv):
        ht  = tv / 2.0
        top = (-P/Av + P*ev*ht/Iv - M*ht/Iv) / 1000.0
        bot = (-P/Av - P*ev*ht/Iv + M*ht/Iv) / 1000.0
        return top, bot

    tr_top,  tr_bot  = stress(Pi, m_dl, e, t, An, In)
    sv1_top, sv1_bot = stress(Pe, ms1,  e, t, Ag, Ig)
    sv3_top, sv3_bot = stress(Pe, ms3,  e, t, Ag, Ig)

    # Flexure
    beta1 = float(np.clip(0.85 - 0.05*(fc-28.0)/7.0, 0.65, 0.85))
    k_fac = 2.0 * (1.04 - fpy_ratio)
    def flexure(dp_arr):
        dp_s = np.maximum(dp_arr, 1e-4)
        c_   = Aps*fpu / (0.85*fc*beta1*b*1000.0 + k_fac*Aps*fpu/dp_s)
        fps_ = np.clip(fpu*(1.0 - k_fac*c_/dp_s), 0.0, fpu)
        a_   = beta1 * c_
        Mn_  = Aps * fps_ * (dp_s - a_/2.0) * 1000.0
        return c_, a_, fps_, Mn_

    dp_pos = z; dp_neg = t - z
    c_pos, a_pos, fps_pos, Mn_pos = flexure(dp_pos)
    c_neg, a_neg, fps_neg, Mn_neg = flexure(dp_neg)
    phi_Mn_pos =  phi_flex * Mn_pos
    phi_Mn_neg = -phi_flex * Mn_neg
    cdp_pos = np.where(dp_pos > 0, c_pos/dp_pos, np.inf)
    cdp_neg = np.where(dp_neg > 0, c_neg/dp_neg, np.inf)

    # Min reinforcement
    fr  = 0.63 * math.sqrt(fc)
    fpe = Pe / Ag / 1000.0
    Sb  = Ig / yc
    Mcr = (fr + fpe) * Sb / 1000.0

    # Shear
    dp_use = np.maximum(dp_pos, dp_neg)
    dv     = np.maximum(0.9*dp_use, 0.72*t)
    Vc     = 0.083*2.0*1.0*math.sqrt(fc)*b*dv*1000.0
    Vn_lim = 0.25*fc*b*dv*1000.0
    phi_Vn = phi_shear * np.minimum(Vc, Vn_lim)

    # Allowable limits
    lim_tr_c  = -0.60*fci;  lim_tr_t  =  0.25*math.sqrt(fci)
    lim_sv_cp = -0.45*fc;   lim_sv_ct = -0.60*fc
    lim_sv_t  =  0.50*math.sqrt(fc)

    return {**locals(), "lim_tr_c":lim_tr_c, "lim_tr_t":lim_tr_t, 
            "lim_sv_cp":lim_sv_cp, "lim_sv_ct":lim_sv_ct, "lim_sv_t":lim_sv_t}

# ─────────────────────────────────────────────────────────────────────────────
# 5.  MAIN PROCESS
# ─────────────────────────────────────────────────────────────────────────────
try:
    dft = prep(df_thk); dfp = prep(df_tdn); dfl = prep(df_ld)
    if any(len(d) < 2 for d in [dft, dfp, dfl]):
        st.warning("⚠️ Enter at least 2 rows in each table."); st.stop()
    
    R = run_calc(dft, dfp, dfl)
    sta_x   = dfl["x (m)"].values
    sta_idx = [int(np.abs(R["x"] - v).argmin()) for v in sta_x]

    # --- REPORT DOWNLOAD BUTTON ---
    def make_report():
        doc = Document()
        doc.add_heading("STRUCTURAL CALCULATION REPORT", 0)
        doc.add_paragraph(f"Project: {st.session_state.proj_name}")
        doc.add_paragraph(f"Prepared by: {st.session_state.eng_name}")
        # รายละเอียดอื่นๆ ใน Report สามารถเพิ่มได้ตามโค้ดเดิมของคุณ
        buf = BytesIO(); doc.save(buf); buf.seek(0)
        return buf

    with st.sidebar:
        st.markdown("---")
        st.download_button(
            label="📥 Download Report (.docx)",
            data=make_report(),
            file_name=f"Report_{st.session_state.proj_name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    # --- TABS DISPLAY ---
    tabs = st.tabs(["📐 Geometry", "🚀 Transfer Stress", "⚖️ Service Stress", "💪 Flexure", "🔪 Shear", "📋 Summary"])
    
    with tabs[0]:
        st.subheader("Visualization")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=R["x"]*1000, y=np.zeros(500), name="Top Face"))
        fig.add_trace(go.Scatter(x=R["x"]*1000, y=-R["t"]*1000, name="Bottom Face", fill='tonexty'))
        fig.add_trace(go.Scatter(x=R["x"]*1000, y=-R["z"]*1000, name="Tendon CGS", line=dict(color='red', width=3)))
        fig.update_layout(yaxis=dict(scaleanchor="x", scaleratio=1), height=400)
        st.plotly_chart(fig, use_container_width=True)

    with tabs[5]:
        st.subheader("Overall Summary")
        summary_rows = []
        for i in sta_idx:
            mu = float(R["mu"][i])
            phiMn = float(R["phi_Mn_pos"][i]) if mu >= 0 else abs(float(R["phi_Mn_neg"][i]))
            summary_rows.append({
                "x (m)": f"{R['x'][i]:.2f}",
                "Mu (kNm)": f"{mu:.2f}",
                "φMn (kNm)": f"{phiMn:.2f}",
                "DCR Flexure": f"{abs(mu)/phiMn:.3f}" if phiMn > 0 else "N/A",
                "Vu (kN)": f"{R['vu'][i]:.2f}",
                "φVn (kN)": f"{R['phi_Vn'][i]:.2f}",
                "DCR Shear": f"{R['vu'][i]/R['phi_Vn'][i]:.3f}" if R['phi_Vn'][i] > 0 else "N/A"
            })
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

except Exception as err:
    st.error(f"Calculation error: {err}")
```.
"""
PSC Box Girder — Top Flange Transverse Design  (v3 fixed)
AASHTO LRFD Bridge Design Specifications  |  1.0 m transverse strip

Fixes applied:
  [BUG-A] fpe, Sb are numpy arrays → must index [i] inside station loop
  [BUG-B] make_report() called before tabs → wrapped in separate try/except
           so tabs always render even if report fails
  [BUG-C] dp_neg = t−z  (hogging, compression face = BOTTOM)
  [BUG-D] Vu uses factored shear magnitudes
  [FIX-STATE] Robust Streamlit Session State binding for Save/Load (Prevent Rerun Loops)
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
    width=12.0, cl_lweb=2.0, cl_rweb=10.0,
    fc=45.0, fci=36.0, fpu=1860.0, fpy_ratio=0.90,
    aps_strand=140.0, duct_dia_mm=70.0,
    num_tendon=1, n_strands=5,
    fpi_ratio=0.75, init_loss_pct=5, eff_ratio=0.80,
    phi_flex=1.00, phi_shear=0.90,
    proj_name="Box Girder Design", doc_no="CALC-STR-001",
    eng_name="Engineer Name", chk_name="Checker Name",
)
DEFAULT_TABLES = dict(
    df_thickness={"x (m)": [0.00, 1.00, 2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00, 9.00, 10.00, 11.00, 12.00], "t (m)": [0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250]},
    df_tendon={"x (m)": [0.00, 1.00, 2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00, 9.00, 10.00, 11.00, 12.00], "z_top (m)": [0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100]},
    df_load={
        "x (m)":         [ 0.00, 1.00, 2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00, 9.00, 10.00, 11.00, 12.00],
        "M_DL (kNm/m)":  [ 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,  0.00,  0.00,  0.00],
        "V_DL (kN/m)":   [ 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,  0.00,  0.00,  0.00],
        "M_SDL (kNm/m)": [ 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,  0.00,  0.00,  0.00],
        "V_SDL (kN/m)":  [ 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,  0.00,  0.00,  0.00],
        "M_LL (kNm/m)":  [ 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,  0.00,  0.00,  0.00],
        "V_LL (kN/m)":   [ 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,  0.00,  0.00,  0.00],
    },
)

# ── Init scalars
for k, v in DEFAULT_SCALARS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Init table SOURCE keys (never same as editor widget key)
# Rule: data_editor(data=session_state["thk_src"], key="ed_thk")
#   - thk_src = stable data source, only changes on file load
#   - ed_thk  = widget internal state managed by Streamlit (never write to it)
# This prevents StreamlitValueAssignmentNotAllowedError AND double-input issue
_TABLE_SRC = {"thk_src": "df_thickness", "tdn_src": "df_tendon", "ld_src": "df_load"}

def _make_float_df(data: dict) -> pd.DataFrame:
    """Create DataFrame and force ALL columns to float64.
    Prevents Streamlit data_editor from locking to integer-only input
    when all default values happen to be whole numbers (0.00 -> int64 by pandas)."""
    df = pd.DataFrame(data)
    for col in df.columns:
        df[col] = df[col].astype(float)
    return df

for src_key, tbl_key in _TABLE_SRC.items():
    if src_key not in st.session_state:
        st.session_state[src_key] = _make_float_df(DEFAULT_TABLES[tbl_key])

if "_uploader_reset" not in st.session_state:
    st.session_state["_uploader_reset"] = 0

# ── One-time cleanup: force data_editors to re-render with updated column_config
# Old widget state (stored under ed_thk/ed_tdn/ed_ld) holds integer step schema.
# Delete it once so Streamlit rebuilds editor with NumberColumn(step=0.01).
_COL_CFG_VER = "v1_decimal"
if st.session_state.get("_col_cfg_ver") != _COL_CFG_VER:
    for _ek in ["ed_thk", "ed_tdn", "ed_ld"]:
        st.session_state.pop(_ek, None)
    st.session_state["_col_cfg_ver"] = _COL_CFG_VER


# ─────────────────────────────────────────────────────────────────────────────
# 2.  SIDEBAR (Native State Binding)
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
# ── 💾 SAVE / 📂 OPEN ────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("💾  Save  /  📂  Open Project", expanded=True):

        # ── SAVE: robust helper — handles DataFrame, dict, or any other type
        def _tbl_save(editor_key, src_key):
            val = st.session_state.get(editor_key)
            if val is None:
                val = st.session_state.get(src_key, pd.DataFrame())
            # Normalise to DataFrame regardless of what Streamlit stored
            try:
                df = val if isinstance(val, pd.DataFrame) else pd.DataFrame(val)
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df.dropna(how="all")
                return df.to_dict(orient="list") if not df.empty else {}
            except Exception:
                # Last-resort fallback: use the stable src key
                src = st.session_state.get(src_key, pd.DataFrame())
                if isinstance(src, pd.DataFrame) and not src.empty:
                    return src.to_dict(orient="list")
                return {}
        _save_data = {
            "scalars": {k: st.session_state[k] for k in DEFAULT_SCALARS.keys()},
            "tables": {
                "df_thickness": _tbl_save("ed_thk", "thk_src"),
                "df_tendon":    _tbl_save("ed_tdn", "tdn_src"),
                "df_load":      _tbl_save("ed_ld",  "ld_src"),
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
        st.caption("ตั้ง Chrome: Settings→Downloads→'Ask where to save' เพื่อเลือก folder เอง")
        st.markdown("---")

        # ── OPEN: โหลดและจัดระเบียบ Type ป้องกัน Slider/Number_input Crash ──
        _up_key = f"uploader_{st.session_state['_uploader_reset']}"
        uploaded_file = st.file_uploader(
            "📂  Open Project  (.json)",
            type="json",
            key=_up_key,
            help="เลือกไฟล์ .json ที่เคย Save ไว้",
        )
        
        if uploaded_file is not None:
            try:
                loaded = json.loads(uploaded_file.read().decode("utf-8"))
                
                # โหลด Scalars พร้อมจับคู่ Type
                for k, v in loaded.get("scalars", {}).items():
                    if k in DEFAULT_SCALARS:
                        def_val = DEFAULT_SCALARS[k]
                        if isinstance(def_val, int):
                            st.session_state[k] = int(v)
                        elif isinstance(def_val, float):
                            st.session_state[k] = float(v)
                        else:
                            st.session_state[k] = str(v)
                            
                # โหลด Tables → อัปเดต src keys + ลบ editor keys ให้ reinit
                _load_map = {"df_thickness":"thk_src","df_tendon":"tdn_src","df_load":"ld_src"}
                loaded_tables = loaded.get("tables", {})
                for tbl_key, src_key in _load_map.items():
                    if tbl_key in loaded_tables:
                        # ตรวจสอบว่าข้อมูลในตารางไม่ว่างเปล่า
                        table_data = loaded_tables[tbl_key]
                        if table_data:
                            new_df = pd.DataFrame(table_data)
                            for col in new_df.columns:
                                new_df[col] = pd.to_numeric(new_df[col], errors="coerce").astype(float)
                            st.session_state[src_key] = new_df
                
                # ลบ editor key state และข้อมูลที่แก้ไขค้างไว้ เพื่อให้ data_editor ดึงค่าใหม่จาก src_key
                for ek in ["ed_thk", "ed_tdn", "ed_ld"]:
                    if ek in st.session_state:
                        del st.session_state[ek]
                    # ลบข้อมูลที่ Streamlit เก็บไว้ใน widget state ภายใน (ถ้ามี)
                    internal_key = f"{ek}_editor_state"
                    if internal_key in st.session_state:
                        del st.session_state[internal_key]

                # ทำลาย Uploader ป้องกัน Loop
                st.session_state["_uploader_reset"] += 1
                st.success("✅  Project loaded successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌  Load error: {e}")
    # ── 📐 Materials & Section ───────────────────────────────────────────────
    with st.expander("📐 Materials & Section", expanded=True):
        # ใช้ key=... อย่างเดียว Streamlit จะซิงค์ค่าให้เอง และไม่ค้างตอนโหลด
        width       = st.number_input("Total Flange Width (m)",   min_value=1.0, key="width")
        fc          = st.number_input("f'c  Service (MPa)",       min_value=20.0, key="fc")
        fci         = st.number_input("f'ci Transfer (MPa)",      min_value=15.0, key="fci")
        fpu         = st.number_input("fpu (MPa)",                key="fpu")
        
        # Selectbox logic
        fpy_opts = [0.90, 0.85]
        if st.session_state.fpy_ratio not in fpy_opts:
            st.session_state.fpy_ratio = 0.90
        fpy_ratio   = st.selectbox("fpy/fpu", fpy_opts, key="fpy_ratio", help="Low-relaxation=0.90  |  Stress-relieved=0.85")
        
        aps_strand  = st.number_input("Aps per strand (mm²)",     key="aps_strand")
        duct_dia_mm = st.number_input("Duct diameter (mm)",       min_value=20.0, key="duct_dia_mm")

    # ── 🌐 Web Geometry ──────────────────────────────────────────────────────
    with st.expander("🌐  Web Geometry", expanded=True):
        st.caption("ระบุตำแหน่ง Centerline ของ Web ซ้าย-ขวา จากขอบซ้ายของ Flange")
        col_wl, col_wr = st.columns(2)
        cl_lweb = col_wl.number_input("CL. L.Web (m)", min_value=0.0, step=0.05, key="cl_lweb")
        cl_rweb = col_wr.number_input("CL. R.Web (m)", min_value=0.0, step=0.05, key="cl_rweb")
        st.info(f"CL.L.Web = **{cl_lweb*1000:.0f} mm** |  "
                f"CL.R.Web = **{cl_rweb*1000:.0f} mm** |  "
                f"Span = **{(cl_rweb-cl_lweb)*1000:.0f} mm**")

    # ── 🔩 Prestressing Force ────────────────────────────────────────────────
    with st.expander("🔩 Prestressing Force", expanded=True):
        num_tendon    = st.number_input("Tendons per 1 m strip",  min_value=1, key="num_tendon")
        n_strands     = st.number_input("Strands per tendon",     min_value=1, key="n_strands")
        fpi_ratio     = st.slider("fpi / fpu  (at jacking)",     0.70, 0.80, key="fpi_ratio")
        init_loss_pct = st.slider("Immediate loss at Transfer (%)", 0, 15, key="init_loss_pct")
        eff_ratio     = st.slider("Pe / Pi  (long-term ratio)",  0.50, 0.95, key="eff_ratio")

    # ── ⚖️ Resistance Factors ────────────────────────────────────────────────
    with st.expander("⚖️ Resistance Factors φ"):
        phi_flex  = st.number_input("φ  Flexure", min_value=0.75, max_value=1.00, key="phi_flex")
        phi_shear = st.number_input("φ  Shear",   min_value=0.70, max_value=1.00, key="phi_shear")

    # ── 📄 Report Info ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📄 Report Information")
    proj_name = st.text_input("Project Name", key="proj_name")
    doc_no    = st.text_input("Document No.", key="doc_no")
    eng_name  = st.text_input("Prepared by",  key="eng_name")
    chk_name  = st.text_input("Checked by",   key="chk_name")


# ─────────────────────────────────────────────────────────────────────────────
# 3.  DATA EDITORS
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏗️  PSC Box Girder — Top Flange Transverse Design")
st.caption("AASHTO LRFD  |  1.0 m transverse strip  |  "
           "Compression (−)  Tension (+)  |  +M = sagging")

c1, c2 = st.columns(2)
with c1:
    st.subheader("📏 Flange Thickness t(x)")
    df_thk = st.data_editor(
        st.session_state["thk_src"], num_rows="dynamic", key="ed_thk",
        column_config={
            "x (m)":  st.column_config.NumberColumn("x (m)",  format="%.2f", step=0.01),
            "t (m)":  st.column_config.NumberColumn("t (m)",  format="%.3f", step=0.001),
        },
    )
    st.subheader("🔩 Tendon Profile z(x)  [from top face]")
    df_tdn = st.data_editor(
        st.session_state["tdn_src"], num_rows="dynamic", key="ed_tdn",
        column_config={
            "x (m)":      st.column_config.NumberColumn("x (m)",      format="%.2f", step=0.01),
            "z_top (m)":  st.column_config.NumberColumn("z_top (m)",  format="%.3f", step=0.001),
        },
    )
with c2:
    st.subheader("📦 Loads per 1 m strip")
    df_ld = st.data_editor(
        st.session_state["ld_src"], num_rows="dynamic", key="ed_ld",
        column_config={
            "x (m)":         st.column_config.NumberColumn("x (m)",         format="%.2f", step=0.01),
            "M_DL (kNm/m)":  st.column_config.NumberColumn("M_DL (kNm/m)",  format="%.2f", step=0.01),
            "V_DL (kN/m)":   st.column_config.NumberColumn("V_DL (kN/m)",   format="%.2f", step=0.01),
            "M_SDL (kNm/m)": st.column_config.NumberColumn("M_SDL (kNm/m)", format="%.2f", step=0.01),
            "V_SDL (kN/m)":  st.column_config.NumberColumn("V_SDL (kN/m)",  format="%.2f", step=0.01),
            "M_LL (kNm/m)":  st.column_config.NumberColumn("M_LL (kNm/m)",  format="%.2f", step=0.01),
            "V_LL (kN/m)":   st.column_config.NumberColumn("V_LL (kN/m)",   format="%.2f", step=0.01),
        },
    )
# No sync-back: Streamlit forbids writing to widget key; data_editor manages ed_thk etc.

# ─────────────────────────────────────────────────────────────────────────────
# 4.  CALCULATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def prep(df):
    df = df.copy()
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna()
    if df.empty:
        return df
    return df.sort_values("x (m)").drop_duplicates(subset="x (m)").reset_index(drop=True)

def run_calc(dft, dfp, dfl):
    """Run all calculations and return results dict."""
    N = 500; b = 1.0
    x = np.linspace(0, width, N)

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
    vu  = 1.25*np.abs(v_dl) + 1.50*np.abs(v_sdl) + 1.75*np.abs(v_ll)  # [FIX-D]

    # Gross section
    Ag = b * t
    Ig = b * t**3 / 12.0

    # Net section (duct deduction — Transfer only)
    A_duct = math.pi / 4.0 * (duct_dia_mm / 1000.0)**2
    n_ducts = int(num_tendon)
    y_duct  = z - yc
    An = Ag - n_ducts * A_duct
    In = Ig - n_ducts * A_duct * y_duct**2

    e = yc - z  # eccentricity

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

    # Flexure — [FIX-C] correct dp per moment sign
    beta1 = float(np.clip(0.85 - 0.05*(fc-28.0)/7.0, 0.65, 0.85))
    k_fac = 2.0 * (1.04 - fpy_ratio)

    def flexure(dp_arr):
        dp_s = np.maximum(dp_arr, 1e-4)
        c_   = Aps*fpu / (0.85*fc*beta1*b*1000.0 + k_fac*Aps*fpu/dp_s)
        fps_ = np.clip(fpu*(1.0 - k_fac*c_/dp_s), 0.0, fpu)
        a_   = beta1 * c_
        Mn_  = Aps * fps_ * (dp_s - a_/2.0) * 1000.0
        return c_, a_, fps_, Mn_

    dp_pos = z;      dp_neg = t - z    # sagging=TOP, hogging=BOT
    c_pos, a_pos, fps_pos, Mn_pos = flexure(dp_pos)
    c_neg, a_neg, fps_neg, Mn_neg = flexure(dp_neg)
    phi_Mn_pos =  phi_flex * Mn_pos
    phi_Mn_neg = -phi_flex * Mn_neg

    cdp_pos = np.where(dp_pos > 0, c_pos/dp_pos, np.inf)
    cdp_neg = np.where(dp_neg > 0, c_neg/dp_neg, np.inf)

    # Min reinforcement
    fr  = 0.63 * math.sqrt(fc)        # scalar
    fpe = Pe / Ag / 1000.0            # array — [FIX-A] index in loop
    Sb  = Ig / yc                     # array — [FIX-A] index in loop
    Mcr = (fr + fpe) * Sb / 1000.0   # array

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

    return dict(
        x=x, t=t, z=z, yc=yc, e=e,
        Ag=Ag, Ig=Ig, An=An, In=In, y_duct=y_duct,
        n_total=n_total, Aps=Aps, fpi_val=fpi_val, Pi=Pi, Pe=Pe,
        beta1=beta1, k_fac=k_fac,
        m_dl=m_dl, m_sdl=m_sdl, m_ll=m_ll,
        v_dl=v_dl, v_sdl=v_sdl, v_ll=v_ll,
        ms1=ms1, ms3=ms3, mu=mu, vu=vu,
        tr_top=tr_top, tr_bot=tr_bot,
        sv1_top=sv1_top, sv1_bot=sv1_bot,
        sv3_top=sv3_top, sv3_bot=sv3_bot,
        dp_pos=dp_pos, dp_neg=dp_neg,
        c_pos=c_pos, a_pos=a_pos, fps_pos=fps_pos,
        c_neg=c_neg, a_neg=a_neg, fps_neg=fps_neg,
        phi_Mn_pos=phi_Mn_pos, phi_Mn_neg=phi_Mn_neg,
        cdp_pos=cdp_pos, cdp_neg=cdp_neg,
        fr=fr, fpe=fpe, Sb=Sb, Mcr=Mcr,
        dv=dv, Vc=Vc, Vn_lim=Vn_lim, phi_Vn=phi_Vn,
        A_duct=A_duct, n_ducts=n_ducts,
        lim_tr_c=lim_tr_c, lim_tr_t=lim_tr_t,
        lim_sv_cp=lim_sv_cp, lim_sv_ct=lim_sv_ct, lim_sv_t=lim_sv_t,
    )

try:
    dft = prep(df_thk); dfp = prep(df_tdn); dfl = prep(df_ld)
    if any(len(d) < 2 for d in [dft, dfp, dfl]):
        st.warning("⚠️ Enter at least 2 rows in each table."); st.stop()

    R = run_calc(dft, dfp, dfl)

    # Station indices
    sta_x   = dfl["x (m)"].values
    sta_idx = [int(np.abs(R["x"] - v).argmin()) for v in sta_x]
    N       = len(R["x"])

    # ─────────────────────────────────────────────────────────────────
    # 5.  REPORT GENERATOR   (called only on button press)
    # ─────────────────────────────────────────────────────────────────
    def make_report():
        doc = Document()
        for sec in doc.sections:
            sec.top_margin=Cm(2.0); sec.bottom_margin=Cm(2.0)
            sec.left_margin=Cm(2.5); sec.right_margin=Cm(2.0)
        doc.styles["Normal"].font.name = "Calibri"
        doc.styles["Normal"].font.size = Pt(10)

        C_BLUE  = RGBColor(0x00, 0x44, 0x88)
        C_GREEN = RGBColor(0x00, 0x70, 0x00)
        C_RED   = RGBColor(0xC0, 0x00, 0x00)
        C_GRAY  = RGBColor(0x60, 0x60, 0x60)

        def h1(s): doc.add_heading(s, level=1)
        def h2(s): doc.add_heading(s, level=2)
        def h3(s): doc.add_heading(s, level=3)

        def para(s, bold=False, italic=False, color=None, indent=0.0, align=None):
            p = doc.add_paragraph()
            r = p.add_run(s)
            r.bold=bold; r.italic=italic
            if color: r.font.color.rgb = color
            p.paragraph_format.left_indent = Inches(indent)
            if align: p.alignment = align
            return p

        def formula(s): return para(s, italic=True,  indent=0.5, color=C_GRAY)
        def subst(s):   return para(s, italic=True,  indent=0.7, color=C_GRAY)
        def result(s):  return para(s, bold=True,    indent=0.7, color=C_BLUE)
        def blank():    return doc.add_paragraph()

        def pf(cond, ok, fail):
            if cond: para(f"  ✔  {ok}   [PASS]",  bold=True, color=C_GREEN, indent=0.5)
            else:    para(f"  ✘  {fail}  [FAIL]",  bold=True, color=C_RED,   indent=0.5)

        def tbl(headers, rows, cw=None):
            t_ = doc.add_table(rows=1, cols=len(headers))
            t_.style = "Table Grid"
            for j,h in enumerate(headers):
                t_.rows[0].cells[j].text = h
                t_.rows[0].cells[j].paragraphs[0].runs[0].bold = True
            for row in rows:
                rc = t_.add_row().cells
                for j,v in enumerate(row): rc[j].text = str(v)
            if cw:
                for row in t_.rows:
                    for j,cell in enumerate(row.cells):
                        cell.width = Cm(cw[j])
            return t_

        # ── Convenience: extract scalar from R at index i ─────────────
        def s(key, i): return float(R[key][i])

        # ══════════════════════════════════════════════════════════════
        # COVER
        # ══════════════════════════════════════════════════════════════
        blank(); blank()
        doc.add_heading("STRUCTURAL CALCULATION REPORT", 0)
        blank()
        tbl(["Item","Description"],[
            ["Project",       proj_name],
            ["Document No.",  doc_no],
            ["Subject",       "Transverse Tendon Design — PSC Box Girder Top Flange"],
            ["Code",          "AASHTO LRFD Bridge Design Specifications"],
            ["Prepared by",   eng_name],
            ["Checked by",    chk_name],
            ["Date",          datetime.datetime.now().strftime("%d %B %Y")],
        ], cw=[4.5,13.0])
        doc.add_page_break()

        # ══════════════════════════════════════════════════════════════
        # SEC 1 — DESIGN BASIS
        # ══════════════════════════════════════════════════════════════
        h1("1.  Design Basis")
        for it in [
            "Code: AASHTO LRFD Bridge Design Specifications",
            "Analysis basis: 1.0 m transverse strip across top flange",
            "Load combinations (AASHTO Table 3.4.1-1):",
            "  Strength I  :  1.25·DC + 1.50·DW + 1.75·LL",
            "  Service  I  :  1.00·DC + 1.00·DW + 1.00·LL  (compression check)",
            "  Service I   :  1.00·DC + 1.00·DW + 1.00·LL  (tension & compression check)",
            "  Transfer    :  Pi (after immediate losses) + M_DC",
            "Strand: Post-tensioned, bonded (fully grouted), low-relaxation",
            "Sign convention: Compression (−)  |  Tension (+)",
            "Positive moment = sagging (compression at TOP fibre)",
        ]: para(it, indent=0.3)
        blank()

        # ══════════════════════════════════════════════════════════════
        # SEC 2 — INPUT SUMMARY
        # ══════════════════════════════════════════════════════════════
        h1("2.  Design Input Summary")

        h2("2.1  Material Properties")
        tbl(["Parameter","Symbol","Value","Unit","Reference"],[
            ["Concrete — service",       "f'c",     f"{fc:.1f}",         "MPa","AASHTO 5.4.2"],
            ["Concrete — transfer",      "f'ci",    f"{fci:.1f}",        "MPa","AASHTO 5.9.2"],
            ["Strand tensile strength",  "fpu",     f"{fpu:.0f}",        "MPa","AASHTO 5.4.4"],
            ["Strand yield ratio",       "fpy/fpu", f"{fpy_ratio:.2f}",  "—",  "Low-relax"],
            ["Area per strand",          "asp",     f"{aps_strand:.1f}", "mm²","Product data"],
            ["PT duct outer diameter",   "d_duct",  f"{duct_dia_mm:.0f}","mm", "Supplier"],
        ], cw=[4.5,2.0,2.0,1.5,4.5])
        blank()

        h2("2.2  Prestressing Configuration")
        tbl(["Parameter","Symbol","Value","Unit"],[
            ["Tendons per 1 m strip",     "n_t",     f"{int(num_tendon)}",       "—"],
            ["Strands per tendon",        "n_s",     f"{int(n_strands)}",        "—"],
            ["Total strands (1m strip)",  "n",       f"{R['n_total']}",          "—"],
            ["Total Aps (1m strip)",      "Aps",     f"{R['Aps']*1e6:.2f}",     "mm²/m"],
            ["Jacking stress ratio",      "fpi/fpu", f"{fpi_ratio:.4f}",         "—"],
            ["Immediate loss",            "Δi",      f"{init_loss_pct:.1f}",     "%"],
            ["Long-term effective ratio", "Pe/Pi",   f"{eff_ratio:.4f}",         "—"],
        ], cw=[5.5,2.5,2.5,2.0])
        blank()

        h2("2.3  Resistance Factors")
        tbl(["Limit State","Symbol","Value"],[
            ["Flexure","φ_f",f"{phi_flex:.2f}"],
            ["Shear",  "φ_v",f"{phi_shear:.2f}"],
        ], cw=[6.0,2.5,2.5])
        blank()

        h2("2.4  Allowable Stress Limits")
        tbl(["Condition","Expression","Limit (MPa)","Article"],[
            ["Transfer — Compression",         "−0.60·f'ci", f"{R['lim_tr_c']:.3f}","5.9.2.3.1a"],
            ["Transfer — Tension (bonded)",    "+0.62·√f'ci",f"+{R['lim_tr_t']:.4f}","5.9.2.3.1b"],
            ["Service I — Compression (permanent loads)", "−0.45·f'c",  f"{R['lim_sv_cp']:.3f}","5.9.2.3.2a"],
            ["Service I — Compression (total loads)",     "−0.60·f'c",  f"{R['lim_sv_ct']:.3f}","5.9.2.3.2a"],
            ["Service I — Tension (bonded)",              "+0.50·√f'c", f"+{R['lim_sv_t']:.4f}","5.9.2.3.2b"],
        ], cw=[5.5,3.5,2.5,2.5])
        blank()

        h2("2.5  Input Geometry and Load at Stations")
        geo_rows = []
        for i in sta_idx:
            geo_rows.append([
                f"{R['x'][i]:.2f}",
                f"{R['t'][i]*1000:.2f}", f"{R['z'][i]*1000:.2f}", f"{R['yc'][i]*1000:.2f}",
                f"{R['e'][i]*1000:.2f}",
                f"{R['m_dl'][i]:.2f}",   f"{R['m_sdl'][i]:.2f}",  f"{R['m_ll'][i]:.2f}",
                f"{R['v_dl'][i]:.2f}",   f"{R['v_sdl'][i]:.2f}",  f"{R['v_ll'][i]:.2f}",
            ])
        tbl(["x(m)","t(mm)","z(mm)","yc(mm)","e(mm)",
             "M_DL","M_SDL","M_LL","V_DL","V_SDL","V_LL"],
            geo_rows, cw=[1.4,1.4,1.4,1.4,1.4,1.6,1.6,1.6,1.6,1.6,1.6])
        para("  M in kNm/m  |  V in kN/m", italic=True, color=C_GRAY)
        doc.add_page_break()

        # ══════════════════════════════════════════════════════════════
        # SEC 3 — GLOBAL PRESTRESS
        # ══════════════════════════════════════════════════════════════
        h1("3.  Global Prestress Force Calculation")

        h2("3.1  Total Prestress Steel Area  Aps")
        formula("Aps  =  n_total × asp")
        subst( f"     =  {R['n_total']} strands  ×  {aps_strand:.1f} mm²/strand")
        result(f"     =  {R['Aps']*1e6:.4f} mm²/m")
        blank()

        h2("3.2  Jacking Stress  fpi  (after immediate losses)")
        formula("fpi  =  fpu × (fpi/fpu) × (1 − Δi/100)")
        subst( f"     =  {fpu:.0f} × {fpi_ratio:.4f} × (1 − {init_loss_pct:.1f}/100)")
        result(f"     =  {R['fpi_val']:.4f} MPa")
        blank()

        h2("3.3  Initial Prestress Force  Pi")
        formula("Pi   =  Aps × fpi  × 10⁻³")
        subst( f"     =  {R['Aps']*1e6:.4f} mm²/m  ×  {R['fpi_val']:.4f} MPa  × 10⁻³")
        result(f"     =  {R['Pi']:.4f} kN/m")
        blank()

        h2("3.4  Effective Prestress Force  Pe  (after all losses)")
        formula("Pe   =  Pi × (Pe/Pi)")
        subst( f"     =  {R['Pi']:.4f}  ×  {eff_ratio:.4f}")
        result(f"     =  {R['Pe']:.4f} kN/m")
        blank()

        h2("3.5  Section Factors")
        formula("β₁  =  0.85 − 0.05 × (f'c − 28.0)/7.0   [0.65 ≤ β₁ ≤ 0.85]")
        subst( f"    =  0.85 − 0.05 × ({fc:.1f} − 28.0)/7.0")
        result(f"    =  {R['beta1']:.4f}")
        blank()
        formula("k   =  2.0 × (1.04 − fpy/fpu)   [AASHTO C5.6.3.1.1]")
        subst( f"    =  2.0 × (1.04 − {fpy_ratio:.2f})")
        result(f"    =  {R['k_fac']:.4f}")
        doc.add_page_break()

        # ══════════════════════════════════════════════════════════════
        # SEC 4 — STATION-BY-STATION
        # ══════════════════════════════════════════════════════════════
        h1("4.  Detailed Station-by-Station Calculations")
        para("Calculations are presented per 1.0 m strip width at each station.", italic=True)
        blank()

        for ks, i in enumerate(sta_idx):
            # ── extract all scalars at this station  [FIX-A: index arrays here]
            xi   = float(R["x"][i])
            ti   = float(R["t"][i]);       zi   = float(R["z"][i])
            yci  = float(R["yc"][i]);      ei   = float(R["e"][i])
            Agi  = float(R["Ag"][i]);      Igi  = float(R["Ig"][i])
            Ani  = float(R["An"][i]);      Ini  = float(R["In"][i])
            ydi  = float(R["y_duct"][i])
            mdi  = float(R["m_dl"][i]);    msdi = float(R["m_sdl"][i])
            mli  = float(R["m_ll"][i]);    vdi  = float(R["v_dl"][i])
            vsdi = float(R["v_sdl"][i]);   vli  = float(R["v_ll"][i])
            ms1i = float(R["ms1"][i]);     ms3i = float(R["ms3"][i])
            mui  = float(R["mu"][i]);      vui  = float(R["vu"][i])
            trt  = float(R["tr_top"][i]);  trb  = float(R["tr_bot"][i])
            s1t  = float(R["sv1_top"][i]); s1b  = float(R["sv1_bot"][i])
            s3t  = float(R["sv3_top"][i]); s3b  = float(R["sv3_bot"][i])
            dpp  = float(R["dp_pos"][i]);  dpn  = float(R["dp_neg"][i])
            cpp  = float(R["c_pos"][i]);   app  = float(R["a_pos"][i])
            fpp  = float(R["fps_pos"][i])
            cpn  = float(R["c_neg"][i]);   apn  = float(R["a_neg"][i])
            fpn  = float(R["fps_neg"][i])
            pMp  = float(R["phi_Mn_pos"][i])
            pMn_ = float(R["phi_Mn_neg"][i])
            cdpp = float(R["cdp_pos"][i]); cdpn = float(R["cdp_neg"][i])
            # [FIX-A] index fpe and Sb as arrays
            fpei = float(R["fpe"][i]);     Sbi  = float(R["Sb"][i])
            Mcri = float(R["Mcr"][i])
            fri  = float(R["fr"])          # scalar, no index needed
            dvi  = float(R["dv"][i]);      Vci  = float(R["Vc"][i])
            pVi  = float(R["phi_Vn"][i]); Vnli = float(R["Vn_lim"][i])
            A_d  = float(R["A_duct"])
            n_d  = int(R["n_ducts"])

            ltr_c = float(R["lim_tr_c"]);  ltr_t = float(R["lim_tr_t"])
            lsv_ct= float(R["lim_sv_ct"]); lsv_t = float(R["lim_sv_t"])

            doc.add_heading(f"4.{ks+1}   Station  x = {xi:.2f} m", level=2)

            # 4.x.1  Section Properties
            h3(f"4.{ks+1}.1   Net Section Properties  (duct deducted — used at Transfer)")
            tbl(["Property","Formula","Substitution","Value","Unit"],[
                ["Slab thickness",      "t",          "input",
                 f"{ti*1000:.2f}","mm"],
                ["Tendon CG from top",  "z",          "input",
                 f"{zi*1000:.2f}","mm"],
                ["Section centroid",    "yc = t/2",
                 f"{ti*1000:.2f}/2", f"{yci*1000:.2f}","mm"],
                ["Eccentricity",        "e = yc − z",
                 f"{yci*1000:.2f}−{zi*1000:.2f}", f"{ei*1000:.4f}","mm"],
                ["Gross area",          "Ag = 1000·t",
                 f"1000×{ti*1000:.2f}", f"{Agi*1e6:.2f}","mm²/m"],
                ["Gross inertia",       "Ig = 1000·t³/12",
                 f"1000×{ti*1000:.2f}³/12", f"{Igi*1e12:.4f}×10⁻³","mm⁴/m"],
                ["Duct area (each)",    "Ad = π·d²/4",
                 f"π×{duct_dia_mm:.0f}²/4", f"{A_d*1e6:.3f}","mm²"],
                ["Duct CG from CG",     "yd = z−yc",
                 f"{zi*1000:.2f}−{yci*1000:.2f}", f"{ydi*1000:.4f}","mm"],
                ["Net area",            "An = Ag − n·Ad",
                 f"{Agi*1e6:.2f}−{n_d}×{A_d*1e6:.3f}", f"{Ani*1e6:.4f}","mm²/m"],
                ["Net inertia",         "In = Ig − n·Ad·yd²",
                 f"{Igi*1e12:.4f}×10⁻³−{n_d}×{A_d*1e6:.3f}×{ydi*1000:.4f}²×10⁻⁶",
                 f"{Ini*1e12:.6f}×10⁻³","mm⁴/m"],
            ], cw=[3.5,3.5,5.5,2.5,1.5])
            blank()

            # 4.x.2  Load Combinations
            h3(f"4.{ks+1}.2   Load Combinations")
            tbl(["Combination","Expression","Substitution","Value","Unit"],[
                ["Service I",
                 "Ms1 = M_DL + M_SDL + M_LL",
                 f"{mdi:.2f}+{msdi:.2f}+{mli:.2f}", f"{ms1i:.4f}","kNm/m"],
                ["Strength I — Moment",
                 "Mu = 1.25·MDL + 1.50·MSDL + 1.75·MLL",
                 f"1.25×{mdi:.2f}+1.50×{msdi:.2f}+1.75×{mli:.2f}",
                 f"{mui:.4f}","kNm/m"],
                ["Strength I — Shear",
                 "Vu = 1.25|VDL| + 1.50|VSDL| + 1.75|VLL|",
                 f"1.25×|{vdi:.2f}|+1.50×|{vsdi:.2f}|+1.75×|{vli:.2f}|",
                 f"{vui:.4f}","kN/m"],
            ], cw=[2.5,5.0,5.0,2.0,1.5])
            blank()

            # 4.x.3  Transfer Stress
            h3(f"4.{ks+1}.3   Stress Check — Transfer  (AASHTO 5.9.2.3.1)")
            para("Loading: Pi + M_DL  |  Net section (duct deducted)",
                 italic=True, indent=0.3)
            blank()
            para("Stress formula:", bold=True, indent=0.3)
            formula("σ_top = [ −Pi/An  +  Pi·e·yc/In  −  M·yc/In ] × 10⁻³  (MPa)")
            formula("σ_bot = [ −Pi/An  −  Pi·e·yc/In  +  M·yc/In ] × 10⁻³  (MPa)")
            blank()
            para("TOP fibre:", bold=True, indent=0.3)
            formula(f"σ_tr,top = [−{R['Pi']:.4f}/{Ani*1e6:.4f}"
                    f" + {R['Pi']:.4f}×{ei*1000:.4f}×{yci*1000:.4f}/{Ini*1e12:.6f}×10⁻³"
                    f" − {mdi:.4f}×{yci*1000:.4f}/{Ini*1e12:.6f}×10⁻³] × 10⁻³")
            result(f"σ_tr,top  =  {trt:.6f} MPa")
            pf(ltr_c <= trt <= ltr_t,
               f"σ_tr,top = {trt:.4f} MPa  within [{ltr_c:.3f},  +{ltr_t:.4f}] MPa",
               f"σ_tr,top = {trt:.4f} MPa  outside [{ltr_c:.3f}, +{ltr_t:.4f}] MPa")
            blank()
            para("BOTTOM fibre:", bold=True, indent=0.3)
            formula(f"σ_tr,bot = [−{R['Pi']:.4f}/{Ani*1e6:.4f}"
                    f" − {R['Pi']:.4f}×{ei*1000:.4f}×{yci*1000:.4f}/{Ini*1e12:.6f}×10⁻³"
                    f" + {mdi:.4f}×{yci*1000:.4f}/{Ini*1e12:.6f}×10⁻³] × 10⁻³")
            result(f"σ_tr,bot  =  {trb:.6f} MPa")
            pf(ltr_c <= trb <= ltr_t,
               f"σ_tr,bot = {trb:.4f} MPa  within [{ltr_c:.3f},  +{ltr_t:.4f}] MPa",
               f"σ_tr,bot = {trb:.4f} MPa  outside [{ltr_c:.3f}, +{ltr_t:.4f}] MPa")
            blank()

            # 4.x.4  Service Stress
            h3(f"4.{ks+1}.4   Stress Check — Service  (AASHTO 5.9.2.3.2)")
            para("Gross section used (ducts grouted).  Loading: Pe + load combination.",
                 italic=True, indent=0.3)
            blank()

            for (combo_name, M_i, t_s, b_s, note) in [
                ("Service I  (compression & tension check)",
                 ms1i, s1t, s1b, "both"),
            ]:
                para(f"── {combo_name}  |  M = {M_i:.4f} kNm/m ──",
                     bold=True, indent=0.3)
                formula(f"σ_top = [−{R['Pe']:.4f}/{Agi*1e6:.4f}"
                        f" + {R['Pe']:.4f}×{ei*1000:.4f}×{yci*1000:.4f}/{Igi*1e12:.6f}×10⁻³"
                        f" − {M_i:.4f}×{yci*1000:.4f}/{Igi*1e12:.6f}×10⁻³] × 10⁻³")
                result(f"σ_top  =  {t_s:.6f} MPa")
                pf(t_s >= lsv_ct,
                   f"σ_top = {t_s:.4f} MPa  ≥  {lsv_ct:.3f} MPa  (−0.60·f'c)",
                   f"σ_top = {t_s:.4f} MPa  <   {lsv_ct:.3f} MPa  EXCEEDS LIMIT")
                blank()
                formula(f"σ_bot = [−{R['Pe']:.4f}/{Agi*1e6:.4f}"
                        f" − {R['Pe']:.4f}×{ei*1000:.4f}×{yci*1000:.4f}/{Igi*1e12:.6f}×10⁻³"
                        f" + {M_i:.4f}×{yci*1000:.4f}/{Igi*1e12:.6f}×10⁻³] × 10⁻³")
                result(f"σ_bot  =  {b_s:.6f} MPa")
                # Compression check (bottom)
                pf(b_s >= lsv_ct,
                   f"σ_bot = {b_s:.4f} MPa  ≥  {lsv_ct:.3f} MPa  (−0.60·f'c)",
                   f"σ_bot = {b_s:.4f} MPa  <   {lsv_ct:.3f} MPa  EXCEEDS LIMIT")
                # Tension check — both fibres (Service I)
                blank()
                para("  Tension check  (both fibres ≤ +0.50√f'c):", bold=True, indent=0.3)
                pf(t_s <= lsv_t,
                   f"σ_top = {t_s:.4f} MPa  ≤  +{lsv_t:.4f} MPa  (tension OK)",
                   f"σ_top = {t_s:.4f} MPa  >  +{lsv_t:.4f} MPa  TENSION EXCEEDED")
                pf(b_s <= lsv_t,
                   f"σ_bot = {b_s:.4f} MPa  ≤  +{lsv_t:.4f} MPa  (tension OK)",
                   f"σ_bot = {b_s:.4f} MPa  >  +{lsv_t:.4f} MPa  TENSION EXCEEDED")
                blank()

            # 4.x.5  Flexural Strength
            h3(f"4.{ks+1}.5   Flexural Strength Check — Strength I  (AASHTO 5.6.3)")
            para("Rectangular stress block | No mild steel | Separate +Mu / −Mu capacity",
                 italic=True, indent=0.3)
            blank()

            for (label, dp_v, c_v, a_v, fp_v, pMnv, cdpv, mux) in [
                ("+Mu  (sagging, comp. face = TOP)",
                 dpp, cpp, app, fpp,  pMp,       cdpp, mui),
                ("−Mu  (hogging, comp. face = BOTTOM)",
                 dpn, cpn, apn, fpn,  abs(pMn_), cdpn, mui),
            ]:
                para(f"── {label} ──", bold=True, indent=0.3)
                para(f"  Effective depth  dp = {dp_v*1000:.2f} mm", indent=0.4)
                blank()

                para("  Step 1  Depth of neutral axis  c:", bold=True, indent=0.3)
                formula("  c  =  Aps·fpu / (0.85·f'c·β₁·b·1000  +  k·Aps·fpu / dp)")
                subst (f"     =  {R['Aps']*1e6:.4f}×{fpu:.0f}"
                       f" / (0.85×{fc:.1f}×{R['beta1']:.4f}×1000"
                       f" + {R['k_fac']:.4f}×{R['Aps']*1e6:.4f}×{fpu:.0f}/{dp_v*1000:.2f})")
                result(f"  c  =  {c_v*1000:.4f} mm")
                blank()

                para("  Step 2  Depth of stress block  a  =  β₁·c:", bold=True, indent=0.3)
                formula(f"  a  =  {R['beta1']:.4f}  ×  {c_v*1000:.4f} mm")
                result(f"  a  =  {a_v*1000:.4f} mm")
                pf(a_v <= dp_v,
                   f"a ({a_v*1000:.2f} mm) ≤ dp ({dp_v*1000:.2f} mm)  — rectangular section OK",
                   f"a ({a_v*1000:.2f} mm) > dp ({dp_v*1000:.2f} mm)  — T-section!")
                blank()

                para("  Step 3  Stress in prestress steel  fps:", bold=True, indent=0.3)
                formula("  fps  =  fpu × [1 − k·(c/dp)]")
                subst (f"      =  {fpu:.0f} × [1 − {R['k_fac']:.4f}×{c_v*1000:.4f}/{dp_v*1000:.2f}]")
                result(f"  fps  =  {fp_v:.4f} MPa")
                blank()

                para("  Step 4  Nominal flexural resistance  Mn:", bold=True, indent=0.3)
                formula("  Mn   =  Aps · fps · (dp − a/2)")
                subst (f"      =  {R['Aps']*1e6:.4f}mm²  ×  {fp_v:.4f}MPa"
                       f"  ×  ({dp_v*1000:.2f} − {a_v*1000:.4f}/2)mm  × 10⁻⁶")
                result(f"  Mn   =  {pMnv/phi_flex:.4f} kNm/m")
                blank()

                para("  Step 5  Factored resistance  φMn:", bold=True, indent=0.3)
                formula(f"  φMn  =  {phi_flex:.2f}  ×  {pMnv/phi_flex:.4f}")
                result(f"  φMn  =  {pMnv:.4f} kNm/m")
                blank()

                para("  Step 6  Demand/Capacity  (DCR):", bold=True, indent=0.3)
                dcr_v = abs(mux)/pMnv if pMnv > 0 else 999
                pf(abs(mux) <= pMnv,
                   f"|Mu|={abs(mux):.4f} ≤ φMn={pMnv:.4f} kNm/m  (DCR={dcr_v:.4f})",
                   f"|Mu|={abs(mux):.4f} > φMn={pMnv:.4f} kNm/m  (DCR={dcr_v:.4f})  FAILS")
                blank()

                para("  Step 7  Ductility  c/dp ≤ 0.42  (AASHTO 5.7.3.3.1):",
                     bold=True, indent=0.3)
                formula(f"  c/dp  =  {c_v*1000:.4f} / {dp_v*1000:.2f}  =  {cdpv:.4f}")
                pf(cdpv <= 0.42,
                   f"c/dp = {cdpv:.4f} ≤ 0.42  — tension-controlled",
                   f"c/dp = {cdpv:.4f} > 0.42  — NOT tension-controlled")
                blank()

            # Min reinforcement — [FIX-A] use fpei and Sbi (scalar)
            para("── Minimum Reinforcement  (AASHTO 5.6.3.3) ──", bold=True, indent=0.3)
            formula("Mcr  =  (fr + fpe) × Sb  × 10⁻³")
            formula(f"     =  ({fri:.4f} MPa  +  {fpei:.4f} MPa)  ×  {Sbi:.8f} m³")
            result(f"Mcr  =  {Mcri:.4f} kNm/m")
            blank()
            min_req = min(1.2*Mcri, 1.33*abs(mui))
            formula(f"1.2·Mcr = {1.2*Mcri:.4f} kNm/m")
            formula(f"1.33·|Mu| = {1.33*abs(mui):.4f} kNm/m   →  governing = {min_req:.4f} kNm/m")
            pf(max(pMp, abs(pMn_)) >= min_req,
               f"φMn = {max(pMp, abs(pMn_)):.4f} ≥ {min_req:.4f} kNm/m  OK",
               f"φMn = {max(pMp, abs(pMn_)):.4f} < {min_req:.4f} kNm/m  INSUFFICIENT")
            blank()

            # 4.x.6  Shear
            h3(f"4.{ks+1}.6   Shear Strength Check — Strength I  (AASHTO 5.7.3)")
            para("Simplified method: β=2.0  |  Vs=0 (no stirrups)  |  Vp=0",
                 italic=True, indent=0.3)
            blank()

            para("  Step 1  Effective shear depth  dv  (AASHTO 5.7.2.8):",
                 bold=True, indent=0.3)
            dp_use_v = max(dpp, dpn)
            formula("  dv  =  max(0.9·dp,  0.72·t)")
            subst (f"      =  max(0.9×{dp_use_v*1000:.2f}mm,  0.72×{ti*1000:.2f}mm)")
            result(f"  dv  =  {dvi*1000:.4f} mm")
            blank()

            para("  Step 2  Concrete shear resistance  Vc  (AASHTO 5.7.3.3-3):",
                 bold=True, indent=0.3)
            formula("  Vc  =  0.083·β·λ·√f'c·bv·dv × 10⁻³")
            subst (f"      =  0.083×2.0×1.0×√{fc:.1f}×1000mm×{dvi*1000:.4f}mm × 10⁻³")
            result(f"  Vc  =  {Vci:.4f} kN/m")
            blank()

            para("  Step 3  Upper limit  Vn,max  (AASHTO 5.7.3.3-2):",
                 bold=True, indent=0.3)
            formula("  Vn,max  =  0.25·f'c·bv·dv × 10⁻³")
            subst (f"         =  0.25×{fc:.1f}MPa×1000mm×{dvi*1000:.4f}mm × 10⁻³")
            result(f"  Vn,max  =  {Vnli:.4f} kN/m")
            blank()

            Vn_use = min(Vci, Vnli)
            para("  Step 4  Nominal shear resistance:", bold=True, indent=0.3)
            formula("  Vn  =  min(Vc, Vn,max)  [Vs=0, Vp=0]")
            result(f"  Vn  =  {Vn_use:.4f} kN/m")
            blank()

            para("  Step 5  Factored resistance  φVn:", bold=True, indent=0.3)
            formula(f"  φVn  =  {phi_shear:.2f}  ×  {Vn_use:.4f}")
            result(f"  φVn  =  {pVi:.4f} kN/m")
            blank()

            para("  Step 6  Demand/Capacity check:", bold=True, indent=0.3)
            dcr_sh = vui/pVi if pVi > 0 else 999
            pf(vui <= pVi,
               f"Vu={vui:.4f} ≤ φVn={pVi:.4f} kN/m  (DCR={dcr_sh:.4f})",
               f"Vu={vui:.4f} > φVn={pVi:.4f} kN/m  (DCR={dcr_sh:.4f})  INSUFFICIENT")
            blank()

            doc.add_page_break()

        # ══════════════════════════════════════════════════════════════
        # SEC 5 — SUMMARY
        # ══════════════════════════════════════════════════════════════
        h1("5.  Summary of Results — All Stations")
        sum_rows = []
        for i in sta_idx:
            mui_ = float(R["mu"][i]); vui_ = float(R["vu"][i])
            pMp_ = float(R["phi_Mn_pos"][i]); pMn__ = float(R["phi_Mn_neg"][i])
            pVi_ = float(R["phi_Vn"][i])
            cap  = pMp_ if mui_ >= 0 else abs(pMn__)
            dcr_m = abs(mui_)/cap   if cap  > 0 else 999
            dcr_v = vui_/pVi_       if pVi_ > 0 else 999
            ok_tr = (R["lim_tr_c"]<=R["tr_top"][i]<=R["lim_tr_t"] and
                     R["lim_tr_c"]<=R["tr_bot"][i]<=R["lim_tr_t"])
            ok_sv = (R["sv1_top"][i] >= R["lim_sv_ct"] and
                     R["sv1_bot"][i] >= R["lim_sv_ct"] and
                     R["sv1_top"][i] <= R["lim_sv_t"]  and
                     R["sv1_bot"][i] <= R["lim_sv_t"])
            sum_rows.append([
                f"{R['x'][i]:.2f}",
                f"{R['tr_top'][i]:.3f}",  f"{R['tr_bot'][i]:.3f}",
                "PASS" if ok_tr else "FAIL",
                f"{R['sv1_top'][i]:.3f}", f"{R['sv1_bot'][i]:.3f}",
                "PASS" if ok_sv else "FAIL",
                f"{mui_:.2f}", f"{cap:.2f}", f"{dcr_m:.4f}",
                "PASS" if abs(mui_)<=cap else "FAIL",
                f"{vui_:.2f}", f"{pVi_:.2f}", f"{dcr_v:.4f}",
                "PASS" if vui_<=pVi_ else "FAIL",
            ])
        tbl(["x(m)",
             "σ_top Tr","σ_bot Tr","Transfer",
             "σ_top SvcI","σ_bot SvcI","Service I",
             "Mu","φMn","DCR_M","Flexure",
             "Vu","φVn","DCR_V","Shear"],
            sum_rows,
            cw=[1.2,1.6,1.6,1.4,1.8,1.8,1.6,1.6,1.6,1.4,1.4,1.6,1.6,1.4,1.4])
        blank()

        h1("6.  Conclusion")
        all_pass = all(
            R["lim_tr_c"]<=R["tr_top"][i]<=R["lim_tr_t"] and
            R["lim_tr_c"]<=R["tr_bot"][i]<=R["lim_tr_t"] and
            R["sv1_top"][i] >= R["lim_sv_ct"] and
            R["sv1_bot"][i] >= R["lim_sv_ct"] and
            R["sv1_top"][i] <= R["lim_sv_t"]  and
            R["sv1_bot"][i] <= R["lim_sv_t"]  and
            abs(float(R["mu"][i])) <= max(float(R["phi_Mn_pos"][i]),
                                          abs(float(R["phi_Mn_neg"][i]))) and
            float(R["vu"][i]) <= float(R["phi_Vn"][i])
            for i in sta_idx
        )
        if all_pass:
            para("► OVERALL: The top flange tendon design is ADEQUATE for all "
                 "AASHTO LRFD limit states checked.",
                 bold=True, color=C_GREEN)
        else:
            para("► OVERALL: The design does NOT satisfy all limit states. "
                 "Revise tendon layout, spacing, or section geometry.",
                 bold=True, color=C_RED)
        blank()
        para("─── END OF CALCULATION ───", color=C_GRAY,
             align=WD_ALIGN_PARAGRAPH.CENTER)

        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

    # ── Download button  [FIX-B] wrapped in own try so tabs always render ──
    with st.sidebar:
        st.markdown("---")
        try:
            report_bytes = make_report()
            st.download_button(
                label="📥 Download Report (.docx)",
                data=report_bytes,
                file_name=f"CalcReport_{proj_name.replace(' ','_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        except Exception as rep_err:
            st.error(f"Report error: {rep_err}")

    # ─────────────────────────────────────────────────────────────────
    # 6.  TABS  (always rendered — outside report try block)
    # ─────────────────────────────────────────────────────────────────
    def dcr_style(df_in, col):
        def _s(val):
            try: v = float(val)
            except: return ""
            if v <= 0.80: return "background-color:#c6efce;color:#276221"
            if v <= 1.00: return "background-color:#ffeb9c;color:#9c6500"
            return "background-color:#ffc7ce;color:#9c0006"
        return df_in.style.map(_s, subset=[col])

    tabs = st.tabs([
        "📐 Geometry",
        "🚀 Transfer Stress",
        "⚖️ Service Stress",
        "💪 Flexure (Envelope)",
        "🔪 Shear",
        "📋 Summary",
    ])

    with tabs[0]:
        st.subheader("Top Flange Cross-Section with Tendon Layout")

        # ── x-axis in metres, y-axis in mm ─────────────────────────────
        x_m    = R["x"]                    # metres (unchanged)
        top_mm = np.zeros(N)               # y in mm
        bot_mm = -R["t"] * 1000.0
        cg_mm  = -R["yc"] * 1000.0
        tdn_mm = -R["z"] * 1000.0

        t_max_mm = float(R["t"].max()) * 1000.0
        t_min_mm = float(R["t"].min()) * 1000.0

        # scaleratio: 1 y-unit (mm) = scale_k x-units (m)
        # target: flange thickness ≈ 15% of visual width
        # scale_k = (0.15 * width_m) / (t_max_mm / 1000)  → unitless ratio
        scale_k  = max(1.0, round(0.15 * width / (t_max_mm / 1000.0)))
        y_margin = t_max_mm * 1.8
        y_range  = [-t_max_mm - y_margin, y_margin]

        fig = go.Figure()

        # Section fill
        fig.add_trace(go.Scatter(
            x=np.concatenate([x_m, x_m[::-1]]),
            y=np.concatenate([top_mm, bot_mm[::-1]]),
            fill="toself",
            fillcolor="rgba(173, 204, 240, 0.45)",
            line=dict(color="steelblue", width=1.5),
            name="Top Flange", hoverinfo="skip",
        ))

        # Section CG
        fig.add_trace(go.Scatter(
            x=x_m, y=cg_mm, mode="lines",
            line=dict(color="gray", dash="dot", width=1),
            name="Section CG",
        ))

        # Tendon CGS — smooth line
        fig.add_trace(go.Scatter(
            x=x_m, y=tdn_mm, mode="lines",
            line=dict(color="red", width=2.0),
            name="Tendon CGS", showlegend=True,
        ))

        # Tendon dots — input stations only
        _tdn_prep = prep(df_tdn)
        tdn_dot_x = _tdn_prep["x (m)"].values          # metres
        tdn_dot_y = -_tdn_prep["z_top (m)"].values * 1000.0
        fig.add_trace(go.Scatter(
            x=tdn_dot_x, y=tdn_dot_y, mode="markers",
            marker=dict(color="red", size=9, symbol="circle",
                        line=dict(color="white", width=1.5)),
            name="Tendon input pts", showlegend=True,
        ))

        # Flange edges — cyan dotted
        for x_edge, label, a_pos in [
            (0.0,   "Edge L.Flange", "top right"),
            (width, "Edge R.Flange", "top left"),
        ]:
            fig.add_vline(
                x=x_edge,
                line=dict(color="rgba(0,170,170,0.85)", dash="dot", width=1.8),
                annotation_text=f"<b>{label}</b>",
                annotation_position=a_pos,
                annotation_font=dict(size=10, color="rgba(0,150,150,1)"),
            )

        # Web centerlines — orange dashed
        for x_wf, label, a_pos in [
            (cl_lweb, "CL. L.Web", "top right"),
            (cl_rweb, "CL. R.Web", "top left"),
        ]:
            fig.add_vline(
                x=x_wf,
                line=dict(color="rgba(200,100,0,0.9)", dash="dash", width=2.0),
                annotation_text=f"<b>{label}</b>",
                annotation_position=a_pos,
                annotation_font=dict(size=10, color="rgba(200,100,0,1)"),
            )

        # No station x-labels (removed as requested)

        fig.update_layout(
            title="Top Flange Cross-Section with Tendon Layout",
            height=420,
            xaxis=dict(
                title="Distance from Left Edge (m)",
                range=[-width*0.04, width*1.04],
                showgrid=True, gridcolor="rgba(200,200,200,0.4)",
            ),
            yaxis=dict(
                title="Depth (mm)",
                range=y_range,
                showgrid=True, gridcolor="rgba(200,200,200,0.4)"
            ),
            legend=dict(orientation="h", y=-0.18),
            plot_bgcolor="white",
            margin=dict(t=50, b=80),
        )

        st.plotly_chart(fig, use_container_width=True)
        col_inf1, col_inf2, col_inf3, col_inf4 = st.columns(4)
        col_inf1.info(f"Scale y:x = 1:{int(scale_k)}")
        col_inf2.info(f"t_min = {t_min_mm:.0f} mm")
        col_inf3.info(f"CL.L.Web = {cl_lweb:.2f} m")
        col_inf4.info(f"CL.R.Web = {cl_rweb:.2f} m")

        c1, c2, c3 = st.columns(3)
        c1.metric("Aps (1m strip)", f"{R['Aps']*1e6:.2f} mm²")
        c2.metric("Pi", f"{R['Pi']:.2f} kN/m")
        c3.metric("Pe", f"{R['Pe']:.2f} kN/m")

    with tabs[1]:
        st.subheader("Stress Check — Transfer  (Pi + M_DL  |  Net section)")
        fig2 = go.Figure([
            go.Scatter(x=R["x"], y=R["tr_top"], name="Top",    line_color="red"),
            go.Scatter(x=R["x"], y=R["tr_bot"], name="Bottom", line_color="blue"),
        ])
        fig2.add_hline(y=R["lim_tr_c"], line_dash="dash", line_color="orange",
                       annotation_text=f"−0.60f'ci = {R['lim_tr_c']:.2f} MPa")
        fig2.add_hline(y=R["lim_tr_t"], line_dash="dash", line_color="green",
                       annotation_text=f"+0.62√f'ci = +{R['lim_tr_t']:.3f} MPa")
        fig2.update_layout(height=380, xaxis_title="x (m)", yaxis_title="Stress (MPa)")
        st.plotly_chart(fig2, use_container_width=True)
        rows_tr = [{"x (m)": f"{R['x'][i]:.2f}",
                    "σ_top (MPa)": f"{R['tr_top'][i]:.4f}",
                    "σ_bot (MPa)": f"{R['tr_bot'][i]:.4f}",
                    "Status": "✅" if (R["lim_tr_c"]<=R["tr_top"][i]<=R["lim_tr_t"] and
                                       R["lim_tr_c"]<=R["tr_bot"][i]<=R["lim_tr_t"]) else "❌"}
                   for i in sta_idx]
        st.dataframe(pd.DataFrame(rows_tr), use_container_width=True)

    with tabs[2]:
        st.subheader("Stress Check — Service I  (Pe + Ms1  |  Gross section)")
        fig3 = go.Figure([
            go.Scatter(x=R["x"], y=R["sv1_top"], name="Top", line_color="red"),
            go.Scatter(x=R["x"], y=R["sv1_bot"], name="Bottom", line_color="blue"),
        ])
        fig3.add_hline(y=R["lim_sv_ct"], line_dash="dash", line_color="orange",
                       annotation_text=f"−0.60f'c = {R['lim_sv_ct']:.2f} MPa")
        fig3.add_hline(y=R["lim_sv_cp"], line_dash="dot",  line_color="orange",
                       annotation_text=f"−0.45f'c = {R['lim_sv_cp']:.2f} MPa")
        fig3.add_hline(y=R["lim_sv_t"],  line_dash="dash", line_color="green",
                       annotation_text=f"+0.50√f'c = +{R['lim_sv_t']:.3f} MPa")
        fig3.update_layout(height=380, xaxis_title="x (m)", yaxis_title="Stress (MPa)")
        st.plotly_chart(fig3, use_container_width=True)
        rows_sv = [{"x (m)":        f"{R['x'][i]:.2f}",
                    "σ_top (MPa)":  f"{R['sv1_top'][i]:.4f}",
                    "σ_bot (MPa)":  f"{R['sv1_bot'][i]:.4f}",
                    "Comp. Limit":  f"{R['lim_sv_ct']:.2f}",
                    "Tens. Limit":  f"+{R['lim_sv_t']:.3f}",
                    "Status": "✅" if (R["sv1_top"][i] >= R["lim_sv_ct"] and
                                       R["sv1_bot"][i] >= R["lim_sv_ct"] and
                                       R["sv1_top"][i] <= R["lim_sv_t"]  and
                                       R["sv1_bot"][i] <= R["lim_sv_t"]) else "❌"}
                   for i in sta_idx]
        st.dataframe(pd.DataFrame(rows_sv), use_container_width=True)

    with tabs[3]:
        st.subheader("Flexural Strength Envelope  —  Strength I")
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=R["x"], y=R["phi_Mn_pos"], name="+φMn",
                                   line=dict(color="green", dash="dash", width=2)))
        fig4.add_trace(go.Scatter(x=R["x"], y=R["phi_Mn_neg"], name="−φMn",
                                   line=dict(color="darkgreen", dash="dash", width=2)))
        fig4.add_trace(go.Scatter(x=R["x"], y=R["mu"], name="Mu",
                                   fill="tozeroy", line_color="rgba(220,50,50,0.8)"))
        fig4.update_layout(height=380, xaxis_title="x (m)", yaxis_title="Moment (kNm/m)")
        st.plotly_chart(fig4, use_container_width=True)
        rows_flx = []
        for i in sta_idx:
            mx   = float(R["mu"][i])
            cap  = float(R["phi_Mn_pos"][i]) if mx>=0 else abs(float(R["phi_Mn_neg"][i]))
            cdp  = float(R["cdp_pos"][i])    if mx>=0 else float(R["cdp_neg"][i])
            dcr  = abs(mx)/cap if cap>0 else 999
            rows_flx.append({"x (m)": f"{R['x'][i]:.2f}",
                              "Mu (kNm/m)":  f"{mx:.4f}",
                              "φMn (kNm/m)": f"{cap:.4f}",
                              "DCR":         f"{dcr:.4f}",
                              "c/dp":        f"{cdp:.4f}",
                              "Strength":    "✅" if abs(mx)<=cap else "❌",
                              "Ductility":   "✅" if cdp<=0.42   else "❌"})
        df_flx = pd.DataFrame(rows_flx)
        st.dataframe(dcr_style(df_flx, "DCR"), use_container_width=True)

    with tabs[4]:
        st.subheader("Shear Strength  —  Strength I  (β=2.0)")
        fig5 = go.Figure([
            go.Scatter(x=R["x"], y=R["phi_Vn"], name="φVn",
                       line=dict(color="green", width=2)),
            go.Scatter(x=R["x"], y=R["vu"],     name="Vu  (factored)",
                       fill="tozeroy", line_color="rgba(0,100,220,0.8)"),
        ])
        fig5.update_layout(height=380, xaxis_title="x (m)", yaxis_title="Shear (kN/m)")
        st.plotly_chart(fig5, use_container_width=True)
        rows_shr = []
        for i in sta_idx:
            vui_= float(R["vu"][i]);  pVi_= float(R["phi_Vn"][i])
            dcr = vui_/pVi_ if pVi_>0 else 999
            rows_shr.append({"x (m)":      f"{R['x'][i]:.2f}",
                              "dv (mm)":    f"{R['dv'][i]*1000:.2f}",
                              "Vc (kN/m)":  f"{R['Vc'][i]:.4f}",
                              "φVn (kN/m)": f"{pVi_:.4f}",
                              "Vu (kN/m)":  f"{vui_:.4f}",
                              "DCR":        f"{dcr:.4f}",
                              "Status":     "✅" if vui_<=pVi_ else "❌"})
        df_shr = pd.DataFrame(rows_shr)
        st.dataframe(dcr_style(df_shr, "DCR"), use_container_width=True)

    with tabs[5]:
        st.subheader("📋 Overall Design Summary")
        rows_sum = []
        for i in sta_idx:
            mui_= float(R["mu"][i]);  vui_= float(R["vu"][i])
            cap = (float(R["phi_Mn_pos"][i]) if mui_>=0
                   else abs(float(R["phi_Mn_neg"][i])))
            pVi_= float(R["phi_Vn"][i])
            ok_tr = (R["lim_tr_c"]<=R["tr_top"][i]<=R["lim_tr_t"] and
                     R["lim_tr_c"]<=R["tr_bot"][i]<=R["lim_tr_t"])
            ok_sv = (R["sv1_top"][i] >= R["lim_sv_ct"] and
                     R["sv1_bot"][i] >= R["lim_sv_ct"] and
                     R["sv1_top"][i] <= R["lim_sv_t"]  and
                     R["sv1_bot"][i] <= R["lim_sv_t"])
            dcr_m = abs(mui_)/cap   if cap >0 else 999
            dcr_v = vui_/pVi_       if pVi_>0 else 999
            rows_sum.append({
                "x (m)":     f"{R['x'][i]:.2f}",
                "Transfer":  "✅" if ok_tr else "❌",
                "Service":   "✅" if ok_sv else "❌",
                "DCR_M":     f"{dcr_m:.4f}",
                "Flexure":   "✅" if abs(mui_)<=cap  else "❌",
                "DCR_V":     f"{dcr_v:.4f}",
                "Shear":     "✅" if vui_<=pVi_       else "❌",
            })
        df_sum = pd.DataFrame(rows_sum)
        st.dataframe(dcr_style(df_sum, "DCR_M"), use_container_width=True)

        all_ok = all(
            r["Transfer"]=="✅" and r["Service"]=="✅" and
            r["Flexure"]=="✅"  and r["Shear"]=="✅"
            for r in rows_sum
        )
        if all_ok:
            st.success("✅  DESIGN ADEQUATE — All checks pass at all stations.")
        else:
            st.error("❌  DESIGN INADEQUATE — One or more checks fail. Revise design.")

        st.caption("DCR: 🟢 ≤0.80  |  🟡 0.80–1.00  |  🔴 >1.00")

except Exception as err:
    st.error(f"Calculation error: {err}")
    raise
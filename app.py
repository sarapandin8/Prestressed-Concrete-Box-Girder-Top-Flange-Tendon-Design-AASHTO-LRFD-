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
    fpi_ratio=0.75,
    t0=3, RH=75,  # transfer age (days), relative humidity (%)
    anch_slip_mm=6.0,
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
for src_key, tbl_key in _TABLE_SRC.items():
    if src_key not in st.session_state:
        st.session_state[src_key] = pd.DataFrame(DEFAULT_TABLES[tbl_key])

# _tbl_ver: increment on load → editor key changes → widget reinits from new src
if "_tbl_ver" not in st.session_state:
    st.session_state["_tbl_ver"] = 0

# _loaded_hash: prevent rerun loop with static uploader key
if "_loaded_hash" not in st.session_state:
    st.session_state["_loaded_hash"] = None


# ─────────────────────────────────────────────────────────────────────────────
# 2.  SIDEBAR (Native State Binding)
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
# ── 💾 SAVE / 📂 OPEN ────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("💾  Save  /  📂  Open Project", expanded=True):

        # ── SAVE ─────────────────────────────────────────────────────────────
        # Read from _cur_thk/_cur_tdn/_cur_ld = data_editor return values
        def _tbl_to_dict(cur_key, src_key):
            df = st.session_state.get(cur_key,
                 st.session_state.get(src_key, pd.DataFrame()))
            if not isinstance(df, pd.DataFrame):
                try:    df = pd.DataFrame(df)
                except: return {}
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.dropna(how="all")
            return df.to_dict(orient="list") if not df.empty else {}

        _save_data = {
            "scalars": {k: st.session_state[k] for k in DEFAULT_SCALARS},
            "tables": {
                "df_thickness": _tbl_to_dict("_cur_thk", "thk_src"),
                "df_tendon":    _tbl_to_dict("_cur_tdn", "tdn_src"),
                "df_load":      _tbl_to_dict("_cur_ld",  "ld_src"),
            },
        }
        _json_bytes = json.dumps(_save_data, indent=2, ensure_ascii=False).encode("utf-8")
        _fname = f"{st.session_state.proj_name.replace(' ','_')}_{st.session_state.doc_no}.json"
        st.download_button(
            label="💾  Save Project  (.json)",
            data=_json_bytes, file_name=_fname,
            mime="application/json", use_container_width=True,
        )
        st.caption("ตั้ง Chrome: Settings → Downloads → 'Ask where to save'")
        st.markdown("---")

        # ── OPEN ─────────────────────────────────────────────────────────────
        # Static key → file always reaches handler
        # Hash check → process each unique file once (no rerun loop)
        uploaded_file = st.file_uploader(
            "📂  Open Project  (.json)", type="json",
            key="proj_uploader",
            help="เลือกไฟล์ .json ที่เคย Save ไว้",
        )
        if uploaded_file is not None:
            _raw   = uploaded_file.getvalue()
            _fhash = hash(_raw)
            if st.session_state["_loaded_hash"] != _fhash:
                try:
                    loaded = json.loads(_raw.decode("utf-8"))
                    # Load scalars
                    for k, v in loaded.get("scalars", {}).items():
                        if k in DEFAULT_SCALARS:
                            dv = DEFAULT_SCALARS[k]
                            st.session_state[k] = (
                                int(v)   if isinstance(dv, int)   else
                                float(v) if isinstance(dv, float) else str(v)
                            )
                    # Load tables → update src keys
                    _lmap = {"df_thickness":"thk_src","df_tendon":"tdn_src","df_load":"ld_src"}
                    for tbl_key, src_key in _lmap.items():
                        raw_tbl = loaded.get("tables", {}).get(tbl_key)
                        if raw_tbl:
                            ndf = pd.DataFrame(raw_tbl)
                            for col in ndf.columns:
                                ndf[col] = pd.to_numeric(ndf[col], errors="coerce")
                            st.session_state[src_key] = ndf.dropna(how="all")
                    # Increment version → editor keys change → widgets reinit from new src
                    st.session_state["_tbl_ver"] += 1
                    for k in ["_cur_thk", "_cur_tdn", "_cur_ld"]:
                        st.session_state.pop(k, None)
                    st.session_state["_loaded_hash"] = _fhash
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
        num_tendon = st.number_input("Tendons per 1 m strip", min_value=1, key="num_tendon")
        n_strands  = st.number_input("Strands per tendon",    min_value=1, key="n_strands")
        fpi_ratio  = st.slider("Jacking stress  fpi/fpu", 0.70, 0.80, key="fpi_ratio",
                               help="Standard = 0.75 fpu  (AASHTO 5.9.2.2)")

    # ── 📉 Prestress Losses (AASHTO LRFD 5.9.3) ─────────────────────────────
    with st.expander("📉 Prestress Loss Parameters", expanded=True):
        st.caption("แอปคำนวณ Loss ตาม AASHTO LRFD 5.9.3 อัตโนมัติ")
        t0_val       = st.number_input("Age at Transfer  t₀ (days)", min_value=1, key="t0",
                                       help="อายุคอนกรีตขณะ Transfer (ปกติ 3–7 วัน)")
        rh_val       = st.number_input("Relative Humidity  RH (%)", min_value=30,
                                       max_value=100, key="RH",
                                       help="ค่าความชื้นสัมพัทธ์เฉลี่ยของสภาพแวดล้อม")
        anch_val     = st.number_input("Anchorage Slip  Δ (mm)", value=6.0, min_value=0.0,
                                       key="anch_slip_mm", help="ค่ามาตรฐาน = 6 mm")
        st.caption("ค่าคงที่มาตรฐาน (7-wire low-relax, internal grouted PT):")
        st.markdown("- μ = 0.20, K = 0.0066 rad/m  *(AASHTO Table 5.9.3.2.1b-1)*")
        st.markdown("- Ep = 197,000 MPa  *(AASHTO 5.4.4.2)*")
        st.markdown("- Jacking: 0.75fpu, One-end")

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

# Versioned keys: change on file load → widgets reinit from updated src
_v = st.session_state["_tbl_ver"]

c1, c2 = st.columns(2)
with c1:
    st.subheader("📏 Flange Thickness t(x)")
    df_thk = st.data_editor(
        st.session_state["thk_src"], num_rows="dynamic", key=f"ed_thk_{_v}")
    st.session_state["_cur_thk"] = df_thk   # plain DataFrame for Save

    st.subheader("🔩 Tendon Profile z(x)  [from top face]")
    df_tdn = st.data_editor(
        st.session_state["tdn_src"], num_rows="dynamic", key=f"ed_tdn_{_v}")
    st.session_state["_cur_tdn"] = df_tdn
with c2:
    st.subheader("📦 Loads per 1 m strip")
    df_ld = st.data_editor(
        st.session_state["ld_src"], num_rows="dynamic", key=f"ed_ld_{_v}")
    st.session_state["_cur_ld"] = df_ld


# ─────────────────────────────────────────────────────────────────────────────
# PRESTRESS LOSS ENGINE  (AASHTO LRFD 5.9.3)
# ─────────────────────────────────────────────────────────────────────────────
def calc_losses(dft, dfp, fc, fci, fpu, fpi_ratio, aps_strand,
                num_tendon, n_strands, duct_dia_mm,
                t0, RH, anch_slip_mm, width):
    """
    Prestress loss calculation per AASHTO LRFD 5.9.3.
    Immediate: Friction (5.9.3.2.1) + Anchorage Set (5.9.3.2.2) + Elastic Shortening (5.9.3.2.3)
    Long-term: Shrinkage + Creep (5.9.3.4) + Relaxation (5.9.3.4.3)
    All stress in MPa. Geometry at midspan (representative section).
    """
    # ── Constants ──────────────────────────────────────────────────────────
    Ep    = 197_000.0    # Modulus of elasticity of prestress steel (MPa) [AASHTO 5.4.4.2]
    mu    = 0.20         # Friction coefficient (-) for grouted PT duct [AASHTO Table 5.9.3.2.1b-1]
    K_wob = 0.0066       # Wobble coefficient (rad/m) for grouted duct
    KL    = 45.0         # Relaxation factor (-) for low-relaxation strand [AASHTO 5.9.3.4.3c]
    b     = 1.0          # Strip width (m)
    wc    = 2400.0       # Unit weight of concrete (kg/m³) normal weight

    # ── Section properties at midspan ─────────────────────────────────────
    x_mid  = width / 2.0
    t_mid  = float(np.interp(x_mid, dft["x (m)"], dft["t (m)"]))
    z_mid  = float(np.interp(x_mid, dfp["x (m)"], dfp["z_top (m)"]))
    yc_mid = t_mid / 2.0
    e_mid  = yc_mid - z_mid    # Eccentricity (+: tendon above centroid) (m)

    Ag_mid = b * t_mid                       # Gross cross-sectional area (m²/m)
    Ig_mid = b * t_mid**3 / 12.0             # Gross moment of inertia (m⁴/m)
    A_duct = math.pi / 4.0 * (duct_dia_mm / 1000.0)**2
    n_duct = int(num_tendon)
    y_duct = z_mid - yc_mid
    An_mid = Ag_mid - n_duct * A_duct        # Net area after duct deduction (m²/m)
    In_mid = Ig_mid - n_duct * A_duct * y_duct**2  # Net inertia (m⁴/m)
    VS     = (b * t_mid) / (2.0 * (b + t_mid))     # Volume-to-Surface ratio (m)
    VS_mm  = VS * 1000.0                             # V/S in mm

    aps_m2  = aps_strand * 1e-6              # Area per strand (m²)
    n_total = int(num_tendon * n_strands)
    Aps     = n_total * aps_m2               # Total tendon area per 1m strip (m²/m)

    # ── Modulus of elasticity of concrete (AASHTO 5.4.2.4) ────────────────
    # Ec = 0.043 × wc^1.5 × √f'c  (MPa, wc in kg/m³)
    Ec  = 0.043 * (wc**1.5) * math.sqrt(fc)    # At service (MPa)
    Eci = 0.043 * (wc**1.5) * math.sqrt(fci)   # At transfer (MPa)

    # ── Tendon geometry ────────────────────────────────────────────────────
    # Angular change α = sum of absolute curvature changes along tendon (rad)
    xs = dft["x (m)"].values.astype(float)
    zs = np.interp(xs, dfp["x (m)"].values, dfp["z_top (m)"].values)
    dz = np.diff(zs); dx = np.diff(xs)
    dx_s = np.where(np.abs(dx) < 1e-9, 1e-9, dx)
    alpha = float(np.sum(np.abs(np.diff(np.append([0], np.arctan(dz / dx_s))))))
    alpha = max(alpha, 0.001)              # Minimum curvature 1 mrad
    L_ten = float(np.sum(np.sqrt(dx**2 + dz**2)))   # Tendon length along profile (m)
    if L_ten < 0.5: L_ten = float(xs[-1] - xs[0])

    # ── Jacking parameters ─────────────────────────────────────────────────
    fpj = fpu * fpi_ratio          # Jacking stress (MPa) = 0.75 fpu default
    Pj  = Aps * fpj * 1e3          # Jacking force per 1m strip (kN/m)

    # ══════════════════════════════════════════════════════════════════════
    # SECTION A — IMMEDIATE LOSSES
    # ══════════════════════════════════════════════════════════════════════

    # ── A1. Friction Loss  ΔfpF  (AASHTO 5.9.3.2.1) ───────────────────────
    # ΔfpF = fpj × (1 − e^(−μα − Kx))
    # Evaluate at full length (dead end) and at midspan (representative)
    exp_full = mu * alpha + K_wob * L_ten
    delta_fpF_full = fpj * (1.0 - math.exp(-exp_full))  # loss at dead end
    exp_mid  = mu * (alpha / 2.0) + K_wob * (L_ten / 2.0)
    delta_fpF = fpj * (1.0 - math.exp(-exp_mid))         # loss at midspan (used)

    # ── A2. Anchorage Set Loss  ΔfpA  (AASHTO 5.9.3.2.2) ──────────────────
    # Friction loss slope (rate of friction loss per unit length) [MPa/m]:
    # w = fpj × (μ × α/L + K)   [MPa/m]
    # [FIX] correct slope uses angular change rate (α/L), not just fpj/L
    friction_slope = fpj * (mu * alpha / L_ten + K_wob)   # MPa/m

    # Anchor set influence length:
    # Lpa = √(Δ_m × Ep_MPa / friction_slope_MPa_per_m)   → result in metres
    # Unit check: √(m × MPa / (MPa/m)) = √(m²) = m  ✓
    Lpa = math.sqrt((anch_slip_mm / 1000.0) * Ep / friction_slope)   # m  [FIX: no /1e3]
    Lpa = min(Lpa, L_ten)

    # Anchorage set stress loss at jacking end:
    # ΔfpA = Δ_m × Ep_MPa / Lpa_m  [MPa]
    delta_fpA = (anch_slip_mm / 1000.0) * Ep / Lpa
    delta_fpA = min(delta_fpA, 0.20 * fpj)   # sanity cap 20% of fpj

    # Stress in tendon at midspan after friction + anchor losses
    # (anchor set affects tendon only within Lpa from jacking end)
    fpt_mid = fpj - delta_fpF - (delta_fpA if Lpa > L_ten / 2.0 else 0.0)
    fpt_mid = max(fpt_mid, 0.5 * fpj)

    # ── A3. Elastic Shortening  ΔfpES  (AASHTO 5.9.3.2.3) ─────────────────
    # fcgp = concrete stress at tendon CG level at transfer
    # fcgp = Pi/An + Pi·e²/In   (compression positive for this term)
    Pi_est = Aps * fpt_mid * 1e3           # Estimated Pi (kN/m)
    fcgp   = (Pi_est/An_mid + Pi_est*e_mid**2/In_mid) / 1000.0  # MPa
    # ΔfpES = (Ep/Eci) × fcgp
    delta_fpES = (Ep / Eci) * fcgp
    delta_fpES = max(0.0, delta_fpES)

    # ── Immediate loss totals ──────────────────────────────────────────────
    delta_imm   = delta_fpF + delta_fpA + delta_fpES
    imm_loss_pct = delta_imm / fpj * 100.0

    fpi_eff  = max(fpj - delta_imm, 0.5 * fpj)   # Effective stress after transfer
    Pi_final = Aps * fpi_eff * 1e3                # Pi per 1m strip (kN/m)

    # ══════════════════════════════════════════════════════════════════════
    # SECTION B — LONG-TERM LOSSES  (AASHTO 5.9.3.4)
    # ══════════════════════════════════════════════════════════════════════

    # ── Correction factors ─────────────────────────────────────────────────
    fci_ksi = fci / 6.895    # f'ci converted to ksi for AASHTO factor formulas

    # kvs: Size factor for V/S ratio (AASHTO 5.4.2.3.2)
    kvs = max(1.45 - 0.0052 * VS_mm, 1.0)    # V/S in mm

    # khs: Humidity factor for shrinkage (AASHTO 5.4.2.3.3)
    khs = max(2.00 - 0.014 * RH, 0.0)

    # khc: Humidity factor for creep (AASHTO 5.4.2.3.2)
    khc = max(1.56 - 0.008 * RH, 0.0)

    # kf: Concrete strength factor — uses f'ci in ksi (AASHTO 5.4.2.3.2)
    # [FIX] must use ksi, not MPa
    kf = 5.0 / (1.0 + fci_ksi)

    # ktd: Time development factor (t→∞ for final losses: ktd = 1)
    ktd = 1.0

    # ── B1. Shrinkage strain  εbdf  (AASHTO 5.4.2.3.3) ────────────────────
    # εbdf = kvs × khs × kf × ktd × 0.48 × 10⁻³
    eps_bdf = kvs * khs * kf * ktd * 0.48e-3   # Shrinkage strain (dimensionless)

    # Shrinkage loss (AASHTO 5.9.3.4.2a-1):
    # ΔfpSH = εbdf × Ep
    delta_fpSH = eps_bdf * Ep                   # MPa

    # ── B2. Creep coefficient  ψb  (AASHTO 5.4.2.3.2) ─────────────────────
    ti_safe = max(float(t0), 1.0)
    # ψb(t,ti) = 1.9 × kvs × khc × kf × ktd × ti^(−0.118)
    psi_b = 1.9 * kvs * khc * kf * ktd * (ti_safe ** -0.118)

    # Concrete stress at tendon CG at transfer  fcgp  (MPa)
    fcgp_lt = (Pi_final/An_mid + Pi_final*e_mid**2/In_mid) / 1000.0  # MPa compression

    # Creep loss (AASHTO 5.9.3.4.2b-1):
    # ΔfpCR = (Ep/Ec) × fcgp × ψb
    delta_fpCR = max((Ep / Ec) * fcgp_lt * psi_b, 0.0)   # MPa

    # ── B3. Relaxation after transfer  ΔfpR2  (AASHTO 5.9.3.4.3c) ─────────
    # For low-relaxation strand:
    # ΔfpR2 = (fpt/KL) × (fpt/fpy − 0.55)  ≥ 0
    fpy = fpu * fpi_ratio / fpi_ratio * 0.9   # yield = 0.9 fpu for low-relax
    # fpt = stress after subtracting portion of long-term losses
    fpt_r = fpi_eff - 0.3 * (delta_fpSH + delta_fpCR)
    fpt_r = max(fpt_r, 0.5 * fpu)
    delta_fpR = max((fpt_r / KL) * (fpt_r / fpy - 0.55), 0.0)   # MPa

    # ── Long-term totals ───────────────────────────────────────────────────
    delta_lt    = delta_fpSH + delta_fpCR + delta_fpR
    lt_loss_pct = delta_lt / fpj * 100.0

    # ── Final effective prestress ──────────────────────────────────────────
    fpe_val  = max(fpi_eff - delta_lt, 0.45 * fpj)
    Pe_final = Aps * fpe_val * 1e3    # Pe per 1m strip (kN/m)

    return dict(
        # Material
        Ec=Ec, Eci=Eci, Ep=Ep,
        # Section
        t_mid=t_mid, z_mid=z_mid, e_mid=e_mid,
        Ag_mid=Ag_mid, Ig_mid=Ig_mid, An_mid=An_mid, In_mid=In_mid,
        VS=VS, VS_mm=VS_mm,
        Aps=Aps, n_total=n_total,
        # Tendon geometry
        alpha=alpha, L_ten=L_ten, Lpa=Lpa, friction_slope=friction_slope,
        # Jacking
        fpj=fpj, Pj=Pj,
        # Immediate losses
        delta_fpF=delta_fpF, delta_fpF_full=delta_fpF_full,
        delta_fpA=delta_fpA, delta_fpES=delta_fpES,
        delta_imm=delta_imm, imm_loss_pct=imm_loss_pct,
        fcgp=fcgp, fpt_mid=fpt_mid, Pi=Pi_final,
        # Long-term factors
        fci_ksi=fci_ksi, kvs=kvs, khs=khs, khc=khc, kf=kf, ktd=ktd,
        psi_b=psi_b, eps_bdf=eps_bdf,
        # Long-term losses
        fcgp_lt=fcgp_lt, delta_fpSH=delta_fpSH,
        delta_fpCR=delta_fpCR, delta_fpR=delta_fpR,
        delta_lt=delta_lt, lt_loss_pct=lt_loss_pct,
        fpi_eff=fpi_eff, fpe=fpe_val, Pe=Pe_final,
        eff_ratio=Pe_final / Pj if Pj > 0 else 0.75,
        total_loss_pct=(delta_imm + delta_lt) / fpj * 100.0,
    )

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

def run_calc(dft, dfp, dfl, L):
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

    # Prestress — use loss engine results (passed as argument)
    n_total = L["n_total"]
    Aps     = L["Aps"]
    fpi_val = L["fpi_eff"]   # effective stress after immediate losses
    Pi      = L["Pi"]
    Pe      = L["Pe"]

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
        L=L,
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

    # Compute losses first, then pass to run_calc
    t0_v   = int(st.session_state.get("t0", 3))
    rh_v   = int(st.session_state.get("RH", 75))
    anch_v = float(st.session_state.get("anch_slip_mm", 6.0))
    L = calc_losses(dft, dfp,
                    fc, fci, fpu, fpi_ratio, aps_strand,
                    num_tendon, n_strands, duct_dia_mm,
                    t0_v, rh_v, anch_v, width)
    R = run_calc(dft, dfp, dfl, L)

    # Station indices
    sta_x   = dfl["x (m)"].values
    sta_idx = [int(np.abs(R["x"] - v).argmin()) for v in sta_x]
    N       = len(R["x"])

    # ─────────────────────────────────────────────────────────────────
        # 5. REPORT GENERATOR (v4 - เพิ่มรูป Section + Stress)
        # ─────────────────────────────────────────────────────────────────
        def fig_to_png(fig, width=900, height=400):
            """แปลง Plotly fig เป็น BytesIO PNG แบบปลอดภัย ไม่กระทบโค้ดหลัก"""
            try:
                img_bytes = fig.to_image(format="png", width=width, height=height, scale=2)
                return BytesIO(img_bytes)
            except Exception as e:
                st.warning(f"สร้างรูปไม่ได้: {e} | ตรวจสอบว่า requirements.txt มี kaleido แล้ว")
                return None
        def make_report():
    doc = Document()
    for sec in doc.sections:
        sec.top_margin=Cm(2.0); sec.bottom_margin=Cm(2.0)
        sec.left_margin=Cm(2.5); sec.right_margin=Cm(2.0)
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)

    C_BLUE = RGBColor(0x00, 0x44, 0x88)
    C_GREEN = RGBColor(0x00, 0x70, 0x00)
    C_RED = RGBColor(0xC0, 0x00, 0x00)
    C_GRAY = RGBColor(0x60, 0x60, 0x60)

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

    def formula(s): return para(s, italic=True, indent=0.5, color=C_GRAY)
    def subst(s): return para(s, italic=True, indent=0.7, color=C_GRAY)
    def result(s): return para(s, bold=True, indent=0.7, color=C_BLUE)
    def blank(): return doc.add_paragraph()

    def pf(cond, ok, fail):
        if cond: para(f" ✔ {ok} [PASS]", bold=True, color=C_GREEN, indent=0.5)
        else: para(f" ✘ {fail} [FAIL]", bold=True, color=C_RED, indent=0.5)

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

    def s(key, i): return float(R[key][i])

    # ══════════════════════════════════════════════════════════════
    # COVER
    # ══════════════════════════════════════════════════════════════
    blank(); blank()
    doc.add_heading("STRUCTURAL CALCULATION REPORT", 0)
    blank()
    tbl(["Item","Description"],[
        ["Project", proj_name],
        ["Document No.", doc_no],
        ["Subject", "Transverse Tendon Design — PSC Box Girder Top Flange"],
        ["Code", "AASHTO LRFD Bridge Design Specifications"],
        ["Prepared by", eng_name],
        ["Checked by", chk_name],
        ["Date", datetime.datetime.now().strftime("%d %B %Y")],
    ], cw=[4.5,13.0])
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # SEC 1 — DESIGN BASIS
    # ══════════════════════════════════════════════════════════════
    h1("1. Design Basis")
    for it in [
        "Code: AASHTO LRFD Bridge Design Specifications",
        "Analysis basis: 1.0 m transverse strip across top flange",
        "Load combinations (AASHTO Table 3.4.1-1):",
        " Strength I : 1.25·DC + 1.50·DW + 1.75·LL",
        " Service I : 1.00·DC + 1.00·DW + 1.00·LL (compression & tension check)",
        " Transfer : Pi (after immediate losses) + M_DC",
        "Strand: Post-tensioned, bonded (fully grouted), low-relaxation",
        "Sign convention: Compression (−) | Tension (+)",
        "Positive moment = sagging (compression at TOP fibre)",
    ]: para(it, indent=0.3)
    blank()

    # ══════════════════════════════════════════════════════════════
    # SEC 2 — INPUT SUMMARY + รูปที่ 1: SECTION
    # ══════════════════════════════════════════════════════════════
    h1("2. Design Input Summary")

    h2("2.1 Material Properties")
    tbl(["Parameter","Symbol","Value","Unit","Reference"],[
        ["Concrete — service", "f'c", f"{fc:.1f}", "MPa","AASHTO 5.4.2"],
        ["Concrete — transfer", "f'ci", f"{fci:.1f}", "MPa","AASHTO 5.9.2"],
        ["Strand tensile strength", "fpu", f"{fpu:.0f}", "MPa","AASHTO 5.4.4"],
        ["Strand yield ratio", "fpy/fpu", f"{fpy_ratio:.2f}", "—", "Low-relax"],
        ["Area per strand", "asp", f"{aps_strand:.1f}", "mm²","Product data"],
        ["PT duct outer diameter", "d_duct", f"{duct_dia_mm:.0f}","mm", "Supplier"],
    ], cw=[4.5,2.0,2.0,1.5,4.5])
    blank()

    h2("2.2 Prestressing Configuration")
    tbl(["Parameter","Symbol","Value","Unit"],[
        ["Tendons per 1 m strip", "n_t", f"{int(num_tendon)}", "—"],
        ["Strands per tendon", "n_s", f"{int(n_strands)}", "—"],
        ["Total strands (1m strip)", "n", f"{R['n_total']}", "—"],
        ["Total Aps (1m strip)", "Aps", f"{R['Aps']*1e6:.2f}", "mm²/m"],
        ["Jacking stress ratio", "fpi/fpu", f"{fpi_ratio:.4f}", "—"],
        ["Immediate loss (computed)", "Δfi", f"{R['L']['imm_loss_pct']:.2f}", "%"],
        ["Long-term loss (computed)", "ΔfLT", f"{R['L']['lt_loss_pct']:.2f}", "%"],
        ["Total loss (computed)", "Δftot", f"{R['L']['total_loss_pct']:.2f}","%"],
    ], cw=[5.5,2.0])
    blank()

    h2("2.3 Resistance Factors")
    tbl(["Limit State","Symbol","Value"],[
        ["Flexure","φ_f",f"{phi_flex:.2f}"],
        ["Shear", "φ_v",f"{phi_shear:.2f}"],
    ], cw=[6.0,2.5,2.5])
    blank()

    h2("2.4 Allowable Stress Limits")
    tbl(["Condition","Expression","Limit (MPa)","Article"],[
        ["Transfer — Compression", "−0.60·f'ci", f"{R['lim_tr_c']:.3f}","5.9.2.3.1a"],
        ["Transfer — Tension (bonded)", "+0.62·√f'ci",f"+{R['lim_tr_t']:.4f}","5.9.2.3.1b"],
        ["Service I — Comp (perm.loads)", "−0.45·f'c", f"{R['lim_sv_cp']:.3f}","5.9.2.3.2a"],
        ["Service I — Comp (total loads)", "−0.60·f'c", f"{R['lim_sv_ct']:.3f}","5.9.2.3.2a"],
        ["Service I — Tension (bonded)", "+0.50·√f'c", f"+{R['lim_sv_t']:.4f}","5.9.2.3.2b"],
    ], cw=[5.5,3.5,2.5])
    blank()

    h2("2.5 Input Geometry and Load at Stations")
    geo_rows = []
    for i in sta_idx:
        geo_rows.append([
            f"{R['x'][i]:.2f}",
            f"{R['t'][i]*1000:.2f}", f"{R['z'][i]*1000:.2f}", f"{R['yc'][i]*1000:.2f}",
            f"{R['e'][i]*1000:.2f}",
            f"{R['m_dl'][i]:.2f}", f"{R['m_sdl'][i]:.2f}", f"{R['m_ll'][i]:.2f}",
            f"{R['v_dl'][i]:.2f}", f"{R['v_sdl'][i]:.2f}", f"{R['v_ll'][i]:.2f}",
        ])
    tbl(["x(m)","t(mm)","z(mm)","yc(mm)","e(mm)",
         "M_DL","M_SDL","M_LL","V_DL","V_SDL","V_LL"],
        geo_rows, cw=[1.4,1.6])
    para(" M in kNm/m | V in kN/m", italic=True, color=C_GRAY)
    blank()

    # ── รูปที่ 1: Section Geometry ───────────────────────────────────
    try:
        x_m = R["x"]; N = len(x_m)
        top_mm = np.zeros(N); bot_mm = -R["t"] * 1000.0
        cg_mm = -R["yc"] * 1000.0; tdn_mm = -R["z"] * 1000.0
        fig_sec = go.Figure()
        fig_sec.add_trace(go.Scatter(
            x=np.concatenate([x_m, x_m[::-1]]),
            y=np.concatenate([top_mm, bot_mm[::-1]]),
            fill="toself", fillcolor="rgba(173, 204, 240, 0.45)",
            line=dict(color="steelblue", width=1.5), name="Top Flange"
        ))
        fig_sec.add_trace(go.Scatter(x=x_m, y=cg_mm, mode="lines",
            line=dict(color="gray", dash="dot", width=1), name="Section CG"))
        fig_sec.add_trace(go.Scatter(x=x_m, y=tdn_mm, mode="lines",
            line=dict(color="red", width=2.0), name="Tendon CGS"))
        fig_sec.add_vline(x=cl_lweb, line=dict(color="rgba(200,100,0,0.9)", dash="dash"),
            annotation_text="<b>CL. L.Web</b>", annotation_position="top right")
        fig_sec.add_vline(x=cl_rweb, line=dict(color="rgba(200,100,0,0.9)", dash="dash"),
            annotation_text="<b>CL. R.Web</b>", annotation_position="top left")
        fig_sec.update_layout(
            title="Figure 2.1: Cross-Section with Tendon Layout",
            xaxis_title="Distance from Left Edge (m)", yaxis_title="Depth (mm)",
            height=400, width=900, plot_bgcolor="white",
            legend=dict(orientation="h", y=-0.2)
        )
        img1 = fig_to_png(fig_sec)
        if img1:
            h3("2.6 Section Geometry Plot")
            doc.add_picture(img1, width=Inches(6.5))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            blank()
    except Exception as e:
        para(f"[ข้ามรูป Section: {e}]", color=C_GRAY, italic=True)

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # SEC 3 — PRESTRESS LOSS
    # ══════════════════════════════════════════════════════════════
    h1("3. Prestress Loss Calculation (AASHTO LRFD 5.9.3)")
    _L = R["L"]; _fpj = _L["fpj"]

    h2("3.1 Loss Summary")
    tbl(["Loss Type","Value (MPa)","% of fpj"],[
        ["Immediate Δfi", f"{_L['delta_imm']:.2f}", f"{_L['imm_loss_pct']:.2f}"],
        ["Long-term ΔfLT", f"{_L['delta_lt']:.2f}", f"{_L['lt_loss_pct']:.2f}"],
        ["Total Δftotal", f"{_L['delta_imm']+_L['delta_lt']:.2f}", f"{_L['total_loss_pct']:.2f}"],
        ["Effective fpe", f"{_L['fpe']:.2f}", f"{_L['fpe']/_fpj*100:.1f}"],
    ], cw=[4,3,3])
    blank()
    result(f"Pe = {_L['Pe']:.2f} kN/m")
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # SEC 4 — STRESS DIAGRAMS + รูปที่ 2,3
    # ══════════════════════════════════════════════════════════════
    h1("4. Stress & Strength Results")

    # ── รูปที่ 2: Transfer Stress ───────────────────────────────────
    try:
        fig_tr = go.Figure([
            go.Scatter(x=R["x"], y=R["tr_top"], name="Top", line_color="red"),
            go.Scatter(x=R["x"], y=R["tr_bot"], name="Bottom", line_color="blue"),
        ])
        fig_tr.add_hline(y=R["lim_tr_c"], line_dash="dash", line_color="orange",
                       annotation_text=f"−0.60f'ci = {R['lim_tr_c']:.2f} MPa")
        fig_tr.add_hline(y=R["lim_tr_t"], line_dash="dash", line_color="green",
                       annotation_text=f"+0.62√f'ci = +{R['lim_tr_t']:.3f} MPa")
        fig_tr.update_layout(
            title="Figure 4.1: Transfer Stress (Pi + M_DL)",
            xaxis_title="x (m)", yaxis_title="Stress (MPa)",
            height=380, width=900, plot_bgcolor="white"
        )
        img2 = fig_to_png(fig_tr)
        if img2:
            h2("4.1 Transfer Stress Diagram")
            doc.add_picture(img2, width=Inches(6.5))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            blank()
    except Exception as e:
        para(f"[ข้ามรูป Transfer: {e}]", color=C_GRAY, italic=True)

    # ── รูปที่ 3: Service Stress ───────────────────────────────────
    try:
        fig_sv = go.Figure([
            go.Scatter(x=R["x"], y=R["sv1_top"], name="Top", line_color="red"),
            go.Scatter(x=R["x"], y=R["sv1_bot"], name="Bottom", line_color="blue"),
        ])
        fig_sv.add_hline(y=R["lim_sv_ct"], line_dash="dash", line_color="orange",
                       annotation_text=f"−0.60f'c = {R['lim_sv_ct']:.2f} MPa")
        fig_sv.add_hline(y=R["lim_sv_t"], line_dash="dash", line_color="green",
                       annotation_text=f"+0.50√f'c = +{R['lim_sv_t']:.3f} MPa")
        fig_sv.update_layout(
            title="Figure 4.2: Service I Stress (Pe + Ms1)",
            xaxis_title="x (m)", yaxis_title="Stress (MPa)",
            height=380, width=900, plot_bgcolor="white"
        )
        img3 = fig_to_png(fig_sv)
        if img3:
            h2("4.2 Service Stress Diagram")
            doc.add_picture(img3, width=Inches(6.5))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            blank()
    except Exception as e:
        para(f"[ข้ามรูป Service: {e}]", color=C_GRAY, italic=True)

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # SEC 5 — SUMMARY TABLE
    # ══════════════════════════════════════════════════════════════
    h1("5. Summary of Results — All Stations")
    sum_rows = []
    for i in sta_idx:
        mui_ = float(R["mu"][i]); vui_ = float(R["vu"][i])
        cap = (float(R["phi_Mn_pos"][i]) if mui_>=0
               else abs(float(R["phi_Mn_neg"][i])))
        pVi_ = float(R["phi_Vn"][i])
        ok_tr = (R["lim_tr_c"]<=R["tr_top"][i]<=R["lim_tr_t"] and
                 R["lim_tr_c"]<=R["tr_bot"][i]<=R["lim_tr_t"])
        ok_sv = (R["sv1_top"][i] >= R["lim_sv_ct"] and
                 R["sv1_bot"][i] >= R["lim_sv_ct"] and
                 R["sv1_top"][i] <= R["lim_sv_t"] and
                 R["sv1_bot"][i] <= R["lim_sv_t"])
        dcr_m = abs(mui_)/cap if cap >0 else 999
        dcr_v = vui_/pVi_ if pVi_>0 else 999
        sum_rows.append({
            "x (m)": f"{R['x'][i]:.2f}",
            "Transfer": "✅" if ok_tr else "❌",
            "Service": "✅" if ok_sv else "❌",
            "DCR_M": f"{dcr_m:.3f}",
            "Flexure": "✅" if abs(mui_)<=cap else "❌",
            "DCR_V": f"{dcr_v:.3f}",
            "Shear": "✅" if vui_<=pVi_ else "❌",
        })
    df_sum = pd.DataFrame(sum_rows)
    tbl(list(df_sum.columns), df_sum.values.tolist(), cw=[1.2,1.4])
    blank()

    all_ok = all(
        r["Transfer"]=="✅" and r["Service"]=="✅" and
        r["Flexure"]=="✅" and r["Shear"]=="✅"
        for r in sum_rows
    )
    if all_ok:
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
        "📉 Prestress Losses",
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
        # ── Prestress Losses Summary ────────────────────────────────────────
        st.subheader("📉 Prestress Loss Summary  (AASHTO LRFD 5.9.3)")
        _L = R["L"]
        _fpj = _L["fpj"]

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Jacking Stress fpj",  f"{_fpj:.1f} MPa")
        col_b.metric("Aps (1m strip)",       f"{_L['Aps']*1e6:.2f} mm²")
        col_c.metric("Pj (per 1m strip)",    f"{_L['Pj']:.2f} kN/m")

        st.markdown("---")
        st.markdown("#### Immediate Losses")
        _d = {
            "Loss Component": [
                "1. Friction  ΔfpF  (at midspan)",
                "2. Anchorage Set  ΔfpA  (at jacking end)",
                "3. Elastic Shortening  ΔfpES",
                "Total Immediate  Δfi",
            ],
            "Formula  [AASHTO Ref.]": [
                "fpj(1−e^(−μα−Kx))  [5.9.3.2.1]",
                "Δ·Ep/Lpa  [5.9.3.2.2]",
                "(Ep/Eci)·fcgp  [5.9.3.2.3]",
                "ΔfpF + ΔfpA + ΔfpES",
            ],
            "Key Params": [
                f"μ={0.20}, K={0.0066}, α={_L['alpha']:.4f}rad",
                f"Δ={st.session_state.get('anch_slip_mm',6):.0f}mm, Lpa={_L['Lpa']:.2f}m (anchor influence length)",
                f"fcgp={_L['fcgp']:.3f}MPa (concrete stress at tendon CG at transfer), Eci={_L['Eci']:.0f}MPa",
                "",
            ],
            "Loss (MPa)": [
                f"{_L['delta_fpF']:.2f}",
                f"{_L['delta_fpA']:.2f}",
                f"{_L['delta_fpES']:.2f}",
                f"{_L['delta_imm']:.2f}",
            ],
            "% of fpj": [
                f"{_L['delta_fpF']/_fpj*100:.2f}",
                f"{_L['delta_fpA']/_fpj*100:.2f}",
                f"{_L['delta_fpES']/_fpj*100:.2f}",
                f"{_L['imm_loss_pct']:.2f}",
            ],
        }
        st.dataframe(pd.DataFrame(_d), use_container_width=True)

        col_x, col_y = st.columns(2)
        col_x.metric("fpi (after imm. losses)", f"{_L['fpi_eff']:.1f} MPa")
        col_y.metric("Pi (per 1m strip)",        f"{_L['Pi']:.2f} kN/m")

        st.markdown("---")
        st.markdown("#### Long-Term Losses  (Approximate Method)")
        _d2 = {
            "Loss Component": [
                "4. Shrinkage  ΔfpSH",
                "5. Creep  ΔfpCR",
                "6. Relaxation  ΔfpR2",
                "Total Long-term  ΔfLT",
                "TOTAL LOSS  Δftotal",
            ],
            "Formula  [AASHTO Ref.]": [
                "εbdf × Ep  [5.9.3.4.2a]",
                "(Ep/Ec) × fcgp × ψb  [5.9.3.4.2b]",
                "(fpt/KL)(fpt/fpy − 0.55)  [5.9.3.4.3c]",
                "ΔfpSH + ΔfpCR + ΔfpR",
                "Δfi + ΔfLT",
            ],
            "Key Params": [
                f"εbdf={_L['eps_bdf']:.5f} (shrinkage strain), kvs={_L['kvs']:.3f} (V/S factor), khs={_L['khs']:.3f} (humidity factor for shrinkage), kf={_L['kf']:.3f} (strength factor)",
                f"ψb={_L['psi_b']:.3f} (creep coefficient), fcgp={_L['fcgp_lt']:.3f}MPa (concrete stress at tendon CG), khc={_L['khc']:.3f} (humidity factor for creep)",
                f"KL={45} (relaxation factor low-relax), fpt/fpy={_L['fpi_eff']/(_fpj*0.9):.3f}",
                "", "",
            ],
            "Loss (MPa)": [
                f"{_L['delta_fpSH']:.2f}",
                f"{_L['delta_fpCR']:.2f}",
                f"{_L['delta_fpR']:.2f}",
                f"{_L['delta_lt']:.2f}",
                f"{_L['delta_imm']+_L['delta_lt']:.2f}",
            ],
            "% of fpj": [
                f"{_L['delta_fpSH']/_fpj*100:.2f}",
                f"{_L['delta_fpCR']/_fpj*100:.2f}",
                f"{_L['delta_fpR']/_fpj*100:.2f}",
                f"{_L['lt_loss_pct']:.2f}",
                f"{_L['total_loss_pct']:.2f}",
            ],
        }
        st.dataframe(pd.DataFrame(_d2), use_container_width=True)

        col_p, col_q, col_r = st.columns(3)
        col_p.metric("fpe (effective)", f"{_L['fpe']:.1f} MPa",
                     delta=f"{_L['fpe']/_fpj*100:.1f}% of fpj")
        col_q.metric("Pe (per 1m strip)", f"{_L['Pe']:.2f} kN/m")
        col_r.metric("Total Loss", f"{_L['total_loss_pct']:.2f}%",
                     delta=f"{_L['fpe']:.0f} MPa remaining")

        st.markdown("---")
        st.markdown("#### Key Factors Used")
        _factors = {
            "Parameter (description)": [
                "Ec  (modulus of elasticity of concrete at service)",
                "Eci  (modulus of elasticity of concrete at transfer)",
                "Ep  (modulus of elasticity of prestress steel)",
                "μ  (friction coefficient, grouted duct)",
                "K  (wobble coefficient, grouted duct)",
                "α  (total angular change of tendon)",
                "L  (tendon length along profile)",
                "friction slope  (rate of friction loss per unit length)",
                "Lpa  (anchor set influence length)",
                "Δ  (anchorage slip)",
                "V/S  (volume-to-surface ratio)",
                "kvs  (V/S size factor for shrinkage/creep)",
                "khs  (humidity factor for shrinkage)",
                "khc  (humidity factor for creep)",
                "kf  (concrete strength factor, uses f'ci in ksi)",
                "ψb  (creep coefficient)",
                "εbdf  (shrinkage strain)",
            ],
            "Value  [Unit]": [
                f"{_L['Ec']:.0f} MPa",
                f"{_L['Eci']:.0f} MPa",
                "197,000 MPa",
                "0.20  [-]",
                "0.0066 rad/m",
                f"{_L['alpha']:.4f} rad",
                f"{_L['L_ten']:.3f} m",
                f"{_L['friction_slope']:.4f} MPa/m",
                f"{_L['Lpa']:.3f} m",
                f"{st.session_state.get('anch_slip_mm', 6.0):.1f} mm",
                f"{_L['VS_mm']:.1f} mm",
                f"{_L['kvs']:.4f}",
                f"{_L['khs']:.4f}",
                f"{_L['khc']:.4f}",
                f"{_L['kf']:.4f}  (f'ci_ksi = {_L['fci_ksi']:.3f} ksi)",
                f"{_L['psi_b']:.4f}",
                f"{_L['eps_bdf']:.6f}",
            ],
        }
        st.dataframe(pd.DataFrame(_factors), use_container_width=True)

    with tabs[2]:
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

    with tabs[3]:
        st.subheader("Stress Check — Service I  (Pe + Ms1  |  Gross section)")
        fig3 = go.Figure([
            go.Scatter(x=R["x"], y=R["sv1_top"], name="Top",    line_color="red"),
            go.Scatter(x=R["x"], y=R["sv1_bot"], name="Bottom", line_color="blue"),
        ])
        fig3.add_hline(y=R["lim_sv_ct"], line_dash="dash", line_color="orange",
                       annotation_text=f"−0.60f'c = {R['lim_sv_ct']:.2f} MPa")
        fig3.add_hline(y=R["lim_sv_cp"], line_dash="dot", line_color="goldenrod",
                       annotation_text=f"−0.45f'c = {R['lim_sv_cp']:.2f} MPa")
        fig3.add_hline(y=R["lim_sv_t"],  line_dash="dash", line_color="green",
                       annotation_text=f"+0.50√f'c = +{R['lim_sv_t']:.3f} MPa")
        fig3.update_layout(height=380, xaxis_title="x (m)", yaxis_title="Stress (MPa)")
        st.plotly_chart(fig3, use_container_width=True)
        rows_sv = [{"x (m)":       f"{R['x'][i]:.2f}",
                    "σ_top (MPa)": f"{R['sv1_top'][i]:.4f}",
                    "σ_bot (MPa)": f"{R['sv1_bot'][i]:.4f}",
                    "Comp. Limit": f"{R['lim_sv_ct']:.2f}",
                    "Tens. Limit": f"+{R['lim_sv_t']:.3f}",
                    "Status": "✅" if (R["sv1_top"][i] >= R["lim_sv_ct"] and
                                       R["sv1_bot"][i] >= R["lim_sv_ct"] and
                                       R["sv1_top"][i] <= R["lim_sv_t"]  and
                                       R["sv1_bot"][i] <= R["lim_sv_t"]) else "❌"}
                   for i in sta_idx]
        st.dataframe(pd.DataFrame(rows_sv), use_container_width=True)

    with tabs[4]:
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

    with tabs[5]:
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

    with tabs[6]:
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
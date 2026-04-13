"""
PSC Box Girder — Top Flange Transverse Design (v4 with Word Images)
AASHTO LRFD Bridge Design Specifications | 1.0 m transverse strip

v4: เพิ่ม fig_to_png + รูป Section/Transfer/Service ใน make_report()
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
# 1. CONFIG & SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="PSC Box Girder — Top Flange Design")

DEFAULT_SCALARS = dict(
    width=12.0, cl_lweb=2.0, cl_rweb=10.0,
    fc=45.0, fci=36.0, fpu=1860.0, fpy_ratio=0.90,
    aps_strand=140.0, duct_dia_mm=70.0,
    num_tendon=1, n_strands=5,
    fpi_ratio=0.75,
    t0=3, RH=75,
    anch_slip_mm=6.0,
    phi_flex=1.00, phi_shear=0.90,
    proj_name="Box Girder Design", doc_no="CALC-STR-001",
    eng_name="Engineer Name", chk_name="Checker Name",
)
DEFAULT_TABLES = dict(
    df_thickness={"x (m)": [0.00, 1.00, 2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00, 9.00, 10.00, 11.00, 12.00], "t (m)": [0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250, 0.250]},
    df_tendon={"x (m)": [0.00, 1.00, 2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00, 9.00, 10.00, 11.00, 12.00], "z_top (m)": [0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100]},
    df_load={
        "x (m)": [ 0.00, 1.00, 2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00, 9.00, 10.00, 11.00, 12.00],
        "M_DL (kNm/m)": [ 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        "V_DL (kN/m)": [ 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        "M_SDL (kNm/m)": [ 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        "V_SDL (kN/m)": [ 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        "M_LL (kNm/m)": [ 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        "V_LL (kN/m)": [ 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    },
)

for k, v in DEFAULT_SCALARS.items():
    if k not in st.session_state:
        st.session_state[k] = v

_TABLE_SRC = {"thk_src": "df_thickness", "tdn_src": "df_tendon", "ld_src": "df_load"}
for src_key, tbl_key in _TABLE_SRC.items():
    if src_key not in st.session_state:
        st.session_state[src_key] = pd.DataFrame(DEFAULT_TABLES[tbl_key])

if "_tbl_ver" not in st.session_state:
    st.session_state["_tbl_ver"] = 0

if "_loaded_hash" not in st.session_state:
    st.session_state["_loaded_hash"] = None

# ─────────────────────────────────────────────────────────────────────────────
# 2. SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    with st.expander("💾 Save / 📂 Open Project", expanded=True):
        def _tbl_to_dict(cur_key, src_key):
            df = st.session_state.get(cur_key, st.session_state.get(src_key, pd.DataFrame()))
            if not isinstance(df, pd.DataFrame):
                try: df = pd.DataFrame(df)
                except: return {}
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.dropna(how="all")
            return df.to_dict(orient="list") if not df.empty else {}

        _save_data = {
            "scalars": {k: st.session_state[k] for k in DEFAULT_SCALARS},
            "tables": {
                "df_thickness": _tbl_to_dict("_cur_thk", "thk_src"),
                "df_tendon": _tbl_to_dict("_cur_tdn", "tdn_src"),
                "df_load": _tbl_to_dict("_cur_ld", "ld_src"),
            },
        }
        _json_bytes = json.dumps(_save_data, indent=2, ensure_ascii=False).encode("utf-8")
        _fname = f"{st.session_state.proj_name.replace(' ','_')}_{st.session_state.doc_no}.json"
        st.download_button(
            label="💾 Save Project (.json)",
            data=_json_bytes, file_name=_fname,
            mime="application/json", use_container_width=True,
        )
        st.caption("ตั้ง Chrome: Settings → Downloads → 'Ask where to save'")
        st.markdown("---")

        uploaded_file = st.file_uploader(
            "📂 Open Project (.json)", type="json",
            key="proj_uploader",
            help="เลือกไฟล์.json ที่เคย Save ไว้",
        )
        if uploaded_file is not None:
            _raw = uploaded_file.getvalue()
            _fhash = hash(_raw)
            if st.session_state["_loaded_hash"]!= _fhash:
                try:
                    loaded = json.loads(_raw.decode("utf-8"))
                    for k, v in loaded.get("scalars", {}).items():
                        if k in DEFAULT_SCALARS:
                            dv = DEFAULT_SCALARS[k]
                            st.session_state[k] = (
                                int(v) if isinstance(dv, int) else
                                float(v) if isinstance(dv, float) else str(v)
                            )
                    _lmap = {"df_thickness":"thk_src","df_tendon":"tdn_src","df_load":"ld_src"}
                    for tbl_key, src_key in _lmap.items():
                        raw_tbl = loaded.get("tables", {}).get(tbl_key)
                        if raw_tbl:
                            ndf = pd.DataFrame(raw_tbl)
                            for col in ndf.columns:
                                ndf[col] = pd.to_numeric(ndf[col], errors="coerce")
                            st.session_state[src_key] = ndf.dropna(how="all")
                    st.session_state["_tbl_ver"] += 1
                    for k in ["_cur_thk", "_cur_tdn", "_cur_ld"]:
                        st.session_state.pop(k, None)
                    st.session_state["_loaded_hash"] = _fhash
                    st.success("✅ Project loaded successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Load error: {e}")

    with st.expander("📐 Materials & Section", expanded=True):
        width = st.number_input("Total Flange Width (m)", min_value=1.0, key="width")
        fc = st.number_input("f'c Service (MPa)", min_value=20.0, key="fc")
        fci = st.number_input("f'ci Transfer (MPa)", min_value=15.0, key="fci")
        fpu = st.number_input("fpu (MPa)", key="fpu")
        fpy_opts = [0.90, 0.85]
        if st.session_state.fpy_ratio not in fpy_opts:
            st.session_state.fpy_ratio = 0.90
        fpy_ratio = st.selectbox("fpy/fpu", fpy_opts, key="fpy_ratio", help="Low-relaxation=0.90 | Stress-relieved=0.85")
        aps_strand = st.number_input("Aps per strand (mm²)", key="aps_strand")
        duct_dia_mm = st.number_input("Duct diameter (mm)", min_value=20.0, key="duct_dia_mm")

    with st.expander("🌐 Web Geometry", expanded=True):
        st.caption("ระบุตำแหน่ง Centerline ของ Web ซ้าย-ขวา จากขอบซ้ายของ Flange")
        col_wl, col_wr = st.columns(2)
        cl_lweb = col_wl.number_input("CL. L.Web (m)", min_value=0.0, step=0.05, key="cl_lweb")
        cl_rweb = col_wr.number_input("CL. R.Web (m)", min_value=0.0, step=0.05, key="cl_rweb")
        st.info(f"CL.L.Web = **{cl_lweb*1000:.0f} mm** | "
                f"CL.R.Web = **{cl_rweb*1000:.0f} mm** | "
                f"Span = **{(cl_rweb-cl_lweb)*1000:.0f} mm**")

    with st.expander("🔩 Prestressing Force", expanded=True):
        num_tendon = st.number_input("Tendons per 1 m strip", min_value=1, key="num_tendon")
        n_strands = st.number_input("Strands per tendon", min_value=1, key="n_strands")
        fpi_ratio = st.slider("Jacking stress fpi/fpu", 0.70, 0.80, key="fpi_ratio",
                               help="Standard = 0.75 fpu (AASHTO 5.9.2.2)")

    with st.expander("📉 Prestress Loss Parameters", expanded=True):
        st.caption("แอปคำนวณ Loss ตาม AASHTO LRFD 5.9.3 อัตโนมัติ")
        t0_val = st.number_input("Age at Transfer t₀ (days)", min_value=1, key="t0",
                                       help="อายุคอนกรีตขณะ Transfer (ปกติ 3–7 วัน)")
        rh_val = st.number_input("Relative Humidity RH (%)", min_value=30,
                                       max_value=100, key="RH",
                                       help="ค่าความชื้นสัมพัทธ์เฉลี่ยของสภาพแวดล้อม")
        anch_val = st.number_input("Anchorage Slip Δ (mm)", value=6.0, min_value=0.0,
                                       key="anch_slip_mm", help="ค่ามาตรฐาน = 6 mm")
        st.caption("ค่าคงที่มาตรฐาน (7-wire low-relax, internal grouted PT):")
        st.markdown("- μ = 0.20, K = 0.0066 rad/m *(AASHTO Table 5.9.3.2.1b-1)*")
        st.markdown("- Ep = 197,000 MPa *(AASHTO 5.4.4.2)*")
        st.markdown("- Jacking: 0.75fpu, One-end")

    with st.expander("⚖️ Resistance Factors φ"):
        phi_flex = st.number_input("φ Flexure", min_value=0.75, max_value=1.00, key="phi_flex")
        phi_shear = st.number_input("φ Shear", min_value=0.70, max_value=1.00, key="phi_shear")

    st.markdown("---")
    st.subheader("📄 Report Information")
    proj_name = st.text_input("Project Name", key="proj_name")
    doc_no = st.text_input("Document No.", key="doc_no")
    eng_name = st.text_input("Prepared by", key="eng_name")
    chk_name = st.text_input("Checked by", key="chk_name")

# ─────────────────────────────────────────────────────────────────────────────
# 3. DATA EDITORS
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏗️ PSC Box Girder — Top Flange Transverse Design")
st.caption("AASHTO LRFD | 1.0 m transverse strip | "
           "Compression (−) Tension (+) | +M = sagging")

_v = st.session_state["_tbl_ver"]

c1, c2 = st.columns(2)
with c1:
    st.subheader("📏 Flange Thickness t(x)")
    df_thk = st.data_editor(
        st.session_state["thk_src"], num_rows="dynamic", key=f"ed_thk_{_v}")
    st.session_state["_cur_thk"] = df_thk

    st.subheader("🔩 Tendon Profile z(x) [from top face]")
    df_tdn = st.data_editor(
        st.session_state["tdn_src"], num_rows="dynamic", key=f"ed_tdn_{_v}")
    st.session_state["_cur_tdn"] = df_tdn
with c2:
    st.subheader("📦 Loads per 1 m strip")
    df_ld = st.data_editor(
        st.session_state["ld_src"], num_rows="dynamic", key=f"ed_ld_{_v}")
    st.session_state["_cur_ld"] = df_ld

# ─────────────────────────────────────────────────────────────────────────────
# PRESTRESS LOSS ENGINE (AASHTO LRFD 5.9.3)
# ─────────────────────────────────────────────────────────────────────────────
def calc_losses(dft, dfp, fc, fci, fpu, fpi_ratio, aps_strand,
                num_tendon, n_strands, duct_dia_mm,
                t0, RH, anch_slip_mm, width):
    Ep = 197_000.0
    mu = 0.20
    K_wob = 0.0066
    KL = 45.0
    b = 1.0
    wc = 2400.0
    x_mid = width / 2.0
    t_mid = float(np.interp(x_mid, dft["x (m)"], dft["t (m)"]))
    z_mid = float(np.interp(x_mid, dfp["x (m)"], dfp["z_top (m)"]))
    yc_mid = t_mid / 2.0
    e_mid = yc_mid - z_mid
    Ag_mid = b * t_mid
    Ig_mid = b * t_mid**3 / 12.0
    A_duct = math.pi / 4.0 * (duct_dia_mm / 1000.0)**2
    n_duct = int(num_tendon)
    y_duct = z_mid - yc_mid
    An_mid = Ag_mid - n_duct * A_duct
    In_mid = Ig_mid - n_duct * A_duct * y_duct**2
    VS = (b * t_mid) / (2.0 * (b + t_mid))
    VS_mm = VS * 1000.0
    aps_m2 = aps_strand * 1e-6
    n_total = int(num_tendon * n_strands)
    Aps = n_total * aps_m2
    Ec = 0.043 * (wc**1.5) * math.sqrt(fc)
    Eci = 0.043 * (wc**1.5) * math.sqrt(fci)
    xs = dft["x (m)"].values.astype(float)
    zs = np.interp(xs, dfp["x (m)"].values, dfp["z_top (m)"].values)
    dz = np.diff(zs); dx = np.diff(xs)
    dx_s = np.where(np.abs(dx) < 1e-9, 1e-9, dx)
    alpha = float(np.sum(np.abs(np.diff(np.append([0], np.arctan(dz / dx_s))))))
    alpha = max(alpha, 0.001)
    L_ten = float(np.sum(np.sqrt(dx**2 + dz**2)))
    if L_ten < 0.5: L_ten = float(xs[-1] - xs[0])
    fpj = fpu * fpi_ratio
    Pj = Aps * fpj * 1e3
    exp_full = mu * alpha + K_wob * L_ten
    delta_fpF_full = fpj * (1.0 - math.exp(-exp_full))
    exp_mid = mu * (alpha / 2.0) + K_wob * (L_ten / 2.0)
    delta_fpF = fpj * (1.0 - math.exp(-exp_mid))
    friction_slope = fpj * (mu * alpha / L_ten + K_wob)
    Lpa = math.sqrt((anch_slip_mm / 1000.0) * Ep / friction_slope)
    Lpa = min(Lpa, L_ten)
    delta_fpA = (anch_slip_mm / 1000.0) * Ep / Lpa
    delta_fpA = min(delta_fpA, 0.20 * fpj)
    fpt_mid = fpj - delta_fpF - (delta_fpA if Lpa > L_ten / 2.0 else 0.0)
    fpt_mid = max(fpt_mid, 0.5 * fpj)
    Pi_est = Aps * fpt_mid * 1e3
    fcgp = (Pi_est/An_mid + Pi_est*e_mid**2/In_mid) / 1000.0
    delta_fpES = (Ep / Eci) * fcgp
    delta_fpES = max(0.0, delta_fpES)
    delta_imm = delta_fpF + delta_fpA + delta_fpES
    imm_loss_pct = delta_imm / fpj * 100.0
    fpi_eff = max(fpj - delta_imm, 0.5 * fpj)
    Pi_final = Aps * fpi_eff * 1e3
    fci_ksi = fci / 6.895
    kvs = max(1.45 - 0.0052 * VS_mm, 1.0)
    khs = max(2.00 - 0.014 * RH, 0.0)
    khc = max(1.56 - 0.008 * RH, 0.0)
    kf = 5.0 / (1.0 + fci_ksi)
    ktd = 1.0
    eps_bdf = kvs * khs * kf * ktd * 0.48e-3
    delta_fpSH = eps_bdf * Ep
    ti_safe = max(float(t0), 1.0)
    psi_b = 1.9 * kvs * khc * kf * ktd * (ti_safe ** -0.118)
    fcgp_lt = (Pi_final/An_mid + Pi_final*e_mid**2/In_mid) / 1000.0
    delta_fpCR = max((Ep / Ec) * fcgp_lt * psi_b, 0.0)
    fpy = fpu * 0.9
    fpt_r = fpi_eff - 0.3 * (delta_fpSH + delta_fpCR)
    fpt_r = max(fpt_r, 0.5 * fpu)
    delta_fpR = max((fpt_r / KL) * (fpt_r / fpy - 0.55), 0.0)
    delta_lt = delta_fpSH + delta_fpCR + delta_fpR
    lt_loss_pct = delta_lt / fpj * 100.0
    fpe_val = max(fpi_eff - delta_lt, 0.45 * fpj)
    Pe_final = Aps * fpe_val * 1e3
    return dict(
        Ec=Ec, Eci=Eci, Ep=Ep,
        t_mid=t_mid, z_mid=z_mid, e_mid=e_mid,
        Ag_mid=Ag_mid, Ig_mid=Ig_mid, An_mid=An_mid, In_mid=In_mid,
        VS=VS, VS_mm=VS_mm,
        Aps=Aps, n_total=n_total,
        alpha=alpha, L_ten=L_ten, Lpa=Lpa, friction_slope=friction_slope,
        fpj=fpj, Pj=Pj,
        delta_fpF=delta_fpF, delta_fpF_full=delta_fpF_full,
        delta_fpA=delta_fpA, delta_fpES=delta_fpES,
        delta_imm=delta_imm, imm_loss_pct=imm_loss_pct,
        fcgp=fcgp, fpt_mid=fpt_mid, Pi=Pi_final,
        fci_ksi=fci_ksi, kvs=kvs, khs=khs, khc=khc, kf=kf, ktd=ktd,
        psi_b=psi_b, eps_bdf=eps_bdf,
        fcgp_lt=fcgp_lt, delta_fpSH=delta_fpSH,
        delta_fpCR=delta_fpCR, delta_fpR=delta_fpR,
        delta_lt=delta_lt, lt_loss_pct=lt_loss_pct,
        fpi_eff=fpi_eff, fpe=fpe_val, Pe=Pe_final,
        eff_ratio=Pe_final / Pj if Pj > 0 else 0.75,
        total_loss_pct=(delta_imm + delta_lt) / fpj * 100.0,
    )

# ─────────────────────────────────────────────────────────────────────────────
# 4. CALCULATION ENGINE
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
    N = 500; b = 1.0
    x = np.linspace(0, width, N)
    t = np.interp(x, dft["x (m)"], dft["t (m)"])
    z = np.interp(x, dfp["x (m)"], dfp["z_top (m)"])
    yc = t / 2.0
    def ip(col): return np.interp(x, dfl["x (m)"], dfl[col])
    m_dl=ip("M_DL (kNm/m)"); v_dl=ip("V_DL (kN/m)")
    m_sdl=ip("M_SDL (kNm/m)"); v_sdl=ip("V_SDL (kN/m)")
    m_ll=ip("M_LL (kNm/m)"); v_ll=ip("V_LL (kN/m)")
    ms1 = m_dl + m_sdl + m_ll
    ms3 = m_dl + m_sdl + 0.8*m_ll
    mu = 1.25*m_dl + 1.50*m_sdl + 1.75*m_ll
    vu = 1.25*np.abs(v_dl) + 1.50*np.abs(v_sdl) + 1.75*np.abs(v_ll)
    Ag = b * t
    Ig = b * t**3 / 12.0
    A_duct = math.pi / 4.0 * (duct_dia_mm / 1000.0)**2
    n_ducts = int(num_tendon)
    y_duct = z - yc
    An = Ag - n_ducts * A_duct
    In = Ig - n_ducts * A_duct * y_duct**2
    e = yc - z
    n_total = L["n_total"]
    Aps = L["Aps"]
    fpi_val = L["fpi_eff"]
    Pi = L["Pi"]
    Pe = L["Pe"]
    def stress(P, M, ev, tv, Av, Iv):
        ht = tv / 2.0
        top = (-P/Av + P*ev*ht/Iv - M*ht/Iv) / 1000.0
        bot = (-P/Av - P*ev*ht/Iv + M*ht/Iv) / 1000.0
        return top, bot
    tr_top, tr_bot = stress(Pi, m_dl, e, t, An, In)
    sv1_top, sv1_bot = stress(Pe, ms1, e, t, Ag, Ig)
    sv3_top, sv3_bot = stress(Pe, ms3, e, t, Ag, Ig)
    beta1 = float(np.clip(0.85 - 0.05*(fc-28.0)/7.0, 0.65, 0.85))
    k_fac = 2.0 * (1.04 - fpy_ratio)
    def flexure(dp_arr):
        dp_s = np.maximum(dp_arr, 1e-4)
        c_ = Aps*fpu / (0.85*fc*beta1*b*1000.0 + k_fac*Aps*fpu/dp_s)
        fps_ = np.clip(fpu*(1.0 - k_fac*c_/dp_s), 0.0, fpu)
        a_ = beta1 * c_
        Mn_ = Aps * fps_ * (dp_s - a_/2.0) * 1000.0
        return c_, a_, fps_, Mn_
    dp_pos = z; dp_neg = t - z
    c_pos, a_pos, fps_pos, Mn_pos = flexure(dp_pos)
    c_neg, a_neg, fps_neg, Mn_neg = flexure(dp_neg)
    phi_Mn_pos = phi_flex * Mn_pos
    phi_Mn_neg = -phi_flex * Mn_neg
    cdp_pos = np.where(dp_pos > 0, c_pos/dp_pos, np.inf)
    cdp_neg = np.where(dp_neg > 0, c_neg/dp_neg, np.inf)
    fr = 0.63 * math.sqrt(fc)
    fpe = Pe / Ag / 1000.0
    Sb = Ig / yc
    Mcr = (fr + fpe) * Sb / 1000.0
    dp_use = np.maximum(dp_pos, dp_neg)
    dv = np.maximum(0.9*dp_use, 0.72*t)
    Vc = 0.083*2.0*1.0*math.sqrt(fc)*b*dv*1000.0
    Vn_lim = 0.25*fc*b*dv*1000.0
    phi_Vn = phi_shear * np.minimum(Vc, Vn_lim)
    lim_tr_c = -0.60*fci; lim_tr_t = 0.25*math.sqrt(fci)
    lim_sv_cp = -0.45*fc; lim_sv_ct = -0.60*fc
    lim_sv_t = 0.50*math.sqrt(fc)
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

    t0_v = int(st.session_state.get("t0", 3))
    rh_v = int(st.session_state.get("RH", 75))
    anch_v = float(st.session_state.get("anch_slip_mm", 6.0))
    L = calc_losses(dft, dfp,
                    fc, fci, fpu, fpi_ratio, aps_strand,
                    num_tendon, n_strands, duct_dia_mm,
                    t0_v, rh_v, anch_v, width)
    R = run_calc(dft, dfp, dfl, L)

    sta_x = dfl["x (m)"].values
    sta_idx = [int(np.abs(R["x"] - v).argmin()) for v in sta_x]
    N = len(R["x"])

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

        # COVER
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

        # SEC 1 — DESIGN BASIS
        h1("1. Design Basis")
        for it in [
            "Code: AASHTO LRFD Bridge Design Specifications",
            "Analysis basis: 1.0 m transverse strip across top flange",
            "Load combinations (AASHTO Table 3.4.1-1):",
            " Strength I : 1.25
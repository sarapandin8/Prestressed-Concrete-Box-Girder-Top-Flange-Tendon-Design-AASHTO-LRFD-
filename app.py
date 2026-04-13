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
        "x (m)": [0.00, 1.00, 2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00, 9.00, 10.00, 11.00, 12.00],
        "M_DL (kNm/m)": [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        "V_DL (kN/m)": [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        "M_SDL (kNm/m)": [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        "V_SDL (kN/m)": [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        "M_LL (kNm/m)": [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        "V_LL (kN/m)": [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
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
    # ─────────────────────────────────
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
            " Strength I : 1.25·DC + 1.50·DW + 1.75·LL",
            " Service I : 1.00·DC + 1.00·DW + 1.00·LL (compression & tension check)",
            " Transfer : Pi (after immediate losses) + M_DC",
            "Strand: Post-tensioned, bonded (fully grouted), low-relaxation",
            "Sign convention: Compression (−) | Tension (+)",
            "Positive moment = sagging (compression at TOP fibre)",
        ]: para(it, indent=0.3)
        blank()

        # SEC 2 — INPUT SUMMARY + รูปที่ 1: SECTION
        h1("2. Design Input Summary")

        h2("2.1 Material Properties")
        tbl(["Parameter","

        h2("2.1 Material Properties")
        tbl(["Parameter","Symbol","Value","Unit","Reference"],[
            ["Concrete — service", "f'c", f"{fc:.1f}", "MPa","AASHTO 5.4.2"],
            ["Concrete — transfer", "f'ci", f"{fci:.1f}", "MPa","AASHTO 5.9.2"],
            ["Strand tensile strength", "fpu", f"{fpu:.0f}", "MPa","AASHTO 5.4.4"],
            ["Strand yield ratio", "fpy/fpu", f"{fpy_ratio:.2f}", "—", "Low-relax"],
            ["Area per strand", "asp", f"{aps_strand:.1f}", "mm²","Product data"],
            ["PT duct outer diameter", "d_duct", f"{duct_dia_mm:.0f}","mm", "Supplier"],
        ], cw=[4.5,2.0,1.5,4.5])
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
        blank()

        h2("3.2 Section Properties at Mid-span")
        tbl(["Parameter","Symbol","Value","Unit"],[
            ["Thickness","t", f"{_L['t_mid']*1000:.1f}", "mm"],
            ["Tendon depth from top","z", f"{_L['z_mid']*1000:.1f}","mm"],
            ["Eccentricity","e", f"{_L['e_mid']*1000:.1f}","mm"],
            ["Gross Area (1m)","Ag", f"{_L['Ag_mid']*1e6:.0f}","mm²"],
            ["Net Area (1m)","An", f"{_L['An_mid']*1e6:.0f}","mm²"],
            ["Gross Inertia","Ig", f"{_L['Ig_mid']*1e12:.2e}","mm⁴"],
            ["Net Inertia","In", f"{_L['In_mid']*1e12:.2e}","mm⁴"],
            ["V/S ratio","V/S", f"{_L['VS']*1000:.1f}","mm"],
        ], cw=[5,2,2.5])
        blank()

        h2("3.3 Immediate Loss Components")
        h3("3.3.1 Friction Loss — Δf_f (AASHTO 5.9.3.2.2)")
        formula("Δf_f = f_pj · (1 − e^(−(μ·α + K·L)))")
        subst(f"f_pj = f_pu × f_pi/f_pu = {fpu:.0f} × {fpi_ratio:.3f} = {_fpj:.2f} MPa")
        subst(f"μ = 0.20, K = 0.0066 rad/m, α = {_L['alpha']:.4f} rad")
        subst(f"L_tendon = {_L['L_ten']:.3f} m")
        subst(f"Exponent = μ·α + K·L = 0.20×{_L['alpha']:.4f} + 0.0066×{_L['L_ten']:.3f} = {_L['alpha']*0.20 + 0.0066*_L['L_ten']:.4f}")
        result(f"Δf_f (full) = {_fpj:.2f} × (1 − e^−{_L['alpha']*0.20 + 0.0066*_L['L_ten']:.4f}) = {_L['delta_fpF_full']:.2f} MPa")
        result(f"Δf_f (mid) = {_L['delta_fpF']:.2f} MPa")
        blank()

        h3("3.3.2 Anchorage Seating — Δf_a (AASHTO 5.9.3.2.1)")
        formula("Δf_a = (Δ_anch × E_p) / L_pa")
        subst(f"Δ_anch = {anch_slip_mm:.1f} mm = {anch_slip_mm/1000:.5f} m")
        subst(f"E_p = {_L['Ep']:.0f} MPa")
        subst(f"L_pa = {_L['Lpa']:.3f} m")
        result(f"Δf_a = {_L['delta_fpA']:.2f} MPa")
        para(f"Note: L_pa < L/2, so Δf_a affects only anchorage region", italic=True, color=C_GRAY, indent=0.5)
        blank()

        h3("3.3.3 Elastic Shortening — Δf_ES (AASHTO 5.9.3.2.3)")
        formula("Δf_ES = (E_p / E_ci) × f_cgp")
        subst(f"E_p = {_L['Ep']:.0f} MPa, E_ci = {_L['Eci']:.0f} MPa")
        subst(f"f_cgp = (P_i/A_n + P_i·e²/I_n) = {_L['fcgp']:.3f} MPa")
        result(f"Δf_ES = {_L['delta_fpES']:.2f} MPa")
        blank()

        h3("3.3.4 Total Immediate Loss")
        formula("Δf_i = Δf_f + Δf_a + Δf_ES")
        result(f"Δf_i = {_L['delta_fpF']:.2f} + {_L['delta_fpA']:.2f} + {_L['delta_fpES']:.2f} = {_L['delta_imm']:.2f} MPa")
        result(f"%Loss = {_L['imm_loss_pct']:.2f} % of f_pj")
        result(f"f_pi (after immediate) = {_fpj:.2f} − {_L['delta_imm']:.2f} = {_L['fpi_eff']:.2f} MPa")
        result(f"P_i = A_ps × f_pi = {R['Aps']*1e6:.1f} × {_L['fpi_eff']:.2f} / 1000 = {_L['Pi']:.2f} kN/m")
        blank()

        h2("3.4 Long-Term Loss Components")
        h3("3.4.1 Shrinkage — Δf_SH (AASHTO 5.9.3.3)")
        formula("Δf_SH = ε_bd × E_p")
        subst(f"k_vs = max(1.45 − 0.0052·V/S, 1.0) = {_L['kvs']:.3f}")
        subst(f"k_hs = max(2.00 − 0.014·RH, 0.0) = {_L['khs']:.3f}")
        subst(f"k_f = 5 / (1 + f'_ci) = {_L['kf']:.3f}")
        subst(f"ε_bd = k_vs × k_hs × k_f × k_td × 0.48×10⁻³ = {_L['eps_bdf']*1e3:.3f} ×10⁻³")
        result(f"Δf_SH = {_L['eps_bdf']*1e6:.1f} × 10⁻⁶ × {_L['Ep']:.0f} = {_L['delta_fpSH']:.2f} MPa")
        blank()

        h3("3.4.2 Creep — Δf_CR (AASHTO 5.9.3.4)")
        formula("Δf_CR = (E_p / E_c) × f_cgp × ψ_b")
        subst(f"E_c = {_L['Ec']:.0f} MPa")
        subst(f"ψ_b = 1.9 × k_vs × k_hc × k_f × k_td × t_i⁻⁰·¹¹⁸ = {_L['psi_b']:.3f}")
        subst(f"f_cgp (long-term) = {_L['fcgp_lt']:.3f} MPa")
        result(f"Δf_CR = {_L['delta_fpCR']:.2f} MPa")
        blank()

        h3("3.4.3 Relaxation — Δf_R (AASHTO 5.9.3.5)")
        formula("Δf_R = (f_pt / K_L) × (f_pt / f_py − 0.55)")
        subst(f"f_pt = f_pi − 0.3×(Δf_SH + Δf_CR) = {_L['fpi_eff'] - 0.3*(_L['delta_fpSH']+_L['delta_fpCR']):.2f} MPa")
        subst(f"K_L = 45, f_py = 0.9×f_pu = {fpu*0.9:.0f} MPa")
        result(f"Δf_R = {_L['delta_fpR']:.2f} MPa")
        blank()

        h3("3.4.4 Total Long-Term Loss")
        formula("Δf_LT = Δf_SH + Δf_CR + Δf_R")
        result(f"Δf_LT = {_L['delta_fpSH']:.2f} + {_L['delta_fpCR']:.2f} + {_L['delta_fpR']:.2f} = {_L['delta_lt']:.2f} MPa")
        result(f"%Loss = {_L['lt_loss_pct']:.2f} % of f_pj")
        blank()

        h2("3.5 Effective Prestress Force")
        formula("f_pe = f_pj − Δf_i − Δf_LT")
        result(f"f_pe = {_fpj:.2f} − {_L['delta_imm']:.2f} − {_L['delta_lt']:.2f} = {_L['fpe']:.2f} MPa")
        result(f"P_e = A_ps × f_pe = {R['Aps']*1e6:.1f} × {_L['fpe']:.2f} / 1000 = {_L['Pe']:.2f} kN/m")
        result(f"Total Loss = {_L['total_loss_pct']:.2f} % | Efficiency = {_L['eff_ratio']*100:.1f} %")
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
        # SEC 5 — STATION-BY-STATION DETAILED
        # ══════════════════════════════════════════════════════════════
        h1("5. Station-by-Station Detailed Calculation")

        for k, i in enumerate(sta_idx):
            h2(f"5.{k+1} Station x = {R['x'][i]:.2f} m")

            h3("5.x.1 Section Properties")
            tbl(["Parameter","Symbol","Value","Unit"],[
                ["Thickness","t", f"{s('t',i)*1000:.1f}", "mm"],
                ["Tendon depth from top","z", f"{s('z',i)*1000:.1f}","mm"],
                ["Centroid from top","y_c", f"{s('yc',i)*1000:.1f}","mm"],
                ["Eccentricity","e", f"{s('e',i)*1000:.1f}","mm"],
                ["Gross Area (1m)","A_g", f"{s('Ag',i)*1e6:.0f}","mm²"],
                ["Net Area (1m)","A_n", f"{s('An',i)*1e6:.0f}","mm²"],
                ["Gross Inertia","I_g", f"{s('Ig',i)*1e12:.2e}","mm⁴"],
                ["Net Inertia","I_n", f"{s('In',i)*1e12:.2e}","mm⁴"],
            ], cw=[4,2,2.5])
            blank()

            h3("5.x.2 Applied Loads")
            tbl(["Load Case","M (kNm/m)","V (kN/m)"],[
                ["DL", f"{s('m_dl',i):.2f}", f"{s('v_dl',i):.2f}"],
                ["SDL", f"{s('m_sdl',i):.2f}", f"{s('v_sdl',i):.2f}"],
                ["LL", f"{s('m_ll',i):.2f}", f"{s('v_ll',i):.2f}"],
                ["Service I", f"{s('ms1',i):.2f}", f"{s('v_dl',i)+s('v_sdl',i)+s('v_ll',i):.2f}"],
                ["Strength I", f"{s('mu',i):.2f}", f"{s('vu',i):.2f}"],
            ], cw=[3,2.5,2.5])
            blank()

            h3("5.x.3 Transfer Stage Stress Check")
            formula("f_top = −P_i/A_n + P_i·e·(t/2)/I_n − M_DL·(t/2)/I_n")
            subst(f"P_i = {R['Pi']:.2f} kN/m, M_DL = {s('m_dl',i):.2f} kNm/m")
            result(f"f_top = {s('tr_top',i):.3f} MPa")
            pf(R['lim_tr_c'] <= s('tr_top',i) <= R['lim_tr_t'], "Transfer Top OK", "Transfer Top FAIL")
            blank()
            formula("f_bot = −P_i/A_n − P_i·e·(t/2)/I_n + M_DL·(t/2)/I_n")
            result(f"f_bot = {s('tr_bot',i):.3f} MPa")
            pf(R['lim_tr_c'] <= s('tr_bot',i) <= R['lim_tr_t'], "Transfer Bot OK", "Transfer Bot FAIL")
            blank()

            h3("5.x.4 Service Stage Stress Check")
            formula("f_top = −P_e/A_g + P_e·e·(t/2)/I_g − M_s1·(t/2)/I_g")
            subst(f"P_e = {R['Pe']:.2f} kN/m, M_s1 = {s('ms1',i):.2f} kNm/m")
            result(f"f_top = {s('sv1_top',i):.3f} MPa")
            pf(R['lim_sv_ct'] <= s('sv1_top',i) <= R['lim_sv_t'], "Service Top OK", "Service Top FAIL")
            blank()
            formula("f_bot = −P_e/A_g − P_e·e·(t/2)/I_g + M_s1·(t/2)/I_g")
            result(f"f_bot = {s('sv1_bot',i):.3f} MPa")
            pf(R['lim_sv_ct'] <= s('sv1_bot',i) <= R['lim_sv_t'], "Service Bot OK", "Service Bot FAIL")
            blank()

            h3("5.x.5 Flexural Strength Check")
            formula("M_n = A_ps × f_ps × (d_p − a/2)")
            subst(f"d_p = {s('dp_pos',i)*1000:.1f} mm (sagging)")
            subst(f"c = {s('c_pos',i)*1000:.1f} mm, a = β₁·c = {s('a_pos',i)*1000:.1f} mm")
            subst(f"f_ps = {s('fps_pos',i):.1f} MPa")
            result(f"φM_n = {s('phi_Mn_pos',i):.2f} kNm/m")
            result(f"M_u = {s('mu',i):.2f} kNm/m")
            pf(abs(s('mu',i)) <= abs(s('phi_Mn_pos',i)), f"Flexure OK (DCR={abs(s('mu',i)/s('phi_Mn_pos',i)):.3f})", "Flexure FAIL")
            blank()

            h3("5.x.6 Shear Strength Check")
            formula("V_c = 0.083 × β × √f'_c × b × d_v")
            subst(f"d_v = max(0.9d, 0.72t) = {s('dv',i)*1000:.1f} mm")
            result(f"φV_n = φ × min(V_c, 0.25f'_c·b·d_v) = {s('phi_Vn',i):.2f} kN/m")
            result(f"V_u = {s('vu',i):.2f} kN/m")
            pf(s('vu',i) <= s('phi_Vn',i), f"Shear OK (DCR={s('vu',i)/s('phi_Vn',i):.3f})", "Shear FAIL")

            if k < len(sta_idx) - 1:
                doc.add_page_break()

        # ══════════════════════════════════════════════════════════════
        # SEC 6 — SUMMARY TABLE
        # ══════════════════════════════════════════════════════════════
        doc.add_page_break()
        h1("6. Summary of Results — All Stations")
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

except Exception as e:
    st.error(f"Calculation Error: {e}")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# 6. TABS FOR RESULTS DISPLAY
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Section & Tendon", "📉 Prestress Loss", "📈 Stress Envelopes",
    "💪 Flexural Capacity", "✂️ Shear Capacity", "📋 Station Tables", "📄 Report"
])

with tab1:
    st.subheader("Cross-Section Geometry")
    x_m = R["x"]; N = len(x_m)
    top_mm = np.zeros(N); bot_mm = -R["t"] * 1000.0
    cg_mm = -R["yc"] * 1000.0; tdn_mm = -R["z"] * 1000.0
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=np.concatenate([x_m, x_m[::-1]]),
        y=np.concatenate([top_mm, bot_mm[::-1]]),
        fill="toself", fillcolor="rgba(173, 204, 240, 0.45)",
        line=dict(color="steelblue", width=1.5), name="Top Flange"
    ))
    fig.add_trace(go.Scatter(x=x_m, y=cg_mm, mode="lines",
        line=dict(color="gray", dash="dot", width=1), name="Section CG"))
    fig.add_trace(go.Scatter(x=x_m, y=tdn_mm, mode="lines",
        line=dict(color="red", width=2.0), name="Tendon CGS"))
    fig.add_vline(x=cl_lweb, line=dict(color="rgba(200,100,0,0.9)", dash="dash"),
        annotation_text="<b>CL. L.Web</b>", annotation_position="top right")
    fig.add_vline(x=cl_rweb, line=dict(color="rgba(200,100,0,0.9)", dash="dash"),
        annotation_text="<b>CL. R.Web</b>", annotation_position="top left")
    fig.update_layout(
        title="Cross-Section with Tendon Layout",
        xaxis_title="Distance from Left Edge (m)", yaxis_title="Depth (mm)",
        height=500, plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.15)
    )
    st.plotly_chart(fig, use_container_width=True)
    st.info(f"**Flange width:** {width:.2f} m | **Web Span:** {(cl_rweb-cl_lweb)*1000:.0f} mm")

with tab2:
    st.subheader("Prestress Loss Breakdown")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Jacking Stress f_pj", f"{L['fpj']:.1f} MPa", f"{fpi_ratio*100:.0f}% f_pu")
        st.metric("After Immediate Loss", f"{L['fpi_eff']:.1f} MPa", f"−{L['imm_loss_pct']:.2f}%")
        st.metric("Effective Stress f_pe", f"{L['fpe']:.1f} MPa", f"−{L['total_loss_pct']:.2f}%")
    with col2:
        st.metric("Immediate Loss Δf_i", f"{L['delta_imm']:.1f} MPa", f"{L['imm_loss_pct']:.2f}% of f_pj")
        st.metric("Long-term Loss Δf_LT", f"{L['delta_lt']:.1f} MPa", f"{L['lt_loss_pct']:.2f}% of f_pj")
        st.metric("Effective Force P_e", f"{L['Pe']:.1f} kN/m", f"Efficiency: {L['eff_ratio']*100:.1f}%")

    st.markdown("---")
    st.subheader("Loss Components")
    loss_df = pd.DataFrame({
        "Component": ["Friction", "Anchorage", "Elastic Shortening", "Shrinkage", "Creep", "Relaxation"],
        "Value (MPa)": [L['delta_fpF'], L['delta_fpA'], L['delta_fpES'],
                       L['delta_fpSH'], L['delta_fpCR'], L['delta_fpR']],
        "Type": ["Immediate", "Immediate", "Immediate", "Long-term", "Long-term"]
    })
    fig_loss = go.Figure(data=[go.Bar(
        x=loss_df["Component"], y=loss_df["Value (MPa)"],
        marker_color=loss_df["Type"].map({"Immediate": "lightcoral", "Long-term": "lightblue"})
    )])
    fig_loss.update_layout(title="Prestress Loss Components", yaxis_title="Loss (MPa)", height=400)
    st.plotly_chart(fig_loss, use_container_width=True)

with tab3:
    st.subheader("Stress Envelopes at Service Stage")
    fig_stress = make_subplots(rows=1, cols=2, subplot_titles=("Transfer Stage", "Service I Stage"))

    fig_stress.add_trace(go.Scatter(x=R["x"], y=R["tr_top"], name="Top (Tr)", line=dict(color="red")), row=1, col=1)
    fig_stress.add_trace(go.Scatter(x=R["x"], y=R["tr_bot"], name="Bot (Tr)", line=dict(color="blue")), row=1, col=1)
    fig_stress.add_hline(y=R["lim_tr_c"], line_dash="dash", line_color="orange", row=1, col=1)
    fig_stress.add_hline(y=R["lim_tr_t"], line_dash="dash", line_color="
    fig_stress.add_hline(y=R["lim_tr_t"], line_dash="dash", line_color="green", row=1, col=1)

    fig_stress.add_trace(go.Scatter(x=R["x"], y=R["sv1_top"], name="Top (Sv)", line=dict(color="red", dash="dash")), row=1, col=2)
    fig_stress.add_trace(go.Scatter(x=R["x"], y=R["sv1_bot"], name="Bot (Sv)", line=dict(color="blue", dash="dash")), row=1, col=2)
    fig_stress.add_hline(y=R["lim_sv_ct"], line_dash="dash", line_color="orange", row=1, col=2)
    fig_stress.add_hline(y=R["lim_sv_t"], line_dash="dash", line_color="green", row=1, col=2)

    fig_stress.update_xaxes(title_text="x (m)", row=1, col=1)
    fig_stress.update_xaxes(title_text="x (m)", row=1, col=2)
    fig_stress.update_yaxes(title_text="Stress (MPa)", row=1, col=1)
    fig_stress.update_yaxes(title_text="Stress (MPa)", row=1, col=2)
    fig_stress.update_layout(height=500, showlegend=True)
    st.plotly_chart(fig_stress, use_container_width=True)

    st.caption("**Limits:** Transfer Comp = −0.60f'ci, Tens = +0.62√f'ci | Service Comp = −0.60f'c, Tens = +0.50√f'c")

with tab4:
    st.subheader("Flexural Capacity Check (Strength I)")
    fig_flex = go.Figure()
    fig_flex.add_trace(go.Scatter(x=R["x"], y=R["mu"], name="M_u (Demand)", line=dict(color="red", width=2)))
    fig_flex.add_trace(go.Scatter(x=R["x"], y=R["phi_Mn_pos"], name="φM_n (Pos)", line=dict(color="green", dash="dash")))
    fig_flex.add_trace(go.Scatter(x=R["x"], y=R["phi_Mn_neg"], name="φM_n (Neg)", line=dict(color="green", dash="dot")))
    fig_flex.add_hline(y=0, line_color="black", line_width=0.5)
    fig_flex.update_layout(
        title="Flexural Demand vs Capacity",
        xaxis_title="x (m)", yaxis_title="Moment (kNm/m)",
        height=500, plot_bgcolor="white"
    )
    st.plotly_chart(fig_flex, use_container_width=True)

    st.subheader("Ductility Check (c/d_p ≤ 0.42)")
    cdp_max = max(np.nanmax(R["cdp_pos"]), np.nanmax(R["cdp_neg"]))
    if cdp_max <= 0.42:
        st.success(f"✅ Ductile section: c/d_p,max = {cdp_max:.3f} ≤ 0.42")
    else:
        st.error(f"❌ Over-reinforced: c/d_p,max = {cdp_max:.3f} > 0.42 — Add compression steel or increase depth")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("φM_n,max (Sagging)", f"{np.max(R['phi_Mn_pos']):.1f} kNm/m")
        st.metric("M_u,max", f"{np.max(np.abs(R['mu'])):.1f} kNm/m")
    with col2:
        st.metric("φM_n,max (Hogging)", f"{np.min(R['phi_Mn_neg']):.1f} kNm/m")
        st.metric("DCR_max", f"{np.max(np.abs(R['mu'])) / np.max(np.abs(R['phi_Mn_pos'])):.3f}")

with tab5:
    st.subheader("Shear Capacity Check (Strength I)")
    fig_shear = go.Figure()
    fig_shear.add_trace(go.Scatter(x=R["x"], y=R["vu"], name="V_u (Demand)", line=dict(color="red", width=2)))
    fig_shear.add_trace(go.Scatter(x=R["x"], y=R["phi_Vn"], name="φV_n (Capacity)", line=dict(color="green", dash="dash")))
    fig_shear.update_layout(
        title="Shear Demand vs Capacity",
        xaxis_title="x (m)", yaxis_title="Shear (kN/m)",
        height=500, plot_bgcolor="white"
    )
    st.plotly_chart(fig_shear, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("φV_n,min", f"{np.min(R['phi_Vn']):.1f} kN/m")
        st.metric("V_u,max", f"{np.max(R['vu']):.1f} kN/m")
    with col2:
        dcr_v_max = np.max(R["vu"] / R["phi_Vn"])
        if dcr_v_max <= 1.0:
            st.success(f"✅ Shear OK: DCR_max = {dcr_v_max:.3f} ≤ 1.0")
        else:
            st.error(f"❌ Shear FAIL: DCR_max = {dcr_v_max:.3f} > 1.0 — Add stirrups or increase depth")
        st.metric("V_c (Concrete)", f"{np.mean(R['Vc']):.1f} kN/m")

with tab6:
    st.subheader("Station-by-Station Results Table")
    summary_rows = []
    for i in sta_idx:
        mui_ = float(R["mu"][i]); vui_ = float(R["vu"][i])
        cap = (float(R["phi_Mn_pos"][i]) if mui_>=0 else abs(float(R["phi_Mn_neg"][i])))
        pVi_ = float(R["phi_Vn"][i])
        ok_tr = (R["lim_tr_c"]<=R["tr_top"][i]<=R["lim_tr_t"] and
                 R["lim_tr_c"]<=R["tr_bot"][i]<=R["lim_tr_t"])
        ok_sv = (R["sv1_top"][i] >= R["lim_sv_ct"] and
                 R["sv1_bot"][i] >= R["lim_sv_ct"] and
                 R["sv1_top"][i] <= R["lim_sv_t"] and
                 R["sv1_bot"][i] <= R["lim_sv_t"])
        dcr_m = abs(mui_)/cap if cap >0 else 999
        dcr_v = vui_/pVi_ if pVi_>0 else 999
        summary_rows.append({
            "x (m)": f"{R['x'][i]:.2f}",
            "t (mm)": f"{R['t'][i]*1000:.0f}",
            "z (mm)": f"{R['z'][i]*1000:.0f}",
            "M_u (kNm/m)": f"{mui_:.1f}",
            "φM_n (kNm/m)": f"{cap:.1f}",
            "DCR_Flex": f"{dcr_m:.3f}",
            "Flexure": "✅" if abs(mui_)<=cap else "❌",
            "V_u (kN/m)": f"{vui_:.1f}",
            "φV_n (kN/m)": f"{pVi_:.1f}",
            "DCR_Shear": f"{dcr_v:.3f}",
            "Shear": "✅" if vui_<=pVi_ else "❌",
            "Transfer": "✅" if ok_tr else "❌",
            "Service": "✅" if ok_sv else "❌",
        })
    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

    st.download_button(
        label="📥 Download Station Results (CSV)",
        data=df_summary.to_csv(index=False).encode("utf-8"),
        file_name=f"{doc_no}_station_results.csv",
        mime="text/csv"
    )

with tab7:
    st.subheader("📄 Download Calculation Report")
    st.markdown("""
    รายงาน Word ประกอบด้วย:
    1. **Cover Page** - ข้อมูลโครงการ
    2. **Design Basis** - สมมติฐานการออกแบบ AASHTO LRFD
    3. **Input Summary** - Material, Prestressing, Geometry + **รูป Section**
    4. **Prestress Loss** - การคำนวณ Loss ทั้ง Immediate และ Long-term
    5. **Stress Diagrams** - **รูป Transfer Stress** + **รูป Service Stress**
    6. **Station-by-Station** - ผลการตรวจสอบทุก Station แบบละเอียด
    7. **Summary Table** - ตารางสรุป DCR และ Pass/Fail
    """)

    report_buf = make_report()
    st.download_button(
        label="📥 Download Report (Word.docx)",
        data=report_buf,
        file_name=f"{doc_no}_Tendon_Design_Report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True
    )

    st.info("💡 **Tip:** เปิดไฟล์ใน Microsoft Word เพื่อดูรูป Section และ Stress Diagrams ที่แทรกอัตโนมัติ")

    st.markdown("---")
    st.subheader("Overall Design Status")
    all_ok = all(
        (R["lim_tr_c"]<=R["tr_top"][i]<=R["lim_tr_t"] and
         R["lim_tr_c"]<=R["tr_bot"][i]<=R["lim_tr_t"] and
         R["sv1_top"][i] >= R["lim_sv_ct"] and R["sv1_bot"][i] >= R["lim_sv_ct"] and
         R["sv1_top"][i] <= R["lim_sv_t"] and R["sv1_bot"][i] <= R["lim_sv_t"] and
         abs(R["mu"][i]) <= (R["phi_Mn_pos"][i] if R["mu"][i]>=0 else abs(R["phi_Mn_neg"][i])) and
         R["vu"][i] <= R["phi_Vn"][i])
        for i in sta_idx
    )
    if all_ok:
        st.success("🎉 **OVERALL: ADEQUATE** — The top flange tendon design satisfies all AASHTO LRFD limit states checked.")
    else:
        st.error("⚠️ **OVERALL: NOT ADEQUATE** — Revise tendon layout, spacing, strand count, or section geometry.")

except Exception as e:
    st.error(f"Calculation Error: {e}")
    st.exception(e)

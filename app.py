import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# =========================================================
# TITLE
# =========================================================
st.title("Prestressed Concrete Box Girder — Top Flange Tendon Design")

# =========================================================
# SESSION INIT
# =========================================================
def init_df(key, data):
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(data)

init_df("df_thk", {"Delete":[False,False],"x (m)":[0,6],"t (m)":[0.25,0.25]})
init_df("df_tdn", {"Delete":[False,False],"x (m)":[0,6],"z (m)":[0.10,0.10]})
init_df("df_ld", {
    "Delete":[False,False],
    "x (m)":[0,6],
    "M_DL":[500,500],"V_DL":[200,200],
    "M_SDL":[200,200],"V_SDL":[100,100],
    "M_LL":[800,800],"V_LL":[300,300]
})

# =========================================================
# CLEAN FUNCTION
# =========================================================
def clean_df(df):
    df = df.copy()
    if "Delete" in df.columns:
        df = df[df["Delete"] != True]

    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna()
    df = df.drop_duplicates(subset="x (m)")
    df = df.sort_values("x (m)")
    return df

# =========================================================
# SIDEBAR INPUT
# =========================================================
st.sidebar.header("Input Panel")

# --- Section ---
st.sidebar.subheader("Section")
width = st.sidebar.number_input("Width (m)", 0.1, 20.0, 6.0, key="sec_width")
web_t = st.sidebar.number_input("Web Thickness (m)", 0.1, 5.0, 0.5, key="sec_web")

df_thk = st.sidebar.data_editor(
    st.session_state.df_thk, num_rows="dynamic", key="sec_table"
)

# --- Tendon ---
st.sidebar.subheader("Tendon")
n_tendon = st.sidebar.number_input("Number of Tendons", 1, 20, 2, key="tdn_n")
n_strand = st.sidebar.number_input("Strands / Tendon", 1, 30, 8, key="tdn_s")

df_tdn = st.sidebar.data_editor(
    st.session_state.df_tdn, num_rows="dynamic", key="tdn_table"
)

# --- Material ---
st.sidebar.subheader("Material")
fc = st.sidebar.number_input("f'c (MPa)", 20.0, 80.0, 40.0, key="mat_fc")
eff = st.sidebar.slider("Prestress Efficiency", 0.5, 0.9, 0.75, key="mat_eff")

aps = 140e-6
fpu = 1860

# --- Loads ---
st.sidebar.subheader("Loads")
df_ld = st.sidebar.data_editor(
    st.session_state.df_ld, num_rows="dynamic", key="ld_table"
)

# =========================================================
# CLEAN DATA
# =========================================================
df_thk = clean_df(df_thk)
df_tdn = clean_df(df_tdn)
df_ld = clean_df(df_ld)

# =========================================================
# GRID
# =========================================================
x = np.linspace(0, width, 400)

# =========================================================
# INTERPOLATION
# =========================================================
def interp_safe(x, df, col):
    return np.interp(x, df["x (m)"], df[col])

# =========================================================
# SECTION + TENDON VIEW
# =========================================================
st.subheader("🔍 Section + Tendon")

if len(df_thk)>=2 and len(df_tdn)>=2:

    t = interp_safe(x, df_thk, "t (m)")
    z = interp_safe(x, df_tdn, "z (m)")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=0*x, name="Top"))
    fig.add_trace(go.Scatter(x=x, y=-t, name="Bottom"))
    fig.add_trace(go.Scatter(x=x, y=-z, name="Tendon", line=dict(width=3)))

    fig.add_vline(x=web_t/2, line_dash="dash")
    fig.add_vline(x=width-web_t/2, line_dash="dash")

    fig.update_layout(title="Section View", xaxis_title="x (m)", yaxis_title="Depth (m)")
    st.plotly_chart(fig, use_container_width=True)

# =========================================================
# LOAD
# =========================================================
st.subheader("📊 Load (Strength I)")

if len(df_ld)>=2:

    M = (1.25*interp_safe(x, df_ld, "M_DL") +
         1.50*interp_safe(x, df_ld, "M_SDL") +
         1.75*interp_safe(x, df_ld, "M_LL"))

    V = (1.25*interp_safe(x, df_ld, "V_DL") +
         1.50*interp_safe(x, df_ld, "V_SDL") +
         1.75*interp_safe(x, df_ld, "V_LL"))

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=x, y=M, name="Mu"))
    fig2.add_trace(go.Scatter(x=x, y=V, name="Vu"))

    fig2.update_layout(title="Strength I", xaxis_title="x (m)")
    st.plotly_chart(fig2, use_container_width=True)

# =========================================================
# STRESS
# =========================================================
st.subheader("🧮 Stress (Service I)")

if len(df_thk)>=2 and len(df_tdn)>=2 and len(df_ld)>=2:

    t = interp_safe(x, df_thk, "t (m)")
    z = interp_safe(x, df_tdn, "z (m)")

    M = (interp_safe(x, df_ld, "M_DL") +
         interp_safe(x, df_ld, "M_SDL") +
         interp_safe(x, df_ld, "M_LL"))

    # Prestress (NEGATIVE = compression)
    P = - n_tendon * n_strand * aps * fpu * eff * 1000

    A = t
    yc = t/2
    I = t**3/12
    e = yc - z

    sigma_top = ((P/A) - (P*e*yc/I) - (M*yc/I)) / 1000
    sigma_bot = ((P/A) - (P*e*(-yc)/I) - (M*(-yc)/I)) / 1000

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=x, y=sigma_top, name="Top", line=dict(color="red")))
    fig3.add_trace(go.Scatter(x=x, y=sigma_bot, name="Bottom", line=dict(color="blue")))

    fig3.add_hline(y=0, line_dash="dash", annotation_text="+T / -C")

    fig3.update_layout(title="Stress", xaxis_title="x (m)", yaxis_title="MPa")
    st.plotly_chart(fig3, use_container_width=True)

    st.write(f"P = {P:.2f} kN")

# =========================================================
# STRESS CHECK
# =========================================================
st.subheader("✅ Stress Check")

if len(df_thk)>=2 and len(df_tdn)>=2 and len(df_ld)>=2:

    comp_lim = -0.6*fc
    tens_lim = 0

    fail = (sigma_top<comp_lim)|(sigma_top>tens_lim)|(sigma_bot<comp_lim)|(sigma_bot>tens_lim)

    if np.any(fail):
        st.error("FAIL")
    else:
        st.success("PASS")











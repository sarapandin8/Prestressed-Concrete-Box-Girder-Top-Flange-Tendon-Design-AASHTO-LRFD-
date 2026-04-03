import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("Prestressed Concrete Box Girder — Top Flange Tendon Design")

# =========================================================
# INIT STATE
# =========================================================
if "init" not in st.session_state:

    st.session_state.df_thk = pd.DataFrame({
        "Delete":[False,False],
        "x (m)":[0.0,6.0],
        "t (m)":[0.25,0.25]
    })

    st.session_state.df_tdn = pd.DataFrame({
        "Delete":[False,False],
        "x (m)":[0.0,6.0],
        "z (m)":[0.10,0.10]
    })

    st.session_state.df_ld = pd.DataFrame({
        "Delete":[False,False],
        "x (m)":[0.0,6.0],
        "M_DL":[500,500],"V_DL":[200,200],
        "M_SDL":[200,200],"V_SDL":[100,100],
        "M_LL":[800,800],"V_LL":[300,300]
    })

    st.session_state.init = True

# =========================================================
# SAFE CONVERT (🔥 ป้องกัน dict bug)
# =========================================================
def ensure_df(data):
    if isinstance(data, pd.DataFrame):
        return data
    try:
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# =========================================================
# CALLBACK (🔥 FIX TYPE)
# =========================================================
def sync_thk():
    st.session_state.df_thk = ensure_df(st.session_state.thk_editor)

def sync_tdn():
    st.session_state.df_tdn = ensure_df(st.session_state.tdn_editor)

def sync_ld():
    st.session_state.df_ld = ensure_df(st.session_state.ld_editor)

# =========================================================
# CLEAN FUNCTION
# =========================================================
def clean_df(df):
    df = ensure_df(df).copy()

    if "Delete" in df.columns:
        df = df[df["Delete"] != True]

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna()

    if "x (m)" in df.columns:
        df = df.drop_duplicates(subset="x (m)")
        df = df.sort_values("x (m)")

    return df

# =========================================================
# SIDEBAR INPUT
# =========================================================
st.sidebar.header("Input")

width = st.sidebar.number_input("Width (m)", 0.1, 20.0, 6.0)
web_t = st.sidebar.number_input("Web Thickness (m)", 0.1, 5.0, 0.5)

n_tendon = st.sidebar.number_input("Number of Tendons", 1, 20, 2)
n_strand = st.sidebar.number_input("Strands / Tendon", 1, 30, 8)

fc = st.sidebar.number_input("f'c (MPa)", 20.0, 80.0, 40.0)
eff = st.sidebar.slider("Prestress Efficiency", 0.5, 0.9, 0.75)

aps = 140e-6
fpu = 1860

# =========================================================
# DATA EDITOR (🔥 STABLE)
# =========================================================
st.sidebar.subheader("Section Geometry")

df_thk = st.sidebar.data_editor(
    ensure_df(st.session_state.df_thk),
    num_rows="dynamic",
    key="thk_editor",
    on_change=sync_thk
)

st.sidebar.subheader("Tendon Profile")

df_tdn = st.sidebar.data_editor(
    ensure_df(st.session_state.df_tdn),
    num_rows="dynamic",
    key="tdn_editor",
    on_change=sync_tdn
)

st.sidebar.subheader("Loads")

df_ld = st.sidebar.data_editor(
    ensure_df(st.session_state.df_ld),
    num_rows="dynamic",
    key="ld_editor",
    on_change=sync_ld
)

# =========================================================
# CLEAN DATA
# =========================================================
df_thk = clean_df(st.session_state.df_thk)
df_tdn = clean_df(st.session_state.df_tdn)
df_ld = clean_df(st.session_state.df_ld)

x = np.linspace(0, width, 400)

def interp(x, df, col):
    return np.interp(x, df["x (m)"], df[col])

# =========================================================
# SECTION + TENDON
# =========================================================
st.subheader("🔍 Section + Tendon")

if len(df_thk) >= 2 and len(df_tdn) >= 2:

    t = interp(x, df_thk, "t (m)")
    z = interp(x, df_tdn, "z (m)")

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=x, y=0*x, name="Top"))
    fig.add_trace(go.Scatter(x=x, y=-t, name="Bottom"))
    fig.add_trace(go.Scatter(x=x, y=-z, name="Tendon", line=dict(width=3)))

    fig.add_vline(x=web_t/2, line_dash="dash")
    fig.add_vline(x=width-web_t/2, line_dash="dash")

    fig.update_layout(
        title="Section View",
        xaxis_title="x (m)",
        yaxis_title="Depth (m)"
    )

    st.plotly_chart(fig, use_container_width=True)

# =========================================================
# LOAD
# =========================================================
st.subheader("📊 Load (Strength I)")

if len(df_ld) >= 2:

    M = (1.25*interp(x, df_ld,"M_DL") +
         1.50*interp(x, df_ld,"M_SDL") +
         1.75*interp(x, df_ld,"M_LL"))

    V = (1.25*interp(x, df_ld,"V_DL") +
         1.50*interp(x, df_ld,"V_SDL") +
         1.75*interp(x, df_ld,"V_LL"))

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=x, y=M, name="Mu"))
    fig2.add_trace(go.Scatter(x=x, y=V, name="Vu"))

    fig2.update_layout(
        title="Strength I",
        xaxis_title="x (m)"
    )

    st.plotly_chart(fig2, use_container_width=True)

# =========================================================
# STRESS
# =========================================================
st.subheader("🧮 Stress (Service I)")

if len(df_thk)>=2 and len(df_tdn)>=2 and len(df_ld)>=2:

    t = interp(x, df_thk,"t (m)")
    z = interp(x, df_tdn,"z (m)")

    M = (interp(x, df_ld,"M_DL") +
         interp(x, df_ld,"M_SDL") +
         interp(x, df_ld,"M_LL"))

    P = - n_tendon*n_strand*aps*fpu*eff*1000

    A = t
    yc = t/2
    I = t**3/12
    e = yc - z

    sigma_top = ((P/A) - (P*e*yc/I) - (M*yc/I))/1000
    sigma_bot = ((P/A) - (P*e*(-yc)/I) - (M*(-yc)/I))/1000

    fig3 = go.Figure()

    fig3.add_trace(go.Scatter(x=x, y=sigma_top, name="Top Fiber"))
    fig3.add_trace(go.Scatter(x=x, y=sigma_bot, name="Bottom Fiber"))

    fig3.add_hline(
        y=0,
        line_dash="dash",
        annotation_text="+Tension / -Compression"
    )

    fig3.update_layout(
        title="Stress Distribution",
        xaxis_title="x (m)",
        yaxis_title="Stress (MPa)"
    )

    st.plotly_chart(fig3, use_container_width=True)

    st.write(f"Prestress Force P = {P:.2f} kN (Compression)")
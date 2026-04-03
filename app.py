import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("Prestressed Concrete Box Girder — Top Flange Tendon Design")

# ==============================
# INIT SESSION
# ==============================
def init_df(key, data):
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(data)

init_df("df_thickness", {
    "Delete": [False, False],
    "x (m)": [0.0, 6.0],
    "t (m)": [0.25, 0.25]
})

init_df("df_tendon", {
    "Delete": [False, False],
    "x (m)": [0.0, 6.0],
    "z from top (m)": [0.10, 0.10]
})

init_df("df_load", {
    "Delete": [False, False],
    "x (m)": [0.0, 6.0],
    "M_DL": [500, 500],
    "V_DL": [200, 200],
    "M_SDL": [200, 200],
    "V_SDL": [100, 100],
    "M_LL": [800, 800],
    "V_LL": [300, 300],
})

# ==============================
# SIDEBAR INPUT
# ==============================
st.sidebar.header("Input Panel")

# Section
st.sidebar.subheader("Section")
width = st.sidebar.number_input("Width (m)", value=6.0)
web_thickness = st.sidebar.number_input("Web Thickness (m)", value=0.5)

df_thickness = st.sidebar.data_editor(
    st.session_state.df_thickness,
    num_rows="dynamic",
    key="thickness_editor"
)

# Tendon
st.sidebar.subheader("Tendon")

num_tendon = st.sidebar.number_input("Number of Tendons", value=2)
strands_per_tendon = st.sidebar.number_input("Number of Strands / Tendon", value=8)

df_tendon = st.sidebar.data_editor(
    st.session_state.df_tendon,
    num_rows="dynamic",
    key="tendon_editor"
)

# Material / Prestress
st.sidebar.subheader("Material & Prestress")

fc = st.sidebar.number_input("f'c (MPa)", value=40.0)
eff = st.sidebar.slider("Effective Prestress Ratio", 0.5, 0.9, 0.75)

aps = 140e-6     # m²
fpu = 1860       # MPa

# Loads
st.sidebar.subheader("Loads")

df_load = st.sidebar.data_editor(
    st.session_state.df_load,
    num_rows="dynamic",
    key="load_editor"
)

# ==============================
# CLEAN FUNCTION
# ==============================
def clean_df(df):
    df = df.copy()

    if "Delete" in df.columns:
        df["Delete"] = df["Delete"].fillna(False)
        df = df[df["Delete"] == False]

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna()
    df = df.drop_duplicates(subset="x (m)")
    df = df.sort_values("x (m)")

    return df

df_thk = clean_df(df_thickness)
df_tdn = clean_df(df_tendon)
df_ld = clean_df(df_load)

# ==============================
# SECTION + TENDON VIEW
# ==============================
st.subheader("🔍 Section + Tendon")

if len(df_thk) >= 2 and len(df_tdn) >= 2:

    x_plot = np.linspace(0, width, 400)

    t = np.interp(x_plot, df_thk["x (m)"], df_thk["t (m)"])
    z = np.interp(x_plot, df_tdn["x (m)"], df_tdn["z from top (m)"])

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=x_plot, y=np.zeros_like(x_plot), name="Top"))
    fig.add_trace(go.Scatter(x=x_plot, y=-t, name="Bottom"))
    fig.add_trace(go.Scatter(x=x_plot, y=-z, name="Tendon", line=dict(width=3)))

    fig.add_vline(x=web_thickness/2, line_dash="dash")
    fig.add_vline(x=width - web_thickness/2, line_dash="dash")

    fig.update_layout(
        title="Section View",
        xaxis_title="x (m)",
        yaxis_title="Depth (m)"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Need at least 2 valid points")

# ==============================
# LOAD GRAPH
# ==============================
st.subheader("📊 Load (Strength I — AASHTO LRFD)")

if len(df_ld) >= 2:

    x_plot = np.linspace(0, width, 400)

    M_DL = np.interp(x_plot, df_ld["x (m)"], df_ld["M_DL"])
    M_SDL = np.interp(x_plot, df_ld["x (m)"], df_ld["M_SDL"])
    M_LL = np.interp(x_plot, df_ld["x (m)"], df_ld["M_LL"])

    V_DL = np.interp(x_plot, df_ld["x (m)"], df_ld["V_DL"])
    V_SDL = np.interp(x_plot, df_ld["x (m)"], df_ld["V_SDL"])
    V_LL = np.interp(x_plot, df_ld["x (m)"], df_ld["V_LL"])

    Mu = 1.25*M_DL + 1.50*M_SDL + 1.75*M_LL
    Vu = 1.25*V_DL + 1.50*V_SDL + 1.75*V_LL

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=x_plot, y=Mu, name="Mu (kN·m/m)"))
    fig2.add_trace(go.Scatter(x=x_plot, y=Vu, name="Vu (kN/m)"))

    fig2.update_layout(
        title="Strength I Load Distribution",
        xaxis_title="x (m)",
        yaxis_title="Force"
    )

    st.plotly_chart(fig2, use_container_width=True)

else:
    st.warning("Need load data")

# ==============================
# STRESS (SERVICE I)
# ==============================
st.subheader("🧮 Stress Check (Service I)")

if len(df_thk) >= 2 and len(df_tdn) >= 2 and len(df_ld) >= 2:

    total_strands = num_tendon * strands_per_tendon

    # Prestress force (kN)
    P = total_strands * aps * fpu * eff * 1000

    x_plot = np.linspace(0, width, 400)

    t = np.interp(x_plot, df_thk["x (m)"], df_thk["t (m)"])
    z = np.interp(x_plot, df_tdn["x (m)"], df_tdn["z from top (m)"])

    M = (np.interp(x_plot, df_ld["x (m)"], df_ld["M_DL"]) +
         np.interp(x_plot, df_ld["x (m)"], df_ld["M_SDL"]) +
         np.interp(x_plot, df_ld["x (m)"], df_ld["M_LL"]))

    # Section properties
    b = 1.0
    A = b * t
    yc = t / 2
    I = b * t**3 / 12

    e = yc - z

    y_top = yc
    y_bot = -yc

    sigma_top = ((P / A) - (P * e * y_top / I) - (M * y_top / I)) / 1000
    sigma_bot = ((P / A) - (P * e * y_bot / I) - (M * y_bot / I)) / 1000

    fig3 = go.Figure()

    fig3.add_trace(go.Scatter(
        x=x_plot,
        y=sigma_top,
        name="Top Fiber (MPa)",
        line=dict(color="red"),
        hovertemplate="x = %{x:.2f} m<br>σ = %{y:.2f} MPa"
    ))

    fig3.add_trace(go.Scatter(
        x=x_plot,
        y=sigma_bot,
        name="Bottom Fiber (MPa)",
        line=dict(color="blue"),
        hovertemplate="x = %{x:.2f} m<br>σ = %{y:.2f} MPa"
    ))

    fig3.add_hline(
        y=0,
        line_dash="dash",
        line_color="black",
        annotation_text="0 MPa (Tension + / Compression -)",
        annotation_position="top left"
    )

    fig3.update_layout(
        title="Service I Stress (+ Tension / - Compression)",
        xaxis_title="x (m)",
        yaxis_title="Stress (MPa)"
    )

    st.plotly_chart(fig3, use_container_width=True)

    st.write(f"Total Tendons = {num_tendon}")
    st.write(f"Strands / Tendon = {strands_per_tendon}")
    st.write(f"Total Strands = {total_strands}")
    st.write(f"Prestress Force P = {P:.2f} kN")

else:
    st.warning("Need full data for stress calculation")

# ==============================
# DEBUG
# ==============================
if st.checkbox("Show Debug Data"):
    st.write("Section:", df_thk)
    st.write("Tendon:", df_tdn)
    st.write("Load:", df_ld)
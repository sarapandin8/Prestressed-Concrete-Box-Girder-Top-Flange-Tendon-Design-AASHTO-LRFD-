import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("Prestressed Concrete Box Girder — Top Flange Tendon Design")

# ==============================
# INIT SESSION
# ==============================
if "df_thickness" not in st.session_state:
    st.session_state.df_thickness = pd.DataFrame({
        "Delete": [False, False],
        "x (m)": [0.0, 6.0],
        "t (m)": [0.25, 0.25]
    })

if "df_tendon" not in st.session_state:
    st.session_state.df_tendon = pd.DataFrame({
        "Delete": [False, False],
        "x (m)": [0.0, 6.0],
        "z from top (m)": [0.10, 0.10]
    })

if "df_load" not in st.session_state:
    st.session_state.df_load = pd.DataFrame({
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

# -------- SECTION --------
st.sidebar.subheader("Section")

width = st.sidebar.number_input("Width (m)", value=6.0)
web_thickness = st.sidebar.number_input("Web Thickness (m)", value=0.5)

df_thickness = st.sidebar.data_editor(
    st.session_state.df_thickness,
    num_rows="dynamic",
    key="thickness_editor"
)

# -------- TENDON --------
st.sidebar.subheader("Tendon")

df_tendon = st.sidebar.data_editor(
    st.session_state.df_tendon,
    num_rows="dynamic",
    key="tendon_editor"
)

# -------- LOAD --------
st.sidebar.subheader("Loads")

df_load = st.sidebar.data_editor(
    st.session_state.df_load,
    num_rows="dynamic",
    key="load_editor"
)

# ==============================
# CLEAN DATA
# ==============================

def clean_df(df):
    df = df.copy()
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
# MAIN SCREEN
# ==============================

col1, col2 = st.columns([2, 1])

# ==============================
# LEFT: SECTION VIEW
# ==============================
with col1:
    st.subheader("🔍 Section + Tendon")

    if len(df_thk) >= 2 and len(df_tdn) >= 2:

        x_plot = np.linspace(0, width, 400)

        t_interp = np.interp(x_plot, df_thk["x (m)"], df_thk["t (m)"])
        z_interp = np.interp(x_plot, df_tdn["x (m)"], df_tdn["z from top (m)"])

        fig = go.Figure()

        fig.add_trace(go.Scatter(x=x_plot, y=np.zeros_like(x_plot), name="Top"))
        fig.add_trace(go.Scatter(x=x_plot, y=-t_interp, name="Bottom"))

        fig.add_trace(go.Scatter(
            x=x_plot,
            y=-z_interp,
            name="Tendon",
            line=dict(width=3)
        ))

        fig.add_vline(x=web_thickness/2)
        fig.add_vline(x=width - web_thickness/2)

        fig.update_layout(
            title="Section View",
            yaxis_title="Depth (m)"
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Need at least 2 points")

# ==============================
# RIGHT: LOAD GRAPH
# ==============================
with col2:
    st.subheader("📊 Load (Strength I)")

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
        fig2.add_trace(go.Scatter(x=x_plot, y=Mu, name="Mu"))
        fig2.add_trace(go.Scatter(x=x_plot, y=Vu, name="Vu"))

        st.plotly_chart(fig2, use_container_width=True)

    else:
        st.warning("Need load data")

# ==============================
# OPTIONAL DEBUG
# ==============================
if st.checkbox("Show Debug Data"):
    st.write("Section:", df_thk)
    st.write("Tendon:", df_tdn)
    st.write("Load:", df_ld)
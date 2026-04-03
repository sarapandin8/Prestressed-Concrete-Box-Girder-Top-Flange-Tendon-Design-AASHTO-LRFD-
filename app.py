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
# TAB SETUP
# ==============================
tab1, tab2 = st.tabs(["Section + Tendon", "Loads"])

# ==============================
# TAB 1
# ==============================
with tab1:
    st.header("Section + Tendon")

    col1, col2 = st.columns(2)

    with col1:
        width = st.number_input("Width (m)", value=6.0)
        web_thickness = st.number_input("Web Thickness (m)", value=0.5)

        df_thickness = st.data_editor(
            st.session_state.df_thickness,
            num_rows="dynamic",
            key="thickness_editor"
        )

        # ---- CLEAN THICKNESS ----
        df_thk = df_thickness.copy()
        df_thk["Delete"] = df_thk["Delete"].fillna(False)
        df_thk = df_thk[df_thk["Delete"] == False]

        df_thk["x (m)"] = pd.to_numeric(df_thk["x (m)"], errors='coerce')
        df_thk["t (m)"] = pd.to_numeric(df_thk["t (m)"], errors='coerce')

        df_thk = df_thk.dropna()
        df_thk = df_thk.drop_duplicates(subset="x (m)")
        df_thk = df_thk.sort_values("x (m)")

    with col2:
        df_tendon = st.data_editor(
            st.session_state.df_tendon,
            num_rows="dynamic",
            key="tendon_editor"
        )

        # ---- CLEAN TENDON ----
        df_tdn = df_tendon.copy()
        df_tdn["Delete"] = df_tdn["Delete"].fillna(False)
        df_tdn = df_tdn[df_tdn["Delete"] == False]

        df_tdn["x (m)"] = pd.to_numeric(df_tdn["x (m)"], errors='coerce')
        df_tdn["z from top (m)"] = pd.to_numeric(df_tdn["z from top (m)"], errors='coerce')

        df_tdn = df_tdn.dropna()
        df_tdn = df_tdn.drop_duplicates(subset="x (m)")
        df_tdn = df_tdn.sort_values("x (m)")

    # ---- PREVIEW ----
    st.subheader("Preview")

    if len(df_thk) >= 2 and len(df_tdn) >= 2:

        x_plot = np.linspace(0, width, 400)

        # Interpolate with pandas
        df_sec = df_thk.set_index("x (m)").reindex(x_plot).interpolate()
        df_ten = df_tdn.set_index("x (m)").reindex(x_plot).interpolate()

        t_interp = df_sec["t (m)"]
        z_interp = df_ten["z from top (m)"]

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

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Need at least 2 valid points")

# ==============================
# TAB 2: LOADS
# ==============================
with tab2:
    st.header("Loads")

    df_load = st.data_editor(
        st.session_state.df_load,
        num_rows="dynamic",
        key="load_editor"
    )

    # ---- CLEAN LOAD ----
    df_ld = df_load.copy()
    df_ld["Delete"] = df_ld["Delete"].fillna(False)
    df_ld = df_ld[df_ld["Delete"] == False]

    for col in df_ld.columns:
        df_ld[col] = pd.to_numeric(df_ld[col], errors='coerce')

    df_ld = df_ld.dropna()
    df_ld = df_ld.drop_duplicates(subset="x (m)")
    df_ld = df_ld.sort_values("x (m)")

    st.write("Clean Data:", df_ld)

    if len(df_ld) >= 2:

        x_plot = np.linspace(0, width, 400)

        df_interp = df_ld.set_index("x (m)").reindex(x_plot).interpolate()

        Mu = 1.25*df_interp["M_DL"] + 1.5*df_interp["M_SDL"] + 1.75*df_interp["M_LL"]
        Vu = 1.25*df_interp["V_DL"] + 1.5*df_interp["V_SDL"] + 1.75*df_interp["V_LL"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x_plot, y=Mu, name="Mu"))
        fig.add_trace(go.Scatter(x=x_plot, y=Vu, name="Vu"))

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Need valid data")
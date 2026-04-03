import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("Prestressed Concrete Box Girder — Top Flange Tendon Design (Phase 1)")

# ==============================
# INIT SESSION STATE
# ==============================
def init_df(name, df):
    if name not in st.session_state:
        st.session_state[name] = df

# ==============================
# TAB SETUP
# ==============================
tab1, tab2, tab3, tab4 = st.tabs(["Section", "Tendon", "Loads", "Visualization"])

# ==============================
# TAB 1: SECTION
# ==============================
with tab1:
    st.header("Section Properties")

    width = st.number_input("Top Flange Width (m)", value=3.0)
    web_thickness = st.number_input("Web Thickness (m)", value=0.5)
    span = st.number_input("Transverse Span (m)", value=3.0)

    init_df("df_thickness", pd.DataFrame({
        "Delete": [False, False],
        "x (m)": [0.0, width],
        "t (m)": [0.25, 0.25]
    }))

    st.subheader("Variable Thickness Input")
    df_thickness = st.data_editor(
        st.session_state.df_thickness,
        num_rows="dynamic",
        key="thickness_editor"
    )

    df_thickness = df_thickness[df_thickness["Delete"] == False]
    st.session_state.df_thickness = df_thickness

# ==============================
# TAB 2: TENDON
# ==============================
with tab2:
    st.header("Tendon Properties")

    strands = st.number_input("Number of Strands", value=8)
    spacing = st.number_input("Spacing between Tendons (m)", value=0.3)

    init_df("df_tendon", pd.DataFrame({
        "Delete": [False, False],
        "x (m)": [0.0, width],
        "z from top (m)": [0.10, 0.10]
    }))

    st.subheader("Tendon Profile")
    df_tendon = st.data_editor(
        st.session_state.df_tendon,
        num_rows="dynamic",
        key="tendon_editor"
    )

    df_tendon = df_tendon[df_tendon["Delete"] == False]
    st.session_state.df_tendon = df_tendon

# ==============================
# TAB 3: LOADS
# ==============================
with tab3:
    st.header("Applied Loads (per 1m strip) — Variable along width")

    init_df("df_load", pd.DataFrame({
        "Delete": [False, False],
        "x (m)": [0.0, width],
        "M_DL": [500.0, 500.0],
        "V_DL": [200.0, 200.0],
        "M_SDL": [200.0, 200.0],
        "V_SDL": [100.0, 100.0],
        "M_LL": [800.0, 800.0],
        "V_LL": [300.0, 300.0],
    }))

    df_load = st.data_editor(
        st.session_state.df_load,
        num_rows="dynamic",
        key="load_editor"
    )

    df_load = df_load[df_load["Delete"] == False]
    st.session_state.df_load = df_load

    if len(df_load) >= 2:

        df_load_clean = df_load.drop(columns=["Delete"]).dropna()

        for col in df_load_clean.columns:
            df_load_clean[col] = pd.to_numeric(df_load_clean[col], errors='coerce')

        df_load_clean = df_load_clean.dropna().sort_values("x (m)")

        if len(df_load_clean) >= 2:

            x_plot = np.linspace(0, width, 100)

            M_DL_i = np.interp(x_plot, df_load_clean["x (m)"], df_load_clean["M_DL"])
            V_DL_i = np.interp(x_plot, df_load_clean["x (m)"], df_load_clean["V_DL"])

            M_SDL_i = np.interp(x_plot, df_load_clean["x (m)"], df_load_clean["M_SDL"])
            V_SDL_i = np.interp(x_plot, df_load_clean["x (m)"], df_load_clean["V_SDL"])

            M_LL_i = np.interp(x_plot, df_load_clean["x (m)"], df_load_clean["M_LL"])
            V_LL_i = np.interp(x_plot, df_load_clean["x (m)"], df_load_clean["V_LL"])

            Mu = 1.25*M_DL_i + 1.50*M_SDL_i + 1.75*M_LL_i
            Vu = 1.25*V_DL_i + 1.50*V_SDL_i + 1.75*V_LL_i

            st.subheader("Load Combination — Strength I")
            st.write("Mu = 1.25·M_DL + 1.50·M_SDL + 1.75·M_LL")
            st.write("Vu = 1.25·V_DL + 1.50·V_SDL + 1.75·V_LL")

            fig_load = go.Figure()
            fig_load.add_trace(go.Scatter(x=x_plot, y=Mu, name="Mu"))
            fig_load.add_trace(go.Scatter(x=x_plot, y=Vu, name="Vu"))

            st.plotly_chart(fig_load, use_container_width=True)

        else:
            st.error("Need at least 2 valid points")

# ==============================
# TAB 4: VISUALIZATION
# ==============================
with tab4:
    st.header("Section & Tendon Visualization")

    df_thickness = st.session_state.df_thickness
    df_tendon = st.session_state.df_tendon

    if len(df_thickness) >= 2 and len(df_tendon) >= 2:

        x = np.linspace(0, width, 100)

        df_thk = df_thickness.drop(columns=["Delete"]).dropna()
        df_thk = df_thk.sort_values("x (m)")

        t_interp = np.interp(x, df_thk["x (m)"], df_thk["t (m)"])

        df_tendon_clean = df_tendon.drop(columns=["Delete"]).dropna()
        df_tendon_clean = df_tendon_clean.sort_values("x (m)")

        z_interp = np.interp(
            x,
            df_tendon_clean["x (m)"],
            df_tendon_clean["z from top (m)"]
        )

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=np.zeros_like(x), name="Top"))
        fig.add_trace(go.Scatter(x=x, y=-t_interp, name="Bottom"))
        fig.add_trace(go.Scatter(x=x, y=-z_interp, name="Tendon"))

        fig.add_vline(x=web_thickness/2)
        fig.add_vline(x=width - web_thickness/2)

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Need at least 2 points")
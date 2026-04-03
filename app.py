import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("Prestressed Concrete Box Girder — Top Flange Tendon Design (Phase 1)")

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
tab1, tab2, tab3, tab4 = st.tabs(["Section", "Tendon", "Loads", "Visualization"])

# ==============================
# TAB 1: SECTION + PREVIEW
# ==============================
with tab1:
    st.header("Section Properties")

    width = st.number_input("Top Flange Width (m)", value=6.0)
    web_thickness = st.number_input("Web Thickness (m)", value=0.5)

    # -------- Thickness --------
    st.subheader("Thickness Input")
    df_thickness = st.data_editor(
        st.session_state.df_thickness,
        num_rows="dynamic",
        key="thickness_editor"
    )

    # -------- Clean Thickness --------
    df_thk = df_thickness.copy()
    df_thk["Delete"] = df_thk["Delete"].fillna(False)
    df_thk = df_thk[df_thk["Delete"] == False]

    df_thk["x (m)"] = pd.to_numeric(df_thk["x (m)"], errors='coerce')
    df_thk["t (m)"] = pd.to_numeric(df_thk["t (m)"], errors='coerce')

    df_thk = df_thk.dropna().sort_values("x (m)")

    # -------- Tendon --------
    st.subheader("Tendon Profile")
    df_tendon = st.data_editor(
        st.session_state.df_tendon,
        num_rows="dynamic",
        key="tendon_editor"
    )

    # -------- Clean Tendon --------
    df_tdn = df_tendon.copy()
    df_tdn["Delete"] = df_tdn["Delete"].fillna(False)
    df_tdn = df_tdn[df_tdn["Delete"] == False]

    df_tdn["x (m)"] = pd.to_numeric(df_tdn["x (m)"], errors='coerce')
    df_tdn["z from top (m)"] = pd.to_numeric(df_tdn["z from top (m)"], errors='coerce')

    df_tdn = df_tdn.dropna().sort_values("x (m)")

    # -------- PREVIEW --------
    st.subheader("🔍 Section + Tendon Preview")

    if len(df_thk) >= 2 and len(df_tdn) >= 2:

        x = np.linspace(0, width, 300)

        t_interp = np.interp(x, df_thk["x (m)"], df_thk["t (m)"])
        z_interp = np.interp(x, df_tdn["x (m)"], df_tdn["z from top (m)"])

        fig = go.Figure()

        fig.add_trace(go.Scatter(x=x, y=np.zeros_like(x), name="Top Surface"))
        fig.add_trace(go.Scatter(x=x, y=-t_interp, name="Bottom Surface"))

        fig.add_trace(go.Scatter(
            x=x,
            y=-z_interp,
            mode='lines',
            name="Tendon",
            line=dict(width=3)
        ))

        fig.add_vline(x=web_thickness/2)
        fig.add_vline(x=width - web_thickness/2)

        fig.update_layout(
            title="Section + Tendon",
            yaxis_title="Depth (m)"
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Enter at least 2 valid points")

# ==============================
# TAB 2: TENDON INFO
# ==============================
with tab2:
    st.header("Tendon Info")
    st.write(df_tdn)

# ==============================
# TAB 3: LOADS
# ==============================
with tab3:
    st.header("Loads")

    df_load = st.data_editor(
        st.session_state.df_load,
        num_rows="dynamic",
        key="load_editor"
    )

    # -------- Clean Load --------
    df_ld = df_load.copy()
    df_ld["Delete"] = df_ld["Delete"].fillna(False)
    df_ld = df_ld[df_ld["Delete"] == False]

    for col in df_ld.columns:
        df_ld[col] = pd.to_numeric(df_ld[col], errors='coerce')

    df_ld = df_ld.dropna().sort_values("x (m)")

    if len(df_ld) >= 2:

        x_plot = np.linspace(0, width, 300)

        Mu = (
            1.25*np.interp(x_plot, df_ld["x (m)"], df_ld["M_DL"]) +
            1.50*np.interp(x_plot, df_ld["x (m)"], df_ld["M_SDL"]) +
            1.75*np.interp(x_plot, df_ld["x (m)"], df_ld["M_LL"])
        )

        Vu = (
            1.25*np.interp(x_plot, df_ld["x (m)"], df_ld["V_DL"]) +
            1.50*np.interp(x_plot, df_ld["x (m)"], df_ld["V_SDL"]) +
            1.75*np.interp(x_plot, df_ld["x (m)"], df_ld["V_LL"])
        )

        st.write("Strength I (AASHTO LRFD)")
        st.write("Mu = 1.25 DL + 1.50 SDL + 1.75 LL")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x_plot, y=Mu, name="Mu"))
        fig.add_trace(go.Scatter(x=x_plot, y=Vu, name="Vu"))

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Need at least 2 valid points")

# ==============================
# TAB 4
# ==============================
with tab4:
    st.header("Visualization")
    st.info("Use Section tab for preview")
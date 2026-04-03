import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("Prestressed Concrete Box Girder — Top Flange Tendon Design (Phase 1)")

# ==============================
# SESSION INIT
# ==============================
def init_df(name, df):
    if name not in st.session_state:
        st.session_state[name] = df

# ==============================
# TAB SETUP
# ==============================
tab1, tab2, tab3, tab4 = st.tabs(["Section", "Tendon", "Loads", "Visualization"])

# ==============================
# TAB 1: SECTION + PREVIEW
# ==============================
with tab1:
    st.header("Section Properties")

    width = st.number_input("Top Flange Width (m)", value=3.0)
    web_thickness = st.number_input("Web Thickness (m)", value=0.5)

    # -------- Thickness Table --------
    init_df("df_thickness", pd.DataFrame({
        "Delete": [False, False],
        "x (m)": [0.0, width],
        "t (m)": [0.25, 0.25]
    }))

    st.subheader("Thickness Input")
    df_thickness = st.data_editor(
        st.session_state.df_thickness,
        num_rows="dynamic",
        key="thickness_editor"
    )

    df_thickness = df_thickness[df_thickness["Delete"] == False]
    st.session_state.df_thickness = df_thickness

    # -------- Tendon Table (Preview ใช้ร่วม) --------
    init_df("df_tendon", pd.DataFrame({
        "Delete": [False, False],
        "x (m)": [0.0, width],
        "z from top (m)": [0.10, 0.10]
    }))

    st.subheader("Tendon Profile (Preview)")
    df_tendon = st.data_editor(
        st.session_state.df_tendon,
        num_rows="dynamic",
        key="tendon_editor_section"
    )

    df_tendon = df_tendon[df_tendon["Delete"] == False]
    st.session_state.df_tendon = df_tendon

    # -------- PREVIEW --------
    st.subheader("🔍 Section + Tendon Preview")

    if len(df_thickness) >= 2 and len(df_tendon) >= 2:

        x = np.linspace(0, width, 100)

        # --- Thickness ---
        df_thk = df_thickness.drop(columns=["Delete"], errors="ignore").dropna()
        df_thk["x (m)"] = pd.to_numeric(df_thk["x (m)"], errors='coerce')
        df_thk["t (m)"] = pd.to_numeric(df_thk["t (m)"], errors='coerce')
        df_thk = df_thk.dropna().sort_values("x (m)")

        # --- Tendon ---
        df_tdn = df_tendon.drop(columns=["Delete"], errors="ignore").dropna()
        df_tdn["x (m)"] = pd.to_numeric(df_tdn["x (m)"], errors='coerce')
        df_tdn["z from top (m)"] = pd.to_numeric(df_tdn["z from top (m)"], errors='coerce')
        df_tdn = df_tdn.dropna().sort_values("x (m)")

        if len(df_thk) >= 2 and len(df_tdn) >= 2:

            t_interp = np.interp(x, df_thk["x (m)"], df_thk["t (m)"])
            z_interp = np.interp(x, df_tdn["x (m)"], df_tdn["z from top (m)"])

            fig = go.Figure()

            # Top
            fig.add_trace(go.Scatter(x=x, y=np.zeros_like(x), name="Top Surface"))

            # Bottom
            fig.add_trace(go.Scatter(x=x, y=-t_interp, name="Bottom Surface"))

            # Tendon
            fig.add_trace(go.Scatter(
                x=x,
                y=-z_interp,
                mode='lines',
                name="Tendon Profile",
                line=dict(width=3)
            ))

            # Webs
            fig.add_vline(x=web_thickness/2)
            fig.add_vline(x=width - web_thickness/2)

            fig.update_layout(
                title="Section + Tendon",
                yaxis_title="Depth (m)"
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("Need valid numeric input")

    else:
        st.info("Enter at least 2 points")

# ==============================
# TAB 2: TENDON (MAIN)
# ==============================
with tab2:
    st.header("Tendon Design Input")

    strands = st.number_input("Number of Strands", value=8)
    spacing = st.number_input("Spacing (m)", value=0.3)

    df_tendon = st.session_state.df_tendon

    st.write(df_tendon)

# ==============================
# TAB 3: LOADS
# ==============================
with tab3:
    st.header("Loads")

    init_df("df_load", pd.DataFrame({
        "Delete": [False, False],
        "x (m)": [0.0, width],
        "M_DL": [500, 500],
        "V_DL": [200, 200],
        "M_SDL": [200, 200],
        "V_SDL": [100, 100],
        "M_LL": [800, 800],
        "V_LL": [300, 300],
    }))

    df_load = st.data_editor(
        st.session_state.df_load,
        num_rows="dynamic",
        key="load_editor"
    )

    df_load = df_load[df_load["Delete"] == False]
    st.session_state.df_load = df_load

    if len(df_load) >= 2:

        df = df_load.drop(columns=["Delete"]).dropna()
        df = df.sort_values("x (m)")

        x_plot = np.linspace(0, width, 100)

        Mu = 1.25*np.interp(x_plot, df["x (m)"], df["M_DL"]) + \
             1.50*np.interp(x_plot, df["x (m)"], df["M_SDL"]) + \
             1.75*np.interp(x_plot, df["x (m)"], df["M_LL"])

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x_plot, y=Mu, name="Mu"))

        st.plotly_chart(fig)

# ==============================
# TAB 4: VISUALIZATION
# ==============================
with tab4:
    st.header("Advanced Visualization")

    st.info("Use Section Tab for real-time preview")
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("Prestressed Concrete Box Girder — Top Flange Tendon Design (Phase 1)")

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

    st.subheader("Variable Thickness Input")
    df_thickness = st.data_editor(
        pd.DataFrame({"x (m)": [0.0, width], "t (m)": [0.25, 0.25]}),
        num_rows="dynamic"
    )

# ==============================
# TAB 2: TENDON
# ==============================
with tab2:
    st.header("Tendon Properties")

    strands = st.number_input("Number of Strands", value=8)
    spacing = st.number_input("Spacing between Tendons (m)", value=0.3)

    st.subheader("Tendon Profile")
    df_tendon = st.data_editor(
        pd.DataFrame({"x (m)": [0.0, width], "z from top (m)": [0.10, 0.10]}),
        num_rows="dynamic"
    )

# ==============================
# TAB 3: LOADS
# ==============================
with tab3:
    st.header("Applied Loads (per 1m strip) — Variable along width")

    st.write("Input M and V along transverse direction (x)")

    df_load = st.data_editor(
        pd.DataFrame({
            "x (m)": [0.0, width],
            "M_DL": [500.0, 500.0],
            "V_DL": [200.0, 200.0],
            "M_SDL": [200.0, 200.0],
            "V_SDL": [100.0, 100.0],
            "M_LL": [800.0, 800.0],
            "V_LL": [300.0, 300.0],
        }),
        num_rows="dynamic"
    )

    if len(df_load) >= 2:

        x_plot = np.linspace(0, width, 100)

        # Interpolation
        M_DL_i = np.interp(x_plot, df_load["x (m)"], df_load["M_DL"])
        V_DL_i = np.interp(x_plot, df_load["x (m)"], df_load["V_DL"])

        M_SDL_i = np.interp(x_plot, df_load["x (m)"], df_load["M_SDL"])
        V_SDL_i = np.interp(x_plot, df_load["x (m)"], df_load["V_SDL"])

        M_LL_i = np.interp(x_plot, df_load["x (m)"], df_load["M_LL"])
        V_LL_i = np.interp(x_plot, df_load["x (m)"], df_load["V_LL"])

        # Strength I Combination
        Mu = 1.25*M_DL_i + 1.50*M_SDL_i + 1.75*M_LL_i
        Vu = 1.25*V_DL_i + 1.50*V_SDL_i + 1.75*V_LL_i

        st.subheader("Load Combination — Strength I (AASHTO LRFD)")

        st.write("Mu = 1.25·M_DL + 1.50·M_SDL + 1.75·M_LL")
        st.write("Vu = 1.25·V_DL + 1.50·V_SDL + 1.75·V_LL")

        st.write("Reference: AASHTO LRFD Table 3.4.1-1")

        # Plot
        fig_load = go.Figure()

        fig_load.add_trace(go.Scatter(x=x_plot, y=Mu, name="Mu (kN·m/m)"))
        fig_load.add_trace(go.Scatter(x=x_plot, y=Vu, name="Vu (kN/m)"))

        fig_load.update_layout(title="Strength I — Load Distribution")

        st.plotly_chart(fig_load, use_container_width=True)

    else:
        st.warning("Please input at least two points.")

# ==============================
# TAB 4: VISUALIZATION
# ==============================
with tab4:
    st.header("Section & Tendon Visualization")

    if len(df_thickness) >= 2 and len(df_tendon) >= 2:

        x = np.linspace(0, width, 100)

        # Interpolate thickness
        t_interp = np.interp(x, df_thickness["x (m)"], df_thickness["t (m)"])

        # Interpolate tendon
        z_interp = np.interp(x, df_tendon["x (m)"], df_tendon["z from top (m)"])

        fig = go.Figure()

        # Top surface
        fig.add_trace(go.Scatter(x=x, y=np.zeros_like(x), name="Top Surface"))

        # Bottom surface
        fig.add_trace(go.Scatter(x=x, y=-t_interp, name="Bottom Surface"))

        # Tendon
        fig.add_trace(go.Scatter(x=x, y=-z_interp, mode='lines', name="Tendon Profile"))

        # Webs
        fig.add_vline(x=web_thickness/2)
        fig.add_vline(x=width - web_thickness/2)

        fig.update_layout(title="Cross Section", yaxis_title="Depth (m)")

        st.plotly_chart(fig, use_container_width=True)

        # Dummy flexural capacity (placeholder)
        phiMn = np.ones_like(x) * Mu * 1.2

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=x, y=phiMn, name="φMn"))
        fig2.add_trace(go.Scatter(x=x, y=np.ones_like(x)*Mu, name="Mu"))

        fig2.update_layout(title="Flexural Check")

        st.plotly_chart(fig2, use_container_width=True)

    else:
        st.warning("Please input at least two points for thickness and tendon profile.")

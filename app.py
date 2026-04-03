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
    st.header("Applied Loads (per 1m strip)")

    M_DL = st.number_input("M_DL (kN·m/m)", value=500.0)
    V_DL = st.number_input("V_DL (kN/m)", value=200.0)

    M_SDL = st.number_input("M_SDL (kN·m/m)", value=200.0)
    V_SDL = st.number_input("V_SDL (kN/m)", value=100.0)

    M_LL = st.number_input("M_LL (kN·m/m)", value=800.0)
    V_LL = st.number_input("V_LL (kN/m)", value=300.0)

    # Load combinations
    Mu = 1.25*M_DL + 1.5*M_SDL + 1.75*M_LL
    Vu = 1.25*V_DL + 1.5*V_SDL + 1.75*V_LL

    st.write(f"**Mu (Strength I)** = {Mu:.2f} kN·m/m")
    st.write(f"**Vu (Strength I)** = {Vu:.2f} kN/m")

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

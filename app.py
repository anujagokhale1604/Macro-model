import streamlit as st

st.set_page_config(page_title="MAS Terminal v5.0")

# THE SIDEBAR TEST
st.sidebar.title("🏛️ SURVEILLANCE TERMINAL V5")
st.sidebar.write("If you see this, the update is LIVE.")

# FX TOGGLES MENTIONED IN RESUME
fx_shock = st.sidebar.slider("Simulate FX Shock (%)", 0.0, 20.0, 0.0)
fx_beta = st.sidebar.slider("FX Pass-Through (Beta)", 0.0, 1.0, 0.2)

st.title("Monetary Policy & FX Surveillance")
st.write(f"Current FX Shock Simulation: {fx_shock}%")
st.write("This version proves the sidebar link is working.")

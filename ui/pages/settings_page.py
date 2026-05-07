# ui/pages/settings_page.py
import streamlit as st

def render(ctx: dict) -> None:
    st.title("⚙️ Settings")
    st.write("System configuration.")

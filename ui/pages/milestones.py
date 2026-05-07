# ui/pages/milestones.py
import streamlit as st

def render(ctx: dict) -> None:
    st.title("🚩 Milestones")
    st.write(ctx["milestones"])

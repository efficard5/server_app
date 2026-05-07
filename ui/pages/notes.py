# ui/pages/notes.py
import streamlit as st

def render(ctx: dict) -> None:
    st.title("📓 Project Notes")
    st.write(ctx["notes_db"])

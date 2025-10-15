# utils/state.py
import streamlit as st

def init_session_state():
    defaults = {
        "token": None,
        "authenticated": False,
        "user_data": {},
        "pipeline_data": {},
        "report_data": {},
        "pipeline_runs": []
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

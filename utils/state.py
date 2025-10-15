import streamlit as st

def init_session_state():
    """
    Initialize all default Streamlit session state variables safely.
    This function is idempotent — it only sets defaults for missing keys,
    so user session data (e.g., updated_df, user_data) isn't lost across reruns.
    """

    defaults = {
        # Auth
        "token": None,
        "authenticated": False,
        "user_data": {},

        # Data pipeline
        "pipeline_data": {},
        "pipeline_runs": [],

        # Reports and generated data
        "report_data": {},

        # Upload data page persistence
        "updated_df": None,
        "last_uploaded_file": None,
        "assignments_applied": False,
    }

    # Only add missing keys without overwriting existing data
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

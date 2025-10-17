import streamlit as st
import pandas as pd
from utils.api import get_pipeline_runs, get_pipeline_data

def query_pipeline_data(selected_run_id: str = None):
    """
    Shared function to fetch and cache pipeline data.
    Handles fetching pipeline runs, caching data in session_state, and progress display.

    Returns:
        (df, run_options, selected_run_id)
    """

    # --- Ensure pipeline runs are available ---
    if not st.session_state.get("pipeline_runs"):
        with st.spinner("Fetching available pipeline runs..."):
            get_pipeline_runs()

    runs = st.session_state.get("pipeline_runs", [])
    if not runs:
        st.error("No pipeline runs found.")
        return None, {}, None

    # --- Prepare run selection dropdown ---
    run_options = {
        run.get("id", str(i)): f"{run.get('run_name', 'Unknown')} ({run.get('id', 'N/A')})"
        for i, run in enumerate(runs)
    }

    # If not provided, ask user to select
    if not selected_run_id:
        selected_run_id = st.selectbox(
            "Select Pipeline Run",
            options=list(run_options.keys()),
            format_func=lambda x: run_options[x],
            index=0 if run_options else None
        )

    # --- Fetch data if new run or not cached ---
    if (
        st.button("Fetch Data") or
        st.session_state.get("current_run_id") != selected_run_id or
        "queried_data" not in st.session_state
    ):
        with st.spinner(f"Fetching data for run ID: {selected_run_id}..."):
            data = get_pipeline_data(selected_run_id)

        if not data:
            st.warning("No data found for this pipeline run.")
            st.session_state.queried_data = None
            st.session_state.current_run_id = None
            return None, run_options, selected_run_id

        df = pd.DataFrame(data)
        st.session_state.queried_data = df
        st.session_state.current_run_id = selected_run_id

    else:
        df = st.session_state.get("queried_data")

    return df, run_options, selected_run_id

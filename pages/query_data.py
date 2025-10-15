import streamlit as st
import pandas as pd
from utils.api import get_pipeline_runs
from utils.visualizations import status_distribution

def query_data_page():
    st.header("Query Pipeline Data")
    if not st.session_state.pipeline_runs:
        get_pipeline_runs()

    if not st.session_state.pipeline_runs:
        st.error("No pipeline runs found.")
        return

    run_options = {run.get('id', str(i)): run.get('run_name', 'Unknown') for i, run in enumerate(st.session_state.pipeline_runs)}
    selected_run_id = st.selectbox("Select Pipeline Run", options=list(run_options.keys()), format_func=lambda x: run_options[x])

    if selected_run_id in st.session_state.pipeline_data:
        df = pd.DataFrame(st.session_state.pipeline_data[selected_run_id])
        tab1, tab2 = st.tabs(["Data", "Visualizations"])
        with tab1:
            st.dataframe(df)
        with tab2:
            status_distribution(df)

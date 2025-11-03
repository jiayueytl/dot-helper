import streamlit as st
import pandas as pd
from utils.api import get_users
from utils.reports import generate_report
from utils.state import init_session_state

# init_session_state()

def dashboard_page():
    st.header("Dashboard")
    if not st.session_state.user_data:
        get_users()
        # st.write(st.session_state.user_data)
        st.write(st.session_state.token)
    st.success(f"{len(st.session_state.user_data)} users loaded.")
    for run_id, data in st.session_state.pipeline_data.items():
        with st.expander(f"Run ID: {run_id}"):
            df = pd.DataFrame(data)
            st.dataframe(df.head())
            report = generate_report(data)
            if not report.empty:
                st.subheader("Status Report")
                st.dataframe(report)

# TODO: Stratified processing
# TODO: Recycle questions = get the undone + new + upload to dataset
import streamlit as st
from utils.reports import generate_report
from datetime import datetime
import pandas as pd

def reports_page():
    st.header("Generate Reports")
    if not st.session_state.pipeline_data:
        st.info("No pipeline data available. Query data first.")
        return

    run_id = st.selectbox("Select Run ID", list(st.session_state.pipeline_data.keys()))
    data = st.session_state.pipeline_data[run_id]
    report = generate_report(data)
    if report.empty:
        st.warning("No data available for report.")
        return

    st.dataframe(report)
    csv = report.to_csv(index=False)
    st.download_button("Download Report", data=csv, file_name=f"report_{run_id}_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

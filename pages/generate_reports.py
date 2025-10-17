import streamlit as st
import pandas as pd
from datetime import datetime
from utils.reports import generate_report
from utils.pipeline_data import query_pipeline_data
from utils.state import init_session_state

init_session_state()

def reports_page():
    st.header("📊 Generate Project Reports")

    # --- Shared data fetch ---
    df, run_options, selected_run_id = query_pipeline_data()

    if df is None or df.empty:
        st.info("No pipeline data found.")
        return

    # --- Generate Report ---
    report = generate_report(df)
    if report.empty:
        st.warning("No report data available.")
        return

    # --- Display + Download ---
    st.subheader("🧾 Report Summary")
    st.dataframe(report)

    csv = report.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ Download Report",
        data=csv,
        file_name=f"report_{selected_run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

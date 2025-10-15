import streamlit as st
import pandas as pd
from datetime import datetime
from utils.data_processing import filter_undone_questions, assign_questions_by_capacity, csv_to_json_zip
from utils.api import upload_zip_file

def recycle_page():
    st.header("Recycle Undone Questions")
    if not st.session_state.pipeline_data:
        st.info("No pipeline data loaded yet.")
        return

    run_id = st.selectbox("Select Pipeline Run", list(st.session_state.pipeline_data.keys()))
    data = st.session_state.pipeline_data[run_id]
    undone = filter_undone_questions(data)
    st.write(f"Found {len(undone)} undone questions.")

    if not undone:
        return

    df = pd.DataFrame(undone)
    st.dataframe(df)

    cap_file = st.file_uploader("Upload Capacity CSV", type=["csv"])
    if not cap_file:
        return

    cap_df = pd.read_csv(cap_file)
    st.dataframe(cap_df)

    if st.button("Assign and Upload"):
        assigned = assign_questions_by_capacity(undone, cap_df)
        new_name = f"recycled_{run_id}_{datetime.now().strftime('%Y%m%d')}"
        zip_file = csv_to_json_zip(pd.DataFrame(assigned))
        upload_zip_file(zip_file, f"recycled_{run_id}", new_name)

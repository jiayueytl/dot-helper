import pandas as pd
import streamlit as st
from config import COMPLETED_STATUS, INCOMPLETE_STATUS, QA_DONE_STATUS

def generate_report(data):
    """Return simple completion report from pipeline data."""
    if data is None or (isinstance(data, pd.DataFrame) and data.empty):
        st.warning("No data provided.")
        return pd.DataFrame()
    
    # If data is not a DataFrame yet, convert it
    if not isinstance(data, pd.DataFrame):
        df = pd.DataFrame(data)
    else:
        df = data

    if 'status' not in df.columns:
        st.warning("No 'status' column found.")
        return pd.DataFrame()

    counts = df['status'].value_counts().reset_index()
    counts.columns = ['Status', 'Count']
    total = counts['Count'].sum()

    if 'annotation_complete' in counts['Status'].values:
        completed = counts.loc[counts['Status'] == 'annotation_complete', 'Count'].iloc[0]
        counts.loc[len(counts)] = ['Completion %', round((completed / total) * 100, 2)]

    return counts

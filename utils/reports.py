import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

def generate_report(data):
    """Return simple completion report from pipeline data."""
    if not data: 
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if 'status' not in df.columns:
        st.warning("No 'status' column found.")
        return pd.DataFrame()
    counts = df['status'].value_counts().reset_index()
    counts.columns = ['Status', 'Count']
    total = counts['Count'].sum()
    if 'completed' in counts['Status'].values:
        completed = counts.loc[counts['Status'] == 'completed', 'Count'].iloc[0]
        counts.loc[len(counts)] = ['Completion %', round((completed/total)*100, 2)]
    return counts

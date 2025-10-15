import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

def status_distribution(df):
    counts = df['status'].value_counts().reset_index()
    counts.columns = ['Status', 'Count']
    fig, ax = plt.subplots(figsize=(10,6))
    sns.barplot(x='Status', y='Count', data=counts, ax=ax)
    ax.set_title("Status Distribution")
    st.pyplot(fig)
    st.dataframe(counts)

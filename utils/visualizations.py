import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from utils.api import get_users
from config import COMPLETED_STATUS, INCOMPLETE_STATUS, QA_DONE_STATUS,USABLE_COLUMNS

def status_distribution(df):
    counts = df['status'].value_counts().reset_index()
    counts.columns = ['Status', 'Count']
    fig, ax = plt.subplots(figsize=(10,6))
    sns.barplot(x='Status', y='Count', data=counts, ax=ax)
    ax.set_title("Status Distribution")
    st.pyplot(fig)
    st.dataframe(counts)

def create_visualizations(df: pd.DataFrame):
    """Create data visualizations based on the pipeline data."""
    # Define completed status
    # completed_status = ["annotation_complete", "ready_for_qa", "qa_approved"]
    
    # 1. Group by status
    st.subheader("1. Status Distribution")
    status_counts = df['status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']
    
    # Create bar chart for status distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x='Status', y='Count', data=status_counts, ax=ax)
    ax.set_title('Status Distribution')
    ax.set_xlabel('Status')
    ax.set_ylabel('Count')
    plt.xticks(rotation=45)
    st.pyplot(fig)
    
    # Display the data table
    st.dataframe(status_counts)
    
    # 2. Completion rate by assignee_name
    st.subheader("2. Completion Rate by Assignee")
    if 'assignee' in df.columns or 'assignee_name' in df.columns:
        # Get user data if not already fetched
        if not st.session_state.user_data:
            with st.spinner("Fetching user data..."):
                get_users()
        
        # Create a reverse mapping from user ID to username
        username_to_id = {v: k for k, v in st.session_state.user_data.items()}
        
        # Map assignee IDs to usernames
        df['assignee_name'] = df['assignee'].map(lambda x: username_to_id.get(x, "Unknown"))

        # st.write(username_to_id)
        
        # Filter for completed status
        completed_df = df[df['status'].isin(COMPLETED_STATUS)]
        
        # Count completed by assignee
        assignee_completion = completed_df['assignee_name'].value_counts().reset_index()
        assignee_completion.columns = ['Assignee', 'Completed Count']
        
        # Get total assigned to each assignee
        total_assigned = df['assignee_name'].value_counts().reset_index()
        total_assigned.columns = ['Assignee', 'Total Assigned']
        
        # Merge to calculate completion rate
        completion_rate = pd.merge(assignee_completion, total_assigned, on='Assignee')
        completion_rate['Completion Rate (%)'] = (completion_rate['Completed Count'] / completion_rate['Total Assigned'] * 100).round(2)
        
        # Create bar chart for completion rate
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(x='Assignee', y='Completion Rate (%)', data=completion_rate, ax=ax)
        ax.set_title('Completion Rate by Assignee')
        ax.set_xlabel('Assignee')
        ax.set_ylabel('Completion Rate (%)')
        plt.xticks(rotation=45)
        st.pyplot(fig)
        
        # Display the data table
        st.dataframe(completion_rate)
    else:
        st.warning("No assignee column found in data")
    
    # 3. Rewrite rates
    st.subheader("3. Rewrite Rates")
    
    # Calculate answer rewrite rate
    total_records = len(df)
    empty_indicators = {'nan', '', 'None'}
    answer_rewrites = (~df['corrected_answer'].astype(str).isin(empty_indicators)).sum()
    answer_rewrite_rate = (answer_rewrites / total_records * 100).round(2)
    
    # Calculate question rewrite rate
    question_rewrites = (~df['corrected_question'].astype(str).isin(empty_indicators)).sum()
    question_rewrite_rate = (question_rewrites / total_records * 100).round(2)
    
    # Display metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Answer Rewrite Rate", f"{answer_rewrite_rate}%", f"{answer_rewrites}/{total_records} records")
    with col2:
        st.metric("Question Rewrite Rate", f"{question_rewrite_rate}%", f"{question_rewrites}/{total_records} records")
    
    # Create a simple bar chart for rewrite rates
    rewrite_data = pd.DataFrame({
        'Type': ['Answer', 'Question'],
        'Rewrite Rate (%)': [answer_rewrite_rate, question_rewrite_rate]
    })
    
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(x='Type', y='Rewrite Rate (%)', data=rewrite_data, ax=ax)
    ax.set_title('Rewrite Rates')
    ax.set_xlabel('Type')
    ax.set_ylabel('Rewrite Rate (%)')
    st.pyplot(fig)
    
    # 4. QA rates
    st.subheader("4. QA Rates by Reviewer")
    if 'reviewer' in df.columns:
        # Filter for QA approved status
        qa_approved_df = df[df['status'].isin(QA_DONE_STATUS)]
        
        # Count QA approved by reviewer
        reviewer_qa = qa_approved_df['reviewer'].value_counts().reset_index()
        reviewer_qa.columns = ['Reviewer', 'QA Approved Count']
        
        # Create a reverse mapping from user ID to username
        id_to_username = {v: k for k, v in st.session_state.user_data.items()}
        
        # Map reviewer IDs to usernames
        reviewer_qa['Reviewer Name'] = reviewer_qa['Reviewer'].map(lambda x: id_to_username.get(x, "Unknown"))
        
        # Create bar chart for QA rates
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(x='Reviewer Name', y='QA Approved Count', data=reviewer_qa, ax=ax)
        ax.set_title('QA Approved Count by Reviewer')
        ax.set_xlabel('Reviewer')
        ax.set_ylabel('QA Approved Count')
        plt.xticks(rotation=45)
        st.pyplot(fig)
        
        # Display the data table
        st.dataframe(reviewer_qa[['Reviewer Name', 'QA Approved Count']])
    else:
        st.warning("No reviewer column found in data")

    
    # --- Basic Annotation Data Distribution ---
    st.subheader("5. Basic Annotation Data Distribution")
    st.info("Charts below show distribution (count by 'uuid') for all configured USABLE_COLUMNS within COMPLETED Data")
    # st.metric("Completed Count", f"{answer_rewrite_rate}%", f"{answer_rewrites}/{total_records} records")
    # Only proceed if there are usable columns present in the dataframe
    usable_cols = [col for col in USABLE_COLUMNS if col in completed_df.columns]

    if len(usable_cols) == 0:
        st.warning("No USABLE_COLUMNS found in the current dataframe.")
    else:
        cols_per_row = 2
        n_rows = (len(usable_cols) + cols_per_row - 1) // cols_per_row

        for i in range(n_rows):
            chart_cols = usable_cols[i * cols_per_row : (i + 1) * cols_per_row]
            st_cols = st.columns(len(chart_cols))

            for st_col, col_name in zip(st_cols, chart_cols):
                with st_col:
                    st.markdown(f"**📊 {col_name} Distribution**")

                    try:
                        # Group by column and count unique uuids
                        chart_df = (
                            completed_df.groupby(col_name)["uuid"]
                            .nunique()
                            .reset_index()
                            .rename(columns={"uuid": "count"})
                            .sort_values("count", ascending=False)
                        )

                        # Use built-in Streamlit bar chart
                        st.bar_chart(chart_df, x=col_name, y="count", use_container_width=True)

                        # Add data labels (Streamlit native chart doesn’t directly support labels)
                        # So show as small table below chart
                        st.dataframe(chart_df, use_container_width=True, hide_index=True)

                    except Exception as e:
                        st.error(f"Could not plot for column '{col_name}': {e}")


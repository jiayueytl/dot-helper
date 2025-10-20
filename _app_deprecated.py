import streamlit as st
import pandas as pd
import requests
import json
import zipfile
import io
from datetime import datetime
import os
import base64
from typing import Dict, List, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration
API_BASE_URL = "https://dot.ytlailabs.tech"
PREFIX = "LF"
SFT_ROUND = "SFT-LF"

# Initialize session state
if 'token' not in st.session_state:
    st.session_state.token = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_data' not in st.session_state:
    st.session_state.user_data = {}
if 'pipeline_data' not in st.session_state:
    st.session_state.pipeline_data = {}
if 'report_data' not in st.session_state:
    st.session_state.report_data = {}
if 'pipeline_runs' not in st.session_state:
    st.session_state.pipeline_runs = []

# Helper functions
def login(username: str, password: str) -> bool:
    """Authenticate with the API and get a token."""
    try:
        # The API expects form data, not JSON. Use the `data` parameter
        # to send the payload as application/x-www-form-urlencoded.
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/token",
            data={"grant_type":"password","username": username, "password": password}
        )
        if response.status_code == 200:
            st.session_state.token = response.json().get("access_token")
            st.session_state.authenticated = True
            return True
        else:
            st.error(f"Login failed: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error during login: {str(e)}")
        return False

def get_users() -> Dict[str, str]:
    """Get all users and return a mapping of username to user ID."""
    if not st.session_state.token:
        st.error("Please login first")
        return {}
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(
            f"{API_BASE_URL}/api/v1/users",
            headers=headers
        )
        if response.status_code == 200:
            users = response.json()
            # Create mapping of username to user ID
            user_map = {user["username"]: user["id"] for user in users}
            st.session_state.user_data = user_map
            return user_map
        else:
            st.error(f"Failed to get users: {response.text}")
            return {}
    except Exception as e:
        st.error(f"Error getting users: {str(e)}")
        return {}

def upload_zip_file(zip_file: io.BytesIO, run_id: str, name: str) -> bool:
    """Upload a zip file to the platform."""
    if not st.session_state.token:
        st.error("Please login first")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        files = {"file": (f"{name}.zip", zip_file, "application/zip")}
        data = {"run_id": run_id, "run_name": name,"modality":"text","data_type":"sft"}
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/data_v2/upload",
            headers=headers,
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            st.success(f"Successfully uploaded {name} with run ID: {run_id}")
            return True
        else:
            st.error(f"Upload failed: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error during upload: {str(e)}")
        return False

def get_pipeline_runs() -> List[Dict]:
    """Get all available pipeline runs."""
    if not st.session_state.token:
        st.error("Please login first")
        return []
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(
            f"{API_BASE_URL}/api/v1/data_v2/pipeline",
            headers=headers
        )
        
        if response.status_code == 200:
            runs = response.json()
            st.session_state.pipeline_runs = runs
            return runs
        else:
            st.error(f"Failed to get pipeline runs: {response.text}")
            return []
    except Exception as e:
        st.error(f"Error getting pipeline runs: {str(e)}")
        return []

def get_pipeline_data(pipeline_run_id: str) -> List[Dict]:
    """Get all data from a pipeline run, handling pagination."""
    if not st.session_state.token:
        st.error("Please login first")
        return []
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        all_data = []
        page = 1
        total_pages = 1
        
        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while page <= total_pages:
            # Update status
            status_text.text(f"Fetching page {page} of {total_pages}...")
            
            # Make request for current page
            response = requests.get(
                f"{API_BASE_URL}/api/v1/data_v2/pipeline/{pipeline_run_id}/data",
                headers=headers,
                params={"page": page}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Update total_pages from the first response
                if page == 1:
                    total_pages = result.get("total_pages", 1)
                    total_rows = result.get("total_rows", 0)
                    st.info(f"Found {total_rows} records across {total_pages} pages")
                
                # Add data from current page
                page_data = result.get("data", [])
                all_data.extend(page_data)
                
                # Update progress
                progress = page / total_pages
                progress_bar.progress(progress)
                
                # Move to next page
                page += 1
            else:
                st.error(f"Failed to get pipeline data for page {page}: {response.text}")
                break
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Store all data in session state
        st.session_state.pipeline_data[pipeline_run_id] = all_data
        
        # Show success message
        st.success(f"Successfully fetched {len(all_data)} records")
        
        return all_data
    except Exception as e:
        st.error(f"Error getting pipeline data: {str(e)}")
        return []

def bulk_update_pipeline(pipeline_run_id: str, update_data: Dict) -> bool:
    """Bulk update pipeline data."""
    if not st.session_state.token:
        st.error("Please login first")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.post(
            f"{API_BASE_URL}/api/v1/data_v2/pipeline/{pipeline_run_id}/bulk-update",
            headers=headers,
            json=update_data
        )
        
        if response.status_code == 200:
            st.success("Bulk update successful")
            return True
        else:
            st.error(f"Bulk update failed: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error during bulk update: {str(e)}")
        return False

def csv_to_json_zip(df: pd.DataFrame) -> io.BytesIO:
    """Convert a DataFrame to JSON and create a zip file."""
    # Convert DataFrame to JSON
    json_data = df.to_json(orient='records')
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("data.json", json_data)
    
    zip_buffer.seek(0)
    return zip_buffer

def generate_report(data: List[Dict]) -> pd.DataFrame:
    """Generate a daily report from pipeline data."""
    if not data:
        return pd.DataFrame()
    
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(data)
    
    # Create report based on status
    if 'status' in df.columns:
        status_counts = df['status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        
        # Add completion percentage
        total = status_counts['Count'].sum()
        if 'completed' in status_counts['Status'].values:
            completed = status_counts[status_counts['Status'] == 'completed']['Count'].iloc[0]
            status_counts.loc[len(status_counts)] = ['Completion %', round((completed/total)*100, 2)]
        
        return status_counts
    else:
        st.warning("No status column found in data")
        return pd.DataFrame()

def filter_undone_questions(data: List[Dict]) -> List[Dict]:
    """Filter out questions that are not done."""
    return [item for item in data if item.get('status') != 'completed']

def assign_questions_by_capacity(questions: List[Dict], capacity_df: pd.DataFrame) -> List[Dict]:
    """Assign questions to users based on capacity."""
    if not questions or capacity_df.empty:
        return questions
    
    # Create a mapping of user ID to capacity
    capacity_map = {}
    for _, row in capacity_df.iterrows():
        user_id = row.get('user_id')
        capacity = row.get('capacity', 0)
        if user_id:
            capacity_map[user_id] = capacity
    
    # Assign questions based on capacity
    assigned_questions = []
    user_load = {user_id: 0 for user_id in capacity_map}
    
    for question in questions:
        # Find user with minimum load who still has capacity
        available_users = [
            user_id for user_id, capacity in capacity_map.items()
            if user_load[user_id] < capacity
        ]
        
        if available_users:
            # Sort users by current load
            available_users.sort(key=lambda x: user_load[x])
            assigned_user = available_users[0]
            
            # Update question with assignee
            question['assignee_id'] = assigned_user
            user_load[assigned_user] += 1
        
        assigned_questions.append(question)
    
    return assigned_questions

def create_visualizations(df: pd.DataFrame):
    """Create data visualizations based on the pipeline data."""
    # Define completed status
    completed_status = ["annotation_complete", "ready_for_qa", "qa_approved"]
    
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
    if 'assignee_name' in df.columns:
        # Get user data if not already fetched
        if not st.session_state.user_data:
            with st.spinner("Fetching user data..."):
                get_users()
        
        # # Create a reverse mapping from user ID to username
        # id_to_username = {v: k for k, v in st.session_state.user_data.items()}
        
        # Map assignee IDs to usernames
        # df['assignee_name'] = df['assignee'].map(lambda x: id_to_username.get(x, "Unknown"))
        
        # Filter for completed status
        completed_df = df[df['status'] == 'annotation_complete']
        
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
        qa_approved_df = df[df['status'] == 'qa_approved']
        
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
        
# Main app
def main():
    st.set_page_config(
        page_title="Data Pipeline Management",
        page_icon="📊",
        layout="wide"
    )
    
    # Login page
    if not st.session_state.authenticated:
        st.title("Login to Data Pipeline Management")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if login(username, password):
                    st.success("Login successful!")
                    st.rerun()
        
        return
    
    # Main app after login
    st.title("Data Pipeline Management")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Select a page",
        ["Dashboard", "Upload Data", "Query Data", "Generate Reports", "Recycle Questions"]
    )
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.token = None
        st.rerun()
    
    # Dashboard page
    if page == "Dashboard":
        st.header("Dashboard")
        
        # Get users if not already fetched
        if not st.session_state.user_data:
            with st.spinner("Fetching user data..."):
                get_users()
        
        if st.session_state.user_data:
            st.success(f"Successfully loaded {len(st.session_state.user_data)} users")
        
        # Display pipeline data summary
        if st.session_state.pipeline_data:
            st.subheader("Pipeline Data Summary")
            for run_id, data in st.session_state.pipeline_data.items():
                with st.expander(f"Run ID: {run_id}"):
                    df = pd.DataFrame(data)
                    st.dataframe(df.head())
                    
                    # Generate report
                    report_df = generate_report(data)
                    if not report_df.empty:
                        st.subheader("Status Report")
                        st.dataframe(report_df)
    
    # Upload Data page
    elif page == "Upload Data":
        st.header("Upload Data")
        base_columns = ['original_id', 'sft_round', 'question', 'answer', 
                            'reason', 'task', 'domain', 'metadata', 'ann_status', 'data_status', 'is_drop', 
                            'is_annotated', 'is_valid', 'assigned', 'assignee_name','assignee']
        
        # Step 1: Upload enriched CSV
        st.subheader("Step 1: Upload Enriched CSV")
        csv_file = st.file_uploader("Upload your enriched CSV file", type=["csv"])
        
        if csv_file:
            df = pd.read_csv(csv_file)
            df["original_id"] = df["original_id"] if "original_id" in df.columns else PREFIX + (df.index + 1).astype(str).str.zfill(5)
            df["sft_round"] = SFT_ROUND
            df["question"] = df["prompt"] if "prompt" in df.columns else df['question']
            df["answer"] = df["response"] if "response" in df.columns else df['answer']
            df["reason"] = df["reason"] if "reason" in df.columns else df['rendered_history']
            df["domain"] = df["domain"] if "domain" in df.columns else df["language"]
            df["task"] = df["task"] if "task" in df.columns else df["source"]

            if "metadata" not in df.columns:
                extra_cols = [col for col in df.columns if col not in base_columns]
                df["metadata"] = df[extra_cols].to_json(orient='records', lines=True).split('\n')[:-1] if extra_cols else "{}"

            df["ann_status"] = df["ann_status"] if "ann_status" in df.columns else ""
            df["data_status"] = df["data_status"] if "data_status" in df.columns else ""
            df["is_drop"] = df["is_drop"] if "is_drop" in df.columns else ""
            df["is_annotated"] = df["is_annotated"] if "is_annotated" in df.columns else ""
            df["is_valid"] = df["is_valid"] if "is_valid" in df.columns else ""
            df["assignee_name"] = df["assignee_name"] if "assignee_name" in df.columns else ""

            st.dataframe(df.sample(n=20))
            
            # Step 2: Get users if not already fetched
            if not st.session_state.user_data:
                with st.spinner("Fetching user data..."):
                    get_users()
            
            # Step 3: Update assignee names with user IDs
            if st.session_state.user_data and 'assignee_name' in df.columns:
                st.subheader("Step 2: Update Assignee Names with User IDs")
                
                # Create a copy of the dataframe
                updated_df = df.copy()
                
                # Check if package_id exists in the dataframe
                has_package_id = 'package_id' in df.columns
                
                if has_package_id:
                    st.write("### Assign Annotators by Package")
                    
                    # Get unique package IDs
                    unique_packages = df['package_id'].unique()
                    
                    # Create a dictionary to store package assignments
                    package_assignments = {}
                    
                    # Create a container for the dropdowns
                    with st.container():
                        # Create columns for better layout
                        cols = st.columns(min(3, len(unique_packages)))
                        
                        # Create a dropdown for each package
                        for i, package_id in enumerate(unique_packages):
                            col_idx = i % len(cols)
                            with cols[col_idx]:
                                st.write(f"**Package ID: {package_id}**")
                                
                                # Get current assignee for this package if any
                                package_rows = df[df['package_id'] == package_id]
                                current_assignee = ""
                                
                                if len(package_rows) > 0 and 'assignee_name' in package_rows.columns:
                                    # Get the first non-null assignee_name for this package
                                    non_null_assignees = package_rows['assignee_name'].dropna()
                                    if len(non_null_assignees) > 0:
                                        current_assignee = non_null_assignees.iloc[0]
                                
                                # Create dropdown for user selection
                                selected_user = st.selectbox(
                                    f"Select annotator for package {package_id}",
                                    options=[""] + list(st.session_state.user_data.keys()),
                                    index=0 if current_assignee == "" else list(st.session_state.user_data.keys()).index(current_assignee) + 1,
                                    key=f"package_{package_id}"
                                )
                                
                                # Store the selection
                                package_assignments[package_id] = selected_user
                    
                    # Button to apply assignments
                    if st.button("Apply Package Assignments"):
                        # Apply the assignments to the dataframe
                        for package_id, assignee in package_assignments.items():
                            updated_df.loc[updated_df['package_id'] == package_id, 'assignee_name'] = assignee
                        
                        # Ensure assignee column exists
                        if 'assignee' not in updated_df.columns:
                            updated_df['assignee'] = ""
                        
                        # Update assignee column
                        updated_df['assignee'] = updated_df['assignee_name']
                        
                        # Ensure assigned column exists
                        if 'assigned' not in updated_df.columns:
                            updated_df['assigned'] = False
                            
                        # Update assigned column - handle null values
                        updated_df["assigned"] = updated_df["assignee"].notna() & (updated_df["assignee"] != "")
                        
                        # Show updated dataframe
                        st.success("Assignments applied successfully!")
                        st.dataframe(updated_df.sample(n=20))
                else:
                    # Original logic for when package_id doesn't exist
                    # Ensure assignee column exists
                    if 'assignee' not in updated_df.columns:
                        updated_df['assignee'] = ""
                        
                    # Update assignee column
                    updated_df['assignee'] = updated_df['assignee_name']
                    
                    # Ensure assigned column exists
                    if 'assigned' not in updated_df.columns:
                        updated_df['assigned'] = False
                        
                    # Update assigned column - handle null values
                    updated_df["assigned"] = updated_df["assignee"].notna() & (updated_df["assignee"] != "")
                    
                    st.dataframe(updated_df.head())
                
                # Reorder columns
                base_columns = ['original_id', 'sft_round', 'question', 'answer', 
                            'reason', 'task', 'domain', 'metadata', 'ann_status', 'data_status', 'is_drop', 
                            'is_annotated', 'is_valid', 'assigned', 'assignee_name','assignee']
                
                # If package_id exists, include it in the display
                if has_package_id:
                    base_columns.append('package_id')
                
                # Only include columns that exist in the dataframe
                final_columns = [col for col in base_columns if col in updated_df.columns]
                
                # Add any additional columns not in base_columns
                for col in updated_df.columns:
                    if col not in final_columns:
                        final_columns.append(col)
                
                updated_df = updated_df[final_columns]
                
                # Step 4: Convert to JSON and zip
                st.subheader("Step 3: Convert to JSON and Zip")
                run_id = st.text_input("Pipeline Run ID")
                dataset_name = st.text_input("Dataset Name")
                
                if st.button("Prepare and Upload"):
                    if run_id and dataset_name:
                        with st.spinner("Preparing and uploading data..."):
                            # Convert to JSON and zip
                            zip_file = csv_to_json_zip(updated_df)
                            
                            # Upload to platform
                            if upload_zip_file(zip_file, run_id, dataset_name):
                                st.success("Data uploaded successfully!")
                            else:
                                st.error("Failed to upload data")
                    else:
                        st.error("Please provide both run ID and dataset name")
    
    # Query Data page
    elif page == "Query Data":
        st.header("Query Pipeline Data")
        
        # Get pipeline runs if not already fetched
        if not st.session_state.pipeline_runs:
            with st.spinner("Fetching pipeline runs..."):
                get_pipeline_runs()
        
        if st.session_state.pipeline_runs:
            # Select pipeline run ID
            run_options = {
                run.get('id', str(i)): f"{run.get('run_name', 'Unknown')} ({run.get('id', 'N/A')})" 
                for i, run in enumerate(st.session_state.pipeline_runs)
            }
            selected_run_id = st.selectbox("Select Pipeline Run", options=list(run_options.keys()), 
                                        format_func=lambda x: run_options[x])
            
            if st.button("Fetch Data"):
                if selected_run_id:
                    with st.spinner(f"Fetching data for run ID: {selected_run_id}..."):
                        data = get_pipeline_data(selected_run_id)
                        
                        if data:
                            df = pd.DataFrame(data)
                            
                            # Create tabs for data view and visualizations
                            tab1, tab2 = st.tabs(["Data View", "Visualizations"])
                            
                            with tab1:
                                st.dataframe(df)
                                
                                # Provide download option
                                csv = df.to_csv(index=False,encoding='utf-8-sig')
                                st.download_button(
                                    label="Download Data as Snapshot",
                                    data=csv,
                                    file_name=f"pipeline_data_{selected_run_id}.csv",
                                    mime="text/csv"
                                )
                            
                            with tab2:
                                # Create visualizations
                                create_visualizations(df)
        else:
            st.error("No pipeline runs available")
    
    # Generate Reports page
    elif page == "Generate Reports":
        st.header("Generate Daily Reports")
        
        # Select pipeline run ID
        if st.session_state.pipeline_data:
            # Select pipeline run ID
            run_options = {
                run.get('id', str(i)): f"{run.get('run_name', 'Unknown')} ({run.get('id', 'N/A')})" 
                for i, run in enumerate(st.session_state.pipeline_runs)
            }
            selected_run_id = st.selectbox("Select Pipeline Run", options=list(run_options.keys()), 
                                        format_func=lambda x: run_options[x])
            
            if selected_run_id:
                data = st.session_state.pipeline_data[selected_run_id]
                
                # Generate report
                report_df = generate_report(data)
                
                if not report_df.empty:
                    st.subheader(f"Daily Report for Run ID: {selected_run_id}")
                    st.dataframe(report_df)
                    
                    # Provide download option
                    csv = report_df.to_csv(index=False)
                    st.download_button(
                        label="Download Report as CSV",
                        data=csv,
                        file_name=f"daily_report_{run_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No report data available")
        else:
            st.info("No pipeline data available. Please query data first.")
    
    # Recycle Questions page
    elif page == "Recycle Questions":
        st.header("Recycle Undone Questions")
        
        # Select pipeline run ID
        if st.session_state.pipeline_data:
            run_options = {
                run.get('id', str(i)): f"{run.get('run_name', 'Unknown')} ({run.get('id', 'N/A')})" 
                for i, run in enumerate(st.session_state.pipeline_runs)
            }
            selected_run_id = st.selectbox("Select Pipeline Run", options=list(run_options.keys()), 
                                        format_func=lambda x: run_options[x])
            
            if selected_run_id:
                data = st.session_state.pipeline_data[selected_run_id]
                
                # Filter undone questions
                undone_questions = filter_undone_questions(data)
                
                st.subheader(f"Undone Questions: {len(undone_questions)}")
                
                if undone_questions:
                    df = pd.DataFrame(undone_questions)
                    st.dataframe(df)
                    
                    # Upload capacity CSV
                    st.subheader("Upload Capacity CSV")
                    capacity_file = st.file_uploader("Upload capacity CSV", type=["csv"])
                    
                    if capacity_file:
                        capacity_df = pd.read_csv(capacity_file)
                        st.dataframe(capacity_df)
                        
                        if st.button("Assign Questions and Create New Dataset"):
                            with st.spinner("Assigning questions and creating new dataset..."):
                                # Assign questions based on capacity
                                assigned_questions = assign_questions_by_capacity(
                                    undone_questions, capacity_df
                                )
                                
                                # Convert to DataFrame
                                assigned_df = pd.DataFrame(assigned_questions)
                                st.dataframe(assigned_df)
                                
                                # Create new dataset name
                                new_dataset_name = f"recycled_{run_id}_{datetime.now().strftime('%Y%m%d')}"
                                new_run_id = st.text_input("New Pipeline Run ID", value=f"recycled_{run_id}")
                                
                                # Convert to JSON and zip
                                zip_file = csv_to_json_zip(assigned_df)
                                
                                # Upload to platform
                                if upload_zip_file(zip_file, new_run_id, new_dataset_name):
                                    st.success("New dataset created successfully!")
                                else:
                                    st.error("Failed to create new dataset")
                else:
                    st.info("No undone questions found")
        else:
            st.info("No pipeline data available. Please query data first.")

if __name__ == "__main__":
    main()
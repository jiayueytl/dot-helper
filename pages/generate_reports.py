import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from config import COMPLETED_STATUS, QA_DONE_STATUS, INCOMPLETE_STATUS, BASE_COLUMNS, USABLE_COLUMNS
from utils.api import get_projects, get_datasets_by_project, get_dataset_records
from utils.data_processing import get_performance_tier

# Cache expensive operations
@st.cache_data
def load_projects():
    """Load and cache projects data"""
    return get_projects()

@st.cache_data
def load_datasets(project_id):
    """Load and cache datasets for a specific project"""
    return get_datasets_by_project(project_id)

@st.cache_data
def load_dataset_records(dataset_ids):
    """Load and cache dataset records"""
    return get_dataset_records(dataset_ids)

def initialize_session_state():
    """Initialize session state variables if they don't exist"""
    if "data_fetched" not in st.session_state:
        st.session_state.data_fetched = False
    if "report_df" not in st.session_state:
        st.session_state.report_df = None
    if "summary_df" not in st.session_state:
        st.session_state.summary_df = None

def fetch_project_data(selected_project_id):
    """Fetch and process data for the selected project"""
    # Get datasets
    datasets = load_datasets(selected_project_id)
    
    if not datasets:
        st.warning("No datasets found in this project.")
        return False
    
    # Extract dataset IDs
    dataset_ids = [d["dataset_id"] for d in datasets if d.get("dataset_id")]
    
    if not dataset_ids:
        st.warning("No valid dataset IDs found.")
        return False
    
    # Fetch all dataset records
    records_df = load_dataset_records(dataset_ids)

    if records_df.empty:
        st.warning("No records found for selected project.")
        return False

    # Store raw records for download
    st.session_state.raw_records_df = records_df
    
    if records_df.empty:
        st.warning("No records found for selected project.")
        return False
    
    # Ensure required columns exist
    for col in ["assignee_name", "status", "qa_flag", "dataset_name"]:
        if col not in records_df.columns:
            records_df[col] = ""
    
    # Process data and create report
    
    st.session_state.report_df = process_records_to_report(records_df)
    st.session_state.summary_df = create_summary_report(st.session_state.report_df)
    st.session_state.data_fetched = True
    
    return True

def process_records_to_report(records_df):
    """Process raw records into a report dataframe"""
    # Show raw data grouped by dataset, assignee, and status
    st.dataframe(records_df.groupby(['dataset_name','assignee_name', 'status']).size().unstack(fill_value=0))
    
    report_rows = []
    for (assignee_name, dataset_name), group in records_df.groupby(["assignee_name", "dataset_name"]):
        total = len(group)
        completed = len(group[group["status"].str.lower().isin(COMPLETED_STATUS)])
        comp_rate = round((completed / total) * 100, 2) if total else 0
        qa_completed = len(group[group["status"].str.lower().isin(QA_DONE_STATUS)])
        qa_comp_rate = round((qa_completed / completed) * 100, 2) if completed and completed > 0 else 0
        
        qa_p = len(group[group["qa_flag"].str.lower() == "pass"])
        qa_f = len(group[group["qa_flag"].str.lower() == "fail"])
        qa_pass_rate = round((qa_p / qa_completed) * 100, 2) if qa_completed and qa_completed > 0 else 0

        report_rows.append({
            "assignee_name": assignee_name or "Unassigned",
            "dataset_name": dataset_name or "Unknown Dataset",
            "total_assigned": total,
            "total_completed": completed,
            "comp_rate": comp_rate,
            "total_qa": qa_completed,
            "qa_comp_rate": qa_comp_rate,
            "qa_pass": qa_p,
            "qa_fail": qa_f,
            "qa_pass_rate": qa_pass_rate,
            "performance_tier": get_performance_tier(qa_pass_rate)
        })
    
    if not report_rows:
        st.warning("No valid data found in datasets.")
        return pd.DataFrame()
    
    return pd.DataFrame(report_rows)

def create_summary_report(report_df):
    """Create a summary report grouped by assignee"""
    summary_df = (
        report_df.groupby("assignee_name")
        .agg({
            "total_assigned": "sum",
            "total_completed": "sum",
            "total_qa": "sum",
            "qa_pass": "sum",
            "qa_fail": "sum",
        })
        .reset_index()
    )
    summary_df["completion_rate"] = round((summary_df["total_completed"] / summary_df["total_assigned"]) * 100, 2)
    summary_df["qa_comp_rate"] = round((summary_df["total_qa"] / summary_df["total_assigned"]) * 100, 2)
    return summary_df

def apply_filters(report_df):
    """Apply dataset and assignee filters to the report"""
    # Add filters
    col1, col2 = st.columns(2)
    with col1:
        dataset_filter = st.multiselect(
            "Filter by Dataset",
            options=sorted(report_df["dataset_name"].unique().tolist()),
            default=None,
            help="Select one or more datasets to view",
        )
    with col2:
        assignee_filter = st.multiselect(
            "Filter by Assignee",
            options=sorted(report_df["assignee_name"].unique().tolist()),
            default=None,
            help="Select one or more assignees to view",
        )
    
    # Apply filters
    filtered_df = report_df.copy()
    if dataset_filter:
        filtered_df = filtered_df[filtered_df["dataset_name"].isin(dataset_filter)]
    if assignee_filter:
        filtered_df = filtered_df[filtered_df["assignee_name"].isin(assignee_filter)]
    
    return filtered_df

def create_visualization(report_df):
    """Create and display visualization"""
    st.subheader("📈 Visualizations")
    try:
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.barplot(data=report_df, x="assignee_name", y="comp_rate", ax=ax)
        plt.xticks(rotation=45, ha="right")
        plt.title("Completion Rate by Assignee")
        plt.ylabel("Completion %")
        plt.xlabel("Assignee")
        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Visualization error: {e}")

def reports_page():
    """Main function for the reports page"""
    st.header("📊 Project Completion Report")
    
    # Initialize session state
    # initialize_session_state()
    
    # Load projects
    projects = load_projects()
    
    if not projects:
        st.warning("No projects found. Please check API or authentication.")
        return
    
    # Select project
    selected_project_id = st.selectbox(
        "Select a project",
        options=list(projects.keys()),
        format_func=lambda x: projects[x],
    )
    
    if not selected_project_id:
        return
    
    selected_project_name = projects[selected_project_id]
    st.markdown(f"### 📁 Project: **{selected_project_name}** ({selected_project_id})")
    
    # Fetch data button
    if st.button("🚀 Fetch Project Data"):
        with st.spinner("Fetching project data..."):
            fetch_project_data(selected_project_id)

        if "raw_records_df" in st.session_state and not st.session_state.raw_records_df.empty:
            raw_csv = st.session_state.raw_records_df.to_csv(index=False, encoding="utf-8-sig")
            raw_json = st.session_state.raw_records_df.to_json(orient="records",indent=2,force_ascii=False)
            with st.expander("👀 Preview Raw Data"):
                st.dataframe(st.session_state.raw_records_df.head(30))
            st.download_button(
                label="⬇️ Download Raw Concatenated Data",
                data=raw_csv,
                file_name=f"raw_dataset_records_{selected_project_id}.csv",
                mime="text/csv",
                help="Download all raw records from selected project's datasets"
            )
            st.download_button(
                label="⬇️ Download Raw Concatenated Data (json)",
                data=raw_json,
                file_name=f"raw_dataset_records_{selected_project_id}.json",
                mime="application/json",
                help="Download all raw records from selected project's datasets"
            )
        else:
            st.info("No raw dataset records available yet. Fetch project data first.")

    
    # Display data if fetched
    if st.session_state.projects and st.session_state.report_data is not None:
        report_df = st.session_state.report_df
        summary_df = st.session_state.summary_df
        
        # Show per dataset report
        st.subheader("📁 Per Dataset Report")
        st.dataframe(report_df)
        
        st.subheader("📋 Filtered Report")
        # Apply filters
        filtered_df = apply_filters(report_df)
        st.dataframe(filtered_df)
        
        # # Show summary report
        st.subheader("📊 Summary Report")
        st.metric('Total Completed',summary_df['total_completed'].sum())
        st.metric('Total Done QA',summary_df['total_qa'].sum())
        # st.metric('Total Done QA',summary_df['total_qa'].sum())
        # st.dataframe(summary_df)
        
        # Download button
        csv = report_df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="⬇️ Download Report CSV",
            data=csv,
            file_name=f"project_report_{selected_project_id}.csv",
            mime="text/csv"
        )
        
        # Create visualization
        create_visualization(report_df)
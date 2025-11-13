import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from config import COMPLETED_STATUS, QA_DONE_STATUS, INCOMPLETE_STATUS, BASE_COLUMNS, USABLE_COLUMNS
from utils.api import get_projects, get_datasets_by_project, get_dataset_records
from utils.data_processing import get_performance_tier
# from streamlit_pandas_profiling import st_profile_report
# from ydata_profiling import ProfileReport
from st_aggrid import AgGrid, GridOptionsBuilder
from datetime import datetime

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
    st.dataframe(sanitize_for_streamlit(records_df).groupby(
        ['project_name','dataset_name','assignee_name', 'status']
    ).size().unstack(fill_value=0))
    
    report_rows = []
    for (project_name, assignee_name, dataset_name), group in records_df.groupby(
            ["project_name","assignee_name", "dataset_name"]
        ):
        total = len(group)
        completed = len(group[group["status"].str.lower().isin(COMPLETED_STATUS)])
        comp_rate = round((completed / total) * 100, 2) if total else 0
        qa_completed = len(group[group["status"].str.lower().isin(QA_DONE_STATUS)])
        qa_comp_rate = round((qa_completed / completed) * 100, 2) if completed and completed > 0 else 0
        
        qa_p = len(group[group["qa_flag"].str.lower() == "pass"])
        qa_f = len(group[group["qa_flag"].str.lower() == "fail"])
        qa_pass_rate = round((qa_p / qa_completed) * 100, 2) if qa_completed and qa_completed > 0 else 0

        report_rows.append({
            "project_name": project_name or "Unknown Project",
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
    st.subheader("📈 Tracker")
    st.dataframe(report_df)
    gb = GridOptionsBuilder.from_dataframe(report_df)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()  # enables pivot/filter/group sidebar
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum')

    grid_options = gb.build()

    st.subheader("🔧 Drag and drop columns to group/pivot")
    with st.expander("Pivot here"):
        grid_response = AgGrid(
            report_df,
            gridOptions=grid_options,
            enable_enterprise_modules=True,  # enables pivot & group
            update_mode="MODEL_CHANGED",
            theme="streamlit",
        )

def create_visualization_streamlit(filtered_df):
    """Visualize numeric/scalar columns using Streamlit charts in 4-column layout."""
    if filtered_df.empty:
        st.info("No data available for visualization.")
        return

    st.subheader("📈 Multi-Project Visualizations (Streamlit Charts)")

    # Select numeric columns or scalar object columns
    numeric_cols = filtered_df.select_dtypes(include=["number"]).columns.tolist()
    
    # Include object columns that are safe (not list/dict)
    scalar_object_cols = []
    for col in filtered_df.select_dtypes(include=["object"]).columns:
        # Check if all values are scalar (not list/dict)
        if filtered_df[col].apply(lambda x: not isinstance(x, (list, dict))).all():
            scalar_object_cols.append(col)
    
    # Combine numeric + safe object columns
    viz_cols = numeric_cols + scalar_object_cols
    if not viz_cols:
        st.warning("No suitable columns available for visualization.")
        return

    # Column selector for user
    selected_cols = st.multiselect(
        "Select columns to visualize",
        options=viz_cols,
        default=viz_cols
    )

    if not selected_cols:
        st.info("Select at least one column to display charts.")
        return

    # Display charts in 4-column grid
    col_count = 4
    for i in range(0, len(selected_cols), col_count):
        cols = st.columns(col_count)
        for j, col_name in enumerate(selected_cols[i:i+col_count]):
            # Only numeric columns can be aggregated for chart
            if col_name in numeric_cols:
                chart_data = (
                    filtered_df.groupby("dataset_name")[col_name]
                    .sum()
                    .sort_values(ascending=False)
                )
                with cols[j]:
                    st.markdown(f"**{col_name.replace('_', ' ').title()}**")
                    st.bar_chart(chart_data)
            else:
                # For scalar object columns, show counts
                chart_data = (
                    filtered_df.groupby("dataset_name")[col_name]
                    .agg(lambda x: x.nunique())
                    .sort_values(ascending=False)
                )
                with cols[j]:
                    st.markdown(f"**{col_name.replace('_', ' ').title()} (unique count)**")
                    st.bar_chart(chart_data)

            # Expandable data table
            with cols[j].expander(f"📋 Data Table for {col_name}"):
                st.dataframe(
                    filtered_df[["project_name", "dataset_name", "assignee_name", col_name]]
                    .sort_values(by=col_name, ascending=False)
                    .reset_index(drop=True)
                )


def sanitize_for_streamlit(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts all non-scalar columns (lists, dicts, objects) to strings
    so Streamlit's st.dataframe / PyArrow can handle them.
    """
    df_copy = df.copy()
    for col in df_copy.columns:
        # Convert only object type columns
        if df_copy[col].dtype == "object":
            df_copy[col] = df_copy[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)
    return df_copy

def make_columns_unique(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename columns if there are duplicates by appending _1, _2, etc.
    """
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        dup_idx = cols[cols == dup].index.tolist()
        for i, idx in enumerate(dup_idx[1:], start=1):
            cols[idx] = f"{dup}_{i}"
    df.columns = cols
    return df



def reports_page():
    """Main function for the reports page (now supports multiple projects)"""
    st.header("📊 Multi-Project Completion Report")

    # --- Load all projects ---
    projects = load_projects()
    if not projects:
        st.warning("No projects found. Please check API or authentication.")
        return

    # --- Multi-select projects ---
    selected_project_ids = st.multiselect(
        "Select one or more projects",
        options=list(projects.keys()),
        format_func=lambda x: projects[x],
        help="You can select multiple projects to view combined reports.",
    )

    if not selected_project_ids:
        st.info("Select one or more projects to continue.")
        return

    # --- Fetch Data for All Selected Projects ---
    all_records = []

    with st.expander("Fetching datasets and records for selected projects..."):
        with st.spinner("May take a while depending on data size..."):
            for project_id in selected_project_ids:
                project_name = projects[project_id]
                datasets = load_datasets(project_id)
                if not datasets:
                    st.warning(f"No datasets found for {project_name}")
                    continue

                dataset_ids = [d["dataset_id"] for d in datasets if d.get("dataset_id")]
                if not dataset_ids:
                    continue

                records_df = load_dataset_records(dataset_ids)
                if records_df is not None and not records_df.empty:
                    records_df["project_id"] = project_id
                    records_df["project_name"] = project_name
                    all_records.append(records_df)

    if not all_records:
        st.warning("No data retrieved from the selected projects.")
        return

    # --- Combine all records ---
    combined_records = pd.concat(all_records, ignore_index=True)
    # combined_records = pd.concat(all_records, ignore_index=True)
    combined_records = make_columns_unique(combined_records)

    st.session_state.raw_records_df = combined_records

    # --- Process into report ---
    combined_report = process_records_to_report(combined_records)
    combined_summary = create_summary_report(combined_report)
    st.session_state.report_df = combined_report
    st.session_state.summary_df = combined_summary

    # --- Filters (dataset, assignee) ---
    st.subheader("🔍 Filters")
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_projects = st.multiselect(
            "Filter by Project",
            options=sorted(combined_report["project_name"].unique().tolist()),
            default=sorted(combined_report["project_name"].unique().tolist()),
        )
    with col2:
        selected_datasets = st.multiselect(
            "Filter by Dataset",
            options=sorted(combined_report["dataset_name"].unique().tolist()),
            default=None,
        )
    with col3:
        selected_assignees = st.multiselect(
            "Filter by Assignee",
            options=sorted(combined_report["assignee_name"].unique().tolist()),
            default=None,
        )

    filtered_df = combined_report.copy()
    if selected_projects:
        filtered_df = filtered_df[filtered_df["project_name"].isin(selected_projects)]
    if selected_datasets:
        filtered_df = filtered_df[filtered_df["dataset_name"].isin(selected_datasets)]
    if selected_assignees:
        filtered_df = filtered_df[filtered_df["assignee_name"].isin(selected_assignees)]

    # --- Show Summary Metrics ---
    st.subheader("📊 Combined Summary")
    st.metric("Total Completed", combined_summary["total_completed"].sum())
    st.metric("Total QA Done", combined_summary["total_qa"].sum())

    # --- Download Combined Data ---
    csv = filtered_df.to_csv(index=False, encoding="utf-8-sig")
    json = filtered_df.to_json(orient="records", indent=2, force_ascii=False)
    st.download_button("⬇️ Download Combined CSV", csv, f"multi_project_report.csv", "text/csv")
    st.download_button("⬇️ Download Combined JSON", json, f"multi_project_report.json", "application/json")

    # --- Visualization ---
    create_visualization(combined_report)
    create_visualization_streamlit(combined_records)

#TODO: data profiling
#TODO: data builder
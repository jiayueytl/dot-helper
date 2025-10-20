import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from config import COMPLETED_STATUS,QA_DONE_STATUS, INCOMPLETE_STATUS, BASE_COLUMNS, USABLE_COLUMNS
from utils.api import get_projects, get_datasets_by_project, get_dataset_records


def reports_page():
    st.header("📊 Project Completion Report")

    # --- Step 1: Load projects ---
    if "projects" not in st.session_state or not st.session_state.projects:
        with st.spinner("Loading projects..."):
            projects = get_projects()
            st.session_state.projects = projects
    else:
        projects = st.session_state.projects

    if not projects:
        st.warning("No projects found. Please check API or authentication.")
        return

    # --- Step 2: Select project ---
    selected_project_id = st.selectbox(
        "Select a project",
        options=list(projects.keys()),
        format_func=lambda x: projects[x],
    )

    if not selected_project_id:
        return

    selected_project_name = projects[selected_project_id]
    st.markdown(f"### 📁 Project: **{selected_project_name}** ({selected_project_id})")

    # --- ✅ Step 3: Fetch button ---
    if not st.button("🚀 Fetch Project Data"):
        return  # Stop here until button is clicked

    # --- Step 4: Get datasets ---
    with st.spinner("Fetching datasets..."):
        datasets = get_datasets_by_project(selected_project_id)

    if not datasets:
        st.warning("No datasets found in this project.")
        return

    # Extract dataset IDs
    dataset_ids = [d["dataset_id"] for d in datasets if d.get("dataset_id")]

    if not dataset_ids:
        st.warning("No valid dataset IDs found.")
        return

    # --- Step 5: Fetch all dataset records ---
    with st.spinner("Fetching all dataset records..."):
        records_df = get_dataset_records(dataset_ids)

    if records_df.empty:
        st.warning("No records found for selected project.")
        return

    # Ensure required columns exist
    for col in ["assignee_name", "status", "qa_status", "dataset_name"]:
        if col not in records_df.columns:
            records_df[col] = ""

    # --- Step 6: Aggregate per assignee ---
    st.dataframe(records_df.groupby(['dataset_name','assignee_name', 'status']).size().unstack(fill_value=0))

    report_rows = []
    for (assignee_name, dataset_name), group in records_df.groupby(["assignee_name", "dataset_name"]):
        total = len(group)
        completed = len(group[group["status"].str.lower().isin(COMPLETED_STATUS)])
        comp_rate = round((completed / total) * 100, 2) if total else 0
        qa_completed = len(group[group["status"].str.lower().isin(QA_DONE_STATUS)])
        qa_comp_rate = round((qa_completed / completed) * 100, 2) if total else 0
        qa_p = len(group[group["qa_status"].str.lower() == "pass"])
        qa_f = len(group[group["qa_status"].str.lower() == "fail"])
        # dataset_names = ", ".join(group["dataset_name"].unique())

        report_rows.append({
            "assignee_name": assignee_name or "Unassigned",
            "dataset_name": dataset_name or "Unknown Dataset",
            "total_assigned": total,
            "total_completed": completed,
            "completion_rate": comp_rate,
            "total_qa": qa_completed,
            "qa_comp_rate": qa_comp_rate,
            "qa_status_pass": qa_p,
            "qa_status_fail": qa_f
        })


    # --- Step 7: Show report ---
    if not report_rows:
        st.warning("No valid data found in datasets.")
        return

    report_df = pd.DataFrame(report_rows)
    st.subheader("📁 Per Dataset Report")
    st.dataframe(report_df)

    summary_df = (
        report_df.groupby("assignee_name")
        .agg({
            "total_assigned": "sum",
            "total_completed": "sum",
            "total_qa": "sum",
            "qa_status_pass": "sum",
            "qa_status_fail": "sum",
        })
        .reset_index()
    )
    summary_df["completion_rate"] = round((summary_df["total_completed"] / summary_df["total_assigned"]) * 100, 2)
    summary_df["qa_comp_rate"] = round((summary_df["total_qa"] / summary_df["total_assigned"]) * 100, 2)

    st.subheader("👤 Per Assignee Summary")
    st.dataframe(summary_df)


    # stats_df = 

    # --- Step 8: Download ---
    csv = report_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="⬇️ Download Report CSV",
        data=csv,
        file_name=f"project_report_{selected_project_id}.csv",
        mime="text/csv"
    )

    # --- Step 9: Visualization ---
    st.subheader("📈 Visualizations")
    try:
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.barplot(data=report_df, x="assignee_name", y="completion_rate", ax=ax)
        plt.xticks(rotation=45, ha="right")
        plt.title("Completion Rate by Assignee")
        plt.ylabel("Completion %")
        plt.xlabel("Assignee")
        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Visualization error: {e}")

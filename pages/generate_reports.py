import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from utils.api import get_projects, get_datasets_by_project, get_dataset_records



def reports_page():
    st.header("📊 Project Completion Report")

    st.write(st.session_state)

    # --- Step 1: Load projects ---
    if "projects" not in st.session_state or not st.session_state.projects:
        with st.spinner("Loading projects..."):
            projects = get_projects()
    else:
        projects = st.session_state.projects

    if not projects:
        st.warning("No projects found. Please check API or authentication.")
        return
    
    st.write("🗂 Available projects:", projects)

    selected_project_id = st.selectbox(
        "Select a project",
        options=list(projects.keys()),
        format_func=lambda x: projects[x],
    )

    if not selected_project_id:
        return

    selected_project_name = projects[selected_project_id]
    st.markdown(f"### 📁 Project: **{selected_project_name}** ({selected_project_id})")

    # --- Step 2: Get datasets ---
    with st.spinner("Fetching datasets..."):
        datasets = get_datasets_by_project(selected_project_id)

    st.write("🗂 Available datasets:", datasets)

    if not datasets:
        st.warning("No datasets found in this project.")
        return
    
    # Extract dataset IDs
    dataset_ids = [d["dataset_id"] for d in datasets if d.get("dataset_id")]
    st.write("📦 Available dataset_ids:", dataset_ids)
    
    if not dataset_ids:
        st.warning("No valid dataset IDs found.")
        return

    # --- Step 3: Fetch all dataset records ---
    st.info("Fetching all dataset records...")
    records_df = get_dataset_records(dataset_ids)

    st.write(records_df)
    
    if records_df.empty:
        st.warning("No records found for selected project.")
        return

    # Ensure key columns exist
    for col in ["assignee_name", "status", "qa_status", "dataset_name"]:
        if col not in records_df.columns:
            records_df[col] = ""

    records_df = records_df.drop_duplicates(subset='id',keep='last')
    # --- Step 4: Aggregate per assignee ---
    report_rows = []

    st.dataframe(records_df.groupby(['assignee_name','status']).size().unstack(fill_value=0))

    for assignee_name, group in records_df.groupby("assignee_name"):
        total = len(group)
        completed = len(group[group["status"].str.lower() == "annotation_complete"])
        comp_rate = round((completed / total) * 100, 2) if total else 0
        qa_p = len(group[group["qa_status"].str.lower() == "pass"])
        qa_f = len(group[group["qa_status"].str.lower() == "fail"])
        dataset_names = ", ".join(group["dataset_name"].unique())

        report_rows.append({
            "assignee_name": assignee_name or "Unassigned",
            "dataset(s)": dataset_names,
            "total_assigned": total,
            "total_completed": completed,
            "completion_rate": comp_rate,
            "qa_status_pass": qa_p,
            "qa_status_fail": qa_f
        })

    # --- Step 5: Show report ---
    if not report_rows:
        st.warning("No valid data found in datasets.")
        return

    report_df = pd.DataFrame(report_rows)
    st.subheader("🧾 Summary Report")
    st.dataframe(report_df)

    # --- Step 6: Download ---
    csv = report_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="⬇️ Download Report CSV",
        data=csv,
        file_name=f"project_report_{selected_project_id}.csv",
        mime="text/csv"
    )

    # --- Step 7: Visualization ---
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

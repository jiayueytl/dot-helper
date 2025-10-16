import streamlit as st
from utils.reports import generate_report
from datetime import datetime
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from utils.api import get_projects, get_datasets_by_project,get_dataset_records

def reports_page():
    st.header("📊 Project Completion Report")

    # --- Step 1: Load projects ---
    if "projects" not in st.session_state or not st.session_state.projects:
        with st.spinner("Loading projects..."):
            projects = get_projects()
    else:
        projects = st.session_state.projects

    if not projects:
        st.warning("No projects found. Please check API or authentication.")
        return
    # st.print(projects)
    project_options = {p["id"]: p.get("name", f"Unnamed ({p['id']})") for p in projects}
    selected_project_id = st.selectbox(
        "Select Project",
        options=list(project_options.keys()),
        format_func=lambda x: project_options[x]
    )

    if not selected_project_id:
        return

    st.markdown(f"### 📁 Project: **{project_options[selected_project_id]}** ({selected_project_id})")

    # --- Step 2: Get datasets for the selected project ---
    with st.spinner("Fetching datasets..."):
        datasets = get_datasets_by_project(selected_project_id)

    if not datasets:
        st.warning("No datasets found in this project.")
        return

    report_rows = []
    progress_bar = st.progress(0)

    for idx, dataset in enumerate(datasets):
        dataset_id = dataset.get("id")
        dataset_name = dataset.get("name", f"Dataset-{dataset_id}")

        records = get_dataset_records(dataset_id)
        if not records:
            continue

        df = pd.DataFrame(records)

        # Skip if required cols missing
        for col in ["assignee_name", "status", "qa_status"]:
            if col not in df.columns:
                df[col] = ""

        # Aggregate logic
        total_assigned = len(df)
        total_completed = len(df[df["status"].str.lower() == "completed"])
        completion_rate = round((total_completed / total_assigned) * 100, 2) if total_assigned else 0

        qa_pass = len(df[df["qa_status"].str.lower() == "pass"])
        qa_fail = len(df[df["qa_status"].str.lower() == "fail"])

        # Summarize per assignee
        for assignee, group in df.groupby("assignee_name"):
            total = len(group)
            completed = len(group[group["status"].str.lower() == "completed"])
            comp_rate = round((completed / total) * 100, 2) if total else 0
            qa_p = len(group[group["qa_status"].str.lower() == "pass"])
            qa_f = len(group[group["qa_status"].str.lower() == "fail"])

            report_rows.append({
                "dataset_name": dataset_name,
                "assignee_name": assignee or "Unassigned",
                "total_assigned": total,
                "total_completed": completed,
                "completion_rate": comp_rate,
                "qa_status_pass": qa_p,
                "qa_status_fail": qa_f
            })

        progress_bar.progress((idx + 1) / len(datasets))

    progress_bar.empty()

    if not report_rows:
        st.warning("No valid data found in datasets.")
        return

    # --- Step 3: Display final report ---
    report_df = pd.DataFrame(report_rows)
    st.subheader("🧾 Summary Report")
    st.dataframe(report_df)

    # --- Step 4: Download report ---
    csv = report_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="⬇️ Download Report CSV",
        data=csv,
        file_name=f"project_report_{selected_project_id}.csv",
        mime="text/csv"
    )

    # --- Step 5: Optional Visualization ---
    st.subheader("📈 Visualizations")

    try:
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.barplot(data=report_df, x="assignee_name", y="completion_rate", hue="dataset_name", ax=ax)
        plt.xticks(rotation=45, ha="right")
        plt.title("Completion Rate by Assignee")
        plt.ylabel("Completion %")
        plt.xlabel("Assignee")
        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Visualization error: {e}")
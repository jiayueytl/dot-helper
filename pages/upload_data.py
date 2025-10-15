import streamlit as st
import pandas as pd
from config import PREFIX, SFT_ROUND
from utils.api import get_users, upload_zip_file
from utils.data_processing import csv_to_json_zip

def upload_data_page2():
    st.header("Upload Data")

    csv_file = st.file_uploader("Upload your enriched CSV file", type=["csv"])
    if not csv_file:
        return
    df = pd.read_csv(csv_file)
    df["sft_round"] = SFT_ROUND
    df["original_id"] = df.get("original_id", PREFIX + (df.index + 1).astype(str).str.zfill(5))
    st.dataframe(df.head())

    if not st.session_state.user_data:
        get_users()

    run_id = st.text_input("Pipeline Run ID")
    dataset_name = st.text_input("Dataset Name")

    if st.button("Upload"):
        if run_id and dataset_name:
            zip_file = csv_to_json_zip(df)
            upload_zip_file(zip_file, run_id, dataset_name)
        else:
            st.error("Please provide both Run ID and Dataset Name.")


def upload_data_page():
    st.header("Upload Data")
    base_columns = ['uuid','original_id', 'sft_round', 'question', 'answer', 
                        'reason', 'task', 'domain', 'metadata', 'ann_status', 'data_status', 'is_drop', 
                        'is_annotated', 'is_valid', 'assigned', 'assignee_name','assignee']

    # Step 1: Upload enriched CSV
    st.subheader("Step 1: Upload Enriched CSV")
    csv_file = st.file_uploader("Upload your enriched CSV file", type=["csv"])

    if csv_file:
        df = pd.read_csv(csv_file)
        df['uuid'] = df['uuid'] if 'uuid' in df.columns else PREFIX + (df.index + 1).astype(str).str.zfill(5)
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
        df["assignee"] = df["assignee"] if "assignee" in df.columns else ""
        
        # if "assignee_name" in df.columns:
        #     if "user_data" in st.session_state and st.session_state.user_data:
        #         # Create a mapping of username → user_id
        #         name_to_id = {name: info["id"] for name, info in st.session_state.user_data.items() if "id" in info}

        #         # Map assignee_name → user_id
        #         df["assignee"] = df["assignee_name"].map(name_to_id).fillna("")
        #     else:
        #         st.warning("User data not loaded — assignee_name cannot be mapped to user IDs.")
        #         df["assignee"] = ""
        # else:
        #     df["assignee"] = ""


        
        st.subheader("Random view of dataset")
        st.dataframe(df.sample(n=20))

        # Step 3: Update assignee names with user IDs
        if st.session_state.user_data and 'assignee_name' in df.columns:
            st.subheader("Step 2: Update Assignee Names with User IDs")

            updated_df = df.copy()
            has_package_id = 'package_id' in df.columns

            if has_package_id:
                st.write("### Assign Annotators by Package")

                unique_packages = df['package_id'].unique()
                package_assignments = {}

                cols = st.columns(min(3, len(unique_packages)))
                for i, package_id in enumerate(unique_packages):
                    col_idx = i % len(cols)
                    with cols[col_idx]:
                        st.write(f"**Package ID: {package_id}**")

                        package_rows = df[df['package_id'] == package_id]
                        current_assignee = ""
                        non_null_assignees = package_rows['assignee_name'].dropna()
                        if len(non_null_assignees) > 0:
                            current_assignee = non_null_assignees.iloc[0]

                        selected_user = st.selectbox(
                            f"Select annotator for package {package_id}",
                            options=[""] + list(st.session_state.user_data.keys()),
                            index=0 if current_assignee == "" else list(st.session_state.user_data.keys()).index(current_assignee) + 1,
                            key=f"package_{package_id}"
                        )

                        package_assignments[package_id] = selected_user.strip()

                # Apply Assignments
                if st.button("Apply Package Assignments"):
                    for package_id, assignee in package_assignments.items():
                        updated_df.loc[updated_df['package_id'] == package_id, 'assignee_name'] = assignee

                    if 'assignee' not in updated_df.columns:
                        updated_df['assignee'] = ""

                    updated_df["assignee"] = updated_df["assignee_name"]
                    updated_df["assigned"] = updated_df["assignee"].notna() & (updated_df["assignee"] != "")

                    # ✅ store in session state
                    st.session_state["updated_df"] = updated_df

                    st.success("Assignments applied successfully!")
                    st.dataframe(updated_df.sample(n=20))
                    st.dataframe(updated_df.groupby(['assigned', 'assignee']).size().reset_index(name='counts'))

        # ✅ Step 3: Prepare & Upload (appears only after Apply)
        if "updated_df" in st.session_state:
            updated_df = st.session_state["updated_df"]

            st.subheader("Step 3: Convert to JSON and Zip")
            st.dataframe(updated_df.head())

            run_id = st.text_input("Pipeline Run ID")
            dataset_name = st.text_input("Dataset Name")

            if st.button("Prepare and Upload"):
                if run_id and dataset_name:
                    with st.spinner("Preparing and uploading data..."):
                        zip_file = csv_to_json_zip(updated_df)

                        if upload_zip_file(zip_file, run_id, dataset_name):
                            st.success("Data uploaded successfully!")
                        else:
                            st.error("Failed to upload data")
                else:
                    st.error("Please provide both run ID and dataset name")


                    # Step 4: Convert to JSON and zip
                    st.subheader("Step 3: Convert to JSON and Zip")
                    st.dataframe(updated_df.head())
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
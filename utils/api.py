import streamlit as st
import requests
from config import API_BASE_URL
from typing import List, Dict
import pandas as pd

def get_users():
    if not st.session_state.token:
        st.error("Please login first")
        return {}
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    response = requests.get(f"{API_BASE_URL}/api/v1/users", headers=headers)
    if response.status_code == 200:
        users = response.json()
        st.session_state.user_data = {u["username"]: u["id"] for u in users}
        return st.session_state.user_data
    st.error(f"Failed to get users: {response.text}")
    return {}

def upload_zip_file(zip_file, run_id, name):
    if not st.session_state.token:
        st.error("Please login first")
        return False
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    files = {"file": (f"{name}.zip", zip_file, "application/zip")}
    data = {"run_id": run_id, "run_name": name, "modality": "text", "data_type": "sft"}
    response = requests.post(f"{API_BASE_URL}/api/v1/data_v2/upload", headers=headers, files=files, data=data)
    if response.status_code == 200:
        st.success(f"Uploaded {name} successfully!")
        return True
    st.error(f"Upload failed: {response.text}")
    return False

def get_pipeline_runs():
    if not st.session_state.token:
        st.error("Please login first")
        return []
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    response = requests.get(f"{API_BASE_URL}/api/v1/data_v2/pipeline", headers=headers)
    if response.status_code == 200:
        runs = response.json()
        st.session_state.pipeline_runs = runs
        return runs
    st.error(f"Failed to get pipeline runs: {response.text}")
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
    
def get_projects():
    if not st.session_state.token:
        st.error("Please login first")
        return []

    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    response = requests.get(f"{API_BASE_URL}/api/v1/projects", headers=headers)

    if response.status_code == 200:
        data = response.json()

        # ✅ safely get the list
        projects = data.get("projects", [])

        # store & return as a list of dicts
        st.session_state.projects = projects
        return projects

    st.error(f"Failed to get projects: {response.text}")
    return []


def get_datasets_by_project(project_id: str):
    """Fetch datasets for a given project."""
    if not st.session_state.token:
        st.error("Please login first")
        return []

    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    url = f"{API_BASE_URL}/api/v1/projects/{project_id}/datasets"

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if not data:
                st.warning("No datasets found for this project.")
                return []

            # Normalize and store in session
            datasets = [
                {
                    "project_id": item.get("id"),
                    "project_name": item.get("name"),
                    "dataset_id": item.get("dataset_id"),
                    "dataset_name": item.get("dataset_name"),
                }
                for item in data
            ]

            # Save in session state
            st.session_state.datasets_data = {
                d["dataset_name"]: d["dataset_id"] for d in datasets
            }

            return datasets

        else:
            st.error(f"Failed to fetch datasets: {response.status_code} - {response.text}")
            return []

    except Exception as e:
        st.error(f"Error fetching datasets for project {project_id}: {e}")
        return []
    

def get_dataset_records(project_id: str):
    """
    Fetch and aggregate all dataset records under a given project.
    Uses get_pipeline_data() to pull data for each dataset's run_id.
    Returns a combined DataFrame with dataset & project info.
    """
    if not st.session_state.token:
        st.error("Please login first")
        return pd.DataFrame()

    try:
        # --- Ensure project list exists ---
        if "projects" not in st.session_state or not st.session_state.projects:
            st.info("Fetching available projects...")
            get_projects()

        # --- Get datasets under the project ---
        st.info(f"Fetching datasets for project {project_id}...")
        datasets = get_datasets_by_project(project_id)
        if not datasets:
            st.warning("No datasets found for this project.")
            return pd.DataFrame()

        all_records = []

        # --- Loop through each dataset ---
        total_datasets = len(datasets)
        progress_bar = st.progress(0)
        for i, dataset in enumerate(datasets, start=1):
            dataset_name = dataset.get("dataset_name")
            run_id = dataset.get("run_id")

            if not run_id:
                st.warning(f"Dataset '{dataset_name}' has no run_id, skipping...")
                continue

            st.write(f"📦 Fetching records for dataset **{dataset_name}** ({i}/{total_datasets})")
            records = get_pipeline_data(run_id)

            if records:
                df = pd.DataFrame(records)
                df["dataset_name"] = dataset_name
                df["dataset_id"] = dataset.get("dataset_id")
                df["project_id"] = project_id
                df["project_name"] = dataset.get("project_name", "Unknown Project")
                all_records.append(df)

            progress_bar.progress(i / total_datasets)

        progress_bar.empty()

        if not all_records:
            st.warning("No dataset records found for this project.")
            return pd.DataFrame()

        # --- Combine all datasets ---
        combined_df = pd.concat(all_records, ignore_index=True)

        # --- Cache in session ---
        st.session_state.dataset_records = combined_df
        st.success(f"✅ Aggregated {len(combined_df)} total records across {len(datasets)} datasets.")
        return combined_df

    except Exception as e:
        st.error(f"Error fetching dataset records: {e}")
        return pd.DataFrame()



import streamlit as st
import requests
from config import API_BASE_URL
from typing import List, Dict

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
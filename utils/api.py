import streamlit as st
import requests
from config import API_BASE_URL

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

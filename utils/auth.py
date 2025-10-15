import streamlit as st
import requests
from config import API_BASE_URL

def login(username: str, password: str) -> bool:
    """Authenticate with the API and store token."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/token",
            data={"grant_type": "password", "username": username, "password": password}
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

import streamlit as st
import requests
from config import API_BASE_URL, ACCESS_TOKEN

def login(username: str = None, password: str = None) -> bool:
    """Authenticate with the API and store token.
    - If ACCESS_TOKEN is defined in config, use it directly.
    - Otherwise, use username/password authentication.
    """
    try:
        # ✅ 1. If config already provides a token, use it directly
        if ACCESS_TOKEN:
            st.session_state.token = ACCESS_TOKEN
            st.session_state.authenticated = True
            st.success("Authenticated using saved API token.")
            return True

        # ✅ 2. Otherwise, use username/password authentication
        if not username or not password:
            st.error("Username and password required if no token in config.")
            return False

        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/token",
            data={"grant_type": "password", "username": username, "password": password}
        )

        if response.status_code == 200:
            st.session_state.token = response.json().get("access_token")
            st.session_state.authenticated = True
            st.success("Login successful.")
            return True
        else:
            st.error(f"Login failed: {response.text}")
            return False

    except Exception as e:
        st.error(f"Error during login: {str(e)}")
        return False

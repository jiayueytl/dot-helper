import streamlit as st
from pages.dashboard import dashboard_page
from pages.upload_data import upload_data_page
from pages.query_data import query_data_page
from pages.generate_reports import reports_page
from pages.recycle_questions import recycle_page
from utils.auth import login
from utils.state import init_session_state

init_session_state()

def main():
    st.set_page_config(page_title="Data Pipeline Management", page_icon="📊", layout="wide")

    if not st.session_state.get("authenticated"):
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login(username, password):
                st.rerun()
        return

    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Select Page", ["Dashboard", "Upload Data", "Query Data", "Generate Reports", "Recycle Questions"])
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if page == "Dashboard":
        dashboard_page()
    elif page == "Upload Data":
        upload_data_page()
    elif page == "Query Data":
        query_data_page()
    elif page == "Generate Reports":
        reports_page()
    elif page == "Recycle Questions":
        recycle_page()

if __name__ == "__main__":
    # init_session_state()
    main()

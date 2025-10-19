# app.py
import streamlit as st
from lib import auth

st.set_page_config(
    page_title="Timesheet Home",
    layout="centered"
)

# Check login status and display appropriate content
if not auth.is_logged_in():
    st.title("Welcome to the Timesheet Application")
    st.info("Please log in using the link in the sidebar to continue.")
    # In Streamlit, pages in the `pages/` directory are automatically added to the sidebar.
    # We can also explicitly link to it.
    st.page_link("pages/login.py", label="Go to Login Page", icon="🔐")

else:
    user = auth.get_current_user()
    st.title(f"👋 Welcome back, {user['full_name']}!")
    st.subheader("Dashboard")
    st.markdown("---")
    
    st.write("Use the navigation panel on the left to access different parts of the application:")
    
    role = user.get('role')

    # Display role-specific navigation hints
    if role in ['user', 'approver', 'admin']:
        st.page_link("pages/employee_timesheet_entry.py", label="My Weekly Timesheet", icon="📅")
    
    if role in ['approver', 'admin']:
        st.page_link("pages/manager_approvals.py", label="Manager Dashboard", icon="🧾")
    
    if role == 'admin':
        st.page_link("pages/project_admin.py", label="Project Administration", icon="📁")
        st.page_link("pages/admin_create_user.py", label="Create New User", icon="👤")

    st.markdown("---")
    if st.button("Logout"):
        auth.logout_user()
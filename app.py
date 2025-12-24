import streamlit as st
from lib import auth

# Global Config
st.set_page_config(page_title="Timesheet App", layout="wide")

# --- Define All Available Pages ---
login_page = st.Page("views/login.py", title="Login", icon="🔐")
home_page = st.Page("views/employee_home.py", title="Home", icon="🏠")
timesheet_page = st.Page("views/employee_timesheet.py", title="My Timesheet", icon="📅")
manager_page = st.Page("views/manager_dashboard.py", title="Manager Dashboard", icon="🎛️")
reports_page = st.Page("views/reports_dashboard.py", title="Reports & Analytics", icon="📈")

# --- Auth Check ---
if not auth.is_logged_in():
    pg = st.navigation([login_page])
else:
    user = auth.get_current_user()
    role = user['role']
    
    # 1. Common Pages
    available_pages = {
        "General": [home_page]
    }

    # 2. Employee Pages (Everyone is an employee essentially)
    if role in ["user", "approver", "admin", "dept_manager"]:
        available_pages["General"].append(timesheet_page)

    # 3. Manager/Admin Pages
    # ADDED: dept_manager
    if role in ["approver", "admin", "dept_manager"]:
        available_pages["Management"] = [manager_page, reports_page]

    pg = st.navigation(available_pages)
    
    # Sidebar Info
    st.sidebar.markdown(f"👤 **{user['full_name']}**")
    st.sidebar.caption(f"Role: {role.upper()}")
    if st.sidebar.button("Logout"):
        auth.logout_user()

pg.run()
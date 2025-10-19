# pages/login.py
import streamlit as st
from lib import auth

st.set_page_config(page_title="Login", layout="centered")

st.title("🔐 Login to Timesheet App")

if auth.is_logged_in():
    user = auth.get_current_user()
    st.success(f"Welcome {user['full_name'] or user['username']} ({user['role']})")
    if st.button("Logout"):
        auth.logout_user()
else:
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if not username or not password:
                st.error("Please enter both username and password.")
            elif auth.login_user(username, password):
                # Rerun to show the "Welcome" message and logout button
                st.rerun()
            else:
                st.error("Invalid username or password.")

    st.info("If you don't have an account, contact your system admin.")
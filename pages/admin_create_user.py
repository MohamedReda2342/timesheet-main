# pages/admin_create_user.py
import streamlit as st
from lib import auth

st.set_page_config(page_title="Create User", layout="centered")

# auth.login_required(roles=["admin"])

st.title("👤 Create a New User")

with st.form("create_user_form"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    full_name = st.text_input("Full Name")
    email = st.text_input("Email")
    role = st.selectbox("Role", ["user", "approver", "admin"])
    submit = st.form_submit_button("Create")

    if submit:
        if not username or not password:
            st.error("Username and password are required.")
        else:
            try:
                user = auth.create_user(username, password, role, full_name, email)
                st.success(f"✅ User '{user.username}' created successfully.")
            except Exception as e:
                st.error(str(e))

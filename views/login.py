import streamlit as st
from lib import auth
from utils.state_helpers import track_page_visit

# Note: We don't use st.set_page_config here because app.py handles it
track_page_visit("login")

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.title("🔐 Login")
    st.markdown("### Corporate Timesheet System")
    
    with st.form("login_form"):
        username = st.text_input("SAP ID / Username")
        password = st.text_input("Password", type="password")
        
        if st.form_submit_button("Sign In", type="primary", use_container_width=True):
            if not username or not password:
                st.error("Credentials required.")
            elif auth.login_user(username, password):
                st.rerun()
            else:
                st.error("Invalid credentials.")
    
    st.caption("Contact IT Support if you cannot access your account.")
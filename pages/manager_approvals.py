# ./pages/manager_approvals.py
import streamlit as st
from lib import auth
from tabs import tab_approvals, tab_assignments, tab_tasks

# ================================================================
# 🔐 Role check and page setup
# ================================================================
st.set_page_config(page_title="Manager Dashboard", layout="wide")
auth.login_required(roles=["approver", "admin"])
user = auth.get_current_user()
st.title("🧾 Manager Dashboard")

# Check if user is Admin
IS_ADMIN = user.get('role') == 'admin'

# ================================================================
# 🧭 Main UI Tabs
# ================================================================

tab_names = ["**Manage Approvals**", "**Manage Assignments**"]
if IS_ADMIN:
    tab_names.append("**Task Definitions**")

tabs = st.tabs(tab_names)

# ----------------------------------------------------------------
# Render Tab Content
# ----------------------------------------------------------------
with tabs[0]:
    tab_approvals.render(user)

with tabs[1]:
    # Note: Dialog triggers are removed from render() and handled below
    tab_assignments.render(user, IS_ADMIN)

if IS_ADMIN:
    with tabs[2]:
        # Note: Dialog triggers are removed from render() and handled below
        tab_tasks.render(user)

# ================================================================
# 🔧 Centralized Dialog Manager (CRITICAL SECTION)
# ================================================================
# This strictly enforces that ONLY ONE dialog function is called per rerun.
# The 'elif' chain prevents "Only one dialog allowed" crashes.

if st.session_state.get("show_assignment_wizard"):
    tab_assignments.assignment_wizard_dialog(user['user_id'], IS_ADMIN)

elif st.session_state.get("view_assign"):
    tab_assignments.view_assignment_dialog(st.session_state.get("view_assign"))

elif st.session_state.get("edit_assign"):
    tab_assignments.edit_assignment_dialog(st.session_state.get("edit_assign"))

elif st.session_state.get("del_assign"):
    tab_assignments.confirm_delete_dialog(st.session_state.get("del_assign"))

elif st.session_state.get("show_task_dialog"):
    tab_tasks.task_form_dialog(st.session_state.get("edit_task_id"), user['user_id'])

elif st.session_state.get("delete_def_info"):
    tab_tasks.confirm_delete_dialog(st.session_state.get("delete_def_info"))

elif st.session_state.get("reject_entry_info"):
    tab_approvals.reject_timesheet_dialog(st.session_state.get("reject_entry_info"), user['user_id'])
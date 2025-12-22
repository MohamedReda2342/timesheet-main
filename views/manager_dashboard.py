import streamlit as st
from lib import auth
from tabs import tab_approvals, tab_assignments, tab_tasks, tab_projects, tab_task_types
from utils.state_helpers import track_page_visit

track_page_visit("manager_approvals")

st.title("🎛️ Manager Dashboard")

user = auth.get_current_user()
IS_ADMIN = user.get('role') == 'admin'

# --- Tabs ---
tab_names = ["**Manage Approvals**", "**Manage Assignments**"]
if IS_ADMIN:
    tab_names.extend(["**Task Definitions**", "**Manage Projects**", "**Task Types**"])

tabs = st.tabs(tab_names)

with tabs[0]:
    tab_approvals.render(user, IS_ADMIN)
with tabs[1]:
    tab_assignments.render(user, IS_ADMIN)

if IS_ADMIN:
    with tabs[2]: tab_tasks.render(user)
    with tabs[3]: tab_projects.render()
    with tabs[4]: tab_task_types.render()

# --- Dialogs ---
if st.session_state.get("show_assignment_wizard"):
    tab_assignments.assignment_wizard_dialog(user['user_id'], IS_ADMIN)
elif st.session_state.get("view_assign"):
    tab_assignments.view_assignment_dialog(st.session_state.get("view_assign"))
elif st.session_state.get("edit_assign"):
    tab_assignments.edit_assignment_dialog(st.session_state.get("edit_assign"), user['user_id'], IS_ADMIN)
elif st.session_state.get("del_assign"):
    tab_assignments.confirm_delete_dialog(st.session_state.get("del_assign"))
elif st.session_state.get("show_task_dialog"):
    tab_tasks.task_form_dialog(st.session_state.get("edit_task_id"), user['user_id'])
elif st.session_state.get("delete_def_info"):
    tab_tasks.confirm_delete_dialog(st.session_state.get("delete_def_info"))
elif st.session_state.get("show_project_dialog"):
    tab_projects.project_form_dialog(st.session_state.get("edit_project_id"))
elif st.session_state.get("view_project_info"):
    tab_projects.show_project_details_dialog(st.session_state.get("view_project_info"))
elif st.session_state.get("delete_project_info"):
    tab_projects.confirm_delete_dialog(st.session_state.get("delete_project_info"))
elif st.session_state.get("show_type_dialog"):
    tab_task_types.task_type_dialog(st.session_state.get("edit_type_id"))
elif st.session_state.get("reject_entry_info"):
    tab_approvals.reject_timesheet_dialog(st.session_state.get("reject_entry_info"), user['user_id'])
elif st.session_state.get("edit_entry_info"):
    tab_approvals.edit_entry_dialog(st.session_state.get("edit_entry_info"), user['user_id'])
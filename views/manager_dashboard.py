import streamlit as st
from lib import auth
from tabs import tab_approvals, tab_assignments, tab_tasks, tab_projects, tab_task_types
from utils.state_helpers import track_page_visit

track_page_visit("manager_approvals")

st.title("🎛️ Manager Dashboard")

user = auth.get_current_user()
IS_ADMIN = user.get('role') == 'admin'
IS_DEPT_MANAGER = user.get('role') == 'dept_manager'

# Define the tabs configuration
# Requested Order: Approvals -> Projects -> Task Types -> Tasks -> Assignments
dashboard_tabs = [
    {
        "name": "Approvals",
        "render": lambda: tab_approvals.render(user, IS_ADMIN),
        "visible": True  # All managers/admins/directors need this
    },
    {
        "name": "Projects",
        "render": lambda: tab_projects.render(),
        "visible": IS_ADMIN  # Admin only
    },
    {
        "name": "Task Types",
        "render": lambda: tab_task_types.render(),
        "visible": IS_ADMIN  # Admin only
    },
    {
        "name": "Tasks",
        "render": lambda: tab_tasks.render(user),
        "visible": IS_ADMIN  # Admin only
    },
    {
        "name": "Assignments",
        "render": lambda: tab_assignments.render(user, IS_ADMIN),
        "visible": not IS_DEPT_MANAGER  # Hidden for Directors/Dept Managers
    }
]

# Filter to get only the tabs the current user is allowed to see
visible_tabs = [t for t in dashboard_tabs if t["visible"]]

if not visible_tabs:
    st.error("Access Denied: You do not have permission to view any dashboard tabs.")
else:
    # Create the tabs
    tab_labels = [f"**{t['name']}**" for t in visible_tabs]
    st_tabs = st.tabs(tab_labels)

    # Render content inside each tab
    for i, tab_config in enumerate(visible_tabs):
        with st_tabs[i]:
            tab_config["render"]()

# --- Dialogs Handling ---
# These checks handle the 'modal' dialogs triggered from within the tabs.
# Since Streamlit dialogs (experimental) or custom logic relies on session state,
# we place this router here to ensure the active dialog is rendered on top.

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
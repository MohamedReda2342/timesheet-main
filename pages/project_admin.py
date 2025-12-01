# ./pages/project_admin.py
import streamlit as st
import pandas as pd
from datetime import date
from lib import auth, admin_queries as aq

# ================================================================
# 🔐 Role check and page setup
# ================================================================
st.set_page_config(page_title="Project Administration", layout="wide")
auth.login_required(roles=["admin"])
st.title("📁 Project Management Dashboard")

ROLE_NAME_MAP = {"Employee": 6, "Admin": 5, "ProjectManager": 4}

# ================================================================
# 🎨 Dialogs
# ================================================================

@st.dialog("✏️ Edit User")
def user_form_dialog(edit_user):
    with st.form("user_form"):
        st.text_input("SAP ID", value=str(edit_user["username"]), disabled=True)
        full_name = st.text_input("Full Name", value=edit_user.get("full_name", ""))
        email = st.text_input("Email", value=edit_user.get("email", ""))
        
        role_options = list(ROLE_NAME_MAP.keys())
        current_role = edit_user.get("role", "Employee")
        if current_role not in role_options: current_role = "Employee"
            
        role = st.selectbox("Role", role_options, index=role_options.index(current_role))

        submitted = st.form_submit_button("💾 Update User", type="primary")
        if submitted:
            aq.update_user(edit_user["user_id"], full_name, email, role)
            st.success("✅ User updated successfully!")
            st.rerun()

@st.dialog("⚠️ Confirm User Deletion")
def confirm_user_delete_dialog(user_info):
    st.warning(f"Delete user **{user_info['full_name']}**?")
    col1, col2 = st.columns(2)
    if col1.button("Yes, Delete", type="primary"):
        aq.delete_user(user_info["user_id"])
        st.success("User deleted.")
        st.rerun()
    if col2.button("Cancel"):
        st.rerun()

@st.dialog("ℹ️ Project Details")
def show_project_details_dialog(project):
    st.subheader(f"📂 {project['project_name']}")
    
    billable_status = "✅ Yes" if project.get('is_billable') else "❌ No"
    
    st.markdown(f"""
    | Field | Value |
    | :--- | :--- |
    | **Project Number** | {project.get('project_number') or 'N/A'} |
    | **Client** | {project.get('client_name') or 'N/A'} |
    | **Department** | {project.get('DepName') or 'N/A'} |
    | **Billable** | {billable_status} |
    | **Status** | {project.get('status')} |
    | **Planned Hours** | {float(project.get('planned_hours') or 0):.2f} hrs |
    | **Start Date** | {project.get('start_date')} |
    | **End Date** | {project.get('end_date') or 'Ongoing'} |
    """)
    
    if st.button("Close", type="primary"):
        st.rerun()

@st.dialog("Project Form")
def project_form_dialog(project_id=None):
    project = aq.get_project(project_id) if project_id else {}
    is_edit = bool(project)
    
    all_departments = aq.fetch_departments()
    all_approvers = aq.get_approvers()
    current_approver_ids = aq.get_project_approvers(project_id) if project_id else []
    
    st.write(f"### {'Edit' if is_edit else 'Add New'} Project")

    with st.form("project_form"):
        c1, c2 = st.columns(2)
        project_name = c1.text_input("Project Name*", value=project.get("project_name", ""))
        project_number = c2.text_input("Project Number", value=project.get("project_number", ""))
        
        client_name = st.text_input("Client Name", value=project.get("client_name", ""))
        
        dep_options = {d['DepId']: d['DepName'] for d in all_departments}
        dep_keys = list(dep_options.keys())
        current_dep_id = project.get('DepId')
        default_idx = dep_keys.index(current_dep_id) if current_dep_id in dep_keys else 0
        
        selected_dep_id = st.selectbox(
            "Department", 
            options=dep_keys, 
            format_func=lambda x: dep_options[x],
            index=default_idx
        )
        
        app_options = {a['user_id']: f"{a['full_name']} (SAP: {a['username']})" for a in all_approvers}
        valid_default_approvers = [uid for uid in current_approver_ids if uid in app_options]
        
        selected_approver_ids = st.multiselect(
            "Approvers (Project Managers/Admins)",
            options=app_options.keys(),
            format_func=lambda x: app_options[x],
            default=valid_default_approvers
        )

        c3, c4 = st.columns(2)
        planned_hours = c3.number_input("Planned Hours", min_value=0.0, value=float(project.get("planned_hours") or 0.0))
        status_options = ["active", "on-hold", "completed"]
        status = c4.selectbox("Status", status_options, index=status_options.index(project.get("status", "active")))

        c5, c6 = st.columns(2)
        start_date_val = c5.date_input("Start Date", value=project.get("start_date") or date.today())
        end_date_val = c6.date_input("End Date", value=project.get("end_date") or None)
        
        # New Billable Checkbox
        is_billable = st.checkbox("Is Project Billable?", value=project.get("is_billable", True))

        submitted = st.form_submit_button("💾 Save", type="primary")
        if submitted:
            if not project_name:
                st.error("Project name is required.")
            else:
                data = {
                    "project_id": project_id,
                    "project_name": project_name,
                    "project_number": project_number,
                    "client_name": client_name,
                    "planned_hours": planned_hours,
                    "start_date": start_date_val,
                    "end_date": end_date_val,
                    "status": status,
                    "DepId": selected_dep_id,
                    "is_billable": is_billable
                }
                aq.upsert_project(data, selected_approver_ids)
                st.success(f"✅ Project saved successfully!")
                st.rerun()

@st.dialog("Confirm Deletion")
def confirm_delete_dialog(project):
    st.warning(f"Delete project **'{project['project_name']}'**?")
    c1, c2 = st.columns(2)
    if c1.button("Yes, Delete", type="primary"):
        aq.delete_project(project['project_id'])
        st.success("Project deleted.")
        st.rerun()
    if c2.button("Cancel"):
        st.rerun()

# ================================================================
# 🧭 Main UI
# ================================================================
tab1, tab2 = st.tabs(["**Manage Projects**", "**Manage Users**"])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Add New Project", type="primary", use_container_width=True):
            st.session_state.edit_project_id = None
            st.session_state.show_project_dialog = True

    st.write("### Existing Projects")
    
    cols = st.columns([0.5, 1, 2, 1.5, 1, 1, 1, 0.5, 0.5, 0.5, 0.5])
    headers = ["ID", "Prj No.", "Project Name", "Client", "Dept", "Hrs", "$", "Status", "View", "Edit", "Del"]
    for col, h in zip(cols, headers):
        col.write(f"**{h}**")
    
    all_projects = aq.list_projects()
    for p in all_projects:
        c = st.columns([0.5, 1, 2, 1.5, 1, 1, 1, 0.5, 0.5, 0.5, 0.5])
        c[0].write(p["project_id"])
        c[1].write(p.get("project_number") or "-")
        c[2].write(p["project_name"])
        c[3].write(p["client_name"] or "-")
        c[4].write(p.get("DepName") or "-")
        c[5].write(f"{float(p.get('planned_hours') or 0):.0f}")
        c[6].write("✅" if p.get("is_billable") else "❌")
        c[7].write(p["status"])

        if c[8].button("👁️", key=f"view_{p['project_id']}", help="View Details"):
            st.session_state.view_project_info = p

        if c[9].button("✏️", key=f"edit_{p['project_id']}", help="Edit project"):
            st.session_state.edit_project_id = p["project_id"]
            st.session_state.show_project_dialog = True

        if c[10].button("🗑️", key=f"del_{p['project_id']}", help="Delete project"):
            st.session_state.delete_project_info = p

with tab2:
    st.subheader("👤 Existing Users")
    st.caption("Users are managed externally.")
    users = aq.fetch_all_users()

    if not users:
        st.info("No users found.")
    else:
        df = pd.DataFrame(users)
        cols = st.columns([1, 2, 2, 3, 2, 2, 2])
        headers = ["ID", "Full Name", "SAP ID", "Email", "Role", "Edit", "Delete"]
        for col, h in zip(cols, headers):
            col.write(f"**{h}**")

        for u in users:
            c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 2, 2, 3, 2, 2, 2])
            c1.write(u["user_id"])
            c2.write(u["full_name"] or "-")
            c3.write(u["username"]) 
            c4.write(u["email"] or "-")
            c5.write(u["role"])

            if c6.button("✏️", key=f"user_edit_{u['user_id']}", use_container_width=True):
                st.session_state.edit_user_info = u

            if c7.button("🗑️", key=f"user_del_{u['user_id']}", use_container_width=True):
                st.session_state.delete_user_info = u

# ================================================================
# 🔧 Dialog Invocation
# ================================================================
if st.session_state.get("show_project_dialog"):
    project_form_dialog(st.session_state.get("edit_project_id"))
    del st.session_state["show_project_dialog"]
    if "edit_project_id" in st.session_state: del st.session_state["edit_project_id"]

if st.session_state.get("view_project_info"):
    show_project_details_dialog(st.session_state.get("view_project_info"))
    del st.session_state["view_project_info"]

if st.session_state.get("delete_project_info"):
    confirm_delete_dialog(st.session_state.get("delete_project_info"))
    del st.session_state["delete_project_info"]

if st.session_state.get("edit_user_info"):
    user_form_dialog(st.session_state.get("edit_user_info"))
    del st.session_state["edit_user_info"]

if st.session_state.get("delete_user_info"):
    confirm_user_delete_dialog(st.session_state.get("delete_user_info"))
    del st.session_state["delete_user_info"]
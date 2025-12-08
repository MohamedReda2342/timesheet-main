# ./tabs/tab_projects.py
import streamlit as st
import pandas as pd
from datetime import date
from lib import admin_queries as aq
from utils.state_helpers import clear_other_dialogs

# ================================================================
# 🎨 Dialogs
# ================================================================

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
        del st.session_state["view_project_info"]
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
        
        # Approver Selection
        app_options = {a['user_id']: f"{a['full_name']} (SAP: {a['username']})" for a in all_approvers}
        # Filter defaults to ensure they still exist in the options
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
                
                # Close Dialog
                if "show_project_dialog" in st.session_state:
                    del st.session_state["show_project_dialog"]
                if "edit_project_id" in st.session_state: 
                    del st.session_state["edit_project_id"]
                st.rerun()

@st.dialog("Confirm Deletion")
def confirm_delete_dialog(project):
    st.warning(f"Delete project **'{project['project_name']}'**?")
    st.caption("This will cascade delete all associated Tasks and Assignments!")
    
    c1, c2 = st.columns(2)
    if c1.button("Yes, Delete", type="primary"):
        aq.delete_project(project['project_id'])
        st.success("Project deleted.")
        if "delete_project_info" in st.session_state:
            del st.session_state["delete_project_info"]
        st.rerun()
    if c2.button("Cancel"):
        if "delete_project_info" in st.session_state:
            del st.session_state["delete_project_info"]
        st.rerun()

# ================================================================
# 🧭 Main Render
# ================================================================

def render():
    col1, col2 = st.columns([3, 1])
    col1.subheader("Manage Projects")
    with col2:
        if st.button("➕ Add New Project", type="primary", use_container_width=True):
            clear_other_dialogs("show_project_dialog")
            st.session_state.edit_project_id = None
            st.session_state.show_project_dialog = True
            st.rerun()

    st.write("### Existing Projects")
    
    # Table Header
    cols = st.columns([0.5, 1, 2, 1.5, 1, 1, 1, 0.5, 0.5, 0.5, 0.5])
    headers = ["ID", "Prj No.", "Project Name", "Client", "Dept", "Hrs", "$", "Status", "View", "Edit", "Del"]
    for col, h in zip(cols, headers):
        col.write(f"**{h}**")
    
    all_projects = aq.list_projects()
    
    if not all_projects:
        st.info("No projects found.")
        return

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
            clear_other_dialogs("view_project_info")
            st.session_state.view_project_info = p
            st.rerun()

        if c[9].button("✏️", key=f"edit_{p['project_id']}", help="Edit project"):
            clear_other_dialogs("show_project_dialog")
            st.session_state.edit_project_id = p["project_id"]
            st.session_state.show_project_dialog = True
            st.rerun()

        if c[10].button("🗑️", key=f"del_{p['project_id']}", help="Delete project"):
            clear_other_dialogs("delete_project_info")
            st.session_state.delete_project_info = p
            st.rerun()
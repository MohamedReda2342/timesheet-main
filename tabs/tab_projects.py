# ./tabs/tab_projects.py
import streamlit as st
import pandas as pd
from datetime import date
from lib import admin_queries as aq
from lib.db import get_connection # Added import
from utils.state_helpers import clear_other_dialogs

# ================================================================
# 🛠️ Helpers
# ================================================================

def get_project_approver_ids(project_id):
    """
    Fetches the list of User IDs (Project Managers) assigned to this project.
    Defined locally to avoid AttributeError if missing in admin_queries.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM project_approvers WHERE project_id = ?", (project_id,))
        rows = cursor.fetchall()
        return [row[0] for row in rows]

# ================================================================
# 🎨 Dialogs
# ================================================================

@st.dialog("Project Form")
def project_form_dialog(project_id=None):
    is_edit = bool(project_id)
    # Fetch existing data if editing
    project = aq.get_project(project_id) if project_id else {}
    
    st.subheader(f"{'Edit' if is_edit else 'New'} Project")
    
    with st.form("project_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Project Name", value=project.get("project_name", ""))
        client = c2.text_input("Client Name", value=project.get("client_name", ""))
        
        c3, c4 = st.columns(2)
        p_num = c3.text_input("Project Number", value=project.get("project_number", ""))
        status = c4.selectbox("Status", ["active", "completed", "on-hold"], index=["active", "completed", "on-hold"].index(project.get("status", "active")))
        
        c5, c6 = st.columns(2)
        start_date = c5.date_input("Start Date", value=project.get("start_date", date.today()))
        end_date = c6.date_input("End Date", value=project.get("end_date", None))

        c7, c8 = st.columns(2)
        planned_hours = c7.number_input("Planned Hours", min_value=0.0, value=float(project.get("planned_hours") or 0.0))
        is_billable = c8.checkbox("Billable Project", value=project.get("is_billable", True))

        # Departments
        depts = aq.fetch_departments()
        dept_opts = {d['DepId']: d['DepName'] for d in depts}
        
        curr_dept = project.get("DepId")
        # Default to first department if current is None or not found
        if curr_dept in dept_opts:
            idx_dept = list(dept_opts.keys()).index(curr_dept)
        else:
            idx_dept = 0
            
        sel_dept = st.selectbox("Department", options=dept_opts.keys(), format_func=lambda x: dept_opts[x], index=idx_dept)

        # Approvers (Multi-select)
        # Fetch all possible users
        users = aq.fetch_all_users()
        user_opts = {u['user_id']: u['full_name'] for u in users}
        
        # Fetch current approvers for this project if editing
        current_approver_ids = []
        if is_edit:
            # FIX: Use local helper function instead of aq.get_project_approver_ids
            current_approver_ids = get_project_approver_ids(project_id)
        
        selected_approver_ids = st.multiselect(
            "Assign Approvers (Project Managers)", 
            options=user_opts.keys(), 
            format_func=lambda x: user_opts[x], 
            default=current_approver_ids
        )

        if st.form_submit_button("💾 Save Project"):
            if not name:
                st.error("Project Name is required.")
            else:
                data = {
                    "project_name": name,
                    "client_name": client,
                    "project_number": p_num,
                    "status": status,
                    "start_date": start_date,
                    "end_date": end_date,
                    "planned_hours": planned_hours,
                    "is_billable": is_billable,
                    "DepId": sel_dept
                }
                
                try:
                    # FIX: Passed project_id as the first argument
                    aq.upsert_project(project_id, data, selected_approver_ids)
                    st.success("Project saved successfully!")
                    
                    if "show_project_dialog" in st.session_state:
                        del st.session_state["show_project_dialog"]
                    if "edit_project_id" in st.session_state:
                        del st.session_state["edit_project_id"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving project: {e}")

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

@st.dialog("Delete Project")
def confirm_delete_dialog(project):
    st.warning(f"Are you sure you want to delete **{project['project_name']}**?")
    st.caption("This action cannot be undone.")
    
    col1, col2 = st.columns(2)
    if col1.button("Yes, Delete", type="primary"):
        aq.delete_project(project['project_id'])
        st.success("Deleted.")
        if "delete_project_info" in st.session_state:
            del st.session_state["delete_project_info"]
        st.rerun()
        
    if col2.button("Cancel"):
        if "delete_project_info" in st.session_state:
            del st.session_state["delete_project_info"]
        st.rerun()

# ================================================================
# Main Render
# ================================================================

def render():
    c1, c2 = st.columns([3, 1])
    c1.subheader("Manage Projects")
    
    if c2.button("➕ Create New Project", type="primary", use_container_width=True):
        clear_other_dialogs("show_project_dialog")
        st.session_state.edit_project_id = None
        st.session_state.show_project_dialog = True
        st.rerun()

    # Table Layout
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
            
        if c[9].button("✏️", key=f"edit_{p['project_id']}", help="Edit Project"):
            clear_other_dialogs("show_project_dialog")
            st.session_state.edit_project_id = p['project_id']
            st.session_state.show_project_dialog = True
            st.rerun()

        if c[10].button("🗑️", key=f"del_{p['project_id']}", help="Delete Project"):
            clear_other_dialogs("delete_project_info")
            st.session_state.delete_project_info = p
            st.rerun()
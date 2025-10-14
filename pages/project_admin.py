# pages/project_admin.py
import streamlit as st
from datetime import date
from lib.db import get_db
from lib.auth import login_required as require_role

# ================================================================
# 🔐 Authentication check
# ================================================================
# require_role(["admin"])
st.set_page_config(page_title="Project Administration", layout="wide")
st.title("📁 Project Management Dashboard")

# ================================================================
# 🧩 Helper Functions
# ================================================================
def list_projects():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects ORDER BY project_id DESC")
    projects = cursor.fetchall()
    cursor.close()
    conn.close()
    return projects

def get_project(project_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects WHERE project_id = %s", (project_id,))
    project = cursor.fetchone()
    cursor.close()
    conn.close()
    return project

def upsert_project(data):
    conn = get_db()
    cursor = conn.cursor()
    if data.get("project_id"):
        cursor.execute("""
            UPDATE projects
            SET project_name=%s, client_name=%s, start_date=%s, end_date=%s, status=%s
            WHERE project_id=%s
        """, (
            data["project_name"], data["client_name"], data["start_date"],
            data["end_date"], data["status"], data["project_id"]
        ))
    else:
        cursor.execute("""
            INSERT INTO projects (project_name, client_name, start_date, end_date, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data["project_name"], data["client_name"],
            data["start_date"], data["end_date"], data["status"]
        ))
    conn.commit()
    cursor.close()
    conn.close()

def delete_project(project_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE project_id=%s", (project_id,))
    conn.commit()
    cursor.close()
    conn.close()

def get_approvers():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, username, full_name FROM users WHERE role='approver'")
    approvers = cursor.fetchall()
    cursor.close()
    conn.close()
    return approvers

def get_project_approvers(project_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM project_approvers WHERE project_id=%s", (project_id,))
    result = [r[0] for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return result

def set_project_approvers(project_id, user_ids):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM project_approvers WHERE project_id=%s", (project_id,))
    for uid in user_ids:
        cursor.execute("INSERT INTO project_approvers (project_id, user_id) VALUES (%s, %s)", (project_id, uid))
    conn.commit()
    cursor.close()
    conn.close()

# ================================================================
# 🧭 Tabs
# ================================================================
tab1, tab2 = st.tabs(["Manage Projects", "Assign Approvers"])

# ================================================================
# 🧱 Tab 1 - Manage Projects
# ================================================================
with tab1:
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Add New Project", type="primary"):
            st.session_state["show_add_dialog"] = True

    # Display Projects Table
    st.write("### Existing Projects")
    cols = st.columns([1, 3, 3, 2, 2, 2, 1, 1])
    headers = ["ID", "Project Name", "Client", "Start", "End", "Status", "✏️", "🗑️"]
    for col, h in zip(cols, headers):
        col.write(f"**{h}**")

    projects = list_projects()
    for p in projects:
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1, 3, 3, 2, 2, 2, 1, 1])
        c1.write(p["project_id"])
        c2.write(p["project_name"])
        c3.write(p["client_name"] or "-")
        c4.write(str(p["start_date"]) if p["start_date"] else "-")
        c5.write(str(p["end_date"]) if p["end_date"] else "-")
        c6.write(p["status"])

        if c7.button("Edit", key=f"edit_{p['project_id']}"):
            st.session_state["edit_project"] = p["project_id"]

        if c8.button("Delete", key=f"del_{p['project_id']}"):
            st.session_state["delete_project"] = p["project_id"]

# ================================================================
# 🧩 Dialogs
# ================================================================
@st.dialog("Add / Edit Project")
def add_edit_project_dialog(project=None):
    is_edit = project is not None
    with st.form("add_edit_project_form"):
        project_name = st.text_input("Project Name", value=project["project_name"] if is_edit else "")
        client_name = st.text_input("Client Name", value=project["client_name"] if is_edit else "")
        start_date_val = st.date_input("Start Date", value=project["start_date"] if is_edit and project["start_date"] else date.today())
        end_date_val = st.date_input("End Date", value=project["end_date"] if is_edit and project["end_date"] else date.today())
        status = st.selectbox("Status", ["active", "on-hold", "completed"], index=["active", "on-hold", "completed"].index(project["status"]) if is_edit else 0)

        col1, col2 = st.columns(2)
        with col1:
            save_btn = st.form_submit_button("💾 Save", type="primary")
        with col2:
            cancel_btn = st.form_submit_button("Cancel")

        if save_btn:
            if not project_name:
                st.error("Project name is required.")
                return
            data = {
                "project_id": project["project_id"] if is_edit else None,
                "project_name": project_name,
                "client_name": client_name,
                "start_date": start_date_val,
                "end_date": end_date_val,
                "status": status
            }
            upsert_project(data)
            st.success("✅ Project saved successfully!")
            st.rerun()
        if cancel_btn:
            st.rerun()

@st.dialog("Delete Project")
def delete_project_dialog(pid):
    st.warning("Are you sure you want to delete this project? This action cannot be undone.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Yes, Delete", type="primary"):
            delete_project(pid)
            st.success("✅ Project deleted.")
            st.rerun()
    with c2:
        if st.button("Cancel"):
            st.rerun()

# ================================================================
# 🔧 Show dialogs conditionally
# ================================================================
if "show_add_dialog" in st.session_state and st.session_state["show_add_dialog"]:
    add_edit_project_dialog()
    st.session_state["show_add_dialog"] = False

if "edit_project" in st.session_state and st.session_state["edit_project"]:
    proj = get_project(st.session_state["edit_project"])
    add_edit_project_dialog(proj)
    st.session_state["edit_project"] = None

if "delete_project" in st.session_state and st.session_state["delete_project"]:
    delete_project_dialog(st.session_state["delete_project"])
    st.session_state["delete_project"] = None

# ================================================================
# 👥 Tab 2 - Assign Approvers
# ================================================================
with tab2:
    st.write("### Assign Approvers to Projects")

    projects = list_projects()
    approvers = get_approvers()
    if not projects or not approvers:
        st.info("No projects or approvers found.")
    else:
        proj_option = st.selectbox("Select Project", options=[(p["project_id"], p["project_name"]) for p in projects], format_func=lambda x: x[1])
        pid = proj_option[0]
        current = get_project_approvers(pid)
        approver_map = {a["full_name"] or a["username"]: a["user_id"] for a in approvers}

        selected = st.multiselect("Select Approvers", options=approver_map.keys(), default=[k for k, v in approver_map.items() if v in current])
        if st.button("💾 Save Approvers"):
            ids = [approver_map[name] for name in selected]
            set_project_approvers(pid, ids)
            st.success("✅ Approvers updated successfully!")

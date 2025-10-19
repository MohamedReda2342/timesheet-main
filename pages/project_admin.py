# pages/project_admin.py
import streamlit as st
import pandas as pd
from datetime import date
from lib import db, auth

# ================================================================
# 🔐 Role check and page setup
# ================================================================
st.set_page_config(page_title="Project Administration", layout="wide")
auth.login_required(roles=["admin"])
st.title("📁 Project Management Dashboard")

# ================================================================
# 🧩 Database Helper Functions
# ================================================================

# User Management Functions
def fetch_all_users():
    conn = db.get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT user_id, username, full_name, email, role, created_at FROM users ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def create_user(username, password, role, full_name=None, email=None):
    conn = db.get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (username, password_hash, role, full_name, email)
            VALUES (%s, SHA2(%s, 256), %s, %s, %s)
        """, (username, password, role, full_name, email))
        conn.commit()
        return {"username": username}
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def update_user(user_id, full_name, email, role):
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET full_name = %s, email = %s, role = %s
        WHERE user_id = %s
    """, (full_name, email, role, user_id))
    conn.commit()
    cur.close()
    conn.close()

def delete_user(user_id):
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

# Project Management Functions
def list_projects():
    """Fetches all projects from the database."""
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects ORDER BY project_id DESC")
    projects = cursor.fetchall()
    cursor.close()
    conn.close()
    return projects

def get_project(project_id):
    """Fetches a single project by its ID."""
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects WHERE project_id = %s", (project_id,))
    project = cursor.fetchone()
    cursor.close()
    conn.close()
    return project

def upsert_project(data):
    """Updates an existing project or inserts a new one."""
    conn = db.get_db_connection()
    cursor = conn.cursor()
    if data.get("project_id"):
        # Update existing project
        cursor.execute("""
            UPDATE projects
            SET project_name=%s, client_name=%s, start_date=%s, end_date=%s, status=%s
            WHERE project_id=%s
        """, (
            data["project_name"], data["client_name"], data["start_date"],
            data["end_date"], data["status"], data["project_id"]
        ))
    else:
        # Insert new project
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
    """Deletes a project from the database."""
    conn = db.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM projects WHERE project_id=%s", (project_id,))
        conn.commit()
    except Exception as e:
        st.error(f"Could not delete project. It might be in use by timesheets. Error: {e}")
    finally:
        cursor.close()
        conn.close()

def get_approvers():
    """Fetches all users with the 'approver' role."""
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, username, full_name FROM users WHERE role IN ('approver', 'admin')")
    approvers = cursor.fetchall()
    cursor.close()
    conn.close()
    return approvers

def get_project_approvers(project_id):
    """Fetches a list of user_ids for approvers of a specific project."""
    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM project_approvers WHERE project_id=%s", (project_id,))
    result = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return result

def set_project_approvers(project_id, user_ids):
    """Sets the list of approvers for a project, replacing any existing ones."""
    conn = db.get_db_connection()
    cursor = conn.cursor()
    try:
        conn.start_transaction()
        # Clear existing approvers for this project
        cursor.execute("DELETE FROM project_approvers WHERE project_id=%s", (project_id,))
        # Insert the new list of approvers
        if user_ids:
            sql = "INSERT INTO project_approvers (project_id, user_id) VALUES (%s, %s)"
            values = [(project_id, uid) for uid in user_ids]
            cursor.executemany(sql, values)
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"An error occurred: {e}")
    finally:
        cursor.close()
        conn.close()

# ================================================================
# 🎨 Dialogs for Add/Edit/Delete
# ================================================================

# User Management Dialogs
@st.dialog("➕ Add / Edit User")
def user_form_dialog(edit_user=None):
    is_edit = bool(edit_user)
    with st.form("user_form"):
        username = st.text_input("Username*", value=edit_user["username"] if is_edit else "", disabled=is_edit)
        full_name = st.text_input("Full Name", value=edit_user.get("full_name", "") if is_edit else "")
        email = st.text_input("Email", value=edit_user.get("email", "") if is_edit else "")
        role = st.selectbox("Role*", ["user", "approver", "admin"],
                            index=["user", "approver", "admin"].index(edit_user["role"]) if is_edit else 0)
        if not is_edit:
            password = st.text_input("Password*", type="password")

        submitted = st.form_submit_button("💾 Save", type="primary")

        if submitted:
            try:
                if is_edit:
                    update_user(edit_user["user_id"], full_name, email, role)
                    st.success("✅ User updated successfully!")
                else:
                    if not username or not password:
                        st.error("Username and password are required.")
                        return
                    create_user(username, password, role, full_name, email)
                    st.success(f"✅ User '{username}' created successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Database error: {e}")

@st.dialog("⚠️ Confirm User Deletion")
def confirm_user_delete_dialog(user_info):
    st.warning(f"Are you sure you want to delete user **{user_info['username']}**?")
    col1, col2 = st.columns(2)
    if col1.button("Yes, Delete", type="primary"):
        delete_user(user_info["user_id"])
        st.success("🗑️ User deleted successfully.")
        st.rerun()
    if col2.button("Cancel"):
        st.rerun()

# Project Management Dialogs
@st.dialog("Project Details")
def project_form_dialog(project_id=None):
    """A dialog to add a new project or edit an existing one."""
    project = get_project(project_id) if project_id else {}
    is_edit = bool(project)
    
    st.write(f"### {'Edit' if is_edit else 'Add New'} Project")

    with st.form("project_form"):
        project_name = st.text_input("Project Name*", value=project.get("project_name", ""))
        client_name = st.text_input("Client Name", value=project.get("client_name", ""))
        
        c1, c2 = st.columns(2)
        start_date_val = c1.date_input("Start Date", value=project.get("start_date") or date.today())
        end_date_val = c2.date_input("End Date", value=project.get("end_date") or None)
        
        status_options = ["active", "on-hold", "completed"]
        current_status_index = status_options.index(project.get("status", "active"))
        status = st.selectbox("Status", status_options, index=current_status_index)

        submitted = st.form_submit_button("💾 Save", type="primary")
        if submitted:
            if not project_name:
                st.error("Project name is a required field.")
            else:
                data = {
                    "project_id": project_id,
                    "project_name": project_name,
                    "client_name": client_name,
                    "start_date": start_date_val,
                    "end_date": end_date_val,
                    "status": status
                }
                upsert_project(data)
                st.success(f"✅ Project '{project_name}' saved successfully!")
                st.rerun()

@st.dialog("Confirm Deletion")
def confirm_delete_dialog(project):
    """A dialog to confirm project deletion."""
    st.warning(f"Are you sure you want to delete the project **'{project['project_name']}'**? This action cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Yes, Delete", type="primary"):
        delete_project(project['project_id'])
        st.success("Project deleted.")
        st.rerun()
    if c2.button("Cancel"):
        st.rerun()

# ================================================================
# 🧭 Main UI with Tabs
# ================================================================
tab1, tab2, tab3 = st.tabs(["**Manage Projects**", "**Assign Approvers**", "**Manage Users**"])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Add New Project", type="primary", use_container_width=True):
            st.session_state.edit_project_id = None
            st.session_state.show_project_dialog = True

    st.write("### Existing Projects")
    
    # Define table headers
    cols = st.columns([1, 4, 3, 2, 2, 2, 1, 1])
    headers = ["ID", "Project Name", "Client", "Start Date", "End Date", "Status", "Edit", "Delete"]
    for col, h in zip(cols, headers):
        col.write(f"**{h}**")
    
    # Display project rows
    all_projects = list_projects()
    for p in all_projects:
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1, 4, 3, 2, 2, 2, 1, 1])
        c1.write(p["project_id"])
        c2.write(p["project_name"])
        c3.write(p["client_name"] or "N/A")
        c4.write(str(p["start_date"]) if p["start_date"] else "-")
        c5.write(str(p["end_date"]) if p["end_date"] else "-")
        c6.write(p["status"])

        if c7.button("✏️", key=f"edit_{p['project_id']}", help="Edit project"):
            st.session_state.edit_project_id = p["project_id"]
            st.session_state.show_project_dialog = True

        if c8.button("🗑️", key=f"del_{p['project_id']}", help="Delete project"):
            st.session_state.delete_project_info = p
            
with tab2:
    st.subheader("Assign Project Approvers")
    
    all_projects = list_projects()
    all_approvers = get_approvers()

    if not all_projects:
        st.info("No projects found. Please create a project first.")
    elif not all_approvers:
        st.info("No users with the 'approver' or 'admin' role found. Please create one first.")
    else:
        # Create a mapping of project name to project ID
        project_options = {p["project_name"]: p["project_id"] for p in all_projects}
        selected_project_name = st.selectbox("Select a Project", options=project_options.keys())
        selected_project_id = project_options[selected_project_name]

        # Get current approvers for the selected project
        current_approver_ids = get_project_approvers(selected_project_id)
        
        # Create a list of approver names for the multiselect widget
        approver_map = {f"{a['full_name']} ({a['username']})": a['user_id'] for a in all_approvers}
        id_to_approver_name = {v: k for k, v in approver_map.items()}
        
        # Set default values for the multiselect
        default_approvers = [id_to_approver_name[uid] for uid in current_approver_ids if uid in id_to_approver_name]
        
        selected_approver_names = st.multiselect(
            "Select Approvers for this Project",
            options=approver_map.keys(),
            default=default_approvers
        )
        
        if st.button("💾 Save Approvers", type="primary"):
            selected_approver_ids = [approver_map[name] for name in selected_approver_names]
            set_project_approvers(selected_project_id, selected_approver_ids)
            st.success(f"✅ Approvers for '{selected_project_name}' updated successfully!")

with tab3:
    # ================================================================
    # 🧭 Main UI — Manage Users
    # ================================================================
    col1, col2 = st.columns([6, 1])
    with col1:
        st.subheader("👤 Existing Users")
    with col2:
        if st.button("➕ Create User", type="primary", use_container_width=True):
            st.session_state.show_user_form = True

    users = fetch_all_users()

    if not users:
        st.info("No users found.")
    else:
        df = pd.DataFrame(users)
        cols = st.columns([1, 2, 2, 3, 2, 2, 2])
        headers = ["ID", "Full Name", "Username", "Email", "Role", "Edit", "Delete"]
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

# ====
# ================================================================
# 🔧 Dialog Invocation Logic (at the end of the script)
# ================================================================
if st.session_state.get("show_project_dialog"):
    project_form_dialog(st.session_state.get("edit_project_id"))
    # Reset state after dialog is used
    if "show_project_dialog" in st.session_state:
        del st.session_state["show_project_dialog"]
    if "edit_project_id" in st.session_state:
        del st.session_state["edit_project_id"]

if st.session_state.get("delete_project_info"):
    confirm_delete_dialog(st.session_state.get("delete_project_info"))
    # Reset state after dialog is used
    if "delete_project_info" in st.session_state:
        del st.session_state["delete_project_info"]

# User Management Dialog Invocation
if st.session_state.get("show_user_form"):
    user_form_dialog()
    del st.session_state["show_user_form"]

if st.session_state.get("edit_user_info"):
    user_form_dialog(st.session_state.get("edit_user_info"))
    del st.session_state["edit_user_info"]

if st.session_state.get("delete_user_info"):
    confirm_user_delete_dialog(st.session_state.get("delete_user_info"))
    del st.session_state["delete_user_info"]
# ============

import streamlit as st
import pandas as pd
from lib.auth import login_required, get_current_user
from lib.db import get_db
from datetime import date
from util.employee_dashboard_home import employee_dashboard_home
# ============ PAGE SETUP ============
st.set_page_config(page_title="Manager Approvals", layout="wide")
login_required(["approver", "admin"])
user = get_current_user()

st.title("🧾 Manager Approvals & Tasks")

# Sidebar logout
st.sidebar.write(f"👤 {user['full_name']} ({user['role']})")
if st.sidebar.button("Logout"):
    from lib.auth import logout_user
    logout_user()

# ============ DB HELPERS ============
def fetch_projects_for_approver(user_id: int):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT p.project_id, p.project_name, p.status
        FROM project_approvers pa
        JOIN projects p ON pa.project_id = p.project_id
        WHERE pa.user_id = %s
        ORDER BY p.project_name
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetch_submitted_entries(user_id: int, filters: dict):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    sql = """
        SELECT te.entry_id, u.full_name AS employee, p.project_name, t.task_name,
               te.entry_date, te.hours, te.notes, te.status
        FROM timesheet_entries te
        JOIN users u ON te.user_id = u.user_id
        JOIN projects p ON te.project_id = p.project_id
        LEFT JOIN tasks t ON te.task_id = t.task_id
        WHERE te.status = 'submitted'
        AND p.project_id IN (SELECT project_id FROM project_approvers WHERE user_id=%s)
    """
    params = [user_id]

    if filters.get("project_id"):
        sql += " AND te.project_id = %s"
        params.append(filters["project_id"])
    if filters.get("employee_name"):
        sql += " AND u.full_name LIKE %s"
        params.append(f"%{filters['employee_name']}%")
    if filters.get("start_date"):
        sql += " AND te.entry_date >= %s"
        params.append(filters["start_date"])
    if filters.get("end_date"):
        sql += " AND te.entry_date <= %s"
        params.append(filters["end_date"])
    if filters.get("project_status"):
        sql += " AND p.status = %s"
        params.append(filters["project_status"])

    sql += " ORDER BY te.entry_date DESC"
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def update_entry_status(entry_id: int, approver_id: int, decision: str, comment=None):
    conn = get_db()
    cur = conn.cursor()
    try:
        conn.start_transaction()
        cur.execute("UPDATE timesheet_entries SET status=%s WHERE entry_id=%s", (decision, entry_id))
        cur.execute(
            "INSERT INTO approvals (entry_id, approver_id, decision, comment) VALUES (%s, %s, %s, %s)",
            (entry_id, approver_id, decision, comment)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Error updating approval: {e}")
    finally:
        cur.close()
        conn.close()

def get_tasks(project_id: int):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT task_id, task_name, is_billable FROM tasks WHERE project_id=%s", (project_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def save_task(project_id: int, task_name: str, is_billable: bool, task_id=None):
    conn = get_db()
    cur = conn.cursor()
    try:
        if task_id:
            cur.execute("UPDATE tasks SET task_name=%s, is_billable=%s WHERE task_id=%s",
                        (task_name, is_billable, task_id))
        else:
            cur.execute("INSERT INTO tasks (project_id, task_name, is_billable) VALUES (%s,%s,%s)",
                        (project_id, task_name, is_billable))
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Error saving task: {e}")
    finally:
        cur.close()
        conn.close()

def delete_task(task_id: int):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM tasks WHERE task_id=%s", (task_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Error deleting task: {e}")
    finally:
        cur.close()
        conn.close()

# ============ TABS ============
tab1, tab2 ,tab3= st.tabs(["🏠 Home","🗂️ Manage Approvals", "🛠️ Manage Tasks"])
# -------------------------------- TAB 1: Home --------------------------------
with tab1:
    employee_dashboard_home()

# -------------------------------- TAB 2: APPROVALS --------------------------------
with tab2:
    st.subheader("Submitted Timesheet Entries")

    # Filters
    projects = fetch_projects_for_approver(user["user_id"])
    project_map = {p["project_id"]: p["project_name"] for p in projects}
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        project_id = st.selectbox("Project", options=[None] + list(project_map.keys()), format_func=lambda x: project_map.get(x, "All"))
    with col2:
        employee_name = st.text_input("Employee Name")
    with col3:
        start_date = st.date_input("Start Date", value=None)
    with col4:
        end_date = st.date_input("End Date", value=None)
    with col5:
        project_status = st.selectbox("Project Status", ["", "active", "on-hold", "completed"])

    filters = {
        "project_id": project_id,
        "employee_name": employee_name,
        "start_date": start_date if start_date else None,
        "end_date": end_date if end_date else None,
        "project_status": project_status if project_status else None,
    }

    entries = fetch_submitted_entries(user["user_id"], filters)
    if not entries:
        st.info("No submitted entries found.")
    else:
        cols = st.columns([1, 2, 2, 2, 1, 3, 2])
        headers = ["Employee", "Project", "Task", "Date", "Hours", "Notes", "Actions"]
        for col, header in zip(cols, headers):
            col.write(f"**{header}**")

        for row in entries:
            c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 2, 2, 2, 1, 3, 2])
            c1.write(row["employee"])
            c2.write(row["project_name"])
            c3.write(row["task_name"] or "-")
            c4.write(str(row["entry_date"]))
            c5.write(f"{row['hours']:.2f}")
            c6.write(row["notes"] or "")

            with c7:
                approve = st.button("Approve ✅", key=f"approve_{row['entry_id']}")
                reject = st.button("Reject ❌", key=f"reject_{row['entry_id']}")
                if approve:
                    update_entry_status(row["entry_id"], user["user_id"], "approved")
                    st.success(f"Approved entry {row['entry_id']}")
                    st.rerun()
                if reject:
                    st.session_state["reject_id"] = row["entry_id"]
                    st.session_state["show_reject_dialog"] = True

        # Reject dialog
        if st.session_state.get("show_reject_dialog"):
            reject_id = st.session_state.get("reject_id")

            @st.dialog("Reject Timesheet Entry")
            def reject_dialog():
                comment = st.text_area("Reason for rejection")
                if st.button("Confirm Rejection"):
                    update_entry_status(reject_id, user["user_id"], "rejected", comment)
                    st.success("Entry rejected.")
                    st.session_state["show_reject_dialog"] = False
                    st.rerun()
                if st.button("Cancel"):
                    st.session_state["show_reject_dialog"] = False
                    st.rerun()

            reject_dialog()

# -------------------------------- TAB 2: MANAGE TASKS --------------------------------
with tab3:
    st.subheader("Manage Project Tasks")

    projects = fetch_projects_for_approver(user["user_id"])
    if not projects:
        st.info("You are not an approver for any projects.")
    else:
        project_map = {p["project_id"]: p["project_name"] for p in projects}

        # Add New Task button at top-right corner
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("➕ Add New Task", type="primary", use_container_width=True):
                st.session_state["edit_task"] = None
                st.session_state["show_task_dialog"] = True

        # Fetch all tasks for all approver projects
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT t.task_id, t.task_name, t.is_billable, p.project_name, p.project_id
            FROM tasks t
            JOIN projects p ON t.project_id = p.project_id
            WHERE p.project_id IN (
                SELECT project_id FROM project_approvers WHERE user_id=%s
            )
            ORDER BY p.project_name, t.task_id
        """, (user["user_id"],))
        tasks = cur.fetchall()
        cur.close()
        conn.close()

        if not tasks:
            st.info("No tasks found for your projects.")
        else:
            # Header
            cols = st.columns([2, 3, 1, 1, 1])
            headers = ["Project", "Task Name", "Billable", "Edit", "Delete"]
            for col, header in zip(cols, headers):
                col.write(f"**{header}**")

            # Rows
            for t in tasks:
                c1, c2, c3, c4, c5 = st.columns([2, 3, 1, 1, 1])
                c1.write(t["project_name"])
                c2.write(t["task_name"])
                c3.write("✅" if t["is_billable"] else "❌")

                with c4:
                    if st.button("✏️ Edit", key=f"edit_{t['task_id']}"):
                        st.session_state["edit_task"] = t
                        st.session_state["show_task_dialog"] = True

                with c5:
                    if st.button("🗑️ Delete", key=f"delete_{t['task_id']}"):
                        delete_task(t["task_id"])
                        st.success("Task deleted successfully.")
                        st.rerun()

        # Dialog for add/edit task
        if st.session_state.get("show_task_dialog"):

            @st.dialog("Add / Edit Task")
            def task_dialog():
                edit_task = st.session_state.get("edit_task")

                project_id = st.selectbox(
                    "Select Project",
                    options=list(project_map.keys()),
                    format_func=lambda x: project_map[x],
                    index=(list(project_map.keys()).index(edit_task["project_id"])
                           if edit_task and edit_task.get("project_id") in project_map
                           else 0)
                )

                task_name = st.text_input(
                    "Task Name",
                    value=edit_task["task_name"] if edit_task else ""
                )

                is_billable = st.checkbox(
                    "Billable",
                    value=bool(edit_task["is_billable"]) if edit_task else True
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Save"):
                        save_task(project_id, task_name, is_billable,
                                  edit_task["task_id"] if edit_task else None)
                        st.success("Task saved successfully!")
                        st.session_state["show_task_dialog"] = False
                        st.rerun()

                with col2:
                    if st.button("Cancel"):
                        st.session_state["show_task_dialog"] = False
                        st.rerun()

            task_dialog()

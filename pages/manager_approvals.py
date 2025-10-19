import streamlit as st
import pandas as pd
from lib import db, auth

# ================================================================
# 🔐 Role check and page setup
# ================================================================
st.set_page_config(page_title="Manager Dashboard", layout="wide")
auth.login_required(roles=["approver", "admin"])
user = auth.get_current_user()
st.title("🧾 Manager Dashboard")

# ================================================================
# 🧩 Database Helper Functions
# ================================================================
def fetch_submitted_weekly_entries(approver_id: int):
    conn = db.get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT te.entry_id, u.full_name AS employee_name, p.project_name, t.task_name,
               te.week_start_date, te.total_hours, te.status
        FROM timesheet_entries te
        JOIN users u ON te.user_id = u.user_id
        JOIN projects p ON te.project_id = p.project_id
        LEFT JOIN tasks t ON te.task_id = t.task_id
        WHERE p.project_id IN (SELECT project_id FROM project_approvers WHERE user_id = %s)
        ORDER BY te.week_start_date DESC, u.full_name
    """, (approver_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def update_entry_status(entry_id: int, approver_id: int, new_status: str, comment: str = None):
    conn = db.get_db_connection()
    cur = conn.cursor()
    try:
        conn.start_transaction()
        cur.execute("UPDATE timesheet_entries SET status = %s WHERE entry_id = %s", (new_status, entry_id))
        decision = 'approved' if new_status == 'approved' else 'rejected'
        cur.execute(
            "INSERT INTO approvals (entry_id, approver_id, decision, comment) VALUES (%s, %s, %s, %s)",
            (entry_id, approver_id, decision, comment)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Database error: {e}")
    finally:
        cur.close()
        conn.close()


# ================================================================
# 🧩 Tasks Management Functions
# ================================================================
def get_tasks_with_assignments(user_id: int):
    conn = db.get_db_connection()
    cur = conn.cursor(dictionary=True)
    sql = """
        SELECT
            t.task_id, t.task_name, t.is_billable, p.project_name, p.project_id,
            GROUP_CONCAT(u.full_name ORDER BY u.full_name SEPARATOR ', ') as assigned_users
        FROM tasks t
        JOIN projects p ON t.project_id = p.project_id
        LEFT JOIN user_tasks ut ON t.task_id = ut.task_id
        LEFT JOIN users u ON ut.user_id = u.user_id
        WHERE p.project_id IN (SELECT project_id FROM project_approvers WHERE user_id=%s)
        GROUP BY t.task_id, t.task_name, t.is_billable, p.project_name, p.project_id
        ORDER BY p.project_name, t.task_name
    """
    cur.execute(sql, (user_id,))
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return tasks


def get_task(task_id: int):
    conn = db.get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM tasks WHERE task_id = %s", (task_id,))
    task = cur.fetchone()
    cur.close()
    conn.close()
    return task


def upsert_task(data: dict):
    conn = db.get_db_connection()
    cur = conn.cursor()
    task_id = data.get("task_id")
    if task_id:
        cur.execute("UPDATE tasks SET task_name=%s, is_billable=%s, project_id=%s WHERE task_id=%s",
                    (data['task_name'], data['is_billable'], data['project_id'], task_id))
    else:
        cur.execute("INSERT INTO tasks (project_id, task_name, is_billable, created_by) VALUES (%s, %s, %s, %s)",
                    (data['project_id'], data['task_name'], data['is_billable'], data['created_by']))
        task_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    return task_id


def delete_task(task_id: int):
    conn = db.get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM tasks WHERE task_id=%s", (task_id,))
        conn.commit()
    except Exception as e:
        st.error(f"Could not delete task. It might be in use by timesheets. Error: {e}")
    finally:
        cur.close()
        conn.close()


def fetch_approver_projects(user_id: int):
    conn = db.get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT p.project_id, p.project_name FROM projects p
        JOIN project_approvers pa ON p.project_id = pa.project_id
        WHERE pa.user_id = %s ORDER BY p.project_name
    """, (user_id,))
    projects = cur.fetchall()
    cur.close()
    conn.close()
    return projects


def get_all_users():
    conn = db.get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT user_id, full_name, username FROM users WHERE role = 'user' ORDER BY full_name")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users


def get_assigned_users_for_task(task_id: int):
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM user_tasks WHERE task_id = %s", (task_id,))
    user_ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return user_ids


def set_task_assignments(task_id: int, user_ids: list):
    conn = db.get_db_connection()
    cur = conn.cursor()
    try:
        conn.start_transaction()
        cur.execute("DELETE FROM user_tasks WHERE task_id = %s", (task_id,))
        if user_ids:
            sql = "INSERT INTO user_tasks (task_id, user_id) VALUES (%s, %s)"
            values = [(task_id, uid) for uid in user_ids]
            cur.executemany(sql, values)
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Database error while assigning users: {e}")
    finally:
        cur.close()
        conn.close()


# ================================================================
# 🎨 Dialogs
# ================================================================
@st.dialog("Reject Timesheet")
def reject_timesheet_dialog(entry):
    st.warning(f"Rejecting timesheet for {entry['employee_name']} (Week of {entry['week_start_date']})")
    with st.form("rejection_form"):
        comment = st.text_area("Reason for Rejection (Required)")
        submitted = st.form_submit_button("Confirm Rejection", type="primary")
        if submitted:
            if not comment:
                st.error("A reason is required to reject a timesheet.")
            else:
                update_entry_status(entry['entry_id'], user['user_id'], 'rejected', comment)
                st.success("Timesheet has been rejected.")
                st.rerun()


# ================================================================
# 🧭 Main UI Tabs
# ================================================================
tab1, tab2 = st.tabs(["**Manage Approvals**", "**Manage Tasks**"])

# ----------------------------------------------------------------
# TAB 1: Manage Approvals with Filters
# ----------------------------------------------------------------
with tab1:
    st.subheader("Pending & Submitted Timesheets")

    entries = fetch_submitted_weekly_entries(user['user_id'])
    if not entries:
        st.info("No timesheets found.")
    else:
        df = pd.DataFrame(entries)

        # --- Filters Row ---
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            emp_filter = st.selectbox("Employee", ["All"] + sorted(df["employee_name"].unique().tolist()))
        with col2:
            proj_filter = st.selectbox(
                "Project / Task",
                ["All"] + sorted({f"{r['project_name']} / {r['task_name'] or ''}" for _, r in df.iterrows()})
            )
        with col3:
            week_filter = st.selectbox("Week Start", ["All"] + sorted(df["week_start_date"].astype(str).unique().tolist(), reverse=True))
        with col4:
            hour_filter = st.selectbox("Total Hours", ["All"] + sorted(df["total_hours"].astype(str).unique().tolist()))
        with col5:
            status_filter = st.selectbox("Status", ["All", "draft", "submitted", "approved", "rejected"])

        # --- Apply Filters ---
        filtered = df.copy()
        if emp_filter != "All":
            filtered = filtered[filtered["employee_name"] == emp_filter]

        if proj_filter != "All":
            proj_name, task_name = proj_filter.split("/", 1)
            proj_name = proj_name.strip()
            task_name = task_name.strip()

            if task_name:  # if a task name exists, match both
                filtered = filtered[
                    (filtered["project_name"] == proj_name) &
                    (filtered["task_name"].fillna("") == task_name)
                ]
            else:  # only project filter
                filtered = filtered[filtered["project_name"] == proj_name]

        if week_filter != "All":
            filtered = filtered[filtered["week_start_date"].astype(str) == week_filter]
        if hour_filter != "All":
            filtered = filtered[filtered["total_hours"].astype(str) == hour_filter]
        if status_filter != "All":
            filtered = filtered[filtered["status"] == status_filter]


        st.markdown("---")

        if filtered.empty:
            st.warning("No results match your filters.")
        else:
            cols = st.columns([3, 3, 2, 2, 2, 2])
            headers = ["Employee", "Project / Task", "Week Start", "Total Hours", "Approve", "Reject / Status"]
            for col, h in zip(cols, headers): col.write(f"**{h}**")

            for entry in filtered.to_dict("records"):
                c1, c2, c3, c4, c5, c6 = st.columns([3, 3, 2, 2, 2, 2])
                c1.write(entry['employee_name'])
                c2.write(f"{entry['project_name']}{' / ' + entry['task_name'] if entry['task_name'] else ''}")
                c3.write(str(entry['week_start_date']))
                c4.write(f"{entry['total_hours']:.2f}")

                # ✅ If already approved/rejected — show status instead of buttons
                if entry["status"] == "approved":
                    c5.markdown("✅ **Approved**")
                    c6.write("")
                elif entry["status"] == "rejected":
                    c5.markdown("❌ **Rejected**")
                    c6.write("")
                else:
                    if c5.button("Approve ✅", key=f"approve_{entry['entry_id']}", use_container_width=True):
                        update_entry_status(entry['entry_id'], user['user_id'], 'approved')
                        st.rerun()
                    if c6.button("Reject ❌", key=f"reject_{entry['entry_id']}", use_container_width=True):
                        st.session_state.reject_entry_info = entry


# ----------------------------------------------------------------
# TAB 2: Manage Tasks
# ----------------------------------------------------------------
with tab2:
    st.subheader("Manage Project Tasks")
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Add New Task", type="primary", use_container_width=True):
            st.session_state.edit_task_id = None
            st.session_state.show_task_dialog = True

    tasks = get_tasks_with_assignments(user['user_id'])
    if not tasks:
        st.info("No tasks found for your projects.")
    else:
        cols = st.columns([3, 3, 3, 1, 1, 1])
        headers = ["Project", "Task Name", "Assigned Users", "Billable", "Edit", "Delete"]
        for col, h in zip(cols, headers):
            col.write(f"**{h}**")

        for task in tasks:
            c1, c2, c3, c4, c5, c6 = st.columns([3, 3, 3, 1, 1, 1])
            c1.write(task['project_name'])
            c2.write(task['task_name'])
            c3.write(task.get('assigned_users') or "_Unassigned_")
            c4.write("✅" if task['is_billable'] else "❌")
            if c5.button("✏️", key=f"edit_{task['task_id']}", help="Edit task"):
                st.session_state.edit_task_id = task['task_id']
                st.session_state.show_task_dialog = True
            if c6.button("🗑️", key=f"del_{task['task_id']}", help="Delete task"):
                st.session_state.delete_task_info = task


# ================================================================
# 🔧 Dialog Invocation Logic
# ================================================================
if st.session_state.get("reject_entry_info"):
    reject_timesheet_dialog(st.session_state.get("reject_entry_info"))
    del st.session_state["reject_entry_info"]

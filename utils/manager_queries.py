# ./utils/manager_queries.py
import pandas as pd
from datetime import date
from lib.db import get_connection, dict_fetchall
from lib.constants import ROLE_ID_ADMIN, ROLE_ID_DEPT_MANAGER, ROLE_ID_PROJECT_MANAGER
from lib.email_utils import send_email # Import Email Utils

# ========================================================
# 1. Dropdown & Helper Fetchers
# ========================================================

def fetch_departments():
    """Fetches all departments for dropdowns."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DepId, DepName FROM Department ORDER BY DepName")
        return dict_fetchall(cur)

def fetch_task_types(dep_id_filter=None):
    """
    Fetches Task Types. 
    If dep_id_filter is provided, returns types matching that Dept OR Global (NULL).
    """
    with get_connection() as conn:
        cur = conn.cursor()
        sql = """
            SELECT tt.TaskTypeId, tt.TaskTypeName, d.DepName 
            FROM TaskTypes tt
            LEFT JOIN Department d ON tt.DepId = d.DepId
        """
        params = []
        if dep_id_filter:
            # Logic: Show types specifically for this Dept OR types with no Dept
            sql += " WHERE tt.DepId = ? OR tt.DepId IS NULL"
            params.append(dep_id_filter)
            
        sql += " ORDER BY d.DepName, tt.TaskTypeName"
        
        cur.execute(sql, params)
        return dict_fetchall(cur)

def fetch_approver_projects(user_id: int, is_admin: bool = False):
    """
    Fetches projects for dropdowns.
    - If Admin: Fetches ALL active projects.
    - If Manager: Fetches only assigned projects (with role-based billable filter).
    """
    with get_connection() as conn:
        cur = conn.cursor()
        if is_admin:
            cur.execute("SELECT project_id, project_name FROM projects WHERE status = 'active' ORDER BY project_name")
        else:
            # Determine strict role for this user to filter dropdowns correctly
            cur.execute("SELECT UserTypeId FROM Employee WHERE EmpId = ?", (user_id,))
            row = cur.fetchone()
            # Default to generic approver if role lookup fails
            role_id = int(row[0]) if row else 0

            if role_id == ROLE_ID_DEPT_MANAGER:
                # Dept Manager: Assigned + Non-Billable (0 or NULL)
                cur.execute("""
                    SELECT p.project_id, p.project_name FROM projects p
                    JOIN project_approvers pa ON p.project_id = pa.project_id
                    WHERE pa.user_id = ? AND (p.is_billable = 0 OR p.is_billable IS NULL)
                    ORDER BY p.project_name
                """, (user_id,))
            elif role_id == ROLE_ID_PROJECT_MANAGER:
                # Project Manager: Assigned + Billable (1)
                cur.execute("""
                    SELECT p.project_id, p.project_name FROM projects p
                    JOIN project_approvers pa ON p.project_id = pa.project_id
                    WHERE pa.user_id = ? AND p.is_billable = 1
                    ORDER BY p.project_name
                """, (user_id,))
            else:
                # Fallback / General Approver (Just Assigned)
                cur.execute("""
                    SELECT p.project_id, p.project_name FROM projects p
                    JOIN project_approvers pa ON p.project_id = pa.project_id
                    WHERE pa.user_id = ? ORDER BY p.project_name
                """, (user_id,))
                
        return dict_fetchall(cur)

def fetch_all_active_projects():
    """Fetches all active projects (Legacy/Admin specific helper)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT project_id, project_name FROM projects WHERE status = 'active' ORDER BY project_name")
        return dict_fetchall(cur)

def fetch_tasks_by_type(type_id):
    """
    Fetches global tasks filtered by TaskType.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        sql = """
            SELECT task_id, task_name 
            FROM tasks 
            WHERE TaskTypeId = ?
            ORDER BY task_name
        """
        cur.execute(sql, (type_id,))
        return dict_fetchall(cur)

def get_all_employees(dep_id=None):
    """
    Fetches employees. 
    If dep_id is provided, filters by Department ID.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        sql = "SELECT EmpId, EmpName, SAP_ID FROM Employee"
        params = []
        
        if dep_id:
            sql += " WHERE DepId = ?"
            params.append(dep_id)
            
        sql += " ORDER BY EmpName"
        
        cur.execute(sql, params)
        return dict_fetchall(cur)

def get_project_details_simple(project_id):
    """Helper to get just the DepId for a project."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DepId FROM projects WHERE project_id = ?", (project_id,))
        row = cur.fetchone()
        return row[0] if row else None

# ========================================================
# 2. Task Management
# ========================================================

def get_tasks_for_manager(user_id: int):
    """
    Fetches ALL tasks defined in the system.
    Tasks are global, so we don't filter by project here.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        sql = """
            SELECT
                t.task_id, t.task_name, 
                tt.TaskTypeName
            FROM tasks t
            LEFT JOIN TaskTypes tt ON t.TaskTypeId = tt.TaskTypeId
            ORDER BY t.task_name
        """
        cur.execute(sql)
        return dict_fetchall(cur)

def get_task(task_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        rows = dict_fetchall(cur)
        return rows[0] if rows else None

def upsert_task(data):
    with get_connection() as conn:
        cur = conn.cursor()
        task_id = data.get("task_id")
        try:
            if task_id:
                cur.execute("""
                    UPDATE tasks 
                    SET task_name=?, TaskTypeId=? 
                    WHERE task_id=?
                """, (data['task_name'], data['TaskTypeId'], task_id))
            else:
                cur.execute("""
                    INSERT INTO tasks (task_name, created_by, TaskTypeId, created_at) 
                    VALUES (?, ?, ?, GETDATE());
                """, (data['task_name'], data['created_by'], data['TaskTypeId']))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

def delete_task(task_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM tasks WHERE task_id=?", (task_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

# ========================================================
# 3. Assignment Management
# ========================================================

def get_all_assignments_for_manager(user_id: int, is_admin: bool = False):
    """
    Fetches assignments.
    - If Admin: Fetches ALL assignments.
    - If Manager: Fetches assignments for projects they approve.
    - REMOVED: assignment_name
    """
    with get_connection() as conn:
        cur = conn.cursor()
        
        base_sql = """
            SELECT
                a.AssignmentId, a.task_id, a.EmpId, 
                a.planned_hours, a.start_date, a.end_date, a.status, a.notes,
                p.project_id, p.project_name,
                t.task_name, t.TaskTypeId, 
                tt.TaskTypeName,
                e.EmpName, e.SAP_ID
            FROM Assignments a
            JOIN projects p ON a.project_id = p.project_id
            JOIN tasks t ON a.task_id = t.task_id
            LEFT JOIN TaskTypes tt ON t.TaskTypeId = tt.TaskTypeId
            JOIN Employee e ON a.EmpId = e.EmpId
        """
        
        if is_admin:
            sql = base_sql + " ORDER BY p.project_name, t.task_name, e.EmpName"
            cur.execute(sql)
        else:
            sql = base_sql + " WHERE p.project_id IN (SELECT project_id FROM project_approvers WHERE user_id=?) ORDER BY p.project_name, t.task_name, e.EmpName"
            cur.execute(sql, (user_id,))
            
        return dict_fetchall(cur)

def upsert_assignment(data):
    """
    Insert/Update Assignment.
    - REMOVED: assignment_name
    """
    with get_connection() as conn:
        cur = conn.cursor()
        aid = data.get("AssignmentId")
        try:
            if aid:
                sql = """
                    UPDATE Assignments
                    SET project_id=?, task_id=?, EmpId=?, planned_hours=?, notes=?, 
                    start_date=?, end_date=?, status=?
                    WHERE AssignmentId=?
                """
                params = (
                    data['project_id'], data['task_id'], data['EmpId'], int(data['planned_hours']), 
                    data['notes'], data['start_date'], data['end_date'], data['status'], aid
                )
                cur.execute(sql, params)
            else:
                sql = """
                    INSERT INTO Assignments (
                        project_id, task_id, EmpId, planned_hours, notes, 
                        start_date, end_date, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    data['project_id'], data['task_id'], data['EmpId'], int(data['planned_hours']), 
                    data['notes'], data['start_date'], data['end_date'], data['status']
                )
                cur.execute(sql, params)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

def delete_assignment(assignment_id):
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM Assignments WHERE AssignmentId=?", (assignment_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

# ========================================================
# 4. Approvals & Timesheet Management
# ========================================================

def fetch_submitted_weekly_entries(approver_id: int, role_id: int, sort_order: str = "DESC"):
    """
    Fetches submitted timesheets based on role.
    sort_order: "ASC" or "DESC" for updated_at column
    """
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Base Query
        base_sql = """
            SELECT te.entry_id, u.EmpName AS employee_name, p.project_name, t.task_name,
                   te.week_start_date, te.total_hours, te.status, te.updated_at
            FROM timesheet_entries te
            JOIN Employee u ON te.user_id = u.EmpId
            JOIN projects p ON te.project_id = p.project_id
            LEFT JOIN tasks t ON te.task_id = t.task_id
        """
        
        try:
            role_id = int(role_id)
        except (ValueError, TypeError):
            role_id = 0

        # Validate sort_order
        if sort_order.upper() not in ["ASC", "DESC"]:
            sort_order = "DESC"
        
        order_clause = f" ORDER BY te.updated_at {sort_order}, u.EmpName"

        if role_id == ROLE_ID_ADMIN:
            sql = base_sql + order_clause
            cur.execute(sql)
            
        elif role_id == ROLE_ID_DEPT_MANAGER:
            sql = base_sql + """
                WHERE p.project_id IN (SELECT project_id FROM project_approvers WHERE user_id = ?) 
                AND (p.is_billable = 0 OR p.is_billable IS NULL)
            """ + order_clause
            cur.execute(sql, (approver_id,))
            
        elif role_id == ROLE_ID_PROJECT_MANAGER:
            sql = base_sql + """
                WHERE p.project_id IN (SELECT project_id FROM project_approvers WHERE user_id = ?) 
                AND p.is_billable = 1
            """ + order_clause
            cur.execute(sql, (approver_id,))
        
        else:
            sql = base_sql + " WHERE p.project_id IN (SELECT project_id FROM project_approvers WHERE user_id = ?) " + order_clause
            cur.execute(sql, (approver_id,))
            
        return dict_fetchall(cur)

def get_timesheet_entry_details(entry_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT te.*, t.TaskTypeId 
            FROM timesheet_entries te
            LEFT JOIN tasks t ON te.task_id = t.task_id
            WHERE te.entry_id = ?
        """, (entry_id,))
        rows = dict_fetchall(cur)
        return rows[0] if rows else None

def update_timesheet_entry_full(data):
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            sql = """
                UPDATE timesheet_entries
                SET project_id=?, task_id=?, status=?, notes=?,
                    sunday_hours=?, monday_hours=?, tuesday_hours=?, 
                    wednesday_hours=?, thursday_hours=?, friday_hours=?, saturday_hours=?
                WHERE entry_id=?
            """
            params = (
                data['project_id'], data['task_id'], data['status'], data['notes'],
                data['sunday'], data['monday'], data['tuesday'],
                data['wednesday'], data['thursday'], data['friday'], data['saturday'],
                data['entry_id']
            )
            cur.execute(sql, params)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

def update_entry_status(entry_id: int, approver_id: int, new_status: str, comment: str = None):
    """
    Updates the status of a timesheet entry and logs the approval decision.
    Triggers an email notification to the employee.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("UPDATE timesheet_entries SET status = ? WHERE entry_id = ?", (new_status, entry_id))
            decision = 'approved' if new_status == 'approved' else 'rejected'
            cur.execute(
                "INSERT INTO approvals (entry_id, approver_id, decision, comment, decision_ts) VALUES (?, ?, ?, ?, GETDATE())",
                (entry_id, approver_id, decision, comment)
            )
            
            # --- EMAIL NOTIFICATION: NOTIFY EMPLOYEE ---
            cur.execute("""
                SELECT e.EmpEmail, e.EmpName, p.project_name, te.week_start_date 
                FROM timesheet_entries te
                JOIN Employee e ON te.user_id = e.EmpId
                JOIN projects p ON te.project_id = p.project_id
                WHERE te.entry_id = ?
            """, (entry_id,))
            row = cur.fetchone()
            
            if row and row[0]: # If email exists
                email, name, proj, week = row
                
                status_color = "green" if new_status == "approved" else "red"
                
                subject = f"Timesheet Update: {new_status.upper()} - {proj}"
                body = f"""
                <h3>Timesheet Status Update</h3>
                <p>Hello <b>{name}</b>,</p>
                <p>Your timesheet entry has been processed.</p>
                <ul>
                    <li><b>Project:</b> {proj}</li>
                    <li><b>Week Starting:</b> {week}</li>
                    <li><b>Status:</b> <span style="color:{status_color}; font-weight:bold;">{new_status.upper()}</span></li>
                </ul>
                <p><b>Manager Comment:</b><br>{comment if comment else 'No comments provided.'}</p>
                """
                send_email(email, subject, body)
            # -------------------------------------------

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

# --- NEW: Admin Create Entry (FIXED) ---
def create_admin_timesheet_entry(data, admin_id):
    """
    Allows Admin to insert and auto-approve a timesheet entry.
    Uses OUTPUT INSERTED.entry_id to reliably get the new ID in one go.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            # 1. Attempt to resolve AssignmentID (Optional, but good for linking)
            cur.execute("""
                SELECT TOP 1 AssignmentId FROM Assignments 
                WHERE EmpId = ? AND project_id = ? AND task_id = ?
            """, (data['target_user_id'], data['project_id'], data['task_id']))
            row = cur.fetchone()
            assignment_id = row[0] if row else None

            # 2. Upsert Timesheet Entry
            cur.execute("""
                SELECT entry_id FROM timesheet_entries 
                WHERE user_id = ? AND project_id = ? AND task_id = ? AND week_start_date = ?
            """, (data['target_user_id'], data['project_id'], data['task_id'], data['week_start_date']))
            existing = cur.fetchone()

            entry_id = None
            if existing:
                entry_id = existing[0]
                cur.execute("""
                    UPDATE timesheet_entries
                    SET sunday_hours=?, monday_hours=?, tuesday_hours=?, wednesday_hours=?, 
                        thursday_hours=?, friday_hours=?, saturday_hours=?, 
                        status='approved', notes=?, updated_at=GETDATE(), AssignmentId=?
                    WHERE entry_id=?
                """, (
                    data['sunday'], data['monday'], data['tuesday'], data['wednesday'],
                    data['thursday'], data['friday'], data['saturday'],
                    data['notes'], assignment_id, entry_id
                ))
            else:
                # Use OUTPUT clause instead of SELECT SCOPE_IDENTITY
                sql_insert = """
                    INSERT INTO timesheet_entries (
                        user_id, project_id, task_id, AssignmentId, week_start_date,
                        sunday_hours, monday_hours, tuesday_hours, wednesday_hours,
                        thursday_hours, friday_hours, saturday_hours, 
                        status, notes, created_at, updated_at
                    ) 
                    OUTPUT INSERTED.entry_id
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', ?, GETDATE(), GETDATE());
                """
                params = (
                    data['target_user_id'], data['project_id'], data['task_id'], assignment_id, data['week_start_date'],
                    data['sunday'], data['monday'], data['tuesday'], data['wednesday'],
                    data['thursday'], data['friday'], data['saturday'], data['notes']
                )
                cur.execute(sql_insert, params)
                row_new = cur.fetchone()
                if row_new:
                    entry_id = int(row_new[0])

            # 3. Log Approval (Auto-approval audit)
            if entry_id:
                cur.execute("""
                    INSERT INTO approvals (entry_id, approver_id, decision, comment, decision_ts)
                    VALUES (?, ?, 'approved', 'Admin Manual Entry', GETDATE())
                """, (entry_id, admin_id))

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
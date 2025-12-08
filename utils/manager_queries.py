# ./utils/manager_queries.py
import pandas as pd
from datetime import date
from lib.db import get_connection, dict_fetchall

# ========================================================
# 1. Dropdown & Helper Fetchers
# ========================================================

def fetch_task_types():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT TaskTypeId, TaskTypeName FROM TaskTypes ORDER BY TaskTypeName")
        return dict_fetchall(cur)

def fetch_approver_projects(user_id: int, is_admin: bool = False):
    """
    Fetches projects for dropdowns.
    - If Admin: Fetches ALL active projects.
    - If Manager: Fetches only assigned projects.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        if is_admin:
            cur.execute("SELECT project_id, project_name FROM projects WHERE status = 'active' ORDER BY project_name")
        else:
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

def get_all_employees():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT EmpId, EmpName, SAP_ID FROM Employee ORDER BY EmpName")
        return dict_fetchall(cur)

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
    """
    with get_connection() as conn:
        cur = conn.cursor()
        
        base_sql = """
            SELECT
                a.AssignmentId, a.task_id, a.EmpId, 
                a.assignment_name, a.planned_hours, a.start_date, a.end_date, a.status, a.notes,
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
    with get_connection() as conn:
        cur = conn.cursor()
        aid = data.get("AssignmentId")
        try:
            if aid:
                sql = """
                    UPDATE Assignments
                    SET project_id=?, task_id=?, EmpId=?, assignment_name=?, planned_hours=?, notes=?, 
                    start_date=?, end_date=?, status=?
                    WHERE AssignmentId=?
                """
                params = (
                    data['project_id'], data['task_id'], data['EmpId'], data['assignment_name'], int(data['planned_hours']), 
                    data['notes'], data['start_date'], data['end_date'], data['status'], aid
                )
                cur.execute(sql, params)
            else:
                sql = """
                    INSERT INTO Assignments (
                        project_id, task_id, EmpId, assignment_name, planned_hours, notes, 
                        start_date, end_date, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    data['project_id'], data['task_id'], data['EmpId'], data['assignment_name'], int(data['planned_hours']), 
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

def fetch_submitted_weekly_entries(approver_id: int, is_admin: bool = False):
    """
    Fetches submitted timesheets.
    - If Admin: Fetches ALL entries.
    - If Manager: Fetches entries for projects they approve.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        base_sql = """
            SELECT te.entry_id, u.EmpName AS employee_name, p.project_name, t.task_name,
                   te.week_start_date, te.total_hours, te.status
            FROM timesheet_entries te
            JOIN Employee u ON te.user_id = u.EmpId
            JOIN projects p ON te.project_id = p.project_id
            LEFT JOIN tasks t ON te.task_id = t.task_id
        """
        
        if is_admin:
            # No filtering by approver_id for admins
            sql = base_sql + " ORDER BY te.week_start_date DESC, u.EmpName"
            cur.execute(sql)
        else:
            # Filter by projects assigned to this approver
            sql = base_sql + " WHERE p.project_id IN (SELECT project_id FROM project_approvers WHERE user_id = ?) ORDER BY te.week_start_date DESC, u.EmpName"
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
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("UPDATE timesheet_entries SET status = ? WHERE entry_id = ?", (new_status, entry_id))
            decision = 'approved' if new_status == 'approved' else 'rejected'
            cur.execute(
                "INSERT INTO approvals (entry_id, approver_id, decision, comment, decision_ts) VALUES (?, ?, ?, ?, GETDATE())",
                (entry_id, approver_id, decision, comment)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
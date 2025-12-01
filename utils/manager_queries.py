# ./utils/manager_queries.py
import pandas as pd
from datetime import date
from lib.db import get_connection, dict_fetchall

# --- Dropdown & Helper Fetchers ---

def fetch_task_types():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT TaskTypeId, TaskTypeName FROM TaskTypes ORDER BY TaskTypeName")
        return dict_fetchall(cur)

def fetch_approver_projects(user_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.project_id, p.project_name FROM projects p
            JOIN project_approvers pa ON p.project_id = pa.project_id
            WHERE pa.user_id = ? ORDER BY p.project_name
        """, (user_id,))
        return dict_fetchall(cur)

def fetch_tasks_by_project_and_type(project_id, type_id):
    with get_connection() as conn:
        cur = conn.cursor()
        sql = """
            SELECT task_id, task_name 
            FROM tasks 
            WHERE project_id = ? AND TaskTypeId = ?
            ORDER BY task_name
        """
        cur.execute(sql, (project_id, type_id))
        return dict_fetchall(cur)

def get_all_employees():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT EmpId, EmpName, SAP_ID FROM Employee ORDER BY EmpName")
        return dict_fetchall(cur)

# --- Task Management ---

def get_tasks_for_manager(user_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        sql = """
            SELECT
                t.task_id, t.task_name, 
                p.project_name, p.project_id,
                tt.TaskTypeName,
                (SELECT COUNT(*) FROM Assignments a WHERE a.task_id = t.task_id) as assignment_count,
                (SELECT SUM(planned_hours) FROM Assignments a WHERE a.task_id = t.task_id) as total_planned_hours
            FROM tasks t
            JOIN projects p ON t.project_id = p.project_id
            LEFT JOIN TaskTypes tt ON t.TaskTypeId = tt.TaskTypeId
            WHERE p.project_id IN (SELECT project_id FROM project_approvers WHERE user_id=?)
            ORDER BY p.project_name, t.task_name
        """
        cur.execute(sql, (user_id,))
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
                    SET task_name=?, project_id=?, TaskTypeId=? 
                    WHERE task_id=?
                """, (data['task_name'], data['project_id'], data['TaskTypeId'], task_id))
            else:
                cur.execute("""
                    INSERT INTO tasks (project_id, task_name, created_by, TaskTypeId, created_at) 
                    VALUES (?, ?, ?, ?, GETDATE());
                """, (data['project_id'], data['task_name'], data['created_by'], data['TaskTypeId']))
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

# --- Assignment Management ---

def get_all_assignments_for_manager(user_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        sql = """
            SELECT
                a.AssignmentId, a.task_id, a.EmpId, 
                a.assignment_name, a.planned_hours, a.start_date, a.end_date, a.status, a.notes,
                t.task_name, tt.TaskTypeName,
                p.project_name, p.project_id,
                e.EmpName, e.SAP_ID
            FROM Assignments a
            JOIN tasks t ON a.task_id = t.task_id
            LEFT JOIN TaskTypes tt ON t.TaskTypeId = tt.TaskTypeId
            JOIN projects p ON t.project_id = p.project_id
            JOIN Employee e ON a.EmpId = e.EmpId
            WHERE p.project_id IN (SELECT project_id FROM project_approvers WHERE user_id=?)
            ORDER BY p.project_name, t.task_name, e.EmpName
        """
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
                    SET EmpId=?, assignment_name=?, planned_hours=?, notes=?, 
                    start_date=?, end_date=?, status=?
                    WHERE AssignmentId=?
                """
                params = (
                    data['EmpId'], data['assignment_name'], int(data['planned_hours']), data['notes'],
                    data['start_date'], data['end_date'], data['status'], aid
                )
                cur.execute(sql, params)
            else:
                sql = """
                    INSERT INTO Assignments (
                        task_id, EmpId, assignment_name, planned_hours, notes, 
                        start_date, end_date, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    data['task_id'], data['EmpId'], data['assignment_name'], int(data['planned_hours']), 
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

# --- Approvals ---

def fetch_submitted_weekly_entries(approver_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT te.entry_id, u.EmpName AS employee_name, p.project_name, t.task_name,
                   te.week_start_date, te.total_hours, te.status
            FROM timesheet_entries te
            JOIN Employee u ON te.user_id = u.EmpId
            JOIN projects p ON te.project_id = p.project_id
            LEFT JOIN tasks t ON te.task_id = t.task_id
            WHERE p.project_id IN (SELECT project_id FROM project_approvers WHERE user_id = ?)
            ORDER BY te.week_start_date DESC, u.EmpName
        """, (approver_id,))
        return dict_fetchall(cur)

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
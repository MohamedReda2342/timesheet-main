import streamlit as st
import mysql.connector
import pandas as pd
import datetime
import altair as alt
from lib import db

# --- Role Enforcement ---
def require_role(allowed_roles):
    if 'role' not in st.session_state:
        st.error("Access denied. Please log in.")
        st.stop()
    if st.session_state.role not in allowed_roles:
        st.error("You are not authorized to view this page.")
        st.stop()

# --- Main Function ---
def employee_dashboard_home():
    require_role(['user', 'admin'])
    user_id = st.session_state.get("user_id")

    conn = db.get_db()
    cursor = conn.cursor(dictionary=True)

    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    last_7_days = today - datetime.timedelta(days=6)

    # --- KPI 1: Total hours logged this week ---
    cursor.execute("""
        SELECT IFNULL(SUM(hours), 0) AS total_hours
        FROM timesheet_entries
        WHERE user_id = %s AND entry_date BETWEEN %s AND %s
    """, (user_id, week_start, today))
    total_hours = cursor.fetchone()['total_hours']

    # --- KPI 2: Approved vs Rejected entries ---
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved,
            SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rejected
        FROM timesheet_entries
        WHERE user_id = %s
    """, (user_id,))
    status_data = cursor.fetchone()
    approved_count = status_data['approved'] or 0
    rejected_count = status_data['rejected'] or 0

    # --- KPI 3: Active projects worked on this month ---
    cursor.execute("""
        SELECT COUNT(DISTINCT project_id) AS active_projects
        FROM timesheet_entries
        WHERE user_id = %s AND entry_date >= %s
    """, (user_id, month_start))
    active_projects = cursor.fetchone()['active_projects']

    # --- Display KPIs ---
    col1, col2, col3 = st.columns(3)
    col1.metric("🕒 Total Hours (This Week)", f"{total_hours:.1f}")
    col2.metric("✅ Approved Entries", approved_count)
    col3.metric("🚫 Rejected Entries", rejected_count)
    st.metric("📁 Active Projects (This Month)", active_projects)

    # --- Bar Chart: Total hours per project (This Month) ---
    cursor.execute("""
        SELECT p.project_name, SUM(t.hours) AS total_hours
        FROM timesheet_entries t
        JOIN projects p ON t.project_id = p.project_id
        WHERE t.user_id = %s AND t.entry_date BETWEEN %s AND %s
        GROUP BY p.project_name
    """, (user_id, month_start, today))
    project_hours = pd.DataFrame(cursor.fetchall())

    if not project_hours.empty:
        bar_chart = alt.Chart(project_hours).mark_bar().encode(
            x=alt.X('project_name', title='Project'),
            y=alt.Y('total_hours', title='Total Hours'),
            color='project_name'
        ).properties(title='Total Hours per Project (This Month)')
        st.altair_chart(bar_chart, use_container_width=True)
    else:
        st.info("No project data available for this month.")

    # --- Line Chart: Hours per day (Last 7 Days) ---
    cursor.execute("""
        SELECT entry_date, SUM(hours) AS total_hours
        FROM timesheet_entries
        WHERE user_id = %s AND entry_date BETWEEN %s AND %s
        GROUP BY entry_date
        ORDER BY entry_date
    """, (user_id, last_7_days, today))
    daily_hours = pd.DataFrame(cursor.fetchall())


    cursor.close()
    conn.close()

# --- Run Page ---
if __name__ == "__main__":
    employee_dashboard_home()

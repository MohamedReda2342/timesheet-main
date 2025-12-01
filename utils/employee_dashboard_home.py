# ./utils/employee_dashboard_home.py

import streamlit as st
import pandas as pd
import datetime
import altair as alt
from lib import employee_queries as eq

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

    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    last_7_days = today - datetime.timedelta(days=6)

    # --- KPI 1: Total hours logged this week ---
    total_hours = eq.get_weekly_hours(user_id, week_start, today)

    # --- KPI 2: Approved vs Rejected entries ---
    status_data = eq.get_entry_status_counts(user_id)
    approved_count = status_data['approved'] or 0
    rejected_count = status_data['rejected'] or 0

    # --- KPI 3: Active projects worked on this month ---
    active_projects = eq.get_active_projects_count(user_id, month_start)

    # --- Display KPIs ---
    col1, col2, col3 = st.columns(3)
    col1.metric("🕒 Total Hours (This Week)", f"{total_hours:.1f}")
    col2.metric("✅ Approved Entries", approved_count)
    col3.metric("🚫 Rejected Entries", rejected_count)
    st.metric("📁 Active Projects (This Month)", active_projects)

    # --- Bar Chart: Total hours per project (This Month) ---
    project_hours_data = eq.get_project_hours_distribution(user_id, month_start, today)
    project_hours = pd.DataFrame(project_hours_data)

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
    daily_hours_data = eq.get_daily_hours_last_7_days(user_id, last_7_days, today)
    daily_hours = pd.DataFrame(daily_hours_data)
    
    if not daily_hours.empty:
         line_chart = alt.Chart(daily_hours).mark_line(point=True).encode(
            x=alt.X('entry_date', title='Date'),
            y=alt.Y('total_hours', title='Hours Logged')
        ).properties(title='Daily Hours (Last 7 Days)')
         st.altair_chart(line_chart, use_container_width=True)

# --- Run Page ---
if __name__ == "__main__":
    employee_dashboard_home()
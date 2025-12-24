# ./views/employee_home.py
import streamlit as st
import pandas as pd
import datetime
import altair as alt
from lib import employee_queries as eq
from lib import auth
from utils.state_helpers import track_page_visit

# Track visit
track_page_visit("employee_home")

# Get User
user = auth.get_current_user()
user_id = user["user_id"]

today = datetime.date.today()
week_start = today - datetime.timedelta(days=today.weekday())
month_start = today.replace(day=1)
last_7_days = today - datetime.timedelta(days=6)

st.title("📊 Dashboard")

col1, col2, col3 = st.columns(3)

total_hours = eq.get_weekly_hours(user_id, week_start, today)
status_data = eq.get_entry_status_counts(user_id)
approved_count = status_data['approved'] or 0
rejected_count = status_data['rejected'] or 0
active_projects = eq.get_active_projects_count(user_id, month_start)

col1.metric("🕒 Hours (This Week)", f"{total_hours:.1f}")
col2.metric("✅ Approved Entries", approved_count)
col3.metric("🚫 Rejected Entries", rejected_count)
st.metric("📁 Active Projects", active_projects)

project_hours_data = eq.get_project_hours_distribution(user_id, month_start, today)
project_hours = pd.DataFrame(project_hours_data)

if not project_hours.empty:
    bar_chart = alt.Chart(project_hours).mark_bar().encode(
        x=alt.X('project_name', title='Project'),
        y=alt.Y('total_hours', title='Total Hours'),
        color='project_name'
    ).properties(title='Hours per Project (This Month)')
    st.altair_chart(bar_chart, use_container_width=True)
else:
    st.info("No project data available for this month.")
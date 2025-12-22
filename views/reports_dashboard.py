# ./views/reports_dashboard.py
import streamlit as st
import pandas as pd
import datetime
import altair as alt
from lib import report_queries as rq
from lib import auth
from utils.state_helpers import track_page_visit

def render(user):
    track_page_visit("reports_dashboard")
    st.title("📈 Reports & Analytics")

    # Access Control
    # Use the passed user object or fetch it if needed
    if not user:
        user = auth.get_current_user()
        
    IS_ADMIN = user.get('role') == 'admin'
    user_id = user['user_id']

    # =========================================================
    # 🔍 Sidebar Filters
    # =========================================================
    st.sidebar.header("Report Filters")
    
    # Date Range
    today = datetime.date.today()
    start_of_month = today.replace(day=1)
    
    start_date = st.sidebar.date_input("Start Date", start_of_month)
    end_date = st.sidebar.date_input("End Date", today)

    # Data Fetchers for Dropdowns
    projects, employees = rq.get_report_filters(user_id, IS_ADMIN)

    # Project Filter
    proj_opts = {p['project_id']: p['project_name'] for p in projects}
    selected_proj_id = st.sidebar.selectbox(
        "Filter by Project", 
        options=["All"] + list(proj_opts.keys()),
        format_func=lambda x: "All Projects" if x == "All" else proj_opts[x]
    )

    # Employee Filter
    emp_opts = {e['EmpId']: e['EmpName'] for e in employees}
    selected_emp_id = st.sidebar.selectbox(
        "Filter by Employee",
        options=["All"] + list(emp_opts.keys()),
        format_func=lambda x: "All Employees" if x == "All" else emp_opts[x]
    )

    if start_date > end_date:
        st.error("Error: Start Date must be before End Date.")
        return

    # =========================================================
    # 📥 Data Fetching
    # =========================================================
    
    # 1. Detailed Data
    details_data = rq.fetch_detailed_timesheet_data(
        start_date, end_date, selected_proj_id, selected_emp_id, user_id, IS_ADMIN
    )
    df_details = pd.DataFrame(details_data)

    # 2. Project Summary Data (For Charts)
    proj_summary = rq.fetch_project_summary(start_date, end_date, user_id, IS_ADMIN)
    df_proj_summary = pd.DataFrame(proj_summary)

    # 3. Status Breakdown
    status_breakdown = rq.fetch_status_breakdown(start_date, end_date, user_id, IS_ADMIN)
    df_status = pd.DataFrame(status_breakdown)

    # =========================================================
    # 📊 Dashboard Tabs
    # =========================================================
    
    tab1, tab2, tab3 = st.tabs(["📊 Executive Summary", "📄 Detailed Report", "📉 Utilization"])

    # --- TAB 1: EXECUTIVE SUMMARY ---
    with tab1:
        # Metrics Row
        total_hours = df_details['total_hours'].sum() if not df_details.empty else 0
        billable_hours = df_details[df_details['is_billable'] == True]['total_hours'].sum() if not df_details.empty else 0
        unique_emps = df_details['EmpName'].nunique() if not df_details.empty else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Hours", f"{total_hours:.1f}")
        c2.metric("Billable Hours", f"{billable_hours:.1f}")
        c3.metric("Utilization", f"{(billable_hours/total_hours*100):.1f}%" if total_hours > 0 else "0%")
        c4.metric("Active Employees", unique_emps)

        st.markdown("---")

        c_chart1, c_chart2 = st.columns(2)
        
        with c_chart1:
            st.subheader("Hours by Project")
            if not df_proj_summary.empty:
                chart_p = alt.Chart(df_proj_summary).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta(field="total_hours", type="quantitative"),
                    color=alt.Color(field="project_name", type="nominal"),
                    tooltip=["project_name", "total_hours"]
                )
                st.altair_chart(chart_p, use_container_width=True)
            else:
                st.info("No data.")

        with c_chart2:
            st.subheader("Status Breakdown")
            if not df_status.empty:
                chart_s = alt.Chart(df_status).mark_bar().encode(
                    x="status",
                    y="total_hours",
                    color="status",
                    tooltip=["status", "entry_count", "total_hours"]
                )
                st.altair_chart(chart_s, use_container_width=True)
            else:
                st.info("No data.")

    # --- TAB 2: DETAILED REPORT ---
    with tab2:
        st.subheader("Detailed Timesheet Entries")
        
        if df_details.empty:
            st.info("No records found for the selected criteria.")
        else:
            # Display Config
            grid_df = df_details[[
                "EmpName", "project_name", "task_name", "TaskTypeName", 
                "week_start_date", "status", "total_hours", "notes"
            ]].copy()
            
            grid_df["week_start_date"] = pd.to_datetime(grid_df["week_start_date"]).dt.date

            st.dataframe(grid_df, use_container_width=True, hide_index=True)
            
            # CSV Download
            csv = grid_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "⬇️ Download CSV",
                csv,
                f"timesheet_report_{start_date}_{end_date}.csv",
                "text/csv",
                key='download-csv'
            )

    # --- TAB 3: UTILIZATION (Task Types) ---
    with tab3:
        st.subheader("Task Type Analysis")
        if not df_details.empty:
            # Group by Task Type
            type_group = df_details.groupby("TaskTypeName")['total_hours'].sum().reset_index()
            
            chart_t = alt.Chart(type_group).mark_bar().encode(
                x=alt.X('total_hours', title='Total Hours'),
                y=alt.Y('TaskTypeName', sort='-x', title='Task Type'),
                color='TaskTypeName',
                tooltip=['TaskTypeName', 'total_hours']
            )
            st.altair_chart(chart_t, use_container_width=True)
            
            st.write("### Billable vs Non-Billable")
            bill_group = df_details.groupby("is_billable")['total_hours'].sum().reset_index()
            bill_group['Type'] = bill_group['is_billable'].map({True: 'Billable', False: 'Non-Billable'})
            
            chart_b = alt.Chart(bill_group).mark_arc().encode(
                theta="total_hours",
                color="Type",
                tooltip=["Type", "total_hours"]
            )
            st.altair_chart(chart_b, use_container_width=True)
            
        else:
            st.info("No data to analyze.")

# --- AUTO-EXECUTION LOGIC ---
# This block is crucial. It runs when Streamlit executes this file as a Page.
if __name__ == "__main__":
    if auth.is_logged_in():
        current_user = auth.get_current_user()
        render(current_user)
    else:
        st.warning("Please login to view reports.")